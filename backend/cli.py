import asyncio
import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

# Add the current directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load env vars
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

from app.agents.planner import planner_agent
# from app.services.supabase import supabase_service # Optional now

async def save_to_file(data: dict):
    """Saves thesis data to a local JSON file."""
    base_dir = "../thesis_data"
    os.makedirs(base_dir, exist_ok=True)
    
    filename = f"{base_dir}/thesis_metadata.json"
    
    # Load existing if present
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            existing = json.load(f)
            existing.update(data)
            data = existing
            
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)
    
    print(f"✅ Saved locally to {filename}")

    # Also save a readable Markdown version
    md_filename = f"{base_dir}/objectives.md"
    with open(md_filename, 'w') as f:
        f.write(f"# Thesis Plan\n\n")
        f.write(f"**Topic:** {data.get('topic')}\n")
        f.write(f"**Case Study:** {data.get('case_study')}\n\n")
        f.write("## Objectives\n")
        for obj in data.get('objectives', []):
            f.write(f"- {obj}\n")
    print(f"✅ Created readable plan at {md_filename}")

async def main():
    print("\n🎓 PhD Thesis Generator - CLI Mode")
    print("===================================\n")
    
    topic = input("Enter Research Topic: ").strip()
    case_study = input("Enter Case Study (e.g., 'South Sudan Ministry of Health'): ").strip()
    
    if not topic:
        print("❌ Topic is required!")
        return

    print(f"\n🧠 Thinking... Generating Draft -> Reviewing -> Refining...")
    
    try:
        result = await planner_agent.generate_objectives(topic, case_study)
        
        print("\n📝 Initial Draft Objectives:")
        print("------------------------")
        for i, obj in enumerate(result["initial"]):
            print(f"{i+1}. {obj}")
            
        print("\n🧐 Review Board Critique:")
        print("------------------------")
        print(result["critique"])
        
        print("\n✅ Final Refined Objectives:")
        print("------------------------")
        for i, obj in enumerate(result["final"]):
            print(f"{i+1}. {obj}")
            
        confirm = input("\n💾 Save these objectives? (y/n): ").strip().lower()
        
        if confirm.startswith('y'):
            data = {
                "topic": topic,
                "case_study": case_study,
                "objectives": result["final"],
                "critique": result["critique"],
                "updated_at": str(datetime.now())
            }
            
            # Try saving to file (Primary for now)
            await save_to_file(data)
            
            # Optional: Try DB
            # try:
            #     response = supabase_service.client.table("thesis").insert(data).execute()
            #     print(f"✅ Saved to Supabase! ID: {response.data[0]['id']}")
            # except Exception as e:
            #     print(f"⚠️ Could not save to DB (Skipping): {e}")
                
        else:
            print("❌ Operation cancelled.")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
