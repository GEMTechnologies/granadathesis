"""
Appendix Generation Module for Study Tools

This module generates research instruments as separate appendix files:
- Questionnaires (Likert-scale, demographics)
- Interview Guides (semi-structured, key informant)
- FGD Guides (focus group facilitation)
- Observation Checklists (structured observation)
- Document Analysis Frameworks (content analysis matrices)
- Desktop Review Protocols (secondary data analysis)
- Key Informant Interview Guides
- Survey Instruments

Methodology-Driven: Analyzes Chapter 3 content to determine appropriate tools.
"""

import os
import re
from typing import List, Dict, Any, Optional
from datetime import datetime


class AppendixGenerator:
    """Generates study tools as separate appendix markdown files.
    
    Enhanced version: Analyzes methodology content to determine appropriate
    research instruments based on:
    - Research design (qualitative, quantitative, mixed methods)
    - Data collection methods mentioned
    - Variables identified
    - Sampling strategy
    """
    
    def __init__(
        self, 
        workspace_dir: str, 
        topic: str, 
        case_study: str, 
        objectives: List[str],
        methodology_content: str = "",
        variables: Dict[str, List[str]] = None,
        research_questions: List[str] = None
    ):
        self.workspace_dir = workspace_dir
        self.topic = topic
        self.case_study = case_study
        self.objectives = objectives or []
        self.methodology_content = methodology_content.lower() if methodology_content else ""
        self.variables = variables or {"independent": [], "dependent": [], "moderating": []}
        self.research_questions = research_questions or []
        self.appendices_dir = os.path.join(workspace_dir, "appendices")
        
        # Analyze methodology to determine research design
        self.research_design = self._detect_research_design()
        self.data_collection_methods = self._detect_data_collection_methods()
        
        # Create appendices directory
        os.makedirs(self.appendices_dir, exist_ok=True)
    
    def _detect_research_design(self) -> str:
        """Detect research design from methodology content."""
        content = self.methodology_content
        
        # Check for mixed methods first
        if any(term in content for term in ['mixed method', 'mixed-method', 'pragmati', 'triangulat', 'both qualitative and quantitative']):
            return 'mixed_methods'
        
        # Check for qualitative
        qualitative_markers = ['qualitative', 'phenomenol', 'grounded theory', 'ethnograph', 'case study design', 
                               'interpretivist', 'constructivist', 'narrative', 'thematic analysis']
        if any(term in content for term in qualitative_markers):
            if any(term in content for term in ['quantitative', 'survey', 'statistical', 'regression']):
                return 'mixed_methods'
            return 'qualitative'
        
        # Check for quantitative
        quantitative_markers = ['quantitative', 'positivist', 'deductive', 'statistical', 'regression', 
                                'correlation', 'experimental', 'quasi-experimental', 'survey design']
        if any(term in content for term in quantitative_markers):
            return 'quantitative'
        
        # Default based on objectives
        objectives_text = " ".join(self.objectives).lower()
        if any(term in objectives_text for term in ['measure', 'determine', 'assess', 'relationship']):
            return 'quantitative'
        if any(term in objectives_text for term in ['explore', 'understand', 'experience']):
            return 'qualitative'
        
        return 'mixed_methods'  # Default to mixed if unclear
    
    def _detect_data_collection_methods(self) -> List[str]:
        """Detect data collection methods from methodology content."""
        methods = []
        content = self.methodology_content + " " + " ".join(self.objectives).lower()
        
        # Primary data methods
        method_patterns = {
            'questionnaire': ['questionnaire', 'survey instrument', 'structured survey', 'likert', 
                             'self-administered', 'survey questionnaire'],
            'interview': ['interview', 'semi-structured', 'in-depth interview', 'key informant', 
                         'face-to-face', 'telephonic interview'],
            'fgd': ['focus group', 'fgd', 'group discussion', 'group interview'],
            'observation': ['observation', 'field observation', 'participant observation', 
                           'non-participant observation', 'direct observation', 'systematic observation'],
            'experiment': ['experiment', 'experimental', 'quasi-experimental', 'control group', 
                          'treatment group', 'random assignment'],
        }
        
        # Secondary data methods  
        secondary_patterns = {
            'document_analysis': ['document analysis', 'documentary analysis', 'content analysis', 
                                 'archival', 'policy analysis', 'records', 'reports'],
            'desktop_review': ['secondary data', 'desktop review', 'literature review', 
                              'existing data', 'published data', 'meta-analysis', 'systematic review'],
        }
        
        # Check primary methods
        for method, patterns in method_patterns.items():
            if any(pattern in content for pattern in patterns):
                methods.append(method)
        
        # Check secondary methods
        for method, patterns in secondary_patterns.items():
            if any(pattern in content for pattern in patterns):
                methods.append(method)
        
        # If nothing detected, infer from research design
        if not methods:
            if self.research_design == 'quantitative':
                methods = ['questionnaire']
            elif self.research_design == 'qualitative':
                methods = ['interview']
            else:  # mixed methods
                methods = ['questionnaire', 'interview']
        
        return methods
    
    def analyse_objectives_for_tools(self) -> List[str]:
        """
        Analyzes methodology and objectives to determine which study tools are needed.
        Enhanced: Uses methodology content for accurate detection.
        
        Returns:
            List of tool types to generate
        """
        tools = []
        
        # Use detected data collection methods
        method_to_tool = {
            'questionnaire': 'questionnaire',
            'interview': 'interview_guide',
            'fgd': 'fgd_guide',
            'observation': 'observation_checklist',
            'document_analysis': 'document_analysis',
            'desktop_review': 'desktop_review',
            'experiment': 'questionnaire',  # Experiments often use questionnaires for measurement
        }
        
        for method in self.data_collection_methods:
            tool = method_to_tool.get(method)
            if tool and tool not in tools:
                tools.append(tool)
        
        # For mixed methods, ensure both qual and quant tools
        if self.research_design == 'mixed_methods':
            if 'questionnaire' not in tools:
                tools.insert(0, 'questionnaire')
            if 'interview_guide' not in tools:
                tools.append('interview_guide')
        
        # Fallback: at least one tool
        if not tools:
            tools.append('questionnaire')
        
        print(f"📋 Research Design: {self.research_design}")
        print(f"📋 Data Collection: {self.data_collection_methods}")
        print(f"📋 Study Tools to Generate: {tools}")
        
        return tools

    
    async def _generate_questionnaire_items_ai(self, objective: str, section_num: int) -> str:
        """Uses AI to generate Likert-scale questionnaire items for a specific objective."""
        try:
            from services.deepseek_direct_service import deepseek_service
            
            prompt = f"""Generate 8 Likert-scale questionnaire items to measure the following research objective:

OBJECTIVE: {objective}

TOPIC: {self.topic}
CASE STUDY: {self.case_study}

Requirements:
1. Generate EXACTLY 8 statements that can be measured on a 5-point Likert scale
2. Each statement should be clear, specific, and directly related to the objective
3. Statements should be in declarative form (e.g., "I believe that...", "The organization has...", "There is adequate...")
4. Avoid double-barreled questions (two ideas in one statement)
5. Mix positive and negative worded items

Format your response as a numbered list ONLY, no explanations:
1. [Statement 1]
2. [Statement 2]
3. [Statement 3]
4. [Statement 4]
5. [Statement 5]
6. [Statement 6]
7. [Statement 7]
8. [Statement 8]
"""
            
            response = await deepseek_service.generate(
                prompt=prompt,
                max_tokens=800,
                temperature=0.7
            )
            
            # Parse the response into items
            items = []
            for line in response.strip().split('\n'):
                line = line.strip()
                if line and line[0].isdigit():
                    # Remove number prefix
                    parts = line.split('.', 1)
                    if len(parts) > 1:
                        item = parts[1].strip()
                        items.append(item)
            
            # Build table rows
            table_rows = ""
            for i, item in enumerate(items[:8], 1):
                table_rows += f"| {i}   | {item} | 1 | 2 | 3 | 4 | 5 |\n"
            
            return table_rows
            
        except Exception as e:
            print(f"⚠️ AI questionnaire generation failed: {e}")
            # Fallback to generic items
            return self._generate_fallback_items(objective, section_num)
    
    def _generate_fallback_items(self, objective: str, section_num: int) -> str:
        """Generate fallback items when AI is unavailable."""
        # Extract key terms from objective
        keywords = objective.lower().replace("to ", "").split()[:5]
        keyword_phrase = " ".join(keywords)
        
        fallback_items = [
            f"The current approach to {keyword_phrase} is effective.",
            f"There is adequate awareness of {keyword_phrase}.",
            f"Resources allocated for {keyword_phrase} are sufficient.",
            f"Stakeholders are actively involved in {keyword_phrase}.",
            f"Policies regarding {keyword_phrase} are well implemented.",
            f"Training on {keyword_phrase} is regularly provided.",
            f"Monitoring of {keyword_phrase} is consistently done.",
            f"Outcomes related to {keyword_phrase} meet expectations.",
        ]
        
        table_rows = ""
        for i, item in enumerate(fallback_items, 1):
            table_rows += f"| {i}   | {item} | 1 | 2 | 3 | 4 | 5 |\n"
        
        return table_rows
    
    async def _generate_interview_theme_ai(self, objective: str, theme_num: int) -> str:
        """Uses AI to generate interview questions for a specific objective."""
        try:
            from services.deepseek_direct_service import deepseek_service
            
            prompt = f"""Generate interview questions for the following research objective:

OBJECTIVE: {objective}

TOPIC: {self.topic}
CASE STUDY: {self.case_study}

Requirements:
1. Generate 1 MAIN open-ended question that explores this objective
2. Generate 4 PROBING questions to deepen the discussion
3. Generate 2 FOLLOW-UP questions

Format your response EXACTLY as follows (no extra text):
MAIN: [Your main question here]
PROBE1: [First probing question]
PROBE2: [Second probing question]
PROBE3: [Third probing question]
PROBE4: [Fourth probing question]
FOLLOWUP1: [First follow-up question]
FOLLOWUP2: [Second follow-up question]
"""
            
            response = await deepseek_service.generate(
                prompt=prompt,
                max_tokens=600,
                temperature=0.7
            )
            
            # Parse the response
            main_q = ""
            probes = []
            followups = []
            
            for line in response.strip().split('\n'):
                line = line.strip()
                if line.startswith('MAIN:'):
                    main_q = line.replace('MAIN:', '').strip().strip('"')
                elif line.startswith('PROBE'):
                    probe = line.split(':', 1)[-1].strip().strip('"')
                    if probe:
                        probes.append(probe)
                elif line.startswith('FOLLOWUP'):
                    followup = line.split(':', 1)[-1].strip().strip('"')
                    if followup:
                        followups.append(followup)
            
            # Build the theme section
            theme_section = f"""
---

**THEME {theme_num}: {objective[:80]}{'...' if len(objective) > 80 else ''}**

*Objective:* {objective}

**Main Question {theme_num}:**
"{main_q if main_q else f"Can you describe your experience with {objective.lower()[:50]}?"}"

**Probes:**
"""
            for probe in (probes[:4] if probes else [
                "Can you give me a specific example?",
                "How did that situation impact you/the organization?",
                "What were the main contributing factors?",
                "Can you elaborate on that point?"
            ]):
                theme_section += f'- "{probe}"\n'
            
            theme_section += """
**Follow-up:**
"""
            for followup in (followups[:2] if followups else [
                "Is there anything else about this you'd like to share?",
                "What would you suggest for improvement?"
            ]):
                theme_section += f'- "{followup}"\n'
            
            return theme_section
            
        except Exception as e:
            print(f"⚠️ AI interview generation failed: {e}")
            return self._generate_fallback_interview_theme(objective, theme_num)
    
    def _generate_fallback_interview_theme(self, objective: str, theme_num: int) -> str:
        """Generate fallback interview theme when AI is unavailable."""
        keywords = objective.lower().replace("to ", "").split()[:5]
        keyword_phrase = " ".join(keywords)
        
        return f"""
---

**THEME {theme_num}: {objective[:80]}{'...' if len(objective) > 80 else ''}**

*Objective:* {objective}

**Main Question {theme_num}:**
"Can you describe your experience with {keyword_phrase}?"

**Probes:**
- "Can you give me a specific example?"
- "How did that situation impact you/the organization?"
- "What were the key challenges you faced?"
- "Can you elaborate on that point?"

**Follow-up:**
- "Is there anything else about {keyword_phrase} you'd like to share?"
- "What recommendations would you make for improvement?"
"""

    
    async def generate_all_appendices(self) -> List[str]:
        """
        Generates all appropriate appendices based on objectives.
        
        Returns:
            List of generated file paths
        """
        tools_needed = self.analyse_objectives_for_tools()
        generated_files = []
        
        for tool in tools_needed:
            if tool == 'questionnaire':
                file_path = await self.generate_questionnaire()
                generated_files.append(file_path)
            
            elif tool == 'interview_guide':
                file_path = await self.generate_interview_guide()
                generated_files.append(file_path)
            
            elif tool == 'fgd_guide':
                file_path = await self.generate_fgd_guide()
                generated_files.append(file_path)
            
            elif tool == 'observation_checklist':
                file_path = await self.generate_observation_checklist()
                generated_files.append(file_path)
            
            elif tool == 'document_analysis':
                file_path = await self.generate_document_analysis()
                generated_files.append(file_path)
            
            elif tool == 'desktop_review':
                file_path = await self.generate_desktop_review()
                generated_files.append(file_path)
        
        return generated_files
    
    async def generate_questionnaire(self) -> str:
        """Generates structured questionnaire appendix with AI-generated items."""
        
        # Generate sections for each objective
        objective_sections = ""
        section_letter = ord('B')  # Start from Section B
        
        for i, objective in enumerate(self.objectives if self.objectives else []):
            # Generate AI-powered questionnaire items
            items_table = await self._generate_questionnaire_items_ai(objective, i + 1)
            
            objective_sections += f"""
---

### SECTION {chr(section_letter)}: {objective[:80]}{'...' if len(objective) > 80 else ''}

**Objective:** {objective}

**Instructions:** Please indicate your level of agreement with each statement using the scale below:

**Scale:**
- **1** = Strongly Disagree (SD)
- **2** = Disagree (D)
- **3** = Neutral (N)
- **4** = Agree (A)
- **5** = Strongly Agree (SA)

| No. | Statement | SD | D | N | A | SA |
|-----|-----------|:--:|:--:|:--:|:--:|:--:|
{items_table}
"""
            section_letter += 1
        
        # If no objectives, create a general section
        if not objective_sections:
            objective_sections = """
---

### SECTION B: GENERAL PERCEPTIONS

**Instructions:** Please indicate your level of agreement with each statement.

| No. | Statement | SD | D | N | A | SA |
|-----|-----------|:--:|:--:|:--:|:--:|:--:|
| 1   | I am familiar with the topic under study. | 1 | 2 | 3 | 4 | 5 |
| 2   | Current measures addressing this issue are effective. | 1 | 2 | 3 | 4 | 5 |
| 3   | Resources allocated for this area are sufficient. | 1 | 2 | 3 | 4 | 5 |
| 4   | Stakeholder engagement is adequate. | 1 | 2 | 3 | 4 | 5 |
| 5   | Policy implementation has been successful. | 1 | 2 | 3 | 4 | 5 |
| 6   | Training and capacity building are prioritized. | 1 | 2 | 3 | 4 | 5 |
| 7   | Monitoring and evaluation systems are functional. | 1 | 2 | 3 | 4 | 5 |
| 8   | Overall outcomes meet expectations. | 1 | 2 | 3 | 4 | 5 |
"""
        
        content = f"""# APPENDIX A: STRUCTURED QUESTIONNAIRE

## RESEARCH QUESTIONNAIRE

**Study Title:** {self.topic}

**Case Study:** {self.case_study}

**Researcher:** [To be filled]

**Institution:** [To be filled]

**Date:** {datetime.now().strftime('%B %Y')}

---

### INTRODUCTION

Dear Respondent,

I am conducting a research study on **{self.topic}** in the context of **{self.case_study}**. Your participation in this study is voluntary and all information provided will be kept strictly confidential. The questionnaire will take approximately 15-20 minutes to complete.

Thank you for your valuable time and cooperation.

---

### SECTION A: DEMOGRAPHIC INFORMATION

Please tick (✓) the appropriate box or fill in the blank.

**1. Age Group:**
- [ ] 18-25 years
- [ ] 26-35 years
- [ ] 36-45 years
- [ ] 46-55 years
- [ ] 56 years and above

**2. Gender:**
- [ ] Male
- [ ] Female
- [ ] Prefer not to say

**3. Highest Education Level:**
- [ ] Diploma
- [ ] Bachelor's Degree
- [ ] Master's Degree
- [ ] PhD
- [ ] Other (please specify): __________

**4. Work Experience:**
- [ ] Less than 2 years
- [ ] 2-5 years
- [ ] 6-10 years
- [ ] 11-15 years
- [ ] More than 15 years

**5. Position/Rank:**
- [ ] Senior Manager/Executive
- [ ] Middle Manager
- [ ] Junior Manager/Supervisor
- [ ] Officer/Staff
- [ ] Other (please specify): __________

**6. Type of Organization:**
- [ ] Public Sector
- [ ] Private Sector
- [ ] NGO/Non-Profit
- [ ] Other (please specify): __________

{objective_sections}

---

### OPEN-ENDED QUESTIONS

**1.** What challenges have you experienced regarding {self.topic.lower()}?

_________________________________________________________________

_________________________________________________________________

**2.** What recommendations would you suggest for improvement?

_________________________________________________________________

_________________________________________________________________

**3.** Any additional comments?

_________________________________________________________________

---

**THANK YOU FOR YOUR PARTICIPATION!**

*Your responses are valuable to this research and will be treated with utmost confidentiality.*

---

**For Official Use Only:**

Questionnaire No.: __________

Date Received: __________

Data Entry: __________
"""
        
        file_path = os.path.join(self.appendices_dir, "Appendix_A_Questionnaire.md")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return file_path

    
    async def generate_interview_guide(self) -> str:
        """Generates semi-structured interview guide appendix with AI-generated themes."""
        
        # Generate interview themes for each objective
        interview_themes = ""
        for i, objective in enumerate(self.objectives if self.objectives else [], 1):
            theme_content = await self._generate_interview_theme_ai(objective, i)
            interview_themes += theme_content
        
        # If no objectives, add default themes
        if not interview_themes:
            interview_themes = """
---

**THEME 1: Background and Context**

**Main Question 1:**
"Can you describe your experience and involvement with the topic of this study?"

**Probes:**
- "Can you give me a specific example?"
- "How did that situation impact you/the organization?"
- "What were the main contributing factors?"
- "Can you elaborate on that point?"

**Follow-up:**
- "Is there anything else you'd like to share?"

---

**THEME 2: Challenges and Barriers**

**Main Question 2:**
"What challenges have you encountered in this area?"

**Probes:**
- "How did these challenges affect operations?"
- "What resources were lacking?"
- "How did you respond to these challenges?"

**Follow-up:**
- "What support would have been helpful?"

---

**THEME 3: Recommendations**

**Main Question 3:**
"Based on your experience, what recommendations would you make for improvement?"

**Probes:**
- "What specific changes would you suggest?"
- "Who should be responsible for these changes?"
- "What would success look like?"

**Follow-up:**
- "Is there anything else you'd like to add?"
"""
        
        content = f"""# APPENDIX B: SEMI-STRUCTURED INTERVIEW GUIDE

## IN-DEPTH INTERVIEW GUIDE

**Study Title:** {self.topic}

**Case Study:** {self.case_study}

**Research Design:** {self.research_design.replace('_', ' ').title()}

**Interviewer:** __________

**Date:** __________

**Time:** From ________ To ________

**Location:** __________

**Participant Code:** __________

**Position/Role:** __________

---

### PRE-INTERVIEW CHECKLIST

- [ ] Recording device tested and working
- [ ] Consent form signed
- [ ] Participant information sheet provided
- [ ] Quiet, private location secured
- [ ] Backup recording device available
- [ ] Note-taking materials ready

---

### INTRODUCTION (5 minutes)

**Opening Script:**

"Good [morning/afternoon], and thank you for agreeing to participate in this interview. My name is [name], and I am conducting research on **{self.topic}** in the context of **{self.case_study}**.

This interview will take approximately 45-60 minutes. With your permission, I would like to record our conversation to ensure I capture your responses accurately. All information will be kept strictly confidential, and you may choose not to answer any question or stop the interview at any time.

Do you have any questions before we begin?"

**Ice Breaker:**
- "Could you tell me a bit about your role and how long you've been in this position?"

---

### MAIN INTERVIEW QUESTIONS

{interview_themes}

---

**CLOSING THEME: Recommendations and Future Outlook**

**Main Question:**
"Based on your experience, what recommendations would you make for relevant stakeholders?"

**Probes:**
- "What specific changes would you suggest?"
- "What barriers might prevent these changes?"
- "What would success look like?"

---

### CLOSING (5 minutes)

**Summary Check:**
"Just to make sure I understood correctly, you mentioned [summarize key points]. Is that accurate? Is there anything I missed or misunderstood?"

**Additional Comments:**
"Is there anything else you'd like to add that we haven't covered in our discussion?"

**Next Steps:**
"Thank you so much for your time and insights. The information you've shared is very valuable to this research. I will be analyzing all interviews and may need to follow up with some participants for clarification. Would you be open to a brief follow-up if needed?"

**Closing:**
"If you have any questions later or would like to know about the research findings, please feel free to contact me at [contact information]. Thank you again for your participation."

---

### POST-INTERVIEW NOTES

**Interview Quality:**
- [ ] Excellent (participant very engaged, detailed responses)
- [ ] Good (participant engaged, adequate detail)
- [ ] Fair (some engagement, limited detail)
- [ ] Poor (participant disengaged or brief responses)

**Observations:**

**Body Language:**
_________________________________________________________________

**Emotional Responses:**
_________________________________________________________________

**Context/Environment:**
_________________________________________________________________

**Key Themes Emerged:**
1. _________________________________________________________________
2. _________________________________________________________________
3. _________________________________________________________________

**Surprising Insights:**
_________________________________________________________________

**Areas Needing Follow-up:**
_________________________________________________________________

**Interviewer Reflections:**
_________________________________________________________________

**Duration:** ________ minutes

**Recording File Name:** __________

**Transcription Status:** [ ] Pending [ ] In Progress [ ] Complete
"""
        
        file_path = os.path.join(self.appendices_dir, "Appendix_B_Interview_Guide.md")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return file_path
    
    async def generate_fgd_guide(self) -> str:
        """Generates FGD facilitation guide appendix."""
        content = f"""# APPENDIX C: FOCUS GROUP DISCUSSION GUIDE

## FGD FACILITATION GUIDE

**Study Title:** {self.topic}

**Case Study:** {self.case_study}

**Facilitator:** __________

**Note-taker:** __________

**Date:** __________

**Venue:** __________

**Session Number:** ________ of ________

**Number of Participants:** ________ (Ideal: 6-10)

---

### PRE-SESSION CHECKLIST

**Logistics:**
- [ ] Room booked and arranged (circular/U-shaped seating)
- [ ] Recording equipment tested (audio/video)
- [ ] Consent forms prepared (one per participant)
- [ ] Name tags/cards ready
- [ ] Refreshments arranged
- [ ] Flip chart, markers, and sticky notes available
- [ ] Participant information sheets printed
- [ ] Attendance sheet prepared

**Materials:**
- [ ] FGD guide printed
- [ ] Ground rules poster
- [ ] Visual aids (if needed)
- [ ] Backup recording device
- [ ] Pens and notepads for participants

---

### SESSION STRUCTURE (Total: 90-120 minutes)

---

## PART 1: INTRODUCTION (10-15 minutes)

**Facilitator Opening Script:**

"Good [morning/afternoon], everyone, and welcome! Thank you all for taking the time to join us today. My name is [name], and I'll be facilitating our discussion. [Note-taker name] will be taking notes to help us capture all your valuable insights.

Today, we're here to discuss **{self.topic}** in the context of **{self.case_study}**. This is a research study, and we're very interested in hearing your experiences, opinions, and ideas.

**Important Points:**
- There are no right or wrong answers—we want your honest opinions
- We expect different viewpoints, and that's perfectly fine
- Please speak one at a time so we can hear everyone
- Everything shared here is confidential
- We'll be recording the session to ensure we don't miss anything
- You may choose not to answer any question
- Feel free to agree or disagree with others respectfully

**Ground Rules:**
1. One person speaks at a time
2. Respect all viewpoints—no judgement
3. No side conversations
4. Phones on silent
5. What's said here stays here (confidentiality)
6. Participate actively—all voices matter
7. It's okay to disagree, but be respectful

Does everyone agree to these ground rules? Any questions before we start?"

**Consent:**
"Before we begin, please review and sign the consent form. This confirms that you're participating voluntarily and understand how the information will be used."

---

## PART 2: WARM-UP (5-10 minutes)

**Introductions:**
"Let's go around the circle. Please share:
- Your first name
- Your role/position
- One word that describes your experience with [topic]"

[Allow each participant to introduce themselves]

---

## PART 3: MAIN DISCUSSION

### TOPIC 1: [Based on Research Objective 1] (20 minutes)

**Opening Question:**
"Let's start by talking about [topic from objective 1]. What are your general thoughts or experiences with this?"

**Probing Questions:**
- "Can someone give a specific example?"
- "Has anyone had a different experience?"
- "Why do you think that is?"
- "How does this affect [relevant area]?"

**Facilitator Notes:**
- Encourage quiet participants: "We haven't heard from [name] yet. What's your perspective?"
- Manage dominant participants: "Thank you, [name]. Let's hear from others as well."
- Probe for depth: "Can you tell us more about that?"

---

### TOPIC 2: [Based on Research Objective 2] (20 minutes)

**Key Question:**
"Now let's discuss [topic from objective 2]. How would you describe [specific aspect]?"

**Probing Questions:**
- "What challenges have you encountered?"
- "How did you address these challenges?"
- "What support did you receive?"
- "What would make this better?"

**Activity (Optional):**
"I'm going to give you sticky notes. Please write down the top 3 [challenges/benefits/factors]. Then we'll share and discuss."

---

### TOPIC 3: [Based on Research Objective 3] (20 minutes)

**Key Question:**
"Let's explore [topic from objective 3]. What are your views on this?"

**Probing Questions:**
- "How has this changed over time?"
- "What factors influence this?"
- "How does this compare to [comparison]?"
- "What would ideal look like?"

---

### TOPIC 4: [Based on Research Objective 4] (15 minutes)

**Key Question:**
"Finally, let's discuss [topic from objective 4]."

**Probing Questions:**
- "What's working well?"
- "What's not working?"
- "What needs to change?"
- "Who should be responsible for these changes?"

---

## PART 4: RECOMMENDATIONS (10 minutes)

**Question:**
"Based on our discussion, what recommendations would you make to [relevant stakeholders] regarding {self.topic}?"

**Probes:**
- "What specific actions should be taken?"
- "What resources are needed?"
- "What barriers might prevent this?"
- "How can these barriers be overcome?"

---

## PART 5: CLOSING (10 minutes)

**Summary:**
"Let me summarize the main points I've heard today:
1. [Point 1]
2. [Point 2]
3. [Point 3]
...

Have I captured this correctly? Is there anything I missed?"

**Final Thoughts:**
"Before we close, is there anything else anyone would like to add that we haven't covered?"

**Wrap-up:**
"Thank you all so much for your time and valuable insights. Your contributions will greatly inform this research. 

**Next Steps:**
- We'll analyse all the discussions
- Findings will be compiled into a report
- You'll be invited to a feedback session [if applicable]
- Feel free to contact me if you have questions

[Distribute incentives if applicable]

Thank you again, and have a great [day/evening]!"

---

### POST-SESSION TASKS

**Immediate (Within 1 hour):**
- [ ] Debrief with note-taker
- [ ] Check recording quality
- [ ] Document initial impressions
- [ ] Note any technical issues

**Within 24 hours:**
- [ ] Transcribe key quotes
- [ ] Identify emerging themes
- [ ] Note areas needing follow-up
- [ ] Compare with other FGDs (if applicable)

---

### FACILITATOR NOTES

**Group Dynamics:**

**Dominant Participants:**
_________________________________________________________________

**Quiet Participants:**
_________________________________________________________________

**Conflicts/Disagreements:**
_________________________________________________________________

**Group Cohesion:**
- [ ] Excellent
- [ ] Good
- [ ] Fair
- [ ] Poor

**Key Themes Identified:**
1. _________________________________________________________________
2. _________________________________________________________________
3. _________________________________________________________________
4. _________________________________________________________________

**Surprising Insights:**
_________________________________________________________________

**Consensus Points:**
_________________________________________________________________

**Divergent Views:**
_________________________________________________________________

**Areas Needing Clarification:**
_________________________________________________________________

**Session Quality:**
- [ ] Excellent (very engaged, rich discussion)
- [ ] Good (engaged, adequate depth)
- [ ] Fair (some engagement, limited depth)
- [ ] Poor (low engagement, superficial)

**Recommendations for Next FGD:**
_________________________________________________________________

**Duration:** ________ minutes

**Recording File Names:**
- Audio: __________
- Video (if applicable): __________

**Transcription Status:** [ ] Pending [ ] In Progress [ ] Complete
"""
        
        file_path = os.path.join(self.appendices_dir, "Appendix_C_FGD_Guide.md")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return file_path
    
    async def generate_observation_checklist(self) -> str:
        """Generates observation checklist appendix."""
        content = f"""# APPENDIX D: STRUCTURED OBSERVATION CHECKLIST

## OBSERVATION PROTOCOL

**Study Title:** {self.topic}

**Case Study:** {self.case_study}

**Observer:** __________

**Date:** __________

**Time:** From ________ To ________

**Location:** __________

**Observation Session:** ________ of ________

**Type of Observation:**
- [ ] Participant Observation
- [ ] Non-Participant Observation
- [ ] Structured Observation
- [ ] Unstructured Observation

---

### OBSERVATION CONTEXT

**Setting Description:**

**Physical Environment:**
_________________________________________________________________

**Number of People Present:** __________

**Activities Occurring:**
_________________________________________________________________

**Weather/Environmental Conditions:**
_________________________________________________________________

**Special Circumstances:**
_________________________________________________________________

---

### OBSERVATION CATEGORIES

**CATEGORY 1: [Behavior/Practice from Objective 1]**

| Time | Behavior Observed | Frequency | Duration | Participants | Context/Notes |
|------|-------------------|-----------|----------|--------------|---------------|
|      |                   |           |          |              |               |
|      |                   |           |          |              |               |
|      |                   |           |          |              |               |
|      |                   |           |          |              |               |

**Frequency Rating:**
- [ ] Never observed (0 times)
- [ ] Rarely observed (1-2 times)
- [ ] Sometimes observed (3-5 times)
- [ ] Often observed (6-10 times)
- [ ] Always/Continuously observed (>10 times)

**Quality Rating:**
- [ ] Excellent
- [ ] Good
- [ ] Fair
- [ ] Poor

---

**CATEGORY 2: [Behavior/Practice from Objective 2]**

| Time | Behavior Observed | Frequency | Duration | Participants | Context/Notes |
|------|-------------------|-----------|----------|--------------|---------------|
|      |                   |           |          |              |               |
|      |                   |           |          |              |               |
|      |                   |           |          |              |               |

**Frequency Rating:**
- [ ] Never
- [ ] Rarely
- [ ] Sometimes
- [ ] Often
- [ ] Always

---

**CATEGORY 3: Interaction Patterns**

| Time | Interaction Type | Participants | Frequency | Quality | Outcome | Notes |
|------|------------------|--------------|-----------|---------|---------|-------|
|      |                  |              |           |         |         |       |
|      |                  |              |           |         |         |       |

**Interaction Quality:**
- [ ] Collaborative
- [ ] Competitive
- [ ] Neutral
- [ ] Conflictual

---

### ENVIRONMENTAL FACTORS

**Physical Space:**

**Layout/Arrangement:**
_________________________________________________________________

**Resources Available:**
_________________________________________________________________

**Accessibility:**
_________________________________________________________________

**Comfort Level:**
- [ ] Very comfortable
- [ ] Comfortable
- [ ] Neutral
- [ ] Uncomfortable
- [ ] Very uncomfortable

**Social Atmosphere:**

**Formality:**
- [ ] Very formal
- [ ] Formal
- [ ] Neutral
- [ ] Informal
- [ ] Very informal

**Collaboration Level:**
- [ ] Highly collaborative
- [ ] Collaborative
- [ ] Neutral
- [ ] Competitive
- [ ] Highly competitive

**Inclusivity:**
- [ ] Very inclusive
- [ ] Inclusive
- [ ] Neutral
- [ ] Exclusive
- [ ] Very exclusive

---

### CRITICAL INCIDENTS

**Incident 1:**

**Time:** __________

**What Happened:**
_________________________________________________________________

**Who Was Involved:**
_________________________________________________________________

**Context:**
_________________________________________________________________

**Significance:**
_________________________________________________________________

**Incident 2:**

**Time:** __________

**What Happened:**
_________________________________________________________________

**Who Was Involved:**
_________________________________________________________________

**Context:**
_________________________________________________________________

**Significance:**
_________________________________________________________________

---

### OBSERVER REFLECTIONS

**Initial Impressions:**
_________________________________________________________________

**Patterns Noticed:**
_________________________________________________________________

**Unexpected Observations:**
_________________________________________________________________

**Questions Arising:**
_________________________________________________________________

**Hypotheses Forming:**
_________________________________________________________________

**Bias Check:**

"How might my presence have influenced the behaviours observed?"
_________________________________________________________________

"What assumptions am I making?"
_________________________________________________________________

"What alternative interpretations exist?"
_________________________________________________________________

---

### FOLLOW-UP ACTIONS

**Areas Needing Further Observation:**
_________________________________________________________________

**Questions for Participants:**
_________________________________________________________________

**Next Observation Focus:**
_________________________________________________________________

---

### OBSERVATION SUMMARY

**Total Duration:** ________ minutes

**Overall Assessment:**
- [ ] Very productive observation
- [ ] Productive observation
- [ ] Somewhat productive
- [ ] Limited productivity

**Data Quality:**
- [ ] Excellent
- [ ] Good
- [ ] Fair
- [ ] Poor

**Recommendations for Next Observation:**
_________________________________________________________________

**Observer Signature:** __________

**Date:** __________
"""
        
        file_path = os.path.join(self.appendices_dir, "Appendix_D_Observation_Checklist.md")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return file_path
    
    async def generate_document_analysis(self) -> str:
        """Generates document analysis framework appendix."""
        content = f"""# APPENDIX E: DOCUMENT ANALYSIS FRAMEWORK

## DOCUMENTARY ANALYSIS PROTOCOL

**Study Title:** {self.topic}

**Case Study:** {self.case_study}

**Analyst:** __________

**Analysis Period:** From ________ To ________

---

### DOCUMENT SELECTION CRITERIA

**Inclusion Criteria:**
- [ ] Published/Created between [start year] and [end year]
- [ ] Related to {self.topic}
- [ ] From {self.case_study}
- [ ] In English [or specify languages]
- [ ] Accessible and complete
- [ ] Official/verified sources
- [ ] [Other criteria specific to study]

**Exclusion Criteria:**
- [ ] Published before [year]
- [ ] Not related to study topic
- [ ] Incomplete or fragmented
- [ ] Unverified sources
- [ ] Duplicate documents
- [ ] [Other exclusion criteria]

---

### DOCUMENT INVENTORY

| Doc ID | Title | Author/Source | Date | Type | Format | Pages | Relevance (1-5) | Status |
|--------|-------|---------------|------|------|--------|-------|-----------------|--------|
| D001   |       |               |      |      |        |       |                 |        |
| D002   |       |               |      |      |        |       |                 |        |
| D003   |       |               |      |      |        |       |                 |        |
| D004   |       |               |      |      |        |       |                 |        |
| D005   |       |               |      |      |        |       |                 |        |

**Document Types:**
- [ ] Policy documents
- [ ] Reports (annual, technical, research)
- [ ] Strategic plans
- [ ] Meeting minutes
- [ ] Correspondence
- [ ] Legal documents
- [ ] Statistical records
- [ ] Media articles
- [ ] Other: __________

---

### ANALYSIS DIMENSIONS

**DIMENSION 1: [From Research Objective 1]**

**Coding Categories:**

**Category 1.1:** [Sub-dimension 1]
- **Definition:** _________________________________________________________________
- **Indicators:** _________________________________________________________________

**Category 1.2:** [Sub-dimension 2]
- **Definition:** _________________________________________________________________
- **Indicators:** _________________________________________________________________

**Data Extraction:**

| Doc ID | Category 1.1 | Category 1.2 | Quotes/Evidence | Page/Section | Notes |
|--------|--------------|--------------|-----------------|--------------|-------|
|        |              |              |                 |              |       |
|        |              |              |                 |              |       |

---

**DIMENSION 2: [From Research Objective 2]**

**Coding Categories:**

**Category 2.1:** [Sub-dimension 1]
- **Definition:** _________________________________________________________________
- **Indicators:** _________________________________________________________________

**Category 2.2:** [Sub-dimension 2]
- **Definition:** _________________________________________________________________
- **Indicators:** _________________________________________________________________

**Data Extraction:**

| Doc ID | Category 2.1 | Category 2.2 | Quotes/Evidence | Page/Section | Notes |
|--------|--------------|--------------|-----------------|--------------|-------|
|        |              |              |                 |              |       |
|        |              |              |                 |              |       |

---

### QUALITY ASSESSMENT

**For Each Document:**

**Authenticity:**
- [ ] Original source
- [ ] Verified copy
- [ ] Secondary source
- [ ] Questionable origin

**Credibility:**
- [ ] Official document
- [ ] Peer-reviewed
- [ ] Expert-authored
- [ ] Anecdotal
- [ ] Unverified

**Representativeness:**
- [ ] Typical of its kind
- [ ] Unique/exceptional
- [ ] Unclear

**Completeness:**
- [ ] Complete document
- [ ] Partial document
- [ ] Fragments only
- [ ] Missing sections

**Meaning/Clarity:**
- [ ] Very clear
- [ ] Clear
- [ ] Somewhat unclear
- [ ] Very unclear

---

### CONTENT ANALYSIS MATRIX

| Theme/Topic | Frequency | Prominence | Tone | Context | Implications |
|-------------|-----------|------------|------|---------|--------------|
|             |           |            |      |         |              |
|             |           |            |      |         |              |
|             |           |            |      |         |              |

**Tone Coding:**
- **Positive (+):** Favorable, supportive, optimistic
- **Neutral (0):** Balanced, factual, objective
- **Negative (-):** Critical, pessimistic, problematic

**Prominence Coding:**
- **High:** Featured prominently, repeated emphasis
- **Medium:** Mentioned several times
- **Low:** Brief mention

---

### THEMATIC ANALYSIS

**Theme 1:** [Emerging theme]

**Supporting Evidence:**
- Document ID: ________ | Quote: _________________________________________________________________
- Document ID: ________ | Quote: _________________________________________________________________

**Interpretation:**
_________________________________________________________________

---

**Theme 2:** [Emerging theme]

**Supporting Evidence:**
- Document ID: ________ | Quote: _________________________________________________________________
- Document ID: ________ | Quote: _________________________________________________________________

**Interpretation:**
_________________________________________________________________

---

### SYNTHESIS NOTES

**Key Findings:**
1. _________________________________________________________________
2. _________________________________________________________________
3. _________________________________________________________________

**Patterns Across Documents:**
_________________________________________________________________

**Contradictions/Inconsistencies:**
_________________________________________________________________

**Gaps in Documentation:**
_________________________________________________________________

**Implications for Research Questions:**

**RQ1:** _________________________________________________________________

**RQ2:** _________________________________________________________________

**RQ3:** _________________________________________________________________

---

### TRIANGULATION

**Comparison with Other Data Sources:**

**Interview Data:**
_________________________________________________________________

**Survey Data:**
_________________________________________________________________

**Observation Data:**
_________________________________________________________________

**Convergence/Divergence:**
_________________________________________________________________

---

### ANALYST REFLECTIONS

**Challenges Encountered:**
_________________________________________________________________

**Limitations of Documents:**
_________________________________________________________________

**Unexpected Findings:**
_________________________________________________________________

**Areas Needing Further Investigation:**
_________________________________________________________________

---

**Analysis Completed By:** __________

**Date:** __________

**Quality Check By:** __________

**Date:** __________
"""
        
        file_path = os.path.join(self.appendices_dir, "Appendix_E_Document_Analysis_Framework.md")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return file_path
    
    async def generate_desktop_review(self) -> str:
        """Generates desktop review protocol appendix."""
        content = f"""# APPENDIX F: DESKTOP REVIEW PROTOCOL

## SYSTEMATIC DESKTOP REVIEW FRAMEWORK

**Study Title:** {self.topic}

**Case Study:** {self.case_study}

**Reviewer:** __________

**Review Period:** From ________ To ________

---

### SEARCH STRATEGY

**Databases Searched:**
- [ ] Google Scholar
- [ ] PubMed
- [ ] Scopus
- [ ] Web of Science
- [ ] JSTOR
- [ ] ProQuest
- [ ] EBSCOhost
- [ ] African Journals Online (AJOL)
- [ ] [Other]: __________

**Search Terms:**

**Primary Keywords:**
- {self.topic.split()[0]}
- {self.topic.split()[1] if len(self.topic.split()) > 1 else ''}
- {self.case_study}

**Secondary Keywords:**
- [Related term 1]
- [Related term 2]
- [Related term 3]

**Boolean Operators:** AND, OR, NOT

**Search String:**
```
("{self.topic}" OR "[alternative term]") AND ("{self.case_study}" OR "[regional term]") NOT ("[exclusion term]")
```

**Date Range:** [Start Year] to [End Year]

**Language:** English [and/or other languages]

---

### SCREENING PROCESS

**Stage 1: Title Screening**

**Initial Search Results:** ________ studies

**Inclusion Criteria:**
- Title clearly related to {self.topic}
- Mentions {self.case_study} or relevant context
- Published within date range

**After Title Screening:** ________ studies

**Excluded:** ________ studies

**Exclusion Reasons:**
- Not related to topic: ________
- Wrong geographical context: ________
- Outside date range: ________
- Other: ________

---

**Stage 2: Abstract Screening**

**Inclusion Criteria:**
- Abstract describes relevant methodology
- Addresses research objectives
- Provides empirical data or theoretical framework

**After Abstract Screening:** ________ studies

**Excluded:** ________ studies

**Exclusion Reasons:**
- Insufficient detail: ________
- Wrong methodology: ________
- Not empirical: ________
- Other: ________

---

**Stage 3: Full-Text Review**

**Inclusion Criteria:**
- Full text available
- Meets quality criteria
- Directly relevant to research questions

**Final Included:** ________ studies

**Excluded:** ________ studies

**Exclusion Reasons:**
- Full text not available: ________
- Low quality: ________
- Not relevant: ________
- Duplicate: ________
- Other: ________

---

### DATA EXTRACTION FORM

| Study ID | Author(s) | Year | Title | Country/Context | Methodology | Sample Size | Key Findings | Quality Score |
|----------|-----------|------|-------|-----------------|-------------|-------------|--------------|---------------|
| S001     |           |      |       |                 |             |             |              |               |
| S002     |           |      |       |                 |             |             |              |               |
| S003     |           |      |       |                 |             |             |              |               |
| S004     |           |      |       |                 |             |             |              |               |
| S005     |           |      |       |                 |             |             |              |               |

---

### QUALITY APPRAISAL

**Quality Criteria (Score each 0-2):**

For each study:

1. **Clear Research Question/Objectives**
   - [ ] 2 = Very clear
   - [ ] 1 = Somewhat clear
   - [ ] 0 = Unclear

2. **Appropriate Methodology**
   - [ ] 2 = Highly appropriate
   - [ ] 1 = Adequate
   - [ ] 0 = Inappropriate

3. **Adequate Sample Size**
   - [ ] 2 = Adequate with justification
   - [ ] 1 = Adequate
   - [ ] 0 = Inadequate

4. **Valid Instruments/Measures**
   - [ ] 2 = Validated instruments
   - [ ] 1 = Adequate instruments
   - [ ] 0 = Questionable validity

5. **Appropriate Analysis**
   - [ ] 2 = Rigorous analysis
   - [ ] 1 = Adequate analysis
   - [ ] 0 = Weak analysis

6. **Clear Results**
   - [ ] 2 = Very clear
   - [ ] 1 = Adequate
   - [ ] 0 = Unclear

7. **Limitations Acknowledged**
   - [ ] 2 = Comprehensive
   - [ ] 1 = Some acknowledgment
   - [ ] 0 = Not acknowledged

8. **Generalizability Discussed**
   - [ ] 2 = Well discussed
   - [ ] 1 = Mentioned
   - [ ] 0 = Not discussed

**Total Quality Score:** ________ / 16

**Quality Rating:**
- 13-16 = High quality
- 9-12 = Medium quality
- 5-8 = Low quality
- 0-4 = Very low quality

---

### SYNTHESIS FRAMEWORK

**By Theme:**

**Theme 1:** [From Objective 1]
- Number of studies: ________
- Key findings: _________________________________________________________________
- Gaps identified: _________________________________________________________________

**Theme 2:** [From Objective 2]
- Number of studies: ________
- Key findings: _________________________________________________________________
- Gaps identified: _________________________________________________________________

**Theme 3:** [From Objective 3]
- Number of studies: ________
- Key findings: _________________________________________________________________
- Gaps identified: _________________________________________________________________

---

**By Methodology:**

**Quantitative Studies:** ________ studies
- Common methods: _________________________________________________________________
- Sample sizes: _________________________________________________________________
- Key findings: _________________________________________________________________

**Qualitative Studies:** ________ studies
- Common methods: _________________________________________________________________
- Sample sizes: _________________________________________________________________
- Key findings: _________________________________________________________________

**Mixed Methods Studies:** ________ studies
- Common approaches: _________________________________________________________________
- Key findings: _________________________________________________________________

---

**By Context/Geography:**

**{self.case_study}:** ________ studies
**Regional (Africa):** ________ studies
**Global:** ________ studies

**Contextual Differences:**
_________________________________________________________________

---

**By Time Period:**

**Before 2010:** ________ studies
**2010-2015:** ________ studies
**2016-2020:** ________ studies
**2021-Present:** ________ studies

**Trends Over Time:**
_________________________________________________________________

---

### GAPS IDENTIFIED

**Methodological Gaps:**
1. _________________________________________________________________
2. _________________________________________________________________
3. _________________________________________________________________

**Geographical Gaps:**
1. _________________________________________________________________
2. _________________________________________________________________

**Theoretical Gaps:**
1. _________________________________________________________________
2. _________________________________________________________________

**Practical Gaps:**
1. _________________________________________________________________
2. _________________________________________________________________

---

### RECOMMENDATIONS FOR PRIMARY RESEARCH

**Based on Desktop Review:**

1. **Research Focus:**
   _________________________________________________________________

2. **Methodology:**
   _________________________________________________________________

3. **Sample/Context:**
   _________________________________________________________________

4. **Theoretical Framework:**
   _________________________________________________________________

5. **Expected Contribution:**
   _________________________________________________________________

---

### SYNTHESIS NARRATIVE

**Overview:**
_________________________________________________________________

**Consistent Findings Across Studies:**
_________________________________________________________________

**Contradictory Findings:**
_________________________________________________________________

**Implications for Current Study:**
_________________________________________________________________

---

**Review Completed By:** __________

**Date:** __________

**Peer Reviewed By:** __________

**Date:** __________
"""
        
        file_path = os.path.join(self.appendices_dir, "Appendix_F_Desktop_Review_Protocol.md")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return file_path
