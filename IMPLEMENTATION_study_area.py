# ADD THIS TO parallel_chapter_generator.py after _build_methodology_intro_prompt

def _build_study_area_prompt(self, section_id: str, title: str, citation_context: str) -> str:
    """Build prompt for Study Area with map and dual-version support."""
    return f"""Write section "{section_id} {title}" - comprehensive study area with map.

TOPIC: {self.state.topic}
CASE STUDY: {self.state.case_study}

{citation_context}

**CRITICAL: START WITH SCHOLARLY DEFINITION**
Begin: "A study area, as defined by Kumar (2019), refers to the geographical and contextual boundaries within which research is conducted..."
Cite 2-3 scholars (Kumar, 2019; Kothari, 2004; Creswell, 2014).

Write 4 paragraphs + 1 map:

**1. Definition (1 paragraph)**
- Scholarly definition of "study area"
- Importance in research design
- Cite (Kumar, 2019; Kothari, 2004)

**2. Geographical Description (1 paragraph)**
- Location, coordinates, size, boundaries
- Regions/states within {self.state.case_study}
- Population statistics
- Cite official sources

**3. Contextual Characteristics (1 paragraph)**
- Socio-economic conditions
- Political/conflict context
- Infrastructure
- Justification for selection

**4. Study Area Map (MANDATORY - ASCII for image generation)**

```
============================================
    MAP: {self.state.case_study.upper()}
============================================
[Simple ASCII map showing:
- Major regions
- Key cities  
- Borders
- Legend]
============================================
```

Caption: Figure 3.2: Map of Study Area  
Source: [Geographical source]

**DUAL-VERSION (CRITICAL):**

---VERSION: PROPOSAL---
The study **will be conducted** in {self.state.case_study}...
[Future tense throughout]

---VERSION: REPORT---
The study **was conducted** in {self.state.case_study}...
[Past tense throughout]

**FORMATTING:**
- Start with scholarly definition
- Bullets for characteristics
- ASCII map in code block
- NO PLACEHOLDERS
- 3-5 citations per paragraph
- Generate BOTH versions

Write the content now:"""


# ADD THIS TO _writer_agent routing (around line 750):
elif style == "study_area":
    prompt = self._build_study_area_prompt(section_id, title, citation_context)
