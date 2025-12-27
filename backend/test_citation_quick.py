#!/usr/bin/env python3
"""
Quick Test - Citation Writer

Simple test to verify the system works without full API calls.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


async def test_imports():
    """Test that all modules can be imported."""
    print("\n" + "="*80)
    print("TESTING CITATION WRITER - IMPORTS")
    print("="*80 + "\n")
    
    try:
        print("✓ Importing citation_microagents...")
        from app.services.citation_microagents import (
            CitationFinderAgent,
            CitationValidatorAgent,
            CitationFormatterAgent,
            SentenceCitationAgent
        )
        
        print("✓ Importing cited_content_generator...")
        from app.services.cited_content_generator import cited_content_generator
        
        print("✓ Importing chapter_generator...")
        from app.services.chapter_generator import chapter_generator
        
        print("✓ Importing thesis_endpoints...")
        from app.api.thesis_endpoints import router
        
        print("\n✅ ALL IMPORTS SUCCESSFUL\n")
        return True
        
    except Exception as e:
        print(f"\n❌ IMPORT FAILED: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return False


async def test_agent_initialization():
    """Test that agents can be initialized."""
    print("\n" + "="*80)
    print("TESTING AGENT INITIALIZATION")
    print("="*80 + "\n")
    
    try:
        from app.services.mdap_llm_client import MDAPlLMClient
        from app.services.citation_microagents import CitationFinderAgent
        
        print("✓ Creating LLM client...")
        llm_client = MDAPlLMClient(model_key="deepseek")
        
        print("✓ Creating CitationFinderAgent...")
        agent = CitationFinderAgent("TestAgent", llm_client, max_tokens=300)
        
        print(f"✓ Agent name: {agent.name}")
        print(f"✓ Agent max_tokens: {agent.max_tokens}")
        
        print("\n✅ AGENT INITIALIZATION SUCCESSFUL\n")
        return True
        
    except Exception as e:
        print(f"\n❌ INITIALIZATION FAILED: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run quick tests."""
    
    print("\n🧪 CITATION WRITER - QUICK TESTS\n")
    
    # Test 1: Imports
    test1 = await test_imports()
    
    # Test 2: Agent initialization
    test2 = await test_agent_initialization()
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80 + "\n")
    
    if test1 and test2:
        print("✅ ALL TESTS PASSED")
        print("\nReady to use!")
        print("\nNext steps:")
        print("1. Run CLI: python3 generate_chapter_cli.py --topic 'AI' --case-study 'Education'")
        print("2. Or start API: uvicorn main:app --reload")
        print("\n")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print("\nCheck the errors above and ensure all dependencies are installed.\n")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
