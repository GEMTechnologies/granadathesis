import re

def extract_short_theme(full_topic: str) -> str:
    """Extract 3-5 key words from a topic for use in objectives, headings, etc.
    
    Example:
        Input: "Security sector reform and political transition in East Africa: A critical analysis of security sector institution in South Sudan, 2011-2014"
        Output: "security sector reform political transition"
    """
    if not full_topic:
        return "the research topic"
    
    # Remove common phrases and prefixes
    text = full_topic.lower()
    for phrase in ['a critical analysis of', 'an examination of', 'a study of', 
                   'an investigation of', 'an assessment of', 'the impact of',
                   'investigating', 'exploring', 'analysing', 'analyzing',
                   'examining', 'assessing', 'evaluating']:
        text = text.replace(phrase, ' ')
    
    # Remove date ranges
    text = re.sub(r'\d{4}\s*[-–]\s*\d{4}', '', text)
    text = re.sub(r',\s*\d{4}', '', text)
    
    # Skip common words
    skip_words = {'the', 'and', 'for', 'with', 'from', 'that', 'this', 'which', 
                  'their', 'of', 'in', 'on', 'a', 'an', 'to', 'by', 'as', 'is',
                  'case', 'study', 'analysis', 'research', 'investigation'}
    words = [w.strip('.,;:()') for w in text.split() if w.lower() not in skip_words and len(w) > 2]
    
    # Return first 4-5 key words
    result = ' '.join(words[:5])
    return result if result else "the research topic"


def generate_smart_objectives(topic: str, num_objectives: int = 4) -> list:
    """Generate meaningful academic objectives based on the topic.
    
    Uses sub-themes to ensure professional academic quality without placeholders.
    """
    short_theme = extract_short_theme(topic)
    
    # Generic but professional academic themes
    themes = [
        f"institutional and regulatory frameworks governing {short_theme}",
        f"critical challenges and barriers affecting {short_theme} implementation",
        f"stakeholder perspectives and socio-political dynamics of {short_theme}",
        f"impact of regional cooperation and external actors on {short_theme}",
        f"underlying socio-economic drivers and conflict legacies in {short_theme}",
        f"strategies and policy interventions for sustainable {short_theme} reform"
    ]
    
    # Generate based on themes
    objectives = [f"To examine the {themes[0]}"]
    if num_objectives > 1:
        objectives.append(f"To analyse the {themes[1]}")
    if num_objectives > 2:
        objectives.append(f"To evaluate the {themes[2]}")
    if num_objectives > 3:
        objectives.append(f"To assess the {themes[3]}")
    if num_objectives > 4:
        objectives.append(f"To investigate the {themes[4]}")
    if num_objectives > 5:
        objectives.append(f"To evaluate the {themes[5]}")
        
    return objectives[:num_objectives]


def normalize_objectives(objectives: any, topic: str, case_study: str) -> dict:
    """Normalize objectives into {general: str, specific: [str,...]}."""
    if isinstance(objectives, dict):
        general = objectives.get("general") or ""
        specific = objectives.get("specific") or []
    elif isinstance(objectives, list):
        general = ""
        specific = objectives
    elif isinstance(objectives, str):
        general = objectives
        specific = []
    else:
        general = ""
        specific = []

    specific = [o.strip() for o in specific if isinstance(o, str) and o.strip()]

    if not general:
        if specific:
            general = f"To investigate {extract_short_theme(topic)} in the context of {case_study}"
        else:
            general = f"To investigate {topic} in the context of {case_study}"

    if not specific:
        specific = generate_smart_objectives(topic, 4)

    return {"general": general, "specific": specific}
