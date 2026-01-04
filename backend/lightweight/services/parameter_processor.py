from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

def validate_parameters(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and normalize thesis generation parameters.
    """
    errors = []
    
    # Required fields
    if not params.get('topic'):
        errors.append("Research topic is required")
    
    # Sample size validation
    sample_size = params.get('sampleSize', 385)
    if not (30 <= sample_size <= 1000):
        errors.append(f"Sample size must be between 30 and 1000 (got {sample_size})")
    
    # Check percentage sums
    distributions = [
        ('genderDistribution', 'Gender distribution'),
        ('ageDistribution', 'Age distribution'),
        ('educationDistribution', 'Education distribution')
    ]
    
    for dist_key, dist_name in distributions:
        dist = params.get(dist_key)
        if dist:
            dist_sum = sum(dist.values())
            if abs(dist_sum - 100) > 0.1:
                errors.append(f"{dist_name} must sum to 100% (currently {dist_sum:.1f}%)")
    
    return {
        "isValid": len(errors) == 0,
        "errors": errors
    }

def calculate_counts(total: int, distribution: Dict[str, float]) -> Dict[str, int]:
    """
    Convert percentages to actual respondent counts.
    Ensures the total matches exactly by adjusting the last category.
    """
    counts = {}
    keys = list(distribution.keys())
    running_total = 0
    
    for key in keys[:-1]:
        count = int(round((distribution[key] / 100.0) * total))
        counts[key] = count
        running_total += count
    
    # Last category gets the remainder
    if keys:
        counts[keys[-1]] = max(0, total - running_total)
        
    return counts

def generate_demographic_df(params: Dict[str, Any]) -> pd.DataFrame:
    """
    Generate a DataFrame of demographic data based on parameters.
    Includes natural variance and some basic correlations.
    """
    sample_size = params.get('sampleSize', 385)
    
    # Calculate counts
    gender_dist = params.get('genderDistribution', {'male': 50, 'female': 50, 'other': 0})
    age_dist = params.get('ageDistribution', {'18-25': 20, '26-35': 30, '36-45': 25, '46-55': 15, '55+': 10})
    edu_dist = params.get('educationDistribution', {'primary': 10, 'secondary': 30, 'tertiary': 45, 'postgraduate': 15})
    
    gender_counts = calculate_counts(sample_size, gender_dist)
    age_counts = calculate_counts(sample_size, age_dist)
    edu_counts = calculate_counts(sample_size, edu_dist)
    
    # Create lists
    genders = []
    for g, count in gender_counts.items():
        genders.extend([g] * count)
    
    ages = []
    for a, count in age_counts.items():
        ages.extend([a] * count)
        
    edus = []
    for e, count in edu_counts.items():
        edus.extend([e] * count)
        
    # Shuffle lists
    np.random.shuffle(genders)
    np.random.shuffle(ages)
    np.random.shuffle(edus)
    
    # Ensure all lists have exactly sample_size elements (should be true by check in calculate_counts)
    genders = genders[:sample_size]
    ages = ages[:sample_size]
    edus = edus[:sample_size]
    
    # Create DataFrame
    df = pd.DataFrame({
        'Respondent_ID': range(1, sample_size + 1),
        'Gender': genders,
        'Age_Range': ages,
        'Education_Level': edus
    })
    
    return df
