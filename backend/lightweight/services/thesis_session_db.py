"""
Thesis Session Database - Persistent storage for thesis generation
Stores objectives, research papers, themes, and cross-chapter data
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

# Database path
DB_PATH = Path(__file__).parent.parent / "data" / "thesis_sessions.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_connection():
    """Get database connection."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database tables."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS thesis_sessions (
            id TEXT PRIMARY KEY,
            topic TEXT NOT NULL,
            case_study TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Objectives table - stores Chapter 1 objectives for Chapter 2
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS objectives (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            objective_type TEXT NOT NULL,  -- 'general', 'specific_1', 'specific_2', etc.
            objective_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES thesis_sessions(id)
        )
    """)
    
    # Research questions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS research_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            question_number INTEGER,
            question_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES thesis_sessions(id)
        )
    """)
    
    # Papers table - all discovered papers
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS papers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            title TEXT NOT NULL,
            authors TEXT,  -- JSON array
            year INTEGER,
            abstract TEXT,
            doi TEXT,
            url TEXT,
            source TEXT,  -- 'openalex', 'crossref', 'semantic_scholar', etc.
            scope TEXT,  -- 'global', 'regional', 'theme1', 'theory', etc.
            cited_in TEXT,  -- JSON array of section IDs where cited
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES thesis_sessions(id),
            UNIQUE(session_id, doi)
        )
    """)
    
    # Themes table - maps objectives to literature themes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS themes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            theme_number INTEGER NOT NULL,
            theme_title TEXT NOT NULL,
            related_objective TEXT,  -- Which objective this theme addresses
            search_queries TEXT,  -- JSON array of search queries
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES thesis_sessions(id)
        )
    """)
    
    # Theories table - stores selected theories
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS theories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            theory_name TEXT NOT NULL,
            related_objective TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES thesis_sessions(id)
        )
    """)
    
    # Generated sections table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            chapter_number INTEGER NOT NULL,
            section_id TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            word_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',  -- 'pending', 'generating', 'complete'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES thesis_sessions(id),
            UNIQUE(session_id, section_id)
        )
    """)
    
    conn.commit()
    conn.close()


class ThesisSessionDB:
    """Database operations for thesis sessions."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        init_db()
    
    # ============ SESSION OPERATIONS ============
    
    def create_session(self, topic: str, case_study: str = "") -> str:
        """Create or update a thesis session."""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO thesis_sessions (id, topic, case_study, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (self.session_id, topic, case_study))
        
        conn.commit()
        conn.close()
        return self.session_id
    
    def get_session(self) -> Optional[Dict]:
        """Get session details."""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM thesis_sessions WHERE id = ?", (self.session_id,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    def get_topic(self) -> Optional[str]:
        """Get the topic for this session."""
        session = self.get_session()
        if session:
            return session.get("topic")
        return None
    
    def get_case_study(self) -> Optional[str]:
        """Get the case study for this session."""
        session = self.get_session()
        if session:
            return session.get("case_study")
        return None
    
    # ============ OBJECTIVES OPERATIONS ============
    
    def save_objectives(self, general: str, specific: List[str]):
        """Save objectives from Chapter 1."""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Clear existing objectives
        cursor.execute("DELETE FROM objectives WHERE session_id = ?", (self.session_id,))
        
        # Save general objective
        cursor.execute("""
            INSERT INTO objectives (session_id, objective_type, objective_text)
            VALUES (?, 'general', ?)
        """, (self.session_id, general))
        
        # Save specific objectives
        for i, obj in enumerate(specific, 1):
            cursor.execute("""
                INSERT INTO objectives (session_id, objective_type, objective_text)
                VALUES (?, ?, ?)
            """, (self.session_id, f'specific_{i}', obj))
        
        conn.commit()
        conn.close()
    
    def get_objectives(self) -> Dict[str, Any]:
        """Get all objectives."""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT objective_type, objective_text 
            FROM objectives WHERE session_id = ?
            ORDER BY objective_type
        """, (self.session_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        result = {"general": "", "specific": []}
        for row in rows:
            if row["objective_type"] == "general":
                result["general"] = row["objective_text"]
            else:
                result["specific"].append(row["objective_text"])
        
        return result
    
    # ============ RESEARCH QUESTIONS ============
    
    def save_questions(self, questions: List[str]):
        """Save research questions."""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM research_questions WHERE session_id = ?", (self.session_id,))
        
        for i, q in enumerate(questions, 1):
            cursor.execute("""
                INSERT INTO research_questions (session_id, question_number, question_text)
                VALUES (?, ?, ?)
            """, (self.session_id, i, q))
        
        conn.commit()
        conn.close()
    
    def get_questions(self) -> List[str]:
        """Get research questions."""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT question_text FROM research_questions 
            WHERE session_id = ? ORDER BY question_number
        """, (self.session_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [row["question_text"] for row in rows]
    
    # ============ PAPERS OPERATIONS ============
    
    def save_paper(self, paper: Dict, scope: str = "global") -> int:
        """Save a research paper."""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO papers 
                (session_id, title, authors, year, abstract, doi, url, source, scope)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.session_id,
                paper.get("title", ""),
                json.dumps(paper.get("authors", [])),
                paper.get("year"),
                paper.get("abstract", ""),
                paper.get("doi", ""),
                paper.get("url", ""),
                paper.get("source", "unknown"),
                scope
            ))
            conn.commit()
            paper_id = cursor.lastrowid
        except Exception as e:
            print(f"Error saving paper: {e}")
            paper_id = 0
        finally:
            conn.close()
        
        return paper_id
    
    def get_papers_by_scope(self, scope: str) -> List[Dict]:
        """Get papers by scope."""
        conn = get_connection()
        cursor = conn.cursor()
        
        if scope == "all":
            cursor.execute("SELECT * FROM papers WHERE session_id = ?", (self.session_id,))
        else:
            cursor.execute("""
                SELECT * FROM papers WHERE session_id = ? AND scope = ?
            """, (self.session_id, scope))
        
        rows = cursor.fetchall()
        conn.close()
        
        papers = []
        for row in rows:
            paper = dict(row)
            paper["authors"] = json.loads(paper["authors"]) if paper["authors"] else []
            papers.append(paper)
        
        return papers
    
    def get_all_papers(self) -> List[Dict]:
        """Get all papers for session."""
        return self.get_papers_by_scope("all")
    
    def get_paper_count(self) -> int:
        """Get total paper count."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM papers WHERE session_id = ?", (self.session_id,))
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    # ============ THEMES OPERATIONS ============
    
    def save_themes(self, themes: List[Dict]):
        """Save literature themes mapped to objectives."""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM themes WHERE session_id = ?", (self.session_id,))
        
        for theme in themes:
            cursor.execute("""
                INSERT INTO themes 
                (session_id, theme_number, theme_title, related_objective, search_queries)
                VALUES (?, ?, ?, ?, ?)
            """, (
                self.session_id,
                theme.get("number", 1),
                theme.get("title", ""),
                theme.get("objective", ""),
                json.dumps(theme.get("queries", []))
            ))
        
        conn.commit()
        conn.close()
    
    def get_themes(self) -> List[Dict]:
        """Get all themes."""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM themes WHERE session_id = ? ORDER BY theme_number
        """, (self.session_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        themes = []
        for row in rows:
            theme = dict(row)
            theme["queries"] = json.loads(theme["search_queries"]) if theme["search_queries"] else []
            themes.append(theme)
        
        return themes
    
    # ============ THEORIES OPERATIONS ============
    
    def save_theories(self, theories: List[str], related_objectives: List[str] = None):
        """Save selected theories."""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM theories WHERE session_id = ?", (self.session_id,))
        
        for i, theory in enumerate(theories):
            obj = related_objectives[i] if related_objectives and i < len(related_objectives) else ""
            cursor.execute("""
                INSERT INTO theories (session_id, theory_name, related_objective)
                VALUES (?, ?, ?)
            """, (self.session_id, theory, obj))
        
        conn.commit()
        conn.close()
    
    def get_theories(self) -> List[str]:
        """Get selected theories."""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT theory_name FROM theories WHERE session_id = ?", (self.session_id,))
        rows = cursor.fetchall()
        conn.close()
        
        return [row["theory_name"] for row in rows]
    
    # ============ SECTIONS OPERATIONS ============
    
    def save_section(self, chapter: int, section_id: str, title: str, content: str = "", status: str = "pending"):
        """Save a generated section."""
        conn = get_connection()
        cursor = conn.cursor()
        
        word_count = len(content.split()) if content else 0
        
        cursor.execute("""
            INSERT OR REPLACE INTO sections 
            (session_id, chapter_number, section_id, title, content, word_count, status, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (self.session_id, chapter, section_id, title, content, word_count, status))
        
        conn.commit()
        conn.close()
    
    def get_chapter_sections(self, chapter: int) -> List[Dict]:
        """Get all sections for a chapter."""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM sections WHERE session_id = ? AND chapter_number = ?
            ORDER BY section_id
        """, (self.session_id, chapter))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_total_word_count(self) -> int:
        """Get total word count across all sections."""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT SUM(word_count) FROM sections WHERE session_id = ?
        """, (self.session_id,))
        
        result = cursor.fetchone()[0]
        conn.close()
        
        return result or 0


# Initialize database on import
init_db()
