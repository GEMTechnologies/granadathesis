"""
LLM-Based Tense Converter for Thesis Proposals

Converts thesis chapters (past tense) to proposal versions (future tense)
using LLM for accurate, context-aware conversion.

Examples:
- "Data was collected using questionnaires" → "Data will be collected using questionnaires"
- "The study employed a survey design" → "The study will employ a survey design"
- "Participants were selected through stratified sampling" → "Participants will be selected through stratified sampling"
"""

from typing import Optional
import asyncio


async def convert_to_future_tense_llm(content: str, chapter_number: int = 3) -> str:
    """
    Convert thesis chapter from past tense to future tense using LLM.
    
    Args:
        content: Chapter content in past tense
        chapter_number: Chapter number (default: 3 for methodology)
    
    Returns:
        Content converted to future tense
    """
    try:
        from services.deepseek_direct import deepseek_direct_service
        
        prompt = f"""Convert this Chapter {chapter_number} from past tense (thesis) to future tense (proposal).

RULES:
1. Change all past tense verbs to future tense
2. Maintain academic tone and formality
3. Keep all citations, tables, and formatting intact
4. Change "was/were" to "will be"
5. Change "used/employed/adopted" to "will use/will employ/will adopt"
6. Keep present tense statements as-is (e.g., "This chapter outlines...")
7. Do NOT change headings or section numbers
8. Do NOT change citations or references

EXAMPLES:
- "Data was collected" → "Data will be collected"
- "The study employed" → "The study will employ"
- "Participants were selected" → "Participants will be selected"
- "was analyzed using SPSS" → "will be analyzed using SPSS"

IMPORTANT: Return ONLY the converted text, no explanations or comments.

CONTENT TO CONVERT:

{content}
"""
        
        result = await deepseek_direct_service.generate_content(
            prompt=prompt,
            system_prompt="You are an expert academic editor specializing in thesis and proposal writing. Convert the text accurately while preserving all academic elements.",
            temperature=0.3  # Low temperature for consistency
        )
        
        return result
        
    except Exception as e:
        print(f"⚠️ LLM conversion failed: {e}")
        # Fallback to regex-based conversion
        return convert_to_future_tense_regex(content)


def convert_to_future_tense_regex(content: str) -> str:
    """
    Fallback regex-based conversion (less accurate but faster).
    
    Args:
        content: Chapter content in past tense
    
    Returns:
        Content converted to future tense
    """
    import re
    
    # Comprehensive past-to-future conversions
    conversions = [
        # "was/were + past participle" → "will be + past participle"
        (r'\bwas\s+(\w+ed)\b', r'will be \1'),
        (r'\bWas\s+(\w+ed)\b', r'Will be \1'),
        (r'\bwere\s+(\w+ed)\b', r'will be \1'),
        (r'\bWere\s+(\w+ed)\b', r'Will be \1'),
        
        # Specific academic verbs
        (r'\bwas collected\b', 'will be collected'),
        (r'\bWas collected\b', 'Will be collected'),
        (r'\bwere collected\b', 'will be collected'),
        (r'\bWere collected\b', 'Will be collected'),
        
        (r'\bwas selected\b', 'will be selected'),
        (r'\bWas selected\b', 'Will be selected'),
        (r'\bwere selected\b', 'will be selected'),
        (r'\bWere selected\b', 'Will be selected'),
        
        (r'\bwas used\b', 'will be used'),
        (r'\bWas used\b', 'Will be used'),
        (r'\bwere used\b', 'will be used'),
        (r'\bWere used\b', 'Will be used'),
        
        (r'\bwas employed\b', 'will be employed'),
        (r'\bWas employed\b', 'Will be employed'),
        (r'\bwere employed\b', 'will be employed'),
        (r'\bWere employed\b', 'Will be employed'),
        
        (r'\bwas adopted\b', 'will be adopted'),
        (r'\bWas adopted\b', 'Will be adopted'),
        (r'\bwere adopted\b', 'will be adopted'),
        (r'\bWere adopted\b', 'Will be adopted'),
        
        (r'\bwas applied\b', 'will be applied'),
        (r'\bWas applied\b', 'Will be applied'),
        (r'\bwere applied\b', 'will be applied'),
        (r'\bWere applied\b', 'Will be applied'),
        
        (r'\bwas conducted\b', 'will be conducted'),
        (r'\bWas conducted\b', 'Will be conducted'),
        (r'\bwere conducted\b', 'will be conducted'),
        (r'\bWere conducted\b', 'Will be conducted'),
        
        (r'\bwas administered\b', 'will be administered'),
        (r'\bWas administered\b', 'Will be administered'),
        (r'\bwere administered\b', 'will be administered'),
        (r'\bWere administered\b', 'Will be administered'),
        
        (r'\bwas distributed\b', 'will be distributed'),
        (r'\bWas distributed\b', 'Will be distributed'),
        (r'\bwere distributed\b', 'will be distributed'),
        (r'\bWere distributed\b', 'Will be distributed'),
        
        (r'\bwas analyzed\b', 'will be analyzed'),
        (r'\bWas analyzed\b', 'Will be analyzed'),
        (r'\bwere analyzed\b', 'will be analyzed'),
        (r'\bWere analyzed\b', 'Will be analyzed'),
        
        (r'\bwas analysed\b', 'will be analysed'),
        (r'\bWas analysed\b', 'Will be analysed'),
        (r'\bwere analysed\b', 'will be analysed'),
        (r'\bWere analysed\b', 'Will be analysed'),
        
        (r'\bwas obtained\b', 'will be obtained'),
        (r'\bWas obtained\b', 'Will be obtained'),
        (r'\bwere obtained\b', 'will be obtained'),
        (r'\bWere obtained\b', 'Will be obtained'),
        
        (r'\bwas ensured\b', 'will be ensured'),
        (r'\bWas ensured\b', 'Will be ensured'),
        (r'\bwere ensured\b', 'will be ensured'),
        (r'\bWere ensured\b', 'Will be ensured'),
        
        (r'\bwas maintained\b', 'will be maintained'),
        (r'\bWas maintained\b', 'Will be maintained'),
        (r'\bwere maintained\b', 'will be maintained'),
        (r'\bWere maintained\b', 'Will be maintained'),
        
        (r'\bwas protected\b', 'will be protected'),
        (r'\bWas protected\b', 'Will be protected'),
        (r'\bwere protected\b', 'will be protected'),
        (r'\bWere protected\b', 'Will be protected'),
        
        (r'\bwas sought\b', 'will be sought'),
        (r'\bWas sought\b', 'Will be sought'),
        (r'\bwere sought\b', 'will be sought'),
        (r'\bWere sought\b', 'Will be sought'),
        
        (r'\bwas validated\b', 'will be validated'),
        (r'\bWas validated\b', 'Will be validated'),
        (r'\bwere validated\b', 'will be validated'),
        (r'\bWere validated\b', 'Will be validated'),
        
        (r'\bwas tested\b', 'will be tested'),
        (r'\bWas tested\b', 'Will be tested'),
        (r'\bwere tested\b', 'will be tested'),
        (r'\bWere tested\b', 'Will be tested'),
        
        # "The study used/employed/adopted" → "The study will use/employ/adopt"
        (r'\bThe study used\b', 'The study will use'),
        (r'\bthe study used\b', 'the study will use'),
        (r'\bThe study employed\b', 'The study will employ'),
        (r'\bthe study employed\b', 'the study will employ'),
        (r'\bThe study adopted\b', 'The study will adopt'),
        (r'\bthe study adopted\b', 'the study will adopt'),
        (r'\bThe research used\b', 'The research will use'),
        (r'\bthe research used\b', 'the research will use'),
        (r'\bThe research employed\b', 'The research will employ'),
        (r'\bthe research employed\b', 'the research will employ'),
        
        # "Data was/were" → "Data will be"
        (r'\bData was\b', 'Data will be'),
        (r'\bdata was\b', 'data will be'),
        (r'\bData were\b', 'Data will be'),
        (r'\bdata were\b', 'data will be'),
        
        # "Participants were" → "Participants will be"
        (r'\bParticipants were\b', 'Participants will be'),
        (r'\bparticipants were\b', 'participants will be'),
        (r'\bRespondents were\b', 'Respondents will be'),
        (r'\brespondents were\b', 'respondents will be'),
        
        # "Questionnaires were" → "Questionnaires will be"
        (r'\bQuestionnaires were\b', 'Questionnaires will be'),
        (r'\bquestionnaires were\b', 'questionnaires will be'),
        (r'\bInstruments were\b', 'Instruments will be'),
        (r'\binstruments were\b', 'instruments will be'),
    ]
    
    result = content
    for pattern, replacement in conversions:
        result = re.sub(pattern, replacement, result)
    
    return result


# Synchronous wrapper for compatibility
def convert_to_future_tense(content: str, chapter_number: int = 3, use_llm: bool = True) -> str:
    """
    Synchronous wrapper for tense conversion.
    
    Args:
        content: Chapter content in past tense
        chapter_number: Chapter number
        use_llm: Whether to use LLM (True) or regex (False)
    
    Returns:
        Content converted to future tense
    """
    if use_llm:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, use regex fallback
                return convert_to_future_tense_regex(content)
            else:
                return loop.run_until_complete(convert_to_future_tense_llm(content, chapter_number))
        except Exception as e:
            print(f"⚠️ LLM conversion failed, using regex: {e}")
            return convert_to_future_tense_regex(content)
    else:
        return convert_to_future_tense_regex(content)


# Example usage
if __name__ == "__main__":
    sample = """
    ## 3.2 Research Design
    
    A survey research design was adopted for this study (Creswell, 2014). This design was appropriate for collecting data from a large population (Mugenda & Mugenda, 2003). The study employed both quantitative and qualitative methods.
    
    ## 3.3 Data Collection
    
    Data was collected using structured questionnaires. The questionnaires were distributed to participants. Participants were selected through stratified random sampling.
    """
    
    print("ORIGINAL:")
    print(sample)
    print("\n" + "="*80 + "\n")
    print("CONVERTED (REGEX):")
    print(convert_to_future_tense_regex(sample))
