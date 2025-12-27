"""
Authentication API Endpoints

Fast JWT-based auth with Redis session caching.
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr
from typing import Optional

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    username: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict

class UserResponse(BaseModel):
    user_id: str
    email: str
    username: str
    workspaces: list[str]

# ============================================================================
# DEPENDENCY: Get current user from token
# ============================================================================

async def get_current_user_from_token(authorization: Optional[str] = Header(None)):
    """Extract and verify JWT token from Authorization header."""
    from services.auth_service import auth_service
    
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.replace("Bearer ", "")
    user = await auth_service.get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return user

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/register", response_model=LoginResponse)
async def register(request: RegisterRequest):
    """
    Register new user.
    
    Creates user account and default workspace.
    Returns access token for immediate login.
    """
    from services.auth_service import auth_service
    
    try:
        user = await auth_service.register_user(
            email=request.email,
            password=request.password,
            username=request.username
        )
        
        # Auto-login after registration
        token = auth_service.create_access_token(user.user_id, user.email)
        
        return LoginResponse(
            access_token=token,
            token_type="bearer",
            user=user.dict()
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
       raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Login with email and password.
    
    Returns JWT access token and user info.
    Session cached in Redis for fast subsequent requests.
    """
    from services.auth_service import auth_service
    
    try:
        result = await auth_service.login(request.email, request.password)
        return LoginResponse(**result)
    
    except ValueError as e:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


@router.get("/me", response_model=UserResponse)
async def get_current_user(current_user = Depends(get_current_user_from_token)):
    """
    Get current authenticated user info.
    
    Ultra-fast: cached in Redis, no database query.
    """
    return UserResponse(**current_user.dict())


@router.post("/workspace/create")
async def create_workspace(
    workspace_name: str,
    current_user = Depends(get_current_user_from_token)
):
    """Create new workspace for current user."""
    from services.auth_service import auth_service
    
    try:
        workspace_id = await auth_service.create_workspace(
            user_id=current_user.user_id,
            workspace_name=workspace_name
        )
        
        return {
            "status": "success",
            "workspace_id": workspace_id,
            "name": workspace_name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/logout")
async def logout(current_user = Depends(get_current_user_from_token)):
    """
    Logout current user.
    
    Invalidates session cache.
    """
    from core.cache import Cache
    
    await Cache.delete(f"session:{current_user.user_id}")
    
    return {"status": "logged_out"}
