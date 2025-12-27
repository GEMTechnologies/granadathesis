#!/usr/bin/env python3
"""
Test Complete Flow - Workspace → Research → Sources → Generation

Verifies that:
1. Workspace is created with correct folder structure
2. Research gathers sources and saves to database
3. Content generation preserves citations
4. No verification destroys content
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lightweight'))

async def test_complete_flow():
    """Test the complete thesis generation flow"""
    
    print("\n" + "=" * 60)
    print("🧪 TESTING COMPLETE THESIS GENERATION FLOW")
    print("=" * 60 + "\n")
    
    # Import services
    from lightweight.services.workspace_service import workspace_service
    from lightweight.services.unified_research import unified_research_service
    from lightweight.services.simple_content_generator import simple_content_generator
    from lightweight.core.database import db
    
    # Test data
    thesis_id = "test_thesis_001"
    topic = "Impact of armed conflict on economic development"
    case_study = "Nuba Mountains, Sudan"
    
    try:
        # Initialize database connection
        await db.get_pool()
        print("✅ Database connected\n")
        
        # Test 1: Workspace Creation
        print("📁 TEST 1: Workspace Creation")
        print("-" * 60)
        workspace_result = await workspace_service.create_workspace(thesis_id)
        
        assert workspace_result['status'] == 'created', "Workspace not created"
        assert workspace_service.workspace_exists(thesis_id), "Workspace doesn't exist"
        
        workspace_path = workspace_service.get_workspace_path(thesis_id)
        assert (workspace_path / "sections").exists(), "sections/ folder missing"
        assert (workspace_path / "sources").exists(), "sources/ folder missing"
        assert (workspace_path / "references.bib").exists(), "references.bib missing"
        
        print(f"✅ Workspace created at: {workspace_path}")
        print(f"✅ All required folders exist\n")
        
        # Test 2: Research & Source Saving
        print("🔍 TEST 2: Research & Source Saving")
        print("-" * 60)
        
        research_result = await unified_research_service.collect_research(
            topic=topic,
            case_study=case_study,
            thesis_id=thesis_id
        )
        
        facts = research_result.get('facts', [])
        print(f"✅ Gathered {len(facts)} fact blocks")
        
        # Check if sources were saved to database
        sources = await db.fetch(
            "SELECT * FROM sources WHERE thesis_id = $1",
            thesis_id
        )
        
        source_count = len(sources)
        print(f"✅ Saved {source_count} sources to database")
        
        if source_count > 0:
            sample_source = dict(sources[0])
            print(f"✅ Sample source: {sample_source['title'][:50]}...")
        
        assert source_count > 0, "No sources saved to database!"
        print()
        
        # Test 3: Content Generation
        print("✍️ TEST 3: Content Generation (No Verification)")
        print("-" * 60)
        
        content_result = await simple_content_generator.generate_cited_section(
            section_title="Introduction",
            topic=topic,
            case_study=case_study,
            word_count=300,
            thesis_id=thesis_id,
            job_id=None  # No job_id for testing
        )
        
        content = content_result['content']
        metrics = content_result['metrics']
        
        print(f"✅ Generated {len(content)} characters")
        print(f"✅ Word count: {metrics['word_count']}")
        print(f"✅ Citations: {metrics['citation_count']}")
        print(f"✅ Verification issues: {metrics['verification_issues']} (should be 0)")
        
        # Check for citations in content
        assert '(' in content and ')' in content, "No citations found in content!"
        
        # Verify no verification happened (issues should be 0)
        assert metrics['verification_issues'] == 0, "Verification should be disabled!"
        
        print(f"\n📝 Sample content (first 200 chars):")
        print(f"   {content[:200]}...\n")
        
        # Test 4: Verify files saved
        print("💾 TEST 4: File Persistence")
        print("-" * 60)
        
        sections_dir = workspace_path / "sections"
        bib_file = workspace_path / "references.bib"
        
        # Check if BibTeX was updated
        bib_content = bib_file.read_text()
        print(f"✅ references.bib size: {len(bib_content)} bytes")
        
        if len(bib_content) > 50:  # More than just header
            print(f"✅ BibTeX entries added")
        
        print()
        
        # Final Summary
        print("=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 60)
        print(f"\n📊 Summary:")
        print(f"   • Workspace: {workspace_path}")
        print(f"   • Sources saved: {source_count}")
        print(f"   • Content generated: {metrics['word_count']} words")
        print(f"   • Citations preserved: {metrics['citation_count']}")
        print(f"   • Verification disabled: ✅")
        print()
        
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        return False
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        await db.close_pool()
        print("🔌 Database disconnected\n")


if __name__ == "__main__":
    result = asyncio.run(test_complete_flow())
    sys.exit(0 if result else 1)
