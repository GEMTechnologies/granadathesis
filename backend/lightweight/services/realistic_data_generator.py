import pandas as pd
import numpy as np
from typing import Dict, Any, List

def generate_realistic_responses(
    df_demographics: pd.DataFrame, 
    likert_scale: int = 5,
    items_per_objective: int = 3,
    num_objectives: int = 3
) -> pd.DataFrame:
    """
    Generate realistic questionnaire responses correlated with demographics.
    """
    sample_size = len(df_demographics)
    total_items = items_per_objective * num_objectives
    
    # Base scores for each objective (1.0 to scale_max)
    # We add some bias based on demographics
    
    df_responses = df_demographics.copy()
    
    for obj_idx in range(1, num_objectives + 1):
        # Objective-specific bias
        # e.g., higher education might correlate with slightly higher/lower scores on certain topics
        edu_map = {'primary': 0, 'secondary': 0.2, 'tertiary': 0.4, 'postgraduate': 0.6}
        age_map = {'18-25': 0.1, '26-35': 0.2, '36-45': 0.3, '46-55': 0.2, '55+': 0}
        
        for item_idx in range(1, items_per_objective + 1):
            col_name = f"OBJ{obj_idx}_Q{item_idx}"
            
            # Generate scores with natural variance and demographic bias
            scores = []
            for _, row in df_demographics.iterrows():
                bias = edu_map.get(row['Education_Level'], 0) + age_map.get(row['Age_Range'], 0)
                
                # Base score is around the middle of the scale
                base = (likert_scale + 1) / 2.0
                
                # Dynamic variance
                variance = np.random.normal(bias, 0.8)
                
                score = round(np.clip(base + variance, 1, likert_scale))
                scores.append(int(score))
                
            df_responses[col_name] = scores
            
    return df_responses

def generate_qualitative_feedback(df_demographics: pd.DataFrame, topic: str) -> List[str]:
    """
    Generate synthetic qualitative feedback matching the persona.
    """
    feedbacks = []
    
    # Generic templates (would be better with LLM but for efficiency we use templates with persona injection)
    templates = [
        "In my opinion as a {edu} professional, {topic} needs more attention in our community.",
        "Based on my experience in the {age} age group, I feel that {topic} is a critical issue.",
        "I believe {topic} affects everyone, especially when considering the lack of resources.",
        "From the perspective of {gender} respondents, {topic} should be addressed through policy changes.",
        "My education at the {edu} level has taught me that {topic} is complex and requires multifaceted solutions."
    ]
    
    for _, row in df_demographics.sample(min(len(df_demographics), 10)).iterrows():
        tpl = np.random.choice(templates)
        feedback = tpl.format(
            edu=row['Education_Level'],
            age=row['Age_Range'],
            gender=row['Gender'],
            topic=topic
        )
        feedbacks.append(feedback)
        
    return feedbacks
