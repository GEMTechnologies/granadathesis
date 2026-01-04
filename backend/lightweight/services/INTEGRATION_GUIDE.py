"""
INTEGRATION GUIDE: Using Uploaded PDFs in Chapter Generation

This file shows how to integrate the sources_context_loader into chapter generators
so that uploaded PDFs teach the LLM new knowledge.
"""

# ============================================================================
# STEP 1: Import the sources context loader
# ============================================================================

from services.sources_context_loader import enhance_prompt_with_sources, load_sources_for_llm

# ============================================================================
# STEP 2: Modify chapter generator to load sources
# ============================================================================

# BEFORE (without sources):
async def generate_chapter_two_old(topic, workspace_id, job_id, session_id):
    prompt = f"""
    Write a literature review on {topic}.
    Include relevant citations.
    """
    
    response = await model.generate_content_async(prompt)
    return response.text

# AFTER (with sources from uploaded PDFs):
async def generate_chapter_two_new(topic, workspace_id, job_id, session_id):
    base_prompt = f"""
    Write a literature review on {topic}.
    Use the provided sources below to support your arguments.
    """
    
    # Enhance prompt with uploaded PDF sources
    enhanced_prompt = enhance_prompt_with_sources(
        base_prompt=base_prompt,
        workspace_id=workspace_id,
        max_sources=10  # Include up to 10 PDFs
    )
    
    response = await model.generate_content_async(enhanced_prompt)
    return response.text

# ============================================================================
# STEP 3: What the LLM receives
# ============================================================================

"""
The enhanced prompt now includes:

1. Original prompt
2. List of uploaded PDF sources with:
   - Title, authors, year
   - Abstract/content preview
   - Citation key (Author, Year)
3. Citation instructions

Example enhanced prompt:

---
Write a literature review on Teacher Performance in Uganda.
Use the provided sources below to support your arguments.

## 📚 Available Literature Sources
Use these sources to support your writing. Cite them using (Author, Year) format.

### Source 1: Smith et al. (2020)
**Title**: Effective Teaching Strategies in Developing Countries
**Citation Key**: (Smith, 2020)
**Content Preview**:
This study examines teaching methodologies in East African schools...
[Full text excerpt from uploaded PDF]
---

### Source 2: Jones (2021)
**Title**: Teacher Motivation and Performance
**Citation Key**: (Jones, 2021)
**Content Preview**:
Research indicates that teacher motivation is a key factor...
[Full text excerpt from uploaded PDF]
---

## Citation Guidelines
- Use in-text citations: (Author, Year)
- For multiple authors: (Smith et al., 2020)
- Cite after statements: "...conclusion (Author, Year)."
---

Now the LLM can write:

"Research shows that effective teaching strategies significantly impact 
student outcomes in developing countries (Smith, 2020). Furthermore, 
teacher motivation plays a crucial role in performance (Jones, 2021)."
"""

# ============================================================================
# STEP 4: Integration into existing generators
# ============================================================================

# Add to parallel_chapter_generator.py, around line 3500 (Chapter 2 generation):

"""
# Load sources for literature review
sources_context = load_sources_for_llm(workspace_id, max_sources=15)

if sources_context:
    await events.publish(
        job_id,
        "log",
        {"message": f"📚 Loaded {len(sources)} uploaded PDF sources for literature review"},
        session_id=session_id
    )
    
    # Add sources to prompt
    prompt += f"\\n\\n{sources_context}"
"""

# ============================================================================
# STEP 5: Automatic citation generation
# ============================================================================

"""
When the LLM generates content with citations like (Smith, 2020),
the bibliography_service automatically has the BibTeX entry ready
in references.bib:

@article{smith2020effective,
  title = {Effective Teaching Strategies in Developing Countries},
  author = {John Smith and Jane Doe},
  year = {2020},
  abstract = {This study examines...}
}

This means:
1. Upload PDFs → Metadata extracted
2. Generate chapter → LLM uses PDF knowledge
3. Citations added → (Smith, 2020)
4. Bibliography ready → references.bib updated
"""

# ============================================================================
# EXAMPLE USAGE
# ============================================================================

async def example_workflow():
    """Complete workflow showing PDF knowledge integration."""
    
    workspace_id = "ws_abc123"
    
    # 1. User uploads 50 PDFs
    # → System extracts metadata
    # → Saves to workspace/sources/pdfs/
    # → Updates references.bib
    
    # 2. User generates Chapter 2
    sources_context = load_sources_for_llm(workspace_id, max_sources=20)
    
    prompt = f"""
    Write a comprehensive literature review on Teacher Performance.
    
    {sources_context}
    """
    
    # 3. LLM generates content using uploaded PDF knowledge
    # → Cites sources: (Smith, 2020), (Jones, 2021)
    # → Uses actual content from PDFs
    # → Bibliography already prepared
    
    # 4. Result: Chapter with proper citations from uploaded literature
    
    print("✅ Chapter generated using knowledge from 20 uploaded PDFs!")
