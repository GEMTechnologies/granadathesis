#!/usr/bin/env python3
"""Test simple_content_generator with mock data"""
import asyncio
import sys
sys.path.insert(0, '/app')

from services.simple_content_generator import simple_content_generator


async def test():
    # Mock paper data
    paper = {
        'title': 'Machine Learning in Healthcare',
        'abstract': 'This study explores the applications of machine learning algorithms in clinical decision-making and patient diagnosis.',
        'authors': [{'name': 'John Smith'}],
        'year': 2024
    }
    
    try:
        print("Testing _generate_sentence_with_context...")
        sentence = await simple_content_generator._generate_sentence_with_context(
            topic="machine learning in healthcare",
            paper=paper,
            context=None
        )
        
        print(f"\n✓ SUCCESS!")
        print(f"Generated sentence: {sentence}")
        return True
        
    except Exception as e:
        print(f"\n✗ FAILED!")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test())
    sys.exit(0 if success else 1)
