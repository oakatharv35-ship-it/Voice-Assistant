import requests
import json
import sys
from config import OLLAMA_BASE_URL, OLLAMA_MODEL

class OllamaClient:
    def __init__(self, model: str = OLLAMA_MODEL, base_url: str = OLLAMA_BASE_URL):
        self.model = model
        self.base_url = base_url

    def chat(self, messages: list[dict], system: str = None) -> str:
        """Send a chat request to Ollama and return the response text."""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        if system:
            payload["system"] = system

        resp = requests.post(f"{self.base_url}/api/chat", json=payload)
        resp.raise_for_status()
        return resp.json()["message"]["content"]

    def generate(self, prompt: str, system: str = None) -> str:
        """Single-turn generation."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system

        resp = requests.post(f"{self.base_url}/api/generate", json=payload)
        resp.raise_for_status()
        return resp.json()["response"]

    def structured_output(self, prompt: str, system: str = None) -> dict:
        """Force JSON output using Ollama's native JSON mode."""
        payload = {
            "model":  self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",   # ← Ollama native JSON mode, forces valid JSON at inference level
        }
        if system:
            payload["system"] = system

        resp = requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        raw = resp.json()["response"]
        print(f"[OllamaClient] Structured output raw: {repr(raw)}")
        return json.loads(raw)   # guaranteed valid JSON, no cleaning needed
