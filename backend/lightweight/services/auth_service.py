"""
Fast JWT Authentication Service

Token-based authentication with Redis session caching for maximum performance.
No database calls on every request - sessions cached in Redis.
"""

import jwt
import bcrypt
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict
from pydantic import BaseModel

# JWT settings
SECRET_KEY = secrets.token_urlsafe(32)  # Generate random secret on startup
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours


class User(BaseModel):
    user_id: str
    email: str
    username: str
    workspaces: list[str] = []
    created_at: str


class AuthService:
    """High-performance authentication with Redis caching."""
    
    def __init__(self):
        self.cache_ttl = 3600  # 1 hour cache
    
    def hash_password(self, password: str) -> str:
        """Hash password with bcrypt (slow but secure)."""
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash."""
        return bcrypt.checkpw(password.encode(), hashed.encode())
    
    def create_access_token(self, user_id: str, email: str) -> str:
        """
        Create JWT access token.
        
        Token is stateless and contains user info.
        """
        payload = {
            "user_id": user_id,
            "email": email,
            "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """
        Verify JWT token and return payload.
        
        Returns None if invalid/expired.
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    async def register_user(
        self,
        email: str,
        password: str,
        username: str
    ) -> User:
        """
        Register new user.
        
        In production, save to database here.
        For now, returns user object.
        """
        from core.database import db
        
        # Check if email already exists
        existing = await db.fetchrow(
            "SELECT user_id FROM users WHERE email = $1",
            email
        )
        
        if existing:
            raise ValueError("Email already registered")
        
        # Hash password
        password_hash = self.hash_password(password)
        
        # Generate user ID
        user_id = f"user_{secrets.token_urlsafe(16)}"
        
        # Save to database
        await db.execute(
            """
            INSERT INTO users (user_id, email, username, password_hash, created_at)
            VALUES ($1, $2, $3, $4, $5)
            """,
            user_id,
            email,
            username,
            password_hash,
            datetime.utcnow().isoformat()
        )
        
        # Create default workspace for user
        workspace_id = f"{user_id}_default"
        await db.execute(
            """
            INSERT INTO workspaces (workspace_id, owner_user_id, name, created_at)
            VALUES ($1, $2, $3, $4)
            """,
            workspace_id,
            user_id,
            "My Workspace",
            datetime.utcnow().isoformat()
        )
        
        return User(
            user_id=user_id,
            email=email,
            username=username,
            workspaces=[workspace_id],
            created_at=datetime.utcnow().isoformat()
        )
    
    async def login(self, email: str, password: str) -> dict:
        """
        Login user and return access token.
        
        Returns: {token, user}
        """
        from core.database import db
        from core.cache import Cache
        
        # Get user from database
        user_row = await db.fetchrow(
            "SELECT user_id, email, username, password_hash FROM users WHERE email = $1",
            email
        )
        
        if not user_row:
            raise ValueError("Invalid credentials")
        
        # Verify password
        if not self.verify_password(password, user_row['password_hash']):
            raise ValueError("Invalid credentials")
        
        # Get user's workspaces
        workspaces = await db.fetch(
            "SELECT workspace_id FROM workspaces WHERE owner_user_id = $1",
            user_row['user_id']
        )
        
        workspace_ids = [w['workspace_id'] for w in workspaces]
        
        user = User(
            user_id=user_row['user_id'],
            email=user_row['email'],
            username=user_row['username'],
            workspaces=workspace_ids,
            created_at=""  # TODO: Add created_at to query
        )
        
        # Create access token
        token = self.create_access_token(user.user_id, user.email)
        
        # Cache user session in Redis (fast lookups!)
        await Cache.set(
            f"session:{user.user_id}",
            user.dict(),
            ttl=self.cache_ttl
        )
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": user.dict()
        }
    
    async def get_current_user(self, token: str) -> Optional[User]:
        """
        Get current user from token.
        
        Uses Redis cache for fast lookups (no DB query on every request!).
        """
        from core.cache import Cache
        
        # Verify token
        payload = self.verify_token(token)
        if not payload:
            return None
        
        user_id = payload.get('user_id')
        
        # Check cache first (FAST!)
        cached_user = await Cache.get(f"session:{user_id}")
        if cached_user:
            return User(**cached_user)
       
        # Fallback: fetch from database
        from core.database import db
        
        user_row = await db.fetchrow(
            "SELECT user_id, email, username, created_at FROM users WHERE user_id = $1",
            user_id
        )
        
        if not user_row:
            return None
        
        # Get workspaces
        workspaces = await db.fetch(
            "SELECT workspace_id FROM workspaces WHERE owner_user_id = $1",
            user_id
        )
        
        user = User(
            user_id=user_row['user_id'],
            email=user_row['email'],
            username=user_row['username'],
            workspaces=[w['workspace_id'] for w in workspaces],
            created_at=user_row['created_at']
        )
        
        # Cache for next time
        await Cache.set(
            f"session:{user_id}",
            user.dict(),
            ttl=self.cache_ttl
        )
        
        return user
    
    async def create_workspace(self, user_id: str, workspace_name: str) -> str:
        """Create new workspace for user."""
        from core.database import db
        
        workspace_id = f"{user_id}_{secrets.token_urlsafe(8)}"
        
        await db.execute(
            """
            INSERT INTO workspaces (workspace_id, owner_user_id, name, created_at)
            VALUES ($1, $2, $3, $4)
            """,
            workspace_id,
            user_id,
            workspace_name,
            datetime.utcnow().isoformat()
        )
        
        # Invalidate user cache (force refresh)
        from core.cache import Cache
        await Cache.delete(f"session:{user_id}")
        
        return workspace_id


# Singleton
auth_service = AuthService()
