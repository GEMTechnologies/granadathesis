import asyncio
import sys
import os

# Add backend/lightweight to path
sys.path.append(os.path.abspath("backend/lightweight"))

# Mock settings if needed
os.environ["TAVILY_API_KEY"] = "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"
os.environ["DEEPSEEK_API_KEY"] = "sk-bb8046b9210e4a67b1b7e789c06d5ca3"

# Mock core.events
from unittest.mock import AsyncMock, MagicMock
sys.modules["core.events"] = MagicMock()
sys.modules["core.events"].events = AsyncMock()
sys.modules["core.events"].events.log = AsyncMock()

# Mock app.core.config
sys.modules["app"] = MagicMock()
sys.modules["app.core"] = MagicMock()
sys.modules["app.core.config"] = MagicMock()
sys.modules["app.core.config"].settings = MagicMock()
sys.modules["app.core.config"].settings.TAVILY_API_KEY = os.environ["TAVILY_API_KEY"]

from services.content_verifier import content_verifier

async def test():
    print("Testing Content Verifier...")
    
    content = """
    The 2024 Solar Eclipse had a significant impact on the global economy. 
    It caused a 5% drop in global stock markets on April 8th, 2024.
    NASA reported that the eclipse lasted for 10 hours.
    """
    
    topic = "Impact of 2024 Solar Eclipse"
    
    result = await content_verifier.verify_and_correct(content, topic)
    
    print("\nOriginal Content:")
    print(content)
    
    print("\nCorrected Content:")
    print(result["content"])
    
    print("\nCorrections:")
    for issue in result["corrections"]:
        print(f"- Claim: {issue['claim']}")
        print(f"  Status: {issue['status']}")
        print(f"  Reasoning: {issue['reasoning']}")

if __name__ == "__main__":
    asyncio.run(test())
