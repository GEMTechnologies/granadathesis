#!/usr/bin/env python3
"""Test DeepSeek API directly inside Docker"""
import asyncio
import sys
sys.path.insert(0, '/app')

from services.deepseek_client import deepseek_client


async def test():
    try:
        print("Testing DeepSeek API...")
        print(f"API Key present: {bool(deepseek_client.api_key)}")
        print(f"API Key (first 10 chars): {deepseek_client.api_key[:10] if deepseek_client.api_key else 'None'}")
        
        response = await deepseek_client.generate(
            prompt="Write one sentence about machine learning.",
            system_prompt="You are a helpful assistant.",
            max_tokens=50,
            temperature=0.7
        )
        
        print(f"\n✓ SUCCESS!")
        print(f"Response: {response}")
        return True
        
    except Exception as e:
        print(f"\n✗ FAILED!")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test())
    sys.exit(0 if success else 1)
