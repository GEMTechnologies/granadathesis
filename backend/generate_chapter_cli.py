#!/usr/bin/env python3
"""
CLI Entry Point for Citation-Heavy Thesis Writer

Run from terminal to generate Chapter 1 with citations.

Usage:
    python generate_chapter_cli.py --topic "Machine Learning" --case-study "Healthcare"
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.chapter_generator import chapter_generator


async def main():
    """Main CLI entry point."""
    
    parser = argparse.ArgumentParser(
        description="Generate heavily-cited thesis Chapter 1"
    )
    parser.add_argument(
        "--topic",
        required=True,
        help="Research topic (e.g., 'Machine Learning')"
    )
    parser.add_argument(
        "--case-study",
        required=True,
        help="Case study/context (e.g., 'Healthcare Diagnosis')"
    )
    parser.add_argument(
        "--output",
        default="chapter_one.docx",
        help="Output DOCX file path (default: chapter_one.docx)"
    )
    parser.add_argument(
        "--word-count",
        type=int,
        default=500,
        help="Word count for Section 1.1 (default: 500)"
    )
    parser.add_argument(
        "--citation-style",
        choices=["APA", "Harvard"],
        default="APA",
        help="Citation style (default: APA)"
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*80)
    print("CITATION-HEAVY THESIS WRITER")
    print("="*80 + "\n")
    
    print(f"📚 Topic: {args.topic}")
    print(f"🏥 Case Study: {args.case_study}")
    print(f"📄 Output: {args.output}")
    print(f"📏 Word Count: {args.word_count}")
    print(f"📖 Citation Style: {args.citation_style}\n")
    
    # Sample objectives (in production, fetch from database)
    objectives = [
        {
            "type": "general",
            "text": f"To develop a comprehensive framework for applying {args.topic.lower()} techniques in {args.case_study.lower()} settings."
        },
        {
            "type": "specific",
            "text": f"To identify and evaluate existing {args.topic.lower()} approaches used in {args.case_study.lower()}."
        },
        {
            "type": "specific",
            "text": f"To design and implement a novel system using {args.topic.lower()} methods."
        },
        {
            "type": "specific",
            "text": "To validate the proposed system through empirical evaluation and performance benchmarking."
        }
    ]
    
    # Sample research questions
    research_questions = [
        f"How can {args.topic.lower()} improve outcomes in {args.case_study.lower()}?",
        f"What are the key challenges in implementing {args.topic.lower()}-based systems?",
        f"Which approaches are most effective for this domain?"
    ]
    
    print("🎯 Objectives: 1 general + 3 specific")
    print("❓ Research Questions: 3\n")
    
    try:
        # Generate Chapter 1
        print("🚀 Starting generation...\n")
        
        result = await chapter_generator.generate_chapter_one(
            topic=args.topic,
            case_study=args.case_study,
            objectives=objectives,
            research_questions=research_questions
        )
        
        # Save document
        chapter_generator.save_document(result['document'], args.output)
        
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
        print(f"   Total References: {metadata['total_references']}\n")
        
        print(f"📁 OUTPUT:")
        print(f"   File: {args.output}")
        print(f"   Sections: {len(metadata['sections'])}\n")
        
        print("📝 STRUCTURE:")
        for section in metadata['sections']:
            print(f"   {section['number']} {section['title']}")
        
        print("\n" + "="*80)
        print(f"✨ Open '{args.output}' to view the formatted chapter!")
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
