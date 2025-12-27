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


async def save_competition_results(competition_result: dict):
    """Save competition results to organized project folder."""
    # Create safe project name from topic
    topic = competition_result["topic"]
    project_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in topic)
    project_name = "_".join(project_name.split()).lower()[:50]  # Limit length
    
    # Organize: thesis_data/{project_name}/competitions/{competition_id}/
    base_dir = f"../thesis_data/{project_name}/competitions"
    competition_id = competition_result["competition_id"]
    competition_dir = f"{base_dir}/{competition_id}"
    
    os.makedirs(competition_dir, exist_ok=True)
    
    print(f"\n💾 SAVED COMPETITION RESULTS")
    print(f"   Project: {project_name}")
    print(f"   Competition ID: {competition_id}")
    
    # Save full competition data
    full_file = f"{competition_dir}/full_competition.json"
    with open(full_file, 'w') as f:
        json.dump(competition_result, f, indent=2)
    print(f"   ✓ Full data: {full_file}")
    
    # Save winner's objectives separately for easy access
    winner_file = f"{competition_dir}/winner_objectives.json"
    winner_data = {
        "competition_id": competition_id,
        "topic": competition_result["topic"],
        "case_study": competition_result["case_study"],
        "winner_model": competition_result["winner"]["model"],
        "winner_score": competition_result["winner"]["score"],
        "objectives": competition_result["winner"]["objectives"],
        "why_it_won": competition_result["winner"]["why_it_won"],
        "timestamp": competition_result["timestamp"]
    }
    with open(winner_file, 'w') as f:
        json.dump(winner_data, f, indent=2)
    print(f"   ✓ Winner objectives: {winner_file}")
    
    # Create readable markdown report
    md_file = f"{competition_dir}/REPORT.md"
    with open(md_file, 'w') as f:
        f.write(f"# Objective Generation Competition Report\n\n")
        f.write(f"**Competition ID:** `{competition_id}`\n\n")
        f.write(f"**Topic:** {competition_result['topic']}\n\n")
        f.write(f"**Case Study:** {competition_result['case_study']}\n\n")
        if competition_result.get('methodology'):
            f.write(f"**Methodology:** {competition_result['methodology']}\n\n")
        f.write(f"**Date:** {datetime.fromisoformat(competition_result['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Participants:** {', '.join([m.upper() for m in competition_result['participants']])}\n\n")
        f.write("---\n\n")
        
        # Winner section
        winner = competition_result["winner"]
        f.write(f"## 🏆 WINNER: {winner['model'].upper()}\n\n")
        f.write(f"**Score:** {winner['score']}/100\n\n")
        
        f.write(f"### Winning Objectives\n\n")
        for i, obj in enumerate(winner['objectives'], 1):
            f.write(f"{i}. {obj}\n\n")
        
        f.write(f"### Why It Won\n\n")
        for reason in winner['why_it_won']:
            f.write(f"- {reason}\n")
        f.write("\n")
        
        # All submissions
        f.write(f"## 📋 All Submissions\n\n")
        for model, objectives in competition_result['submissions'].items():
            f.write(f"### {model.upper()}\n\n")
            for i, obj in enumerate(objectives, 1):
                f.write(f"{i}. {obj}\n")
            f.write("\n")
        
        # Rankings
        f.write(f"## 📊 Full Rankings\n\n")
        ranking = competition_result["ranking"]
        if "rankings" in ranking:
            for entry in ranking["rankings"]:
                f.write(f"### {entry['rank']}. {entry['model'].upper()} - {entry['score']}/100\n\n")
                
                if entry.get('quality_score') is not None:
                    f.write(f"**Breakdown:**\n")
                    f.write(f"- Quality: {entry.get('quality_score', 0)}/40\n")
                    f.write(f"- Resilience: {entry.get('resilience_score', 0)}/30\n")
                    f.write(f"- Critique Quality: {entry.get('critique_score', 0)}/20\n")
                    f.write(f"- Excellence: {entry.get('excellence_score', 0)}/10\n\n")
                
                f.write(f"**Strengths:**\n")
                for s in entry.get('strengths', []):
                    f.write(f"- {s}\n")
                f.write(f"\n**Weaknesses:**\n")
                for w in entry.get('weaknesses', []):
                    f.write(f"- {w}\n")
                f.write("\n")
        
        # Detailed reasoning
        if "detailed_reasoning" in ranking:
            f.write(f"## 📝 Judge's Detailed Reasoning\n\n")
            f.write(f"{ranking['detailed_reasoning']}\n\n")
        
        # Critique analysis
        if "critique_analysis" in ranking:
            f.write(f"## 🔍 Critique Analysis\n\n")
            for model, analysis in ranking['critique_analysis'].items():
                f.write(f"### {model.upper()}\n\n")
                if 'received' in analysis:
                    f.write(f"**Critiques Received:**\n")
                    for crit in analysis['received']:
                        f.write(f"- {crit}\n")
                    f.write("\n")
                if 'gave' in analysis:
                    f.write(f"**Critiques Given:**\n")
                    for crit in analysis['gave']:
                        f.write(f"- {crit}\n")
                    f.write("\n")
                if 'critique_quality' in analysis:
                    f.write(f"**Critique Quality:** {analysis['critique_quality']}\n\n")
        
        # Lessons learned
        if "lessons_learned" in ranking:
            f.write(f"## 💡 Lessons Learned\n\n")
            for lesson in ranking['lessons_learned']:
                f.write(f"- {lesson}\n")
            f.write("\n")
        
        # Close call note
        if ranking.get('close_call'):
            f.write(f"## ⚖️ Close Call\n\n")
            f.write(f"{ranking['close_call']}\n\n")
    
    print(f"   ✓ Markdown report: {md_file}")
    
    # Create project summary file
    summary_file = f"../thesis_data/{project_name}/PROJECT_INFO.md"
    if not os.path.exists(summary_file):
        with open(summary_file, 'w') as f:
            f.write(f"# Project: {competition_result['topic']}\n\n")
            f.write(f"**Case Study:** {competition_result['case_study']}\n\n")
            if competition_result.get('methodology'):
                f.write(f"**Methodology:** {competition_result['methodology']}\n\n")
            f.write(f"**Created:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")
            f.write("## Competitions\n\n")
            f.write(f"- [{competition_id}](competitions/{competition_id}/REPORT.md) - {datetime.fromisoformat(competition_result['timestamp']).strftime('%Y-%m-%d %H:%M')}\n")
        print(f"   ✓ Project info: {summary_file}")
    else:
        # Append to existing project summary
        with open(summary_file, 'a') as f:
            f.write(f"- [{competition_id}](competitions/{competition_id}/REPORT.md) - {datetime.fromisoformat(competition_result['timestamp']).strftime('%Y-%m-%d %H:%M')}\n")
        print(f"   ✓ Updated project info: {summary_file}")
    
    print(f"\n📁 All files saved to: ../thesis_data/{project_name}/\n")



async def main():
    print("\n🏆 COMPETITIVE MULTI-MODEL OBJECTIVE GENERATION")
    print("=" * 70)
    print("\nThis will run a competition between 4 AI models:")
    print("  • Claude 3.5 Sonnet (academic writing expert)")
    print("  • GPT-4 Turbo (strong reasoning)")
    print("  • DeepSeek Chat (cost-effective)")
    print("  • Gemini 1.5 Pro (strong analysis)")
    print("\nEach model will:")
    print("  1. Generate objectives independently")
    print("  2. Critique all other models' objectives")
    print("  3. Be judged by a central meta-evaluator")
    print("\n" + "=" * 70 + "\n")
    
    topic = input("Enter Research Topic: ").strip()
    case_study = input("Enter Case Study: ").strip()
    
    if not topic:
        print("❌ Topic is required!")
        return
    
    methodology = input("Methodology (Quantitative/Qualitative/Mixed, or leave blank): ").strip()
    if not methodology:
        methodology = None
    
    print(f"\n🚀 Starting competition...\n")
    
    try:
        result = await objective_agent.generate_objectives_competitive(
            topic=topic,
            case_study=case_study,
            methodology=methodology
        )
        
        # Display winner's objectives
        print("\n" + "=" * 70)
        print("🎉 WINNING OBJECTIVES")
        print("=" * 70 + "\n")
        for i, obj in enumerate(result["winner"]["objectives"], 1):
            print(f"{i}. {obj}\n")
        
        # Ask to save
        save = input("\n💾 Save competition results? (y/n): ").strip().lower()
        
        if save.startswith('y'):
            await save_competition_results(result)
            print("\n✅ Competition results saved successfully!")
        else:
            print("\n❌ Results not saved.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
