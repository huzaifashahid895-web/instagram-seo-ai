# backend/app/services/llm/ollama_provider.py
# Cost classification: FREE + OPEN SOURCE
"""
Ollama LLM provider implementation.
Communicates with local Ollama server (ollama.com) for LLM inference.
Default model: qwen2.5:3b-instruct-q4_K_M (Apache 2.0 license)
"""

import json
from typing import Iterator
from pydantic import BaseModel
import httpx

from app.services.providers import LLMProvider


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider"""
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen2.5:3b-instruct-q4_K_M",
        timeout: float = 120.0
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)
    
    def generate(self, prompt: str, system: str | None = None, **kwargs) -> str:
        """
        Generate text completion from prompt.
        
        Args:
            prompt: User prompt
            system: Optional system message
            **kwargs: Additional Ollama parameters (temperature, top_p, etc.)
        
        Returns:
            Generated text
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": kwargs
        }
        
        response = self._client.post(f"{self.base_url}/api/chat", json=payload)
        response.raise_for_status()
        
        data = response.json()
        return data["message"]["content"]
    
    def stream(self, prompt: str, system: str | None = None, **kwargs) -> Iterator[str]:
        """
        Stream text completion from prompt.
        
        Args:
            prompt: User prompt
            system: Optional system message
            **kwargs: Additional Ollama parameters
        
        Yields:
            Text chunks as they're generated
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": kwargs
        }
        
        with self._client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    if "message" in data and "content" in data["message"]:
                        yield data["message"]["content"]
    
    def structured_output(self, prompt: str, schema: type[BaseModel], system: str | None = None, **kwargs) -> BaseModel:
        """
        Generate structured output matching a Pydantic schema.
        
        Args:
            prompt: User prompt
            schema: Pydantic model class
            system: Optional system message
            **kwargs: Additional Ollama parameters
        
        Returns:
            Instance of the provided schema
        """
        # Add JSON schema instructions to the prompt
        schema_json = schema.model_json_schema()
        enhanced_prompt = f"""{prompt}

You must respond with valid JSON matching this exact schema:
{json.dumps(schema_json, indent=2)}

Respond with ONLY the JSON object, no additional text or explanation."""
        
        # Generate response
        response_text = self.generate(enhanced_prompt, system=system, **kwargs)
        
        # Extract JSON from response (in case there's surrounding text)
        response_text = response_text.strip()
        
        # Find JSON boundaries
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        
        if start == -1 or end == 0:
            raise ValueError(f"No JSON object found in response: {response_text[:100]}...")
        
        json_str = response_text[start:end]
        
        # Parse and validate against schema
        return schema.model_validate_json(json_str)
    
    def health_check(self) -> bool:
        """Check if Ollama server is responsive"""
        try:
            response = self._client.get(f"{self.base_url}/api/tags", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False
    
    def list_models(self) -> list[str]:
        """List available models on Ollama server"""
        try:
            response = self._client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            return [model["name"] for model in data.get("models", [])]
        except Exception:
            return []
    
    def __del__(self):
        """Cleanup HTTP client"""
        if hasattr(self, "_client"):
            self._client.close()
