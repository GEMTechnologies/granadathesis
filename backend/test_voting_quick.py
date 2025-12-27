#!/usr/bin/env python3
"""
Quick test of MAKER voting - non-interactive
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.agents.objective import objective_agent


async def test():
    print("\n🧪 TESTING MAKER VOTING (Non-Interactive)\n")
    
    # Test data
    topic = "Impact of War on Education"
    case_study = "Sudan, 2011-2023"
    
    print(f"Topic: {topic}")
    print(f"Case Study: {case_study}")
    print(f"k-threshold: 3")
    print(f"Red-flagging: Enabled\n")
    print("="*70)
    
    try:
        result = await objective_agent.generate_objectives_with_voting(
            topic=topic,
            case_study=case_study,
            methodology=None,
            k=3,
            enable_red_flags=True,
            thesis_id=None
        )
        
        print("\n" + "="*70)
        print("✅ SUCCESS! MAKER VOTING WORKS!")
        print("="*70)
        
        print("\n📋 FINAL OBJECTIVES:")
        for i, obj in enumerate(result["objectives"], 1):
            print(f"{i}. {obj}")
        
        stats = result["voting_stats"]
        print(f"\n📊 VOTING STATS:")
        print(f"   Total samples: {stats['total_samples']}")
        print(f"   Flagged: {stats['flagged_samples']}")
        print(f"   Winner votes: {stats['winner_votes']}")
        print(f"   Convergence rounds: {stats['convergence_rounds']}")
        
        print(f"\n💰 COST: ${result['actual_cost']:.4f}")
        
        validation = result["validation"]
        print(f"\n✅ VALIDATION: {'PASSED' if validation['is_valid'] else 'FAILED'}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test())
    sys.exit(0 if success else 1)
