import re

message = '/uoj_phd n=120 design=case_study topic="Security sector Reform and Political Transition in East Africa: A critical analysis of Security sector institutipon in South Sudan, 2011-2014" case_study="Juba"'

print(f"Original message: {message}")

# 1. Test ThesisConfigurationManager regex
topic_match_1 = re.search(r'topic[=:\s]+["\']([^"\']+)["\']', message, re.IGNORECASE)
print(f"ConfigManager match: {topic_match_1.group(1) if topic_match_1 else 'None'}")

# 2. Test ActionAgent regex
topic_match_2 = re.search(r"topic\s*[:=]\s*['\"]?([^'\"]+)['\"]?", message, re.IGNORECASE)
print(f"ActionAgent match: {topic_match_2.group(1) if topic_match_2 else 'None'}")

# 3. Test ActionAgent fallback scenario (if regex fails)
fallback = message[:50]
print(f"Fallback: {fallback}")
