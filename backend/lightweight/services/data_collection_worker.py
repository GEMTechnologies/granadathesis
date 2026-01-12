"""
AI Data Collection Worker

This module generates synthetic research datasets by:
1. Parsing questionnaires to extract items
2. Extracting sample size from methodology
3. Deploying AI agents to simulate realistic respondents
4. Generating CSV datasets ready for SPSS/statistical analysis
5. Generating interview/KII transcripts with text responses
"""

import os
import re
import csv
import random
import asyncio
import math
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path


class DataCollectionWorker:
    """AI-powered synthetic data generation for research instruments."""
    
    def __init__(
        self,
        topic: str,
        case_study: str,
        questionnaire_content: str = "",
        methodology_content: str = "",
        objectives: List[str] = None,
        sample_size: int = None,
        interview_sample_size: int = None,
        likert_scale: int = 5,
        items_per_objective: int = None,
        demographic_distributions: Optional[Dict[str, Dict[str, float]]] = None
    ):
        self.topic = topic
        self.case_study = case_study
        self.questionnaire_content = questionnaire_content
        self.methodology_content = methodology_content
        self.methodology_content = methodology_content
        self.objectives = objectives or []
        self.objective_variables = {}
        self.likert_scale = likert_scale if likert_scale in (3, 5, 7) else 5
        self.items_per_objective = items_per_objective or 5
        self.demographic_distributions = demographic_distributions or {}
        
        # Load Golden Thread variables
        try:
            import json
            from services.workspace_service import WORKSPACES_DIR
            
            # Use specific workspace directory if provided, else scan default
            # We assume the caller provides the correct workspace context
            workspace_id = getattr(self, 'workspace_id', 'default')
            plan_path = WORKSPACES_DIR / workspace_id / "thesis_plan.json"
            
            if not plan_path.exists():
                # Fallback to scanning for the first available plan ONLY if workspace_id is default
                if workspace_id == 'default':
                    for path in WORKSPACES_DIR.iterdir():
                        if path.is_dir() and (path / "thesis_plan.json").exists():
                            plan_path = path / "thesis_plan.json"
                            break
                        
            if plan_path.exists():
                with open(plan_path, 'r', encoding='utf-8') as f:
                    plan_data = json.load(f)
                    self.objective_variables = plan_data.get("objective_variables", {})
                print(f"📊 Worker loaded {len(self.objective_variables)} objective variables from {plan_path}")
        except Exception as e:
            print(f"⚠️ Worker failed to load variables: {e}")
            
        # Parse questionnaire to extract items
        self.demographic_questions = self._extract_demographics()
        self.demographic_questions = self._extract_demographics()
        self.likert_sections = self._extract_likert_sections()
        
        # Get sample size from methodology or use provided/default
        self.sample_size = sample_size or self._extract_sample_size() or 50
        self.interview_sample_size = interview_sample_size or min(15, self.sample_size // 5) or 10
        
        print(f"📊 DataCollectionWorker initialized:")
        print(f"   - Topic: {self.topic[:50]}...")
        print(f"   - Questionnaire Sample Size: {self.sample_size}")
        print(f"   - Interview Sample Size: {self.interview_sample_size}")
        print(f"   - Likert Sections: {len(self.likert_sections)}")
        print(f"   - Total Items: {sum(len(s['items']) for s in self.likert_sections)}")
        print(f"   - Likert Scale: {self.likert_scale}-point")
    
    def _extract_sample_size(self) -> int:
        """Extract sample size from methodology content."""
        content = self.methodology_content.lower()
        
        patterns = [
            r'sample\s+size\s+(?:of\s+)?(\d+)',
            r'n\s*=\s*(\d+)',
            r'(\d+)\s+respondents',
            r'(\d+)\s+participants',
            r'sample\s+of\s+(\d+)',
            r'(\d+)\s+questionnaires',
            r'total\s+of\s+(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                size = int(match.group(1))
                if 10 <= size <= 10000:
                    print(f"📊 Extracted sample size: {size}")
                    return size
        
        return None
    
    def _extract_demographics(self) -> List[Dict[str, Any]]:
        """Extract demographic questions from questionnaire."""
        demographics = []

        def normalize_weights(dist: Dict[str, float], options: List[str], mapping: Dict[str, str]) -> Optional[List[float]]:
            if not dist:
                return None
            mapped = {mapping.get(k.lower(), k).lower(): v for k, v in dist.items()}
            weights = []
            for opt in options:
                key = opt.lower()
                weights.append(max(0.0, float(mapped.get(key, 0))))
            total = sum(weights)
            if total <= 0:
                return None
            return [w / total for w in weights]

        age_options = ['18-25', '26-35', '36-45', '46-55', '55+']
        gender_options = ['Male', 'Female', 'Other']
        education_options = ['Primary', 'Secondary', 'Tertiary', 'Postgraduate', 'Other']

        age_weights = normalize_weights(
            self.demographic_distributions.get('age', {}),
            age_options,
            {k: k for k in age_options}
        ) or [0.15, 0.30, 0.25, 0.20, 0.10]

        gender_weights = normalize_weights(
            self.demographic_distributions.get('gender', {}),
            gender_options,
            {'male': 'Male', 'female': 'Female', 'other': 'Other'}
        ) or [0.50, 0.48, 0.02]

        education_weights = normalize_weights(
            self.demographic_distributions.get('education', {}),
            education_options,
            {
                'primary': 'Primary',
                'secondary': 'Secondary',
                'tertiary': 'Tertiary',
                'postgraduate': 'Postgraduate',
                'other': 'Other'
            }
        ) or [0.10, 0.30, 0.45, 0.12, 0.03]

        demographics.append({
            'name': 'Age',
            'variable': 'age_group',
            'options': age_options,
            'weights': age_weights
        })

        demographics.append({
            'name': 'Gender',
            'variable': 'gender',
            'options': gender_options,
            'weights': gender_weights
        })

        demographics.append({
            'name': 'Education',
            'variable': 'education',
            'options': education_options,
            'weights': education_weights
        })
        
        demographics.append({
            'name': 'Experience',
            'variable': 'work_experience',
            'options': ['<2 years', '2-5 years', '6-10 years', '11-15 years', '15+ years'],
            'weights': [0.10, 0.25, 0.30, 0.20, 0.15]
        })
        
        demographics.append({
            'name': 'Position',
            'variable': 'position',
            'options': ['Senior Manager', 'Middle Manager', 'Supervisor', 'Staff', 'Other'],
            'weights': [0.10, 0.20, 0.25, 0.35, 0.10]
        })
        
        demographics.append({
            'name': 'Organization',
            'variable': 'org_type',
            'options': ['Public', 'Private', 'NGO', 'Other'],
            'weights': [0.35, 0.40, 0.20, 0.05]
        })
        
        return demographics
    
    def _extract_likert_sections(self) -> List[Dict[str, Any]]:
        """Extract Likert scale sections from questionnaire markdown."""
        sections = []
        content = self.questionnaire_content
        
        if not content:
            # No questionnaire content - use objectives-based fallback
            return self._create_sections_from_objectives()
        
        # Split content by section headers (### SECTION X: ... or #### Objective X: ...)
        section_pattern = r'(?:###\s+SECTION\s+([A-Z]):\s*|####\s+Objective\s+(\d+):\s*)([^\n]+)'
        section_matches = list(re.finditer(section_pattern, content, re.IGNORECASE))
        
        for i, match in enumerate(section_matches):
            letter = match.group(1).upper() if match.group(1) else chr(ord('A') + int(match.group(2)))
            title = match.group(3).strip()
            
            # Skip demographics section
            if 'demographic' in title.lower():
                continue
            
            # Get content between this section and next
            start_pos = match.end()
            end_pos = section_matches[i + 1].start() if i + 1 < len(section_matches) else len(content)
            section_content = content[start_pos:end_pos]
            
            # Extract items from markdown table: | No. | Statement | ...
            items = []
            # Pattern matches: | 1.1 | Statement text | or | 1 | Text |
            table_pattern = r'\|\s*(\d+(?:\.\d+)?)\s*\|\s*([^|]+?)\s*\|'
            
            for item_match in re.finditer(table_pattern, section_content):
                num_str = item_match.group(1).strip()
                text = item_match.group(2).strip()
                
                # Skip header rows and empty items
                if text.lower() in ['statement', 'no.', 'no', 'sd', 'd', 'n', 'a', 'sa', 'item']:
                    continue
                if len(text) < 10:
                    continue
                    
                # Create a clean variable name (replace dots with underscores)
                var_num = num_str.replace('.', '_')
                
                items.append({
                    'number': num_str,
                    'text': text[:200],
                    'variable': f"Q{letter}_{var_num}"
                })
            
            if items:
                sections.append({
                    'letter': letter,
                    'title': title,
                    'items': items
                })
                print(f"📋 Extracted {len(items)} items from Section {letter}: {title[:40]}")
        
        # Fallback if no sections found
        if not sections:
            sections = self._create_sections_from_objectives()
        
        return sections
    
    def _create_sections_from_objectives(self) -> List[Dict[str, Any]]:
        """Create default sections based on objectives."""
        sections = []
        
        if self.objectives:
            for i, obj in enumerate(self.objectives, 1):
                letter = chr(ord('A') + i)  # B, C, D, E, F, G...
                items = []
                
                # Use variables if available for this objective
                obj_vars = self.objective_variables.get(str(i), self.objective_variables.get(i, []))
                
                if obj_vars:
                    # Generate items for each variable (2 items per variable)
                    for v_idx, variable in enumerate(obj_vars, 1):
                        items.append({
                            'number': (v_idx * 2) - 1,
                            'text': f"I am satisfied with the {variable.lower()}",
                            'variable': f"Q{letter}_{v_idx}_1"
                        })
                        items.append({
                            'number': v_idx * 2,
                            'text': f"The {variable.lower()} is effective",
                            'variable': f"Q{letter}_{v_idx}_2"
                        })
                else:
                    # Fallback to generic items (8 items per objective)
                    for j in range(1, self.items_per_objective + 1):
                        items.append({
                            'number': j,
                            'text': f"Item {j} measuring {obj[:80]}",
                            'variable': f"Q{letter}_{j}"
                        })
                        
                sections.append({
                    'letter': letter,
                    'title': obj,
                    'items': items
                })
        else:
            # Ultimate fallback
            sections = [
                {'letter': 'B', 'title': 'General Perceptions', 'items': [{'number': i, 'text': f'Statement {i}', 'variable': f'QB_{i}'} for i in range(1, 9)]},
                {'letter': 'C', 'title': 'Implementation', 'items': [{'number': i, 'text': f'Statement {i}', 'variable': f'QC_{i}'} for i in range(1, 9)]},
                {'letter': 'D', 'title': 'Outcomes', 'items': [{'number': i, 'text': f'Statement {i}', 'variable': f'QD_{i}'} for i in range(1, 9)]},
            ]
        
        return sections
    
    def _generate_timestamp(self, respondent_id: int) -> str:
        """Generate a realistic collection timestamp spread over data collection period."""
        # Simulate data collection over 2-4 weeks
        base_date = datetime.now() - timedelta(days=random.randint(14, 30))
        # Add random hours/minutes within business hours
        hours_offset = respondent_id * (8 * 60 / self.sample_size)  # Spread across collection period
        collection_time = base_date + timedelta(minutes=hours_offset)
        # Add some randomness
        collection_time += timedelta(minutes=random.randint(-60, 60))
        return collection_time.strftime('%Y-%m-%d %H:%M:%S')
    
    def _generate_demographic_response(self, demographic: Dict[str, Any]) -> str:
        """Generate a realistic demographic response - returns actual text value."""
        options = demographic['options']
        weights = demographic.get('weights', [1/len(options)] * len(options))
        return random.choices(options, weights=weights)[0]
    
    def _generate_likert_response(self, respondent_profile: Dict[str, Any], section_idx: int) -> int:
        """Generate a realistic Likert scale response (1-N)."""
        scale = self.likert_scale
        respondent_bias = respondent_profile.get('bias', 0)

        mid = (scale + 1) / 2.0
        sigma = max(1.0, scale / 3.0)
        weights = []
        for i in range(1, scale + 1):
            base = math.exp(-((i - mid) ** 2) / (2 * sigma ** 2))
            shift = (i - mid) * respondent_bias * 0.15
            weights.append(max(0.01, base + shift))

        total = sum(weights)
        weights = [w / total for w in weights]

        return random.choices(list(range(1, scale + 1)), weights=weights)[0]
    
    async def _generate_respondent(self, respondent_id: int) -> Dict[str, Any]:
        """Generate a complete respondent with all responses."""
        
        profile = {
            'respondent_id': respondent_id + 1,
            'timestamp': self._generate_timestamp(respondent_id),
            'bias': random.gauss(0, 0.3),
        }
        
        # Generate demographics - actual text values
        for demo in self.demographic_questions:
            profile[demo['variable']] = self._generate_demographic_response(demo)
        
        # Generate Likert responses - numeric 1-5
        for section_idx, section in enumerate(self.likert_sections):
            for item in section['items']:
                profile[item['variable']] = self._generate_likert_response(profile, section_idx)
        
        return profile
    
    async def _generate_interview_response(self, respondent_id: int, question: str, objective: str) -> str:
        """Generate a realistic interview text response using AI."""
        try:
            from services.deepseek_direct_service import deepseek_service
            
            prompt = f"""Generate a realistic interview response for a research study.

TOPIC: {self.topic}
CASE STUDY: {self.case_study}
OBJECTIVE: {objective}

INTERVIEW QUESTION: {question}

Generate a realistic 3-5 sentence response from a respondent. The response should:
1. Be in first person
2. Include specific examples or experiences
3. Be relevant to the question and topic
4. Sound natural and conversational
5. Vary in perspective (some positive, some negative, some mixed)

Respond with ONLY the interview response text, no labels or formatting:"""
            
            response = await deepseek_service.generate(
                prompt=prompt,
                max_tokens=300,
                temperature=0.8
            )
            
            return response.strip()
            
        except Exception as e:
            # Fallback text responses
            fallback_responses = [
                f"In my experience with {self.topic[:30]}, I have seen both challenges and opportunities. There is still much work to be done to address the core issues.",
                f"Based on what I have observed, the situation regarding {self.topic[:30]} has evolved over time. We need more resources and better coordination.",
                f"I believe that {self.topic[:30]} requires a comprehensive approach. The current efforts are making progress, but there are gaps that need attention.",
                f"From my perspective working in this area, {self.topic[:30]} presents unique challenges. Community involvement is crucial for success.",
                f"The challenges we face with {self.topic[:30]} are significant but not insurmountable. With proper support and policies, we can make meaningful progress.",
            ]
            return random.choice(fallback_responses)
    
    async def generate_interview_data(
        self,
        output_dir: str = None,
        progress_callback = None
    ) -> str:
        """Generate interview/KII transcript data."""
        from config import get_datasets_dir
        output_dir = output_dir or str(get_datasets_dir('default'))
        os.makedirs(output_dir, exist_ok=True)
        
        # Interview questions based on objectives
        interview_questions = []
        for i, obj in enumerate(self.objectives if self.objectives else ["Understanding experiences", "Identifying challenges", "Recommendations"], 1):
            interview_questions.append({
                'number': i,
                'objective': obj,
                'main_question': f"Can you describe your experience regarding {obj[:50]}?",
                'probes': [
                    "Can you give me a specific example?",
                    "How did that affect you or your organization?",
                    "What challenges did you face?"
                ]
            })
        
        # Generate interview transcripts
        transcripts = []
        
        for r_id in range(self.interview_sample_size):
            respondent = {
                'respondent_id': f"KII_{r_id + 1:03d}",
                'interview_date': self._generate_timestamp(r_id),
                'demographics': {},
                'responses': []
            }
            
            # Demographics
            for demo in self.demographic_questions[:4]:  # First 4 demographics
                respondent['demographics'][demo['name']] = self._generate_demographic_response(demo)
            
            # Generate response for each question
            for q in interview_questions:
                response_text = await self._generate_interview_response(
                    r_id, 
                    q['main_question'], 
                    q['objective']
                )
                
                respondent['responses'].append({
                    'question_number': q['number'],
                    'objective': q['objective'],
                    'question': q['main_question'],
                    'response': response_text
                })
            
            transcripts.append(respondent)
            
            if progress_callback:
                await progress_callback(f"Generated interview {r_id + 1}/{self.interview_sample_size}")
        
        # Save as CSV with SHORT filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"interviews_kii_{timestamp}.csv"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Headers
            writer.writerow([
                'respondent_id', 'interview_date', 'age', 'gender', 'education', 'position',
                'question_number', 'objective', 'question', 'response'
            ])
            
            for transcript in transcripts:
                for response in transcript['responses']:
                    writer.writerow([
                        transcript['respondent_id'],
                        transcript['interview_date'],
                        transcript['demographics'].get('Age', ''),
                        transcript['demographics'].get('Gender', ''),
                        transcript['demographics'].get('Education', ''),
                        transcript['demographics'].get('Position', ''),
                        response['question_number'],
                        response['objective'][:50],
                        response['question'],
                        response['response']
                    ])
        
        print(f"✅ Interview data generated: {filepath}")
        return filepath
    
    async def generate_fgd_data(
        self,
        output_dir: str = None,
        num_groups: int = 3,
        participants_per_group: int = 8,
        progress_callback = None
    ) -> str:
        """Generate FGD transcript data - organized by group and discussion theme."""
        from config import get_datasets_dir
        output_dir = output_dir or str(get_datasets_dir('default'))
        os.makedirs(output_dir, exist_ok=True)
        
        fgd_data = []
        
        for group_id in range(1, num_groups + 1):
            # Generate participants for this group
            participants = []
            for p_id in range(1, participants_per_group + 1):
                participants.append({
                    'id': f"P{p_id}",
                    'gender': self._generate_demographic_response(self.demographic_questions[1]),
                    'age': self._generate_demographic_response(self.demographic_questions[0]),
                })
            
            # Discussion themes based on objectives
            objectives_list = []
            if isinstance(self.objectives, dict):
                objectives_list = self.objectives.get("specific", []) or []
            elif isinstance(self.objectives, list):
                objectives_list = self.objectives
            if not objectives_list:
                objectives_list = ["General discussion"]

            for theme_idx, obj in enumerate(objectives_list[:4], 1):
                # Each participant contributes to each theme
                for participant in participants:
                    response = await self._generate_interview_response(
                        int(participant['id'][1:]), 
                        f"What are your views on {obj[:40]}?",
                        obj
                    )
                    
                    fgd_data.append({
                        'fgd_group': f"FGD_{group_id}",
                        'date_conducted': self._generate_timestamp(group_id),
                        'participant_id': participant['id'],
                        'participant_gender': participant['gender'],
                        'participant_age': participant['age'],
                        'theme_number': theme_idx,
                        'theme': obj[:50],
                        'response': response
                    })
            
            if progress_callback:
                await progress_callback(f"Generated FGD {group_id}/{num_groups}")
        
        # Save to CSV with SHORT filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"fgd_transcripts_{timestamp}.csv"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(fgd_data[0].keys()) if fgd_data else [])
            writer.writeheader()
            writer.writerows(fgd_data)
        
        print(f"✅ FGD data generated: {filepath}")
        return filepath
    
    async def generate_observation_data(
        self,
        output_dir: str = None,
        num_observations: int = 20,
        progress_callback = None
    ) -> str:
        """Generate observation checklist data."""
        from config import get_datasets_dir
        output_dir = output_dir or str(get_datasets_dir('default'))
        os.makedirs(output_dir, exist_ok=True)
        
        observations = []
        
        # Observation items based on objectives
        observation_items = []
        objectives_list = []
        if isinstance(self.objectives, dict):
            objectives_list = self.objectives.get("specific", []) or []
        elif isinstance(self.objectives, list):
            objectives_list = self.objectives
        if not objectives_list:
            objectives_list = ["General observation"]
        for obj in objectives_list[:5]:
            observation_items.extend([
                f"Presence of {obj[:30]} related activity",
                f"Level of engagement with {obj[:30]}",
                f"Resources available for {obj[:30]}",
                f"Challenges observed in {obj[:30]}",
            ])
        
        for obs_id in range(1, num_observations + 1):
            observation = {
                'observation_id': f"OBS_{obs_id:03d}",
                'date_observed': self._generate_timestamp(obs_id),
                'location': random.choice(['Site A', 'Site B', 'Site C', 'Site D', 'Site E']),
                'observer': f"Observer_{random.randint(1, 3)}",
                'duration_minutes': random.randint(30, 120),
            }
            
            # Rate each observation item (1-5 scale or Yes/No/NA)
            for i, item in enumerate(observation_items[:10], 1):
                observation[f"item_{i}_observed"] = random.choice(['Yes', 'No', 'Partially', 'NA'])
                observation[f"item_{i}_rating"] = random.randint(1, 5) if random.random() > 0.2 else 'NA'
            
            # Field notes
            observation['field_notes'] = random.choice([
                f"Observed significant activity related to {self.topic[:30]}. Further investigation recommended.",
                f"Limited activity during observation period. Environmental factors may have influenced results.",
                f"High level of engagement observed. Participants showed interest in {self.topic[:30]}.",
                f"Mixed observations. Some areas showed progress while others need improvement.",
                f"Noteworthy findings regarding {self.topic[:30]}. Recommend follow-up observation.",
            ])
            
            observations.append(observation)
            
            if progress_callback and obs_id % 5 == 0:
                await progress_callback(f"Generated observation {obs_id}/{num_observations}")
        
        # Save to CSV with SHORT filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"observations_{timestamp}.csv"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(observations[0].keys()) if observations else [])
            writer.writeheader()
            writer.writerows(observations)
        
        print(f"✅ Observation data generated: {filepath}")
        return filepath

    
    async def generate_dataset(
        self,
        output_dir: str = None,
        progress_callback = None
    ) -> Tuple[str, Dict[str, Any]]:
        """Generate the complete synthetic dataset."""
        from config import get_datasets_dir
        output_dir = output_dir or str(get_datasets_dir('default'))
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"🚀 Starting data collection simulation...")
        print(f"   Generating {self.sample_size} respondent profiles...")
        
        respondents = []
        batch_size = 10
        
        for i in range(0, self.sample_size, batch_size):
            batch_end = min(i + batch_size, self.sample_size)
            batch = []
            
            for j in range(i, batch_end):
                respondent = await self._generate_respondent(j)
                batch.append(respondent)
            
            respondents.extend(batch)
            
            if progress_callback:
                progress = (batch_end / self.sample_size) * 100
                await progress_callback(f"Generated {batch_end}/{self.sample_size} responses ({progress:.0f}%)")
        
        # Build headers with timestamp
        headers = ['respondent_id', 'date_collected']
        
        for demo in self.demographic_questions:
            headers.append(demo['variable'])
        
        for section in self.likert_sections:
            for item in section['items']:
                headers.append(item['variable'])
        
        # Generate CSV with SHORT filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"questionnaire_data_{timestamp}.csv"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            
            for respondent in respondents:
                row = {
                    'respondent_id': respondent['respondent_id'],
                    'date_collected': respondent['timestamp']
                }
                
                # Add demographics - actual text values (Male, Female, etc.)
                for demo in self.demographic_questions:
                    row[demo['variable']] = respondent.get(demo['variable'], '')
                
                # Add Likert responses - numeric values (1, 2, 3, 4, 5)
                for section in self.likert_sections:
                    for item in section['items']:
                        row[item['variable']] = respondent.get(item['variable'], '')
                
                writer.writerow(row)
        
        stats = self._calculate_statistics(respondents)
        
        print(f"✅ Dataset generated successfully!")
        print(f"   📁 File: {filepath}")
        print(f"   📊 Respondents: {len(respondents)}")
        print(f"   📋 Variables: {len(headers)}")
        
        # Also generate XLSX
        xlsx_path = filepath.replace('.csv', '.xlsx')
        try:
            from openpyxl import Workbook
            wb = Workbook()
            ws = wb.active
            ws.title = "Questionnaire Data"
            
            # Write headers
            ws.append(headers)
            
            # Write data
            for respondent in respondents:
                row_data = [respondent['respondent_id'], respondent['timestamp']]
                for demo in self.demographic_questions:
                    row_data.append(respondent.get(demo['variable'], ''))
                for section in self.likert_sections:
                    for item in section['items']:
                        row_data.append(respondent.get(item['variable'], ''))
                ws.append(row_data)
            
            wb.save(xlsx_path)
            print(f"   📊 XLSX: {xlsx_path}")
        except Exception as e:
            print(f"⚠️ Could not create XLSX: {e}")
            xlsx_path = None
        
        # =====================================================
        # SAVE VARIABLE MAPPING JSON (for Chapter 4 to use real statement text)
        # =====================================================
        mapping_path = filepath.replace('.csv', '_variable_mapping.json')
        try:
            import json
            variable_mapping = {
                'demographics': {demo['variable']: demo.get('name', demo.get('question', demo['variable'])) for demo in self.demographic_questions},
                'likert_items': {},
                'likert_scale': self.likert_scale
            }
            
            for section in self.likert_sections:
                for item in section['items']:
                    variable_mapping['likert_items'][item['variable']] = {
                        'section': section['letter'],
                        'section_title': section['title'],
                        'number': item['number'],
                        'text': item['text'],
                        'full_label': item['text']
                    }
            
            with open(mapping_path, 'w', encoding='utf-8') as f:
                json.dump(variable_mapping, f, indent=2, ensure_ascii=False)
            
            print(f"   📝 Variable mapping: {mapping_path}")
        except Exception as e:
            print(f"⚠️ Could not create variable mapping: {e}")
            mapping_path = None
        
        stats['xlsx_path'] = xlsx_path
        stats['mapping_path'] = mapping_path
        return filepath, stats
    
    def _calculate_statistics(self, respondents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate descriptive statistics for the dataset."""
        stats = {
            'n': len(respondents),
            'demographics': {},
            'likert_summary': {},
            'likert_scale': self.likert_scale
        }
        
        for demo in self.demographic_questions:
            var = demo['variable']
            freq = {}
            for r in respondents:
                val = r.get(var, 'Unknown')
                freq[val] = freq.get(val, 0) + 1
            stats['demographics'][var] = freq
        
        for section in self.likert_sections:
            section_responses = []
            for item in section['items']:
                var = item['variable']
                values = [r.get(var, 0) for r in respondents if isinstance(r.get(var), int)]
                if values:
                    section_responses.extend(values)
                    mean = sum(values) / len(values)
                    stats['likert_summary'][var] = {
                        'mean': round(mean, 2),
                        'min': min(values),
                        'max': max(values)
                    }
            
            if section_responses:
                section_mean = sum(section_responses) / len(section_responses)
                stats['likert_summary'][f"section_{section['letter']}_mean"] = round(section_mean, 2)
        
        return stats
    
    def generate_spss_syntax(self, csv_path: str) -> str:
        """Generate SPSS syntax for importing and analyzing the dataset."""
        
        syntax = f"""* SPSS Syntax for Dataset Analysis
* Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
* Topic: {self.topic}
* Sample Size: {self.sample_size}

* Import data
GET DATA /TYPE=TXT
  /FILE='{csv_path}'
  /ENCODING='UTF8'
  /DELIMITERS=","
  /QUALIFIER='"'
  /ARRANGEMENT=DELIMITED
  /FIRSTCASE=2
  /VARIABLES=
    respondent_id F4.0
    date_collected A20
"""
        
        for demo in self.demographic_questions:
            syntax += f"    {demo['variable']} A25\n"
        
        for section in self.likert_sections:
            for item in section['items']:
                syntax += f"    {item['variable']} F1.0\n"
        
        syntax += """  /MAP.
EXECUTE.

* Variable labels
"""
        
        for demo in self.demographic_questions:
            syntax += f'VARIABLE LABELS {demo["variable"]} "{demo["name"]}".\n'
        
        for section in self.likert_sections:
            for item in section['items']:
                syntax += f'VARIABLE LABELS {item["variable"]} "{item["text"][:50]}".\n'
        
        syntax += """
* Value labels for Likert items
"""
        for section in self.likert_sections:
            for item in section['items']:
                syntax += f"""VALUE LABELS {item['variable']}
  1 'Strongly Disagree'
  2 'Disagree'
  3 'Neutral'
  4 'Agree'
  5 'Strongly Agree'.
"""
        
        syntax += """
* Descriptive statistics
FREQUENCIES VARIABLES="""
        
        for demo in self.demographic_questions:
            syntax += f"{demo['variable']} "
        
        syntax += """
  /ORDER=ANALYSIS.

* Reliability analysis (Cronbach's Alpha)
"""
        for section in self.likert_sections:
            items = ' '.join([item['variable'] for item in section['items']])
            syntax += f"""
RELIABILITY
  /VARIABLES={items}
  /SCALE('Section {section["letter"]}') ALL
  /MODEL=ALPHA.
"""
        
        syntax += """
* Correlation matrix
CORRELATIONS
  /VARIABLES="""
        
        all_likert = []
        for section in self.likert_sections:
            for item in section['items']:
                all_likert.append(item['variable'])
        syntax += ' '.join(all_likert[:20])
        
        syntax += """
  /PRINT=TWOTAIL NOSIG
  /MISSING=PAIRWISE.
"""
        
        return syntax


async def generate_research_dataset(
    topic: str,
    case_study: str,
    questionnaire_path: str = None,
    methodology_path: str = None,
    sample_size: int = None,
    objectives: List[str] = None,
    job_id: str = None,
    session_id: str = None,
    generate_interviews: bool = True,
    output_dir: str = None,
    likert_scale: int = 5,
    items_per_objective: int = None,
    demographic_distributions: Optional[Dict[str, Dict[str, float]]] = None,
    **kwargs
) -> Dict[str, Any]:
    """Main function to generate research dataset.
    
    Returns:
        Dict with csv_path, interview_path, stats, and spss_syntax_path
    """
    
    # Use provided output_dir or default
    output_dir = output_dir or "/home/gemtech/Desktop/thesis/datasets"
    os.makedirs(output_dir, exist_ok=True)
    
    questionnaire_content = ""
    if questionnaire_path and os.path.exists(questionnaire_path):
        with open(questionnaire_path, 'r', encoding='utf-8') as f:
            questionnaire_content = f.read()
    
    methodology_content = ""
    if methodology_path and os.path.exists(methodology_path):
        with open(methodology_path, 'r', encoding='utf-8') as f:
            methodology_content = f.read()
    
    worker = DataCollectionWorker(
        topic=topic,
        case_study=case_study,
        questionnaire_content=questionnaire_content,
        methodology_content=methodology_content,
        objectives=objectives,
        sample_size=sample_size,
        likert_scale=likert_scale,
        items_per_objective=items_per_objective,
        demographic_distributions=demographic_distributions
    )
    
    async def progress_callback(message: str):
        if job_id:
            try:
                from services.events import events
                await events.publish(job_id, "log", {"message": f"📊 {message}"}, session_id=session_id)
            except:
                pass
        print(f"📊 {message}")
    
    # Generate questionnaire dataset
    csv_path, stats = await worker.generate_dataset(output_dir=output_dir, progress_callback=progress_callback)
    
    # Generate SPSS syntax
    spss_syntax = worker.generate_spss_syntax(csv_path)
    spss_path = csv_path.replace('.csv', '_SPSS_syntax.sps')
    with open(spss_path, 'w', encoding='utf-8') as f:
        f.write(spss_syntax)
    
    result = {
        'csv_path': csv_path,
        'spss_syntax_path': spss_path,
        'stats': stats,
        'sample_size': worker.sample_size,
        'total_variables': len(worker.demographic_questions) + sum(len(s['items']) for s in worker.likert_sections),
        'files': [csv_path, spss_path]
    }
    
    # Generate interview/KII data
    if generate_interviews:
        await progress_callback("Generating interview transcripts...")
        interview_path = await worker.generate_interview_data(output_dir=output_dir, progress_callback=progress_callback)
        result['interview_path'] = interview_path
        result['interview_sample_size'] = worker.interview_sample_size
        result['files'].append(interview_path)
    
    # Generate FGD data
    if generate_interviews:
        await progress_callback("Generating FGD transcripts...")
        fgd_path = await worker.generate_fgd_data(output_dir=output_dir, progress_callback=progress_callback)
        result['fgd_path'] = fgd_path
        result['files'].append(fgd_path)
    
    # Generate observation data
    if generate_interviews:
        await progress_callback("Generating observation data...")
        obs_path = await worker.generate_observation_data(output_dir=output_dir, progress_callback=progress_callback)
        result['observation_path'] = obs_path
        result['files'].append(obs_path)
    
    return result


async def generate_study_tools(
    topic: str,
    objectives: List[str] = None,
    output_dir: str = None,
    job_id: str = None,
    session_id: str = None,
    sample_size: int = None,
    likert_scale: int = 5,
    items_per_objective: int = 5,
    interview_questions: int = 10,
    fgd_questions: int = 8,
    include_questionnaire: bool = True,
    include_interviews: bool = True,
    include_fgd: bool = True,
    include_observation: bool = True
) -> Dict[str, Any]:
    """Generate research study tools (questionnaire, interview guide, FGD guide, observation checklist).
    
    Args:
        topic: Research topic
        objectives: List of research objectives
        output_dir: Directory to save the tools
        job_id: Job ID for SSE events
        session_id: Session ID for SSE events
    
    Returns:
        Dict with paths to all generated study tools
    """
    from datetime import datetime
    
    output_dir = output_dir or "/home/gemtech/Desktop/thesis"
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    objectives = objectives or []
    
    async def publish_log(message: str):
        if job_id:
            try:
                from services.events import events
                await events.publish(job_id, "log", {"message": message}, session_id=session_id)
            except:
                pass
        print(message)
    
    questionnaire_path = None
    interview_path = None
    fgd_path = None
    observation_path = None

    scale = likert_scale if likert_scale in (3, 5, 7) else 5
    if items_per_objective < 2:
        items_per_objective = 2
    elif items_per_objective > 8:
        items_per_objective = 8

    if scale == 3:
        scale_labels = {
            1: "Disagree",
            2: "Neutral",
            3: "Agree"
        }
    elif scale == 7:
        scale_labels = {
            1: "Strongly Disagree",
            2: "Disagree",
            3: "Slightly Disagree",
            4: "Neutral",
            5: "Slightly Agree",
            6: "Agree",
            7: "Strongly Agree"
        }
    else:
        scale_labels = {
            1: "Strongly Disagree",
            2: "Disagree",
            3: "Neutral",
            4: "Agree",
            5: "Strongly Agree"
        }

    scale_header = " | ".join([f"{scale_labels[num]} ({num})" for num in range(1, scale + 1)])
    scale_cells = " | ".join(["[ ]" for _ in range(1, scale + 1)])
    scale_lines = "\n".join([f"- **{num}** = {scale_labels[num]}" for num in range(1, scale + 1)])
    
    if include_questionnaire:
        await publish_log("📋 Generating structured questionnaire and transmittal letter...")

        # ===================== QUESTIONNAIRE =====================
        questionnaire_content = f"""# TRANSMITTAL LETTER
    
Dear Respondent,

I am conducting a research study on **{topic}**. This study involves a total of **{sample_size or 385} participants**. 

Your participation in this study is highly valued. The information you provide will be used for academic purposes only and will be handled with the utmost confidentiality.

Thank you for your time and contribution.

Yours faithfully,

Researcher

---

# Research Questionnaire
## {topic}

---

### SECTION A: DEMOGRAPHIC INFORMATION

**Instructions:** Please encircle the letter corresponding to your response.

1. **Age Group:**
A. 18-25 years
B. 26-35 years
C. 36-45 years
D. 46-55 years
E. 55 years and above

2. **Gender:**
A. Male
B. Female
C. Other

3. **Highest Level of Education:**
A. Primary
B. Secondary
C. Tertiary
D. Postgraduate
E. Other

4. **Years of Experience:**
A. Less than 2 years
B. 2-5 years
C. 6-10 years
D. 11-15 years
E. Above 15 years

5. **Current Position/Rank:**
A. Senior Manager
B. Middle Manager
C. Supervisor
D. Staff
E. Other

6. **Type of Organization:**
A. Public Sector
B. Private Sector
C. NGO/Civil Society
D. Other

---

### SECTION B: MAIN RESEARCH QUESTIONS

**Instructions:** Please indicate your level of agreement with each statement using the following scale:

{scale_lines}
"""

        item_templates = [
            "I believe that {objective} is important",
            "Adequate measures exist to support {objective}",
            "Current practices effectively address {objective}",
            "There are challenges related to {objective}",
            "Notable improvements are needed regarding {objective}",
            "Stakeholders demonstrate commitment to {objective}",
            "Resources allocated to {objective} are sufficient",
            "Policies governing {objective} are implemented effectively"
        ]

        for i, obj in enumerate(objectives, 1):
            # Clean objective text
            obj_clean = obj.strip()
            if obj_clean.lower().startswith('to '):
                obj_clean = obj_clean[3:]
            obj_title = obj_clean.capitalize()
            
            questionnaire_content += (
                f"\n#### Objective {i}: {obj_title}\n\n"
                f"| # | Statement | {scale_header} |\n"
                f"|---|-----------|{('|' + '|'.join(['---'] * scale) + '|')}"
            )

            for item_idx in range(1, items_per_objective + 1):
                template = item_templates[(item_idx - 1) % len(item_templates)]
                statement = template.format(objective=obj_clean.lower())
                questionnaire_content += f"\n| {i}.{item_idx} | {statement} | {scale_cells} |"
        
        questionnaire_content += """
---

### SECTION C: OPEN-ENDED QUESTIONS

Please provide brief responses to the following:

1. What do you consider to be the main challenges in this area?
   
   _____________________________________________________________

2. What improvements would you recommend?
   
   _____________________________________________________________

3. Any other comments or suggestions?
   
   _____________________________________________________________

---

**Thank you for your participation!**

*This questionnaire is for academic research purposes only. All responses will be kept confidential.*
"""
        
        questionnaire_path = os.path.join(output_dir, f"Questionnaire_{timestamp}.md")
        with open(questionnaire_path, 'w', encoding='utf-8') as f:
            f.write(questionnaire_content)

    if include_interviews:
        await publish_log("📝 Generating Key Informant Interview (KII) Guide...")
    
        # ===================== INTERVIEW GUIDE =====================
        interview_content = f"""# Key Informant Interview (KII) Guide
## {topic}

---

### Introduction Script

Good [morning/afternoon]. My name is ____________ and I am conducting research on **{topic}**. 

This interview is part of an academic study and will take approximately 30-45 minutes. Your participation is voluntary, and all responses will be kept strictly confidential. With your permission, I would like to record this interview for accuracy purposes.

Do you have any questions before we begin?

---

### Section A: Background Information

1. Could you please tell me about your role/position and how long you have been in this position?

2. How does your work relate to {topic.lower()}?

---

### Section B: Main Interview Questions

"""

        for i, obj in enumerate(objectives, 1):
            obj_clean = obj.strip()
            if obj_clean.lower().startswith('to '):
                obj_clean = obj_clean[3:]
            
            interview_content += f"""
#### Theme {i}: {obj_clean.capitalize()}

**Q{i}.1:** In your experience, how would you describe the current state of {obj_clean.lower()}?

**Q{i}.2:** What are the main factors that influence {obj_clean.lower()}?

**Q{i}.3:** What challenges have you observed regarding {obj_clean.lower()}?

**Q{i}.4:** What measures or strategies do you think could improve {obj_clean.lower()}?

**Probes:**
- Can you give me an example?
- Could you elaborate on that?
- What has been your personal experience with this?

"""

        interview_content += """
---

### Section C: Closing Questions

1. Is there anything else you would like to add that we haven't discussed?

2. Who else would you recommend I speak with about this topic?

---

### Closing Script

Thank you very much for your time and valuable insights. Your responses will contribute significantly to this research. If you have any questions about this study, please feel free to contact me.

---

*Interview conducted by: _______________*  
*Date: _______________*  
*Duration: _______________*
"""

        interview_path = os.path.join(output_dir, f"Interview_Guide_{timestamp}.md")
        with open(interview_path, 'w', encoding='utf-8') as f:
            f.write(interview_content)

    if include_fgd:
        await publish_log("👥 Generating Focus Group Discussion (FGD) Guide...")
    
        # ===================== FGD GUIDE =====================
        fgd_content = f"""# Focus Group Discussion (FGD) Guide
## {topic}

---

### Session Details
- **Topic:** {topic}
- **Target Participants:** 8-12 participants per session
- **Duration:** 60-90 minutes
- **Materials Needed:** Flip chart, markers, audio recorder, refreshments

---

### Moderator's Introduction (5 minutes)

Welcome everyone and thank you for taking time to participate in this discussion. My name is ____________ and I will be facilitating today's session.

We are here to discuss **{topic}**. This discussion is part of an academic research study. There are no right or wrong answers – we are interested in your experiences, opinions, and perspectives.

**Ground Rules:**
1. One person speaks at a time
2. All opinions are valid and respected
3. Feel free to agree or disagree with others
4. Please keep what is said in this room confidential
5. We will be recording for accuracy – is everyone comfortable with this?

---

### Warm-up Activity (5 minutes)

Let's go around the room and have each person briefly introduce themselves and share one word that comes to mind when you think of {topic.lower()}.

---

### Main Discussion Questions

"""

        for i, obj in enumerate(objectives, 1):
            obj_clean = obj.strip()
            if obj_clean.lower().startswith('to '):
                obj_clean = obj_clean[3:]
            
            fgd_content += f"""
#### Topic {i}: {obj_clean.capitalize()} (15 minutes)

**Opening Question:** What is your understanding of {obj_clean.lower()}?

**Follow-up Questions:**
1. What has been your experience with {obj_clean.lower()}?
2. What do you see as the main challenges?
3. What improvements would you suggest?

**Activity:** Let's brainstorm solutions on the flip chart.

"""

        fgd_content += """
---

### Wrap-up (10 minutes)

1. Of all the things we discussed today, what do you think is the most important issue?

2. Is there anything we missed that you would like to add?

---

### Closing

Thank you all for your valuable participation. Your insights will be very helpful for this research. If you have any questions later, please feel free to contact me.

*[Distribute refreshments and any appreciation tokens]*

---

**Session Notes:**

- Date: _______________
- Location: _______________
- Number of Participants: _______________
- Moderator: _______________
- Note-taker: _______________
"""

        fgd_path = os.path.join(output_dir, f"FGD_Guide_{timestamp}.md")
        with open(fgd_path, 'w', encoding='utf-8') as f:
            f.write(fgd_content)

    if include_observation:
        await publish_log("📋 Generating Observation Checklist...")
    
        # ===================== OBSERVATION CHECKLIST =====================
        observation_content = f"""# Observation Checklist
## {topic}

---

### Observer Information
- **Observer Name:** _______________
- **Date:** _______________
- **Time:** Start: _______ End: _______
- **Location:** _______________

---

### Instructions
Observe and record findings related to each criterion. Use the rating scale:
- **1** = Not Present / Poor
- **2** = Partially Present / Fair
- **3** = Present / Good
- **4** = Fully Present / Excellent
- **N/A** = Not Applicable

---

### Observation Criteria

"""

        for i, obj in enumerate(objectives, 1):
            obj_clean = obj.strip()
            if obj_clean.lower().startswith('to '):
                obj_clean = obj_clean[3:]
            
            observation_content += f"""
#### Category {i}: {obj_clean.capitalize()}

| # | Observation Item | 1 | 2 | 3 | 4 | N/A | Notes |
|---|-----------------|---|---|---|---|-----|-------|
| {i}.1 | Evidence of {obj_clean.lower()} practices | [ ] | [ ] | [ ] | [ ] | [ ] | |
| {i}.2 | Resources available for {obj_clean.lower()} | [ ] | [ ] | [ ] | [ ] | [ ] | |
| {i}.3 | Staff/participant engagement | [ ] | [ ] | [ ] | [ ] | [ ] | |
| {i}.4 | Documentation and records | [ ] | [ ] | [ ] | [ ] | [ ] | |
| {i}.5 | Overall impression | [ ] | [ ] | [ ] | [ ] | [ ] | |

"""

        observation_content += """
---

### General Observations

**Physical Environment:**
_____________________________________________________________

**Interactions Observed:**
_____________________________________________________________

**Challenges Noted:**
_____________________________________________________________

**Positive Aspects:**
_____________________________________________________________

---

### Summary and Recommendations

_____________________________________________________________

---

**Observer's Signature:** _______________  
**Date:** _______________
"""

        observation_path = os.path.join(output_dir, f"Observation_Checklist_{timestamp}.md")
        with open(observation_path, 'w', encoding='utf-8') as f:
            f.write(observation_content)

    await publish_log("✅ Study tools generated successfully!")

    files = [path for path in [questionnaire_path, interview_path, fgd_path, observation_path] if path]

    return {
        'questionnaire_path': questionnaire_path,
        'interview_path': interview_path,
        'fgd_path': fgd_path,
        'observation_path': observation_path,
        'files': files
    }
