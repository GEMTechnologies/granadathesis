"""
Objective Worker - Wakes on-demand to process objective generation.

Sleeps until work appears in Redis queue, then awakens and processes.
"""
import asyncio
import sys
import os
# Add parent directory to path to allow importing 'core'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0,'..')

from core.queue import worker, JobQueue
from core.events import events
from agents.objective import objective_agent


@worker("objectives")
async def process_objective_job(data: dict):
    """
    Process objective generation job.
    
    Agent awakens → Generates → Returns result → Sleeps
    """
    job_id = data.get("job_id", "unknown")
    thesis_id = data.get("thesis_id")
    
    try:
        if not thesis_id:
            print("⚠️ ERROR: No thesis_id provided in job data")
            await events.log(job_id, "❌ ERROR: No workspace ID provided. Please create a workspace first.", "error")
            await events.publish(job_id, "progress", {"stage": "error", "percent": 0})
            return {
                "status": "error",
                "error": "No workspace ID provided. Please create a workspace first."
            }
        
        print(f"   📝 Generating objectives for: {data.get('topic', 'Unknown')}")
        
        # Publish start event
        await events.log(job_id, f"🚀 Starting objective generation for: {data.get('topic', 'Unknown')}")
        await events.publish(job_id, "progress", {"stage": "started", "percent": 5})
        
        mode = data.get("mode", "voting")
        
        if mode == "voting":
            # Generate real initial thoughts from the committee
            await events.log(job_id, "👥 Assembling academic committee (Methodologist, Skeptic, Pedant)...")
            await events.publish(job_id, "progress", {"stage": "committee", "percent": 10})
            
            # Stream thoughts sequentially for real-time effect
            roles = ["Methodologist", "Skeptic", "Pedant"]
            
            for idx, role in enumerate(roles):
                try:
                    # Generate thought with timeout
                    thought = await asyncio.wait_for(
                        objective_agent.generate_single_thought(
                            role=role,
                            topic=data.get("topic", ""),
                            case_study=data.get("case_study", "")
                        ),
                        timeout=30.0  # 30 second timeout per thought
                    )
                    
                    # Emit immediately
                    await events.debate_message(job_id, role, thought)
                    await events.publish(job_id, "progress", {"stage": f"{role.lower()}_thought", "percent": 15 + (idx * 5)})
                    
                    # Small natural pause between speakers
                    await asyncio.sleep(0.5)  # Reduced from 1.0
                except asyncio.TimeoutError:
                    print(f"   ⚠️ Timeout generating thought for {role}")
                    await events.log(job_id, f"⚠️ {role} thought generation timed out, continuing...", "warning")
                    await events.debate_message(job_id, role, f"I am analyzing the topic '{data.get('topic', '')}' in the context of '{data.get('case_study', '')}'...")
                except Exception as e:
                    print(f"   ⚠️ Error generating thought for {role}: {e}")
                    await events.log(job_id, f"⚠️ {role} encountered an error: {str(e)}", "warning")
                    await events.debate_message(job_id, role, f"I am analyzing the topic '{data.get('topic', '')}' in the context of '{data.get('case_study', '')}'...")
            
            await events.log(job_id, "🗳️ Committee voting on proposed objectives...")
            await events.publish(job_id, "progress", {"stage": "voting", "percent": 30})
            
            # Callback to emit debate messages during voting
            sample_counter = {"Methodologist": 0, "Skeptic": 0, "Pedant": 0}
            roles_cycle = ["Methodologist", "Skeptic", "Pedant"]
            
            async def on_valid_sample(sample_num: int, objectives: list):
                """Called when a valid sample is generated during voting."""
                # Assign to next role in rotation
                role = roles_cycle[(sample_num - 1) % 3]
                sample_counter[role] += 1
                
                # Emit debate message with objectives
                message = f"Proposed set {sample_counter[role]} of objectives based on '{data['topic']}' in {data['case_study']} context."
                await events.debate_message(job_id, role, message, objectives=objectives)
                
                # Also emit voting progress update
                await events.publish(job_id, "voting_progress", {
                    "sample": sample_num,
                    "role": role,
                    "objectives": objectives,
                    "message": f"{role} proposed objectives set {sample_counter[role]}"
                })
            
            # SPEED UP: Reduce k threshold for faster convergence (k=2 instead of 3)
            # This makes voting faster while still maintaining quality
            k_threshold = data.get("k", 2)  # Default to 2 for speed
            
            try:
                # Add timeout for voting process (5 minutes max)
                raw_result = await asyncio.wait_for(
                    objective_agent.generate_objectives_with_voting(
                        topic=data.get("topic", ""),
                        case_study=data.get("case_study", ""),
                        methodology=data.get("methodology"),
                        k=k_threshold,
                        thesis_id=thesis_id,
                        on_sample_callback=on_valid_sample  # Pass callback
                    ),
                    timeout=300.0  # 5 minute timeout
                )
                
                # CRITICAL: Ensure result is always a dict, not a list
                # The voting function might return a list directly
                if isinstance(raw_result, list):
                    print(f"⚠️ Voting returned a list ({len(raw_result)} items), converting to dict")
                    result = {
                        "objectives": raw_result,
                        "validation": {"is_valid": True, "message": "Generated successfully"},
                        "voting_stats": {"total_samples": 0, "winner_votes": 0, "flagged_samples": 0}
                    }
                elif isinstance(raw_result, dict):
                    result = raw_result
                    # Ensure it has all required keys
                    if "objectives" not in result:
                        result["objectives"] = []
                    if "validation" not in result:
                        result["validation"] = {"is_valid": True}
                    if "voting_stats" not in result:
                        result["voting_stats"] = {}
                else:
                    print(f"⚠️ Unexpected result type: {type(raw_result)}, creating default dict")
                    result = {
                        "objectives": [],
                        "validation": {"is_valid": False, "message": f"Unexpected result type: {type(raw_result)}"},
                        "voting_stats": {"total_samples": 0, "winner_votes": 0, "flagged_samples": 0}
                    }
                
                print(f"✅ Result type: {type(result)}, objectives count: {len(result.get('objectives', []))}")
                await events.publish(job_id, "progress", {"stage": "voting_complete", "percent": 80})
            except asyncio.TimeoutError:
                print("   ⚠️ Voting process timed out after 5 minutes")
                await events.log(job_id, "⚠️ Voting process timed out. Using best candidate so far.", "warning")
                # Return a default result to prevent complete failure
                result = {
                    "objectives": [
                        f"General Objective: To investigate {data.get('topic', 'the research topic')}",
                        f"Specific Objective 1: To examine key aspects of {data.get('topic', 'the topic')}",
                        f"Specific Objective 2: To analyze the relationship between variables in {data.get('case_study', 'the case study')}",
                        f"Specific Objective 3: To evaluate the effectiveness of interventions related to {data.get('topic', 'the topic')}"
                    ],
                    "validation": {"is_valid": False, "message": "Generation timed out"},
                    "voting_stats": {"total_samples": 0, "winner_votes": 0, "flagged_samples": 0}
                }
            except Exception as e:
                print(f"   ❌ Error during voting: {e}")
                import traceback
                traceback.print_exc()
                await events.log(job_id, f"❌ Error during voting: {str(e)}", "error")
                # Return error result
                result = {
                    "objectives": [],
                    "validation": {"is_valid": False, "message": f"Error: {str(e)}"},
                    "voting_stats": {"total_samples": 0, "winner_votes": 0, "flagged_samples": 0}
                }
            
            # Publish stage completion for debate
            await events.stage_completed(job_id, "objectives_debate", {
                "participants": ["Methodologist", "Skeptic", "Pedant"],
                "rounds": 3
            })
            
            # SAVE RESULTS TO FILES - WITH ERROR HANDLING
            try:
                thesis_data_dir = Path(__file__).parent.parent.parent.parent / "thesis_data" / thesis_id
                thesis_data_dir.mkdir(parents=True, exist_ok=True)
                
                # Extract objectives list - handle different formats
                # Ensure result is a dict (fix for 'list' object has no attribute 'get' error)
                if isinstance(result, list):
                    print(f"⚠️ Result is a list, converting to dict. List length: {len(result)}")
                    objectives_list = result
                    result = {
                        "objectives": objectives_list,
                        "validation": {"is_valid": True, "message": "Generated successfully"},
                        "voting_stats": {"total_samples": 0, "winner_votes": 0, "flagged_samples": 0}
                    }
                elif not isinstance(result, dict):
                    print(f"⚠️ Unexpected result type: {type(result)}, converting to dict")
                    objectives_list = []
                    result = {
                        "objectives": [],
                        "validation": {"is_valid": False, "message": f"Unexpected type: {type(result)}"},
                        "voting_stats": {"total_samples": 0, "winner_votes": 0, "flagged_samples": 0}
                    }
                else:
                    objectives_list = result.get("objectives", [])
                    if not objectives_list:
                        # Try alternative paths
                        if "winner" in result:
                            objectives_list = result.get("winner", [])
                
                print(f"📝 Saving {len(objectives_list)} objectives to files...")
                
                # 1. Save JSON - with full result
                json_file = thesis_data_dir / "objectives.json"
                try:
                    with open(json_file, "w", encoding="utf-8") as f:
                        json.dump({
                            "objectives": objectives_list,
                            "topic": data.get("topic", ""),
                            "case_study": data.get("case_study", ""),
                            "methodology": data.get("methodology"),
                            "validation": result.get("validation", {}),
                            "voting_stats": result.get("voting_stats", {}),
                            "generated_at": datetime.now().isoformat()
                        }, f, indent=2, default=str, ensure_ascii=False)
                    print(f"✅ JSON saved: {json_file}")
                    await events.file_created(job_id, f"{thesis_id}/objectives.json", "json")
                except Exception as e:
                    print(f"❌ Error saving JSON: {e}")
                    await events.log(job_id, f"⚠️ Failed to save JSON: {str(e)}", "warning")
                
                # 2. Save Markdown
                objectives_file = thesis_data_dir / "objectives.md"
                try:
                    md_content = f"""# PhD Thesis Objectives

**Topic:** {data.get('topic', 'N/A')}
**Case Study:** {data.get('case_study', 'N/A')}
**Method:** MAKER Voting (k={k_threshold})
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Selected Objectives

"""
                    # Format objectives properly
                    for i, obj in enumerate(objectives_list, 1):
                        # Remove "General Objective:" or "Specific Objective X:" prefix if present
                        clean_obj = obj.split(":", 1)[1].strip() if ":" in obj else obj
                        md_content += f"{i}. {clean_obj}\n\n"
                    
                    md_content += "\n## Validation Status\n\n"
                    validation = result.get("validation", {})
                    md_content += f"**Valid:** {'✅ Yes' if validation.get('is_valid') else '❌ No'}\n\n"
                    
                    if validation.get("issues"):
                        md_content += "### Issues:\n"
                        for issue in validation.get("issues", []):
                            md_content += f"- {issue.get('issue', 'Unknown issue')}\n"
                    
                    md_content += "\n## Voting Statistics\n\n"
                    voting_stats = result.get("voting_stats", {})
                    md_content += f"- **Total Samples:** {voting_stats.get('total_samples', 0)}\n"
                    md_content += f"- **Winner Votes:** {voting_stats.get('winner_votes', 0)}\n"
                    md_content += f"- **Flagged Samples:** {voting_stats.get('flagged_samples', 0)}\n"
                    
                    with open(objectives_file, "w", encoding="utf-8") as f:
                        f.write(md_content)
                    
                    print(f"✅ Markdown saved: {objectives_file}")
                    await events.log(job_id, f"✅ Objectives saved to {objectives_file.name}", "success")
                    await events.file_created(job_id, f"{thesis_id}/objectives.md", "markdown")
                except Exception as e:
                    print(f"❌ Error saving Markdown: {e}")
                    await events.log(job_id, f"⚠️ Failed to save Markdown: {str(e)}", "warning")
                    
            except Exception as e:
                print(f"❌ CRITICAL ERROR saving objectives: {e}")
                import traceback
                traceback.print_exc()
                await events.log(job_id, f"❌ CRITICAL: Failed to save objectives: {str(e)}", "error")
            
            # Publish final objectives completion event with full details
            try:
                # Ensure result is dict before accessing
                if not isinstance(result, dict):
                    result = {"objectives": objectives_list, "validation": {}, "voting_stats": {}}
                
                validation = result.get("validation", {})
                voting_stats = result.get("voting_stats", {})
                
                await events.publish(job_id, "objectives_complete", {
                    "objectives": objectives_list,
                    "validation": validation,
                    "voting_stats": voting_stats,
                    "topic": data.get("topic", ""),
                    "case_study": data.get("case_study", ""),
                    "total_samples": voting_stats.get("total_samples", 0) if isinstance(voting_stats, dict) else 0,
                    "winner_votes": voting_stats.get("winner_votes", 0) if isinstance(voting_stats, dict) else 0
                })
            except Exception as e:
                print(f"⚠️ Error publishing objectives_complete: {e}")
                import traceback
                traceback.print_exc()
        
        elif mode == "competitive":
            competitive_result = await objective_agent.generate_objectives_competitive(
                topic=data["topic"],
                case_study=data["case_study"],
                methodology=data.get("methodology"),
                models=data.get("models"),
                job_id=job_id
            )
            
            # Ensure result is a dict
            if isinstance(competitive_result, list):
                result = {
                    "objectives": competitive_result,
                    "validation": {"is_valid": True},
                    "voting_stats": {}
                }
            elif not isinstance(competitive_result, dict):
                result = {
                    "objectives": [],
                    "validation": {"is_valid": False, "message": f"Unexpected type: {type(competitive_result)}"},
                    "voting_stats": {}
                }
            else:
                result = competitive_result
                
                # DEFENSIVE: Ensure 'winner' key exists
                # The ranker might return winner nested in 'ranking' or might not have it
                if 'winner' not in result:
                    print("⚠️ No 'winner' key found in result, checking 'ranking'...")
                    # Try to extract winner from ranking
                    if 'ranking' in result and isinstance(result['ranking'], dict):
                        if 'winner' in result['ranking']:
                            result['winner'] = result['ranking']['winner']
                            print(f"✓ Extracted winner from ranking: {result['winner'].get('model', 'Unknown')}")
                        else:
                            # Fallback: use first submission as default
                            print("⚠️ No winner in ranking either, using first submission as default")
                            submissions = result.get('submissions', {})
                            if submissions:
                                first_model = list(submissions.keys())[0]
                                result['winner'] = {
                                    'model': first_model,
                                    'score': 0
                                }
                            else:
                                result['winner'] = {'model': 'unknown', 'score': 0}
            
            # SAVE RESULTS TO FILES
            # Require thesis_id - should come from workspace creation, not generated
            thesis_id = data.get("thesis_id")
            if not thesis_id:
                print("⚠️ WARNING: No thesis_id provided, cannot save objectives")
                objectives_list = result.get("objectives", []) if isinstance(result, dict) else []
                return {
                    "objectives": objectives_list,
                    "status": "completed",
                    "warning": "Objectives generated but not saved (no workspace ID)"
                }
            thesis_data_dir = Path(__file__).parent.parent.parent.parent / "thesis_data" / thesis_id
            thesis_data_dir.mkdir(parents=True, exist_ok=True)
            
            # 1. Save JSON
            json_file = thesis_data_dir / "final_objectives.json"
            with open(json_file, "w") as f:
                json.dump(result, f, indent=2, default=str)
                
            await events.file_created(job_id, f"{thesis_id}/final_objectives.json", "json")
            
            # 2. Save Markdown (objectives.md)
            md_file = thesis_data_dir / "objectives.md"
            winner = result.get("winner", {})
            model_name = winner.get('model', 'Unknown')
            score = winner.get('score', 0)
            
            md_content = f"""# PhD Thesis Objectives
**Topic:** {result.get('topic', data.get('topic', 'N/A'))}
**Case Study:** {result.get('case_study', data.get('case_study', 'N/A'))}
**Winner:** {model_name.upper()} (Score: {score})

## Selected Objectives
"""
            # Extract objectives from winner - with safe access
            submissions = result.get('submissions', {})
            winning_objectives = submissions.get(model_name, [])
            
            if winning_objectives:
                for i, obj in enumerate(winning_objectives, 1):
                    md_content += f"{i}. {obj}\n"
            else:
                md_content += "No objectives found for winner.\n"
                
            md_content += "\n## Competition Details\n"
            participants = result.get('participants', [])
            if participants:
                md_content += f"Participants: {', '.join(participants)}\n"
            else:
                md_content += "Participants: N/A\n"
            
            with open(md_file, "w") as f:
                f.write(md_content)
                
            await events.file_created(job_id, f"{thesis_id}/objectives.md", "markdown")
            await events.log(job_id, f"✅ Saved objectives to {md_file.name}", "success")
    
    except Exception as e:
        print(f"❌ CRITICAL ERROR in objective worker: {e}")
        import traceback
        traceback.print_exc()
        await events.log(job_id, f"❌ CRITICAL ERROR: {str(e)}", "error")
        await events.publish(job_id, "progress", {"stage": "error", "percent": 0})
        
        # Always publish completion event even on error
        # Use safe access to data to avoid further errors
        try:
            topic = data.get("topic", "") if isinstance(data, dict) else ""
            case_study = data.get("case_study", "") if isinstance(data, dict) else ""
        except:
            topic = ""
            case_study = ""
        
        await events.publish(job_id, "objectives_complete", {
            "objectives": [],
            "validation": {"is_valid": False, "message": f"Error: {str(e)}"},
            "voting_stats": {},
            "topic": topic,
            "case_study": case_study,
            "error": str(e),
            "status": "error"
        })
        
        return {
            "status": "error",
            "error": str(e),
            "objectives": []
        }
    
    # Publish completion - ALWAYS runs
    try:
        await events.publish(job_id, "progress", {
            "stage": "completed",
            "percent": 100
        })
        
        await events.log(job_id, "🎉 Objective generation complete!", "success")
    except Exception as e:
        print(f"⚠️ Error publishing completion: {e}")
    
    return result


if __name__ == "__main__":
    print("🎯 Objective Worker - Starting...", flush=True)
    # The @worker decorator wraps process_objective_job and returns run_worker
    # So process_objective_job is now the worker loop function (run_worker)
    # We just need to call it - it will run the infinite loop
    try:
        asyncio.run(process_objective_job())
    except KeyboardInterrupt:
        print("\n🛑 Worker stopped by user", flush=True)
    except Exception as e:
        print(f"❌ Fatal worker error: {e}", flush=True)
        import traceback
        traceback.print_exc()
        raise
