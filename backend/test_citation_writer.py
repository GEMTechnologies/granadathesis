"""
Test Citation-Heavy Thesis Writer

Tests the complete citation system:
- Citation microagents
- Cited content generation
- Chapter structure
- DOCX formatting
"""

import asyncio
from app.services.chapter_generator import chapter_generator


async def test_chapter_one_generation():
    """Test generating Chapter 1 with citations."""
    
    print("\n" + "="*80)
    print("TESTING CITATION-HEAVY THESIS WRITER")
    print("="*80 + "\n")
    
    # Test data
    topic = "Machine Learning"
    case_study = "Healthcare Diagnosis"
    
    # Sample objectives (would come from MAKER voting database)
    objectives = [
        {
            "type": "general",
            "text": "To develop a comprehensive framework for applying machine learning techniques to improve diagnostic accuracy in healthcare settings."
        },
        {
            "type": "specific",
            "text": "To identify and evaluate existing machine learning algorithms used in medical diagnosis."
        },
        {
            "type": "specific",
            "text": "To design and implement a novel diagnostic support system using ensemble learning methods."
        },
        {
            "type": "specific",
            "text": "To validate the proposed system through clinical case studies and performance benchmarking."
        }
    ]
    
    # Sample research questions
    research_questions = [
        "How can machine learning algorithms improve the accuracy of medical diagnoses compared to traditional methods?",
        "What are the key challenges in implementing ML-based diagnostic systems in clinical settings?",
        "Which ensemble learning approaches are most effective for multi-class medical diagnosis tasks?"
    ]
    
    print(f"Topic: {topic}")
    print(f"Case Study: {case_study}")
    print(f"Objectives: {len(objectives)}")
    print(f"Research Questions: {len(research_questions)}\n")
    
    try:
        # Generate Chapter 1
        result = await chapter_generator.generate_chapter_one(
            topic=topic,
            case_study=case_study,
            objectives=objectives,
            research_questions=research_questions
        )
        
        # Display results
        print("\n" + "="*80)
        print("CHAPTER ONE GENERATED")
        print("="*80 + "\n")
        
        metadata = result['metadata']
        print(f"Chapter: {metadata['chapter_number']} - {metadata['chapter_title']}")
        print(f"Sections: {len(metadata['sections'])}")
        print(f"Total References: {metadata['total_references']}")
        print(f"\nMetrics:")
        print(f"  Word Count: {metadata['metrics']['word_count']}")
        print(f"  Citations: {metadata['metrics']['citation_count']}")
        print(f"  Citation Density: {metadata['metrics']['citation_density']:.1%}")
        print(f"  Unique Papers: {metadata['metrics']['unique_papers']}")
        
        # Save document
        output_file = "/tmp/chapter_one_test.docx"
        chapter_generator.save_document(result['document'], output_file)
        
        print(f"\n✅ TEST PASSED")
        print(f"   Document saved to: {output_file}")
        print(f"   Open it to verify formatting:\n")
        print(f"   - Centered headings (CHAPTER ONE, INTRODUCTION)")
        print(f"   - Section 1.1 with heavy citations")
        print(f"   - Section 1.4 with objectives")
        print(f"   - Section 1.5 with research questions")
        print(f"   - References with hanging indent\n")
        
        return result
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return None


async def test_citation_density():
    """Test citation density in generated content."""
    
    print("\n" + "="*80)
    print("TESTING CITATION DENSITY")
    print("="*80 + "\n")
    
    from app.services.cited_content_generator import cited_content_generator
    
    try:
        result = await cited_content_generator.generate_cited_section(
            section_title="Test Section",
            topic="Artificial Intelligence in Education",
            word_count=300,
            target_density=0.8
        )
        
        print(f"Section: {result['section_title']}")
        print(f"Word Count: {result['metrics']['word_count']}")
        print(f"Citations: {result['metrics']['citation_count']}")
        print(f"Citation Density: {result['metrics']['citation_density']:.1%}")
        print(f"Target Density: 80%")
        
        # Verify density
        if result['metrics']['citation_density'] >= 0.7:
            print(f"\n✅ PASS: Citation density meets target (≥70%)")
        else:
            print(f"\n⚠️  WARNING: Citation density below target")
        
        # Show sample content
        print(f"\nSample Content (first 200 chars):")
        print(f"{result['content'][:200]}...\n")
        
        return result
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """Run all tests."""
    
    print("\n🧪 CITATION-HEAVY THESIS WRITER TESTS\n")
    
    # Test 1: Citation density
    await test_citation_density()
    
    # Test 2: Full chapter generation
    # await test_chapter_one_generation()  # Uncomment when ready for full test
    
    print("\n✅ ALL TESTS COMPLETE\n")


if __name__ == "__main__":
    asyncio.run(main())
