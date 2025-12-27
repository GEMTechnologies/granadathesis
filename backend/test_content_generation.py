"""
Test Content Generation - 500 words, well-cited

Tests the lightweight system's ability to generate cited content.
"""
import asyncio
import sys
sys.path.insert(0, '/home/gemtech/Desktop/thesis/backend/lightweight')

from services.cited_content_generator import cited_content_generator


async def test_generation():
    """Test generating 500-word cited section."""
    
    print("🧪 Testing Content Generation")
    print("="*60)
    print("Topic: Machine Learning")
    print("Case Study: Healthcare")
    print("Target: 500 words, 75% citation density")
    print("="*60 + "\n")
    
    try:
        result = await cited_content_generator.generate_cited_section(
            section_title="Setting the Scene",
            topic="Machine Learning in Healthcare",
            word_count=500,
            target_density=0.75
        )
        
        print(f"✅ Generation Complete!\n")
        print(f"📊 Metrics:")
        print(f"   Words: {result['metrics']['word_count']}")
        print(f"   Sentences: {result['metrics']['sentence_count']}")
        print(f"   Citations: {result['metrics']['citation_count']}")
        print(f"   Density: {result['metrics']['citation_density']:.1%}")
        print(f"   Unique Papers: {result['metrics']['unique_papers']}\n")
        
        print(f"📝 Content Preview (first 300 chars):")
        print("-"*60)
        print(result['content'][:300] + "...")
        print("-"*60 + "\n")
        
        print(f"📚 References ({len(result['references'])}):")
        for i, ref in enumerate(result['references'][:3], 1):
            print(f"   {i}. {ref[:80]}...")
        
        if len(result['references']) > 3:
            print(f"   ... and {len(result['references']) - 3} more\n")
        
        print("✅ TEST PASSED - System can generate cited content!")
        return True
        
    except Exception as e:
        print(f"❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_generation())
    sys.exit(0 if success else 1)
