"""
Objective Store - The Central Brain of the Thesis System.

This module manages the single source of truth for thesis objectives,
syncing between:
1. Database (JSONB column in 'thesis' table)
2. File System (objective_store.json)
3. In-memory cache
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio

from core.database import db

class ObjectiveStore:
    """
    Centralized manager for thesis objectives.
    Ensures all agents and UI see the same data.
    """
    
    def __init__(self, thesis_id: str):
        self.thesis_id = thesis_id
        # Determine paths
        # Assuming thesis_id is a UUID or workspace ID. 
        # We need to resolve the directory path.
        # For now, we assume THESIS_DATA_DIR is available or passed in.
        self.base_dir = Path(__file__).parent.parent.parent.parent / "thesis_data" / thesis_id
        self.store_path = self.base_dir / "objective_store.json"
        
    async def load(self) -> Dict[str, Any]:
        """
        Load the objective store.
        Priority: DB -> File -> Empty Default
        """
        # 1. Try DB first (Most authoritative)
        try:
            row = await db.fetchrow(
                "SELECT objective_store FROM thesis WHERE id::text = $1 OR topic = $2", 
                self.thesis_id, self.thesis_id
            )
            if row and row.get('objective_store') and row['objective_store'] != {}:
                # Found in DB
                store = json.loads(row['objective_store']) if isinstance(row['objective_store'], str) else row['objective_store']
                # Sync to file just in case
                self._save_to_file(store)
                return store
        except Exception as e:
            print(f"⚠️ Error loading from DB: {e}")

        # 2. Try File
        if self.store_path.exists():
            try:
                with open(self.store_path, 'r') as f:
                    store = json.load(f)
                # Sync back to DB if DB was empty/failed
                await self._save_to_db(store)
                return store
            except Exception as e:
                print(f"⚠️ Error loading from file: {e}")
        
        # 3. Return Default Structure
        return self._create_default_structure()

    async def save(self, store_data: Dict[str, Any]):
        """
        Save the objective store to both DB and File.
        """
        # Update metadata
        store_data['last_updated'] = datetime.utcnow().isoformat()
        store_data['version'] = store_data.get('version', 0) + 1
        
        # 1. Save to File
        self._save_to_file(store_data)
        
        # 2. Save to DB
        await self._save_to_db(store_data)
        
    def _save_to_file(self, data: Dict[str, Any]):
        """Helper to save to JSON file."""
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            with open(self.store_path, 'w') as f:
                json.dump(data, f, indent=4, default=str)
        except Exception as e:
            print(f"❌ Error saving objective store to file: {e}")
            raise

    async def _save_to_db(self, data: Dict[str, Any]):
        """Helper to save to DB JSONB column."""
        try:
            # We need to find the thesis UUID first
            row = await db.fetchrow(
                "SELECT id FROM thesis WHERE id::text = $1 OR topic = $2", 
                self.thesis_id, self.thesis_id
            )
            
            if row:
                # Update existing
                await db.execute(
                    "UPDATE thesis SET objective_store = $1, updated_at = timezone('utc', now()) WHERE id = $2",
                    json.dumps(data, default=str), row['id']
                )
            else:
                # Create new thesis record if strictly necessary, 
                # but usually thesis should exist by now.
                # If not, we might be in a weird state, but let's try to insert.
                import uuid
                new_id = uuid.uuid4()
                await db.execute(
                    """
                    INSERT INTO thesis (id, topic, objective_store, created_at, updated_at)
                    VALUES ($1, $2, $3, timezone('utc', now()), timezone('utc', now()))
                    """,
                    new_id, self.thesis_id, json.dumps(data, default=str)
                )
        except Exception as e:
            print(f"❌ Error saving objective store to DB: {e}")
            raise

    def _create_default_structure(self) -> Dict[str, Any]:
        """Create the empty skeleton of the store."""
        return {
            "thesis_id": self.thesis_id,
            "general_objective": "",
            "specific_objectives": [],
            "scope": "",
            "assumptions": [],
            "key_terms": {},
            "version": 1,
            "last_updated": datetime.utcnow().isoformat()
        }

    @staticmethod
    def convert_legacy_list(objectives_list: List[str]) -> Dict[str, Any]:
        """
        Convert a flat list of strings (legacy format) into the structured store format.
        """
        store = {
            "general_objective": "",
            "specific_objectives": [],
            "version": 1,
            "last_updated": datetime.utcnow().isoformat()
        }
        
        import re
        
        for obj in objectives_list:
            if "General Objective" in obj or obj.startswith("General"):
                text = obj.split(":", 1)[1].strip() if ":" in obj else obj
                store["general_objective"] = text
            else:
                # Specific
                text = obj.split(":", 1)[1].strip() if ":" in obj else obj
                # Try to extract number
                match = re.search(r'Specific Objective (\d+)', obj)
                num = match.group(1) if match else str(len(store["specific_objectives"]) + 1)
                
                store["specific_objectives"].append({
                    "id": f"SO{num}",
                    "text": text,
                    "research_question": "",
                    "hypothesis": "",
                    "variables": {}
                })
                
        return store
