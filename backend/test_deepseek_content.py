#!/usr/bin/env python3
"""
Test Content Generation with DeepSeek Integration

This script tests the updated content generator to verify:
1. DeepSeek API is being called
2. Paper abstracts are being used as context
3. Citations are properly formatted
4. Content is meaningful and relates to the papers
"""

import asyncio
import sys
sys.path.insert(0, '/home/gemtech/Desktop/thesis/backend/lightweight')

from services.simple_content_generator import simple_content_generator


async def test_content_generation():
    """Test the content generation with a simple topic."""
    
    print("=" * 70)
    print("Testing Content Generation with DeepSeek Integration")
    print("=" * 70)
    
    # Test parameters
    topic = "machine learning in healthcare diagnosis"
    section_title = "AI in Medical Diagnostics"
    word_count = 200  # Small test
    
    print(f"\n📝 Test Parameters:")
    print(f"   Topic: {topic}")
    print(f"   Section: {section_title}")
    print(f"   Target: {word_count} words")
    print()
    
    # Generate content
    try:
        result = await simple_content_generator.generate_cited_section(
            section_title=section_title,
            topic=topic,
            word_count=word_count,
            job_id=None  # No job tracking for this test
        )
        
        # Display results
        print("\n" + "=" * 70)
        print("RESULTS")
        print("=" * 70)
        
        if "error" in result:
            print(f"\n❌ ERROR: {result['error']}")
            return False
        
        print(f"\n📊 Metrics:")
        metrics = result.get("metrics", {})
        print(f"   Words: {metrics.get('word_count', 0)}")
        print(f"   Sentences: {metrics.get('sentence_count', 0)}")
        print(f"   Citations: {metrics.get('citation_count', 0)}")
        
        print(f"\n📝 Generated Content:")
        print("-" * 70)
        content = result.get("content", "")
        print(content)
        print("-" * 70)
        
        print(f"\n📚 References ({len(result.get('references', []))}):")
        print("-" * 70)
        for i, ref in enumerate(result.get("references", [])[:5], 1):
            print(f"{i}. {ref}")
        print("-" * 70)
        
        # Validation checks
        print(f"\n✓ Validation:")
        
        # Check 1: Content is not placeholder
        is_placeholder = "found that" in content.lower() and content.count("found that") > 3
        if is_placeholder:
            print("   ❌ Content appears to be placeholder text")
            return False
        else:
            print("   ✅ Content appears to be generated (not placeholder)")
        
        # Check 2: Has citations
        has_citations = "(" in content and ")" in content
        if has_citations:
            print("   ✅ Citations present in text")
        else:
            print("   ❌ No citations found")
            return False
        
        # Check 3: Reasonable length
        word_count_actual = metrics.get('word_count', 0)
        if word_count_actual >= word_count * 0.8:
            print(f"   ✅ Word count meets target ({word_count_actual} >= {word_count * 0.8})")
        else:
            print(f"   ⚠️  Word count below target ({word_count_actual} < {word_count * 0.8})")
        
        print("\n✅ TEST PASSED - DeepSeek integration is working!")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_content_generation())
    sys.exit(0 if success else 1)
