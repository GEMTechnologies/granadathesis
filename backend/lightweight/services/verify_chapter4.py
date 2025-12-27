import sys
import os
import random

# Add parent directory to path so we can import the module
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, '../..'))
sys.path.append(backend_dir)

from lightweight.services.chapter4_generator import Chapter4Generator

# Mock data
likert_items = {
    'S1': {'text': 'Statement 1 text here'},
    'S2': {'text': 'Statement 2 text here', 'variable': 'S2'},
    'S3': {'text': 'Statement 3 text here', 'variable': 'S3'},
    'S4': {'text': 'Statement 4 text here', 'variable': 'S4'},
    'S5': {'text': 'Statement 5 text here', 'variable': 'S5'}
}
variable_mapping = {'likert_items': likert_items}

# Mock questionnaire data
questionnaire_data = []
for _ in range(50):
    questionnaire_data.append({
        'S1': str(random.randint(1, 5)),
        'S2': str(random.randint(1, 5)),
        'S3': str(random.randint(1, 5)),
        'S4': str(random.randint(1, 5)),
        'S5': str(random.randint(1, 5))
    })

generator = Chapter4Generator(
    topic="Test Topic",
    case_study="Test Case",
    objectives=["To test header generation"],
    questionnaire_data=questionnaire_data,
    variable_mapping=variable_mapping,
    hypotheses=["There is a significant relationship."]
)


async def main():
    print("--- TESTING LIKERT TABLE ---")
    dummy_items = [{'stats': {'n': 100, 'mean': 4.5, 'std': 0.5}}]
    likert_table, table_num = generator._format_likert_descriptive_table_phd("Test Title", dummy_items, 1)
    print(likert_table)
    if "|:-" in likert_table or "-:| " in likert_table:
        print("FAILED: Likert table contains centered separators")
    else:
        print("PASSED: Likert table is clean")

    print("\n--- TESTING INFERENTIAL STATISTICS ---")
    inferential_stats = await generator._generate_inferential_stats_section(1, "To test header generation")
    print(inferential_stats)

    if "|:-" in inferential_stats or "-:| " in inferential_stats:
        print("FAILED: Inferential stats contains centered separators")
    else:
        print("PASSED: Inferential stats is clean")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

