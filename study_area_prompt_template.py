# Study Area Prompt for Chapter 3

def _build_study_area_prompt(self, section_id: str, title: str, citation_context: str) -> str:
    """Build prompt for Study Area section with map generation."""
    return f"""Write section "{section_id} {title}" - comprehensive study area description with map.

TOPIC: {self.state.topic}
CASE STUDY: {self.state.case_study}

{citation_context}

**CRITICAL: START WITH SCHOLARLY DEFINITION**
Begin the section with: "A study area, as defined by [Scholar, Year], refers to..."
Then cite 2-3 definitions from methodology scholars (Kumar, 2019; Kothari, 2004; Creswell, 2014).

Write 4 paragraphs + 1 map:

**1. Definition and Importance (1 paragraph)**
- Start with scholarly definition of "study area" 
- Explain why defining the study area is critical for research
- Cite (Kumar, 2019; Kothari, 2004)

**2. Geographical Description (1 paragraph)**
- Describe the geographical location of {self.state.case_study}
- Include: coordinates, size, boundaries, regions/states
- Population statistics
- Cite official sources

**3. Contextual Characteristics (1 paragraph)**
- Describe relevant characteristics for the study:
  * Socio-economic conditions
  * Political situation
  * Infrastructure
  * Any conflict/development context
- Justify why this area is appropriate for the study

**4. Study Area Map (MANDATORY)**
Create a simple ASCII map representation:

```
============================================
    MAP OF STUDY AREA: {self.state.case_study.upper()}
============================================
[Create simple ASCII representation showing:
- Major regions/states
- Key cities
- Borders
- Legend]
============================================
```

Caption: Figure 3.2: Map of Study Area  
Source: [Appropriate geographical source]

**DUAL-VERSION REQUIREMENT:**
- **PROPOSAL VERSION (will/future tense)**: "The study **will be conducted** in..."
- **REPORT VERSION (was/past tense)**: "The study **was conducted** in..."

Generate BOTH versions separated by:
---VERSION: PROPOSAL---
[content in future tense]
---VERSION: REPORT---
[content in past tense]

**FORMATTING:**
- Start with scholarly definition
- Use bullets for characteristics
- ASCII map in code block for image generation
- NO PLACEHOLDERS
- 3-5 citations per paragraph

Write the content now:"""
