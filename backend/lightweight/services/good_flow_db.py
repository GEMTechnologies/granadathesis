"""Local DB for /good flow configurations."""

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional


def _db_path() -> Path:
    base_dir = Path(__file__).resolve().parents[3]
    good_dir = base_dir / "good"
    good_dir.mkdir(parents=True, exist_ok=True)
    return good_dir / "good.db"


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_db_path()))
    conn.row_factory = sqlite3.Row
    return conn


def init_good_db() -> None:
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS good_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workspace_id TEXT,
            session_id TEXT,
            topic TEXT NOT NULL,
            country TEXT,
            case_study TEXT,
            objectives TEXT,
            uploaded_materials TEXT,
            literature_year_start INTEGER,
            literature_year_end INTEGER,
            study_type TEXT,
            population TEXT,
            extra_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def save_good_config(config: Dict[str, Any]) -> Dict[str, Any]:
    init_good_db()
    conn = _get_conn()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO good_configs (
            workspace_id,
            session_id,
            topic,
            country,
            case_study,
            objectives,
            uploaded_materials,
            literature_year_start,
            literature_year_end,
            study_type,
            population,
            extra_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            config.get("workspace_id"),
            config.get("session_id"),
            config.get("topic"),
            config.get("country"),
            config.get("case_study"),
            json.dumps(config.get("objectives") or []),
            json.dumps(config.get("uploaded_materials") or []),
            config.get("literature_year_start"),
            config.get("literature_year_end"),
            config.get("study_type"),
            config.get("population"),
            json.dumps(config.get("extra") or {}),
        ),
    )

    conn.commit()
    row_id = cursor.lastrowid
    conn.close()

    return {"id": row_id, **config}


def get_latest_good_config(workspace_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    init_good_db()
    conn = _get_conn()
    cursor = conn.cursor()

    if workspace_id:
        cursor.execute(
            """
            SELECT * FROM good_configs
            WHERE workspace_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (workspace_id,),
        )
    else:
        cursor.execute(
            """
            SELECT * FROM good_configs
            ORDER BY created_at DESC
            LIMIT 1
            """
        )

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    result = dict(row)
    for key in ["objectives", "uploaded_materials", "extra_json"]:
        try:
            result[key] = json.loads(result.get(key) or "[]")
        except json.JSONDecodeError:
            pass
    return result


def get_good_config_by_id(config_id: int) -> Optional[Dict[str, Any]]:
    init_good_db()
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM good_configs
        WHERE id = ?
        LIMIT 1
        """,
        (config_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    result = dict(row)
    for key in ["objectives", "uploaded_materials", "extra_json"]:
        try:
            result[key] = json.loads(result.get(key) or "[]")
        except json.JSONDecodeError:
            pass
    return result


def update_good_objectives(
    config_id: int,
    objectives: list,
    general_objective: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    init_good_db()
    existing = get_good_config_by_id(config_id) or {}
    extra = existing.get("extra_json") or {}
    if isinstance(extra, str):
        try:
            extra = json.loads(extra)
        except json.JSONDecodeError:
            extra = {}
    extra["generated_objectives"] = objectives
    if general_objective:
        extra["generated_general_objective"] = general_objective
    user_objectives = extra.get("user_objectives") or []
    objectives_to_store = user_objectives if user_objectives else objectives

    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE good_configs
        SET objectives = ?, extra_json = ?
        WHERE id = ?
        """,
        (
            json.dumps(objectives_to_store or []),
            json.dumps(extra),
            config_id,
        ),
    )
    conn.commit()
    conn.close()
    return get_good_config_by_id(config_id)


def update_good_research_metadata(config_id: Optional[int], metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not config_id:
        return None
    init_good_db()
    existing = get_good_config_by_id(config_id) or {}
    extra = existing.get("extra_json") or {}
    if isinstance(extra, str):
        try:
            extra = json.loads(extra)
        except json.JSONDecodeError:
            extra = {}
    research_meta = extra.get("research") or {}
    if isinstance(research_meta, str):
        try:
            research_meta = json.loads(research_meta)
        except json.JSONDecodeError:
            research_meta = {}
    research_meta.update(metadata or {})
    extra["research"] = research_meta

    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE good_configs
        SET extra_json = ?
        WHERE id = ?
        """,
        (json.dumps(extra), config_id),
    )
    conn.commit()
    conn.close()
    return get_good_config_by_id(config_id)


def update_good_status(config_id: Optional[int], updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not config_id:
        return None
    init_good_db()
    existing = get_good_config_by_id(config_id) or {}
    extra = existing.get("extra_json") or {}
    if isinstance(extra, str):
        try:
            extra = json.loads(extra)
        except json.JSONDecodeError:
            extra = {}
    status = extra.get("status") or {}
    if isinstance(status, str):
        try:
            status = json.loads(status)
        except json.JSONDecodeError:
            status = {}
    status.update(updates or {})
    extra["status"] = status

    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE good_configs
        SET extra_json = ?
        WHERE id = ?
        """,
        (json.dumps(extra), config_id),
    )
    conn.commit()
    conn.close()
    return get_good_config_by_id(config_id)
