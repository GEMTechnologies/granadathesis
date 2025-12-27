import requests
import json
import os
import uuid
import time
from pathlib import Path

API_URL = "http://localhost:8002"
THESIS_ID = str(uuid.uuid4()) # New test thesis
THESIS_TOPIC = f"Test Thesis {THESIS_ID}"

def verify_objective_store():
    print(f"🧪 Verifying Objective Store for Thesis: {THESIS_ID}")
    
    # 1. Add Objective via API
    print("\n1. Adding Objective via API...")
    resp = requests.post(f"{API_URL}/objectives/{THESIS_ID}/add", json={
        "objective_text": "General Objective: To verify the objective store system.",
        "objective_type": "general"
    })
    print(f"   Status: {resp.status_code}")
    assert resp.status_code == 200
    
    resp = requests.post(f"{API_URL}/objectives/{THESIS_ID}/add", json={
        "objective_text": "Specific Objective 1: To check DB sync.",
        "objective_type": "specific",
        "objective_number": 1
    })
    print(f"   Status: {resp.status_code}")
    assert resp.status_code == 200

    # 2. Verify File Creation
    print("\n2. Verifying File System...")
    # Wait a moment for async save if needed (though API waits)
    time.sleep(1)
    
    file_path = Path(__file__).parent.parent.parent.parent / "thesis_data" / THESIS_ID / "objective_store.json"
    if file_path.exists():
        print("   ✅ objective_store.json exists")
        with open(file_path) as f:
            data = json.load(f)
            print(f"   Content: {json.dumps(data, indent=2)}")
            assert data["general_objective"] == "To verify the objective store system."
            assert len(data["specific_objectives"]) == 1
            assert data["specific_objectives"][0]["text"] == "To check DB sync."
    else:
        print("   ❌ objective_store.json NOT found")
        # Fail if file not found
        assert False, "File not found"

    # 3. Verify API GET (reads from store)
    print("\n3. Verifying API GET (reads from store)...")
    resp = requests.get(f"{API_URL}/objectives/{THESIS_ID}")
    objs = resp.json()
    print(f"   API returned: {json.dumps(objs, indent=2)}")
    assert len(objs) == 2
        
    # 4. Update Objective
    print("\n4. Updating Objective via API...")
    # Note: API might expect "SO1" or UUID depending on implementation.
    # Our API update logic handles "SOx" IDs.
    resp = requests.put(f"{API_URL}/objectives/{THESIS_ID}/SO1", json={
        "objective_text": "Specific Objective 1: To check DB sync UPDATED.",
        "objective_number": 1
    })
    print(f"   Status: {resp.status_code}")
    assert resp.status_code == 200
        
    # 5. Verify Update in File
    print("\n5. Verifying Update in File...")
    with open(file_path) as f:
        data = json.load(f)
        print(f"   Updated Content: {data['specific_objectives'][0]['text']}")
        assert data["specific_objectives"][0]["text"] == "To check DB sync UPDATED."
            
    # 5. Verify Maps Generation
    print("\n5. Verifying Map Generation...")
    time.sleep(2) # Give a moment for async generation
    
    base_dir = Path(__file__).parent.parent.parent.parent / "thesis_data" / THESIS_ID
    theme_map = base_dir / "theme_map.json"
    variable_map = base_dir / "variable_map.json"
    
    if theme_map.exists():
        print("   ✅ theme_map.json exists")
        with open(theme_map) as f:
            print(f"      Content preview: {str(f.read())[:100]}...")
    else:
        print("   ❌ theme_map.json MISSING")

    if variable_map.exists():
        print("   ✅ variable_map.json exists")
        with open(variable_map) as f:
            print(f"      Content preview: {str(f.read())[:100]}...")
    else:
        print("   ❌ variable_map.json MISSING")

    print("\n✅ Verification Complete!")

if __name__ == "__main__":
    verify_objective_store()
