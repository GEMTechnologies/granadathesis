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

from app.agents.objective import objective_agent

async def save_objectives(topic: str, case_study: str, objectives: list, critique: str):
    """Saves objectives to a dedicated file."""
    base_dir = "../thesis_data"
    os.makedirs(base_dir, exist_ok=True)
    
    # Save as JSON
    objectives_file = f"{base_dir}/objectives.json"
    data = {
        "topic": topic,
        "case_study": case_study,
        "objectives": objectives,
        "critique": critique,
        "generated_at": str(datetime.now())
    }
    
    with open(objectives_file, 'w') as f:
        json.dump(data, f, indent=4)
    
    print(f"✅ Saved to {objectives_file}")
    
    # Save as readable Markdown
    md_file = f"{base_dir}/objectives.md"
    with open(md_file, 'w') as f:
        f.write(f"# Research Objectives\n\n")
        f.write(f"**Topic:** {topic}\n\n")
        f.write(f"**Case Study:** {case_study}\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write("---\n\n")
        f.write("## Final Objectives\n\n")
        for i, obj in enumerate(objectives, 1):
            f.write(f"{i}. {obj}\n\n")
    
    print(f"✅ Created readable version at {md_file}")

async def main():
    print("\n🎓 PhD Thesis Objectives Generator")
    print("===================================\n")
    
    topic = input("Enter Research Topic: ").strip()
    case_study = input("Enter Case Study: ").strip()
    
    if not topic:
        print("❌ Topic is required!")
        return

    print(f"\n🧠 Generating objectives...\n")
    
    try:
        result = await objective_agent.generate_objectives(topic, case_study)
        
        print("\n📝 Initial Draft:")
        print("─" * 50)
        for i, obj in enumerate(result["initial"], 1):
            print(f"{i}. {obj}")
            
        print("\n\n🧐 Review Board Critique:")
        print("─" * 50)
        print(result["critique"])
        
        print("\n\n✅ Final Refined Objectives:")
        print("─" * 50)
        for i, obj in enumerate(result["final"], 1):
            print(f"{i}. {obj}")
            
        print("\n")
        confirm = input("💾 Save these objectives? (y/n): ").strip().lower()
        
        if confirm.startswith('y'):
            await save_objectives(topic, case_study, result["final"], result["critique"])
        else:
            print("❌ Not saved.")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
