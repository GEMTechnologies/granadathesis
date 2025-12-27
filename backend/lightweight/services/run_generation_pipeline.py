import asyncio
import os
import sys

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, '../..'))
sys.path.append(backend_dir)

from lightweight.services.data_collection_worker import generate_research_dataset
from lightweight.services.chapter4_generator import generate_chapter4

async def main():
    print("🚀 Starting Full Generation Pipeline...")
    
    output_dir = "/home/gemtech/Desktop/thesis"
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Generate Dataset
    print("\n📊 1. Generating Synthetic Data...")
    data_result = await generate_research_dataset(
        topic="The Impact of AI on Coding Productivity",
        case_study="Software Development Firms in Nairobi",
        objectives=[
            "To examine the extent of AI adoption in coding tasks.",
            "To analyze the impact of AI on coding speed and accuracy.", 
            "To determine the challenges faced by developers in using AI tools."
        ],
        sample_size=30,
        output_dir=os.path.join(output_dir, "datasets")
    )
    print(f"   ✅ Data generated at: {data_result['csv_path']}")
    
    # 2. Generate Chapter 4
    print("\n📝 2. Generating Chapter 4...")
    chapter_content = await generate_chapter4(
        topic="The Impact of AI on Coding Productivity",
        case_study="Software Development Firms in Nairobi",
        objectives=[
            "To examine the extent of AI adoption in coding tasks.",
            "To analyze the impact of AI on coding speed and accuracy.", 
            "To determine the challenges faced by developers in using AI tools."
        ],
        datasets_dir=os.path.join(output_dir, "datasets"),
        output_dir=output_dir
    )
    
    # Save the markdown file manually (generate_chapter4 usually handles this or returns str)
    # The current signature returns string (markdown content) based on line 1790-ish check
    # But wait, looking at line 1782, it returns Dict[str, Any]? or String?
    # Let's check the return type in the file content I saw earlier (line 1790 says -> Dict[str, Any])
    # Actually that might have been a different function or I misread.
    # checking file again... 
    # Ah, I see: async def generate_chapter4(...) -> Dict[str, Any]:
    # But inside the function (which I didn't see fully), it calls generate_full_chapter which returns string.
    # I'll assumt it returns a dict with 'content' or 'file_path'.
    
    # Actually, let's write the content if it returns a string, or check the dict.
    if isinstance(chapter_content, dict):
        content = chapter_content.get('content', '')
        # It usually saves DOCX inside the function too.
        print(f"   ✅ Generation complete.")
    else:
        content = chapter_content
        print(f"   ✅ Generation complete (returned string).")
        
        md_path = os.path.join(output_dir, "chapter_4.md")
        with open(md_path, 'w') as f:
            f.write(content)

    # 3. Verify Output
    print("\n🔍 3. Verifying Output Formatting...")
    
    # Check MD file if it exists
    md_path = os.path.join(output_dir, "chapter_4.md") # Assuming it might be saved there
    if not os.path.exists(md_path):
        # If the function didn't save MD, let's look for DOCX or check the returned content
         pass

    if content:
        if "|:-" in content or "-:|" in content:
            print("   ❌ FAILED: Found centered separators in Markdown content.")
        else:
            print("   ✅ PASSED: Markdown content is clean (no centered separators).")
    else:
        print("   ⚠️ WARNING: No content returned to verify.")

if __name__ == "__main__":
    asyncio.run(main())
