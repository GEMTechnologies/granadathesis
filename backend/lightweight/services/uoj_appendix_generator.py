"""
University of Juba Appendix Generator
Generates Introductory Letter and Research Questionnaires (Likert + Open-ended).
"""
from typing import List, Dict, Any
from services.deepseek_direct import deepseek_direct_service

async def generate_appendices_uoj(
    topic: str,
    objectives: Dict[str, Any]
) -> str:
    """Generate Appendices I (Letter) and II (Questionnaire)."""
    
    specific_objs = objectives.get("specific", [])
    
    # 1. Appendix I: Introductory Letter
    appendix_i = f"""
# APPENDIX I: INTRODUCTORY LETTER

**UNIVERSITY OF JUBA**
**SCHOOL OF EDUCATION**

Dear Respondent,

**RE: REQUEST FOR YOUR PARTICIPATION IN RESEARCH STUDY**

I am a student at the University of Juba, conducting a research study on the topic: "**{topic.upper()}**".

You have been selected to participate in this study. The information you provide will be treated with strict confidentiality and used solely for academic purposes. Your honest participation is highly appreciated.

Thank you for your cooperation.

Yours faithfully,

________________________
**(Student Researcher)**
"""

    # 2. Appendix II: Questionnaire
    # Header
    questionnaire_intro = f"""
# APPENDIX II: QUESTIONNAIRE FOR TEACHERS/STUDENTS

**Instructions:**
Please tick [√] in the appropriate box or write your response in the spaces provided. Do not write your name on this questionnaire.

**SECTION A: BIO-DATA INFORMATION**
1. **Gender**:  [ ] Male    [ ] Female
2. **Age**:     [ ] 20-30   [ ] 31-40   [ ] 41-50   [ ] 50+
3. **Education**: [ ] Certificate [ ] Diploma [ ] Degree [ ] Masters
4. **Experience**: [ ] 1-3 years  [ ] 4-6 years [ ] 7+ years
"""

    # Section B: Likert Scale (Generated per objective)
    likert_questions = ""
    for i, obj in enumerate(specific_objs, 1):
        prompt = f"""Generate 5 Likert scale questionnaire items (statements) for the objective: "{obj}".
        Format: Just the statements, numbered 1-5. No intro text.
        Topic: {topic}."""
        statements_text = await deepseek_direct_service.generate_content(prompt, max_tokens=200)
        
        # Format as table rows (text representation)
        rows = ""
        items = statements_text.strip().split('\n')
        for item in items:
            clean_item = item.strip().lstrip('1234567890. ')
            if clean_item:
                rows += f"| {clean_item} | | | | | |\n"
        
        likert_questions += f"""
**SECTION B{i}: QUESTIONS ON OBJECTIVE {i}**
**{obj}**

| Statement | SA | A | N | D | SD |
| :--- | :---: | :---: | :---: | :---: | :---: |
{rows}
*(Key: SA=Strongly Agree, A=Agree, N=Neutral, D=Disagree, SD=Strongly Disagree)*
"""

    # Section C: Open Ended
    open_ended = "**SECTION C: GENERAL VIEWS**\n\n"
    prompt_open = f"""Generate 3 open-ended research questions about {topic} covering the objectives: {specific_objs}.
    Format: Numbered 1-3. Leave space for writing."""
    open_text = await deepseek_direct_service.generate_content(prompt_open, max_tokens=200)
    
    open_ended += open_text + "\n\n**THANK YOU FOR YOUR PARTICIPATION!**"
    
    return f"{appendix_i}\n<div style='page-break-after: always;'></div>\n{questionnaire_intro}\n{likert_questions}\n{open_ended}\n"
