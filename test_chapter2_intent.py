#!/usr/bin/env python3
"""Test intent detection for Chapter 2 requests"""

import sys
sys.path.insert(0, '/home/gemtech/Desktop/thesis/backend/lightweight')

from services.intelligent_intent import intelligent_intent
import asyncio

async def test_intents():
    """Test various Chapter 2 request phrases"""
    
    test_cases = [
        "generate chapter 2",
        "write chapter 2",
        "create chapter two",
        "generate chapter two literature review",
        "write literature review",
        "make chapter 2 on youth mental health",
        "chapter 2 on depression",
        "generate the second chapter",
        "write my literature review chapter",
    ]
    
    print("="*60)
    print("CHAPTER 2 INTENT DETECTION TEST")
    print("="*60)
    
    for i, message in enumerate(test_cases, 1):
        print(f"\n{i}. Testing: '{message}'")
        result = await intelligent_intent.understand(message)
        
        gen_type = result.params.get('generation_type', 'NOT SET')
        chapter_num = result.params.get('chapter', 'N/A')
        
        print(f"   Intent: {result.intent.value}")
        print(f"   Route: {result.route.value}")
        print(f"   Chapter: {chapter_num}")
        print(f"   Generation Type: {gen_type}")
        print(f"   Confidence: {result.confidence}")
        
        # Check if it correctly detected Chapter 2
        is_chapter_2 = gen_type == "chapter_two_generate" or chapter_num == "2"
        status = "✅ CORRECT - Chapter 2" if is_chapter_2 else "❌ WRONG - Chapter 1 or Other"
        print(f"   Status: {status}")

if __name__ == "__main__":
    asyncio.run(test_intents())
