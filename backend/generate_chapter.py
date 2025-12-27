#!/usr/bin/env python3
"""
Simple Thesis Chapter Generator

Single entry point - just provide topic and case study.
Generates Chapter 1 with heavy citations automatically.

Estimated time: 2-4 minutes for 500 words
"""

import asyncio
import sys
from pathlib import Path
import time

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.chapter_generator import chapter_generator
from app.agents.objective import ObjectiveAgent


async def generate_objectives_with_maker(topic: str, case_study: str) -> list:
    """Generate objectives using MAKER competitive generation."""
    print("\n" + "="*80)
    print("🎯 STEP 1: GENERATING OBJECTIVES (Competitive Generation)")
    print("="*80 + "\n")
    
    print(f"📚 Topic: {topic}")
    print(f"🏢 Case Study: {case_study}")
    print(f"🏆 Using competitive multi-model generation\n")
    
    try:
        # Initialize objective agent
        objective_agent = ObjectiveAgent()
        
        # Generate objectives competitively
        print("🚀 Generating objectives with 4 competing models...")
        result = await objective_agent.generate_objectives_competitive(
            topic=topic,
            case_study=case_study
        )
        
        if result.get('winner') and result['winner'].get('objectives'):
            objectives_list = result['winner']['objectives']
            
            # Parse objectives into structured format
            objectives_data = []
            for obj_text in objectives_list:
                if "General Objective:" in obj_text:
                    obj_type = "general"
                    text = obj_text.replace("General Objective:", "").strip()
                else:
                    obj_type = "specific"
                    # Remove "Specific Objective N:" prefix
                    text = obj_text
                    for i in range(1, 10):
                        text = text.replace(f"Specific Objective {i}:", "").strip()
                    text = text.split(":", 1)[-1].strip() if ":" in text else text
                
                objectives_data.append({
                    "type": obj_type,
                    "text": text
                })
            
            print(f"\n✅ Objectives Generated!")
            print(f"   Winner: {result['winner']['model'].upper()}")
            print(f"   Score: {result['winner']['score']}/100")
            print(f"   Total: {len(objectives_data)} objectives\n")
            
            print("📋 Generated Objectives:")
            for i, obj in enumerate(objectives_data, 1):
                obj_type = obj.get('type', 'specific')
                print(f"   {i}. [{obj_type.upper()}] {obj.get('text', '')[:80]}...")
            
            print()
            return objectives_data
        else:
            print(f"⚠️  Objective generation failed, using fallback\n")
            return None
            
    except Exception as e:
        print(f"⚠️  Competitive generation failed: {str(e)}")
        print(f"   Using fallback objectives\n")
        return None


async def main():
    """Main entry point - interactive prompts."""
    
    print("\n" + "="*80)
    print("📚 THESIS CHAPTER GENERATOR")
    print("="*80 + "\n")
    
    # Get user input
    print("Please provide the following information:\n")
    
    topic = input("🎯 Research Topic: ").strip()
    if not topic:
        print("❌ Topic is required!")
        return 1
    
    case_study = input("🏢 Case Study/Context: ").strip()
    if not case_study:
        print("❌ Case study is required!")
        return 1
    
    # Step 1: Generate objectives with MAKER voting
    objectives = await generate_objectives_with_maker(topic, case_study)
    
    # Fallback objectives if MAKER fails
    if not objectives:
        print("📋 Using fallback objectives...\n")
        objectives = [
            {
                "type": "general",
                "text": f"To develop a comprehensive framework for applying {topic.lower()} in {case_study.lower()} settings."
            },
            {
                "type": "specific",
                "text": f"To identify and evaluate existing {topic.lower()} approaches used in {case_study.lower()}."
            },
            {
                "type": "specific",
                "text": f"To design and implement a novel {topic.lower()}-based system for {case_study.lower()}."
            },
            {
                "type": "specific",
                "text": "To validate the proposed system through empirical evaluation and performance benchmarking."
            }
        ]
    
    # Step 2: Generate Chapter 1
    print("\n" + "="*80)
    print("📝 STEP 2: GENERATING CHAPTER ONE")
    print("="*80 + "\n")
    
    print(f"📚 Topic: {topic}")
    print(f"🏢 Case Study: {case_study}")
    print(f"📄 Output: chapter_one.docx")
    print(f"📏 Word Count: 500 words")
    print(f"📖 Citation Style: APA")
    print(f"🎯 Citation Density Target: 75%")
    print(f"⏱️  Estimated Time: 2-4 minutes")
    print(f"💰 Estimated Cost: ~$0.015 (DeepSeek)\n")
    
    # Auto-generate research questions
    research_questions = [
        f"How can {topic.lower()} improve outcomes in {case_study.lower()}?",
        f"What are the key challenges in implementing {topic.lower()}-based systems in {case_study.lower()}?",
        f"Which {topic.lower()} approaches are most effective for this domain?"
    ]
    
    print("🚀 Starting chapter generation...\n")
    print("💡 This will take 2-4 minutes using DeepSeek with MDAP voting.")
    print("   You'll see progress updates as it generates.\n")
    
    start_time = time.time()
    
    try:
        # Generate Chapter 1
        result = await chapter_generator.generate_chapter_one(
            topic=topic,
            case_study=case_study,
            objectives=objectives,
            research_questions=research_questions
        )
        
        elapsed_time = time.time() - start_time
        
        # Save document
        output_file = "chapter_one.docx"
        chapter_generator.save_document(result['document'], output_file)
        
        # Display results
        print("\n" + "="*80)
        print("✅ CHAPTER ONE GENERATED SUCCESSFULLY")
        print("="*80 + "\n")
        
        metadata = result['metadata']
        
        print(f"📊 METRICS:")
        print(f"   Word Count: {metadata['metrics']['word_count']}")
        print(f"   Citations: {metadata['metrics']['citation_count']}")
        print(f"   Citation Density: {metadata['metrics']['citation_density']:.1%}")
        print(f"   Unique Papers: {metadata['metrics']['unique_papers']}")
        print(f"   Total References: {metadata['total_references']}")
        print(f"   Generation Time: {elapsed_time/60:.1f} minutes\n")
        
        print(f"📁 OUTPUT:")
        print(f"   File: {output_file}")
        print(f"   Sections: {len(metadata['sections'])}\n")
        
        print("📝 STRUCTURE:")
        print("   CHAPTER ONE (centered)")
        print("   INTRODUCTION (centered)")
        for section in metadata['sections']:
            print(f"   {section['number']} {section['title']}")
        print("   References (alphabetically sorted)\n")
        
        print("="*80)
        print(f"✨ Open '{output_file}' to view your chapter!")
        print("="*80 + "\n")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
