from typing import Dict, Any, Optional, List
import httpx
import json
from core.config import settings
from tools.filesystem import write_file, read_file, list_files

class DeepSeekService:
    def __init__(self):
        self.api_key = settings.DEEPSEEK_API_KEY
        self.base_url = "https://api.deepseek.com/v1"  # Verify exact endpoint
        
    async def generate_content(
        self, 
        prompt: str, 
        system_prompt: str = "You are a helpful academic assistant.",
        temperature: float = 0.7,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        if not self.api_key:
            raise ValueError("DeepSeek API Key is not configured")
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        payload = {
            "model": "deepseek-chat", 
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 4000
        }
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        
        async with httpx.AsyncClient() as client:
            # First call to LLM
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60.0
            )
            response.raise_for_status()
            response_data = response.json()
            message = response_data["choices"][0]["message"]
            
            # Check for tool calls
            if message.get("tool_calls"):
                # Append assistant's message with tool calls
                messages.append(message)
                
                # Execute tool calls
                for tool_call in message["tool_calls"]:
                    function_name = tool_call["function"]["name"]
                    arguments = json.loads(tool_call["function"]["arguments"])
                    
                    result = await self._execute_tool(function_name, arguments)
                    
                    # Append tool result
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": json.dumps(result)
                    })
                
                # Second call to LLM with tool results
                payload["messages"] = messages
                # Remove tools from second call to prevent loops (optional, but safer for now)
                # payload.pop("tools", None) 
                # payload.pop("tool_choice", None)
                
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=60.0
                )
                response.raise_for_status()
                final_message = response.json()["choices"][0]["message"]["content"]
                return final_message
            
            return message["content"]

    async def _execute_tool(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the requested tool."""
        try:
            if function_name == "write_file":
                return write_file(arguments["path"], arguments["content"])
            elif function_name == "read_file":
                return read_file(arguments["path"])
            elif function_name == "list_files":
                return list_files(arguments.get("path", "."))
            else:
                return {"status": "error", "error": f"Unknown tool: {function_name}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

deepseek_service = DeepSeekService()
