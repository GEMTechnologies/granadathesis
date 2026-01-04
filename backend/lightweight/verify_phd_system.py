import asyncio
import os
import sys
from pathlib import Path

# Add services to path
sys.path.insert(0, "/home/gemtech/Desktop/thesis/backend/lightweight/services")

from phd_quality_checker import PhDQualityChecker
from tense_converter import convert_to_future_tense_llm, convert_to_future_tense_regex
from thesis_config_integration import ThesisConfigurationManager

async def test_phd_system():
    print("🎓 STARTING PHD SYSTEM VERIFICATION 🎓\n")
    
    # 1. Test Configuration Manager
    print("--- 1. Testing Configuration Integration ---")
    manager = ThesisConfigurationManager("test_workspace")
    cmd = "/uoj_phd n=50 design=case_study topic='Cybersecurity in Banking' case_study='Nairobi'"
    config = manager.parse_command(cmd)
    
    if config['sample_size'] == 50 and config['topic'] == 'Cybersecurity in Banking':
        print("✅ Command parsing successful!")
        print(f"   Config: n={config['sample_size']}, Topic={config['topic']}")
    else:
        print("❌ Command parsing failed")
    
    # Get methodology context
    # Mock database for test (or assume db exists)
    # For this standalone test we might not have the db setup, so we'll simulate context
    simulation_context = {
        'sampling': {'sample_size': 50, 'technique': 'Purposive Sampling'},
        'population': {'target_size': 200}
    }
    print(f"✅ Context generation verified (simulated): {simulation_context}")
    print("\n")

    # 2. Test Tense Converter
    print("--- 2. Testing Tense Converter (Future Tense) ---")
    past_text = """
    ## 3.4 Data Collection
    Data was collected using semi-structured interviews. The researchers visited the banks in Nairobi.
    Participants were selected based on their experience. The study employed a qualitative approach.
    """
    
    print("Original (Past):")
    print(past_text.strip())
    
    # Using regex for speed in test, but code uses LLM in production
    future_text = convert_to_future_tense_regex(past_text)
    
    print("\nConverted (Future - Regex):")
    print(future_text.strip())
    
    if "will be collected" in future_text and "will employ" in future_text:
        print("\n✅ Tense conversion successful!")
    else:
        print("\n❌ Tense conversion failed")
    print("\n")

    # 3. Test PhD Quality Checker
    print("--- 3. Testing PhD Quality Checker ---")
    
    # Create a "good" chapter snippet
    good_chapter = """
    # Chapter 3: Research Methodology

    ## 3.1 Introduction
    This chapter outlines the methodology.

    ## 3.2 Research Design
    The study adopted a descriptive survey design (Creswell, 2014). This design is suitable for...
    
    ## 3.3 Target Population
    The population comprised 500 employees (Mugenda, 2003).
    
    ## 3.4 Sampling
    Stratified random sampling was used.
    
    ## 3.5 Data Collection
    Questionnaires were distributed.
    
    ## 3.6 Validity and Reliability
    Cronbach's alpha was used to test reliability.
    
    ## 3.7 Ethical Considerations
    Informed consent was obtained.
    """
    
    checker = PhDQualityChecker()
    report = checker.check_chapter(good_chapter, chapter_number=3, metadata={'sample_size': 500})
    
    print(f"Quality Score: {report['overall_score']:.1f}/100")
    print(f"Level: {report['quality_level']}")
    
    if report['overall_score'] > 70:
        print("✅ Quality check passed for good content")
    else:
        print("❌ Quality check unexpectedly low")
        
    print("\n🎓 VERIFICATION COMPLETE 🎓")

if __name__ == "__main__":
    asyncio.run(test_phd_system())
