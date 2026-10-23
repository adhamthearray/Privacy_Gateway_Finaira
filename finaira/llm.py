from dataclasses import dataclass
import re
import os
import json
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from .env import load_project_env


@dataclass
class MockLLM:
    mode: str = "echo"

    def complete(self, system_prompt: str, task: str, protected_document: str) -> str:
        if self.mode == "invent":
            return protected_document + " __FN_PERSON_9999__"
        if self.mode == "leak":
            return protected_document + " original-sensitive-value"
        # Deterministic mock: the document is the answer, preserving tokens exactly.
        return protected_document


class OpenAIResponsesLLM:
    """Real OpenAI Responses API adapter using OPENAI_API_KEY."""
    def __init__(self, model: str | None = None, client=None):
        from openai import OpenAI
        load_project_env()
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-5-mini")
        self.client = client or OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def complete(self, system_prompt: str, task: str, protected_document: str) -> str:
        response = self.client.responses.create(
            model=self.model,
            instructions=system_prompt,
            input=f"Task:\n{task}\n\nProtected document:\n{protected_document}",
        )
        return response.output_text


class GeminiLLM:
    """Gemini generateContent adapter using GEMINI_API_KEY and REST."""
    def __init__(self, model: str | None = None, api_key: str | None = None, timeout: int = 30, retries: int = 1):
        load_project_env()
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.timeout = timeout
        self.retries = retries
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set")

    def complete(self, system_prompt: str, task: str, protected_document: str) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        body = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": f"Task:\n{task}\n\nProtected document:\n{protected_document}"}]}],
        }
        request = Request(url, data=json.dumps(body).encode("utf-8"), method="POST",
                          headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key})
        for attempt in range(self.retries + 1):
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    data = json.loads(response.read().decode("utf-8"))
                break
            except HTTPError as exc:
                if exc.code not in {429, 500, 502, 503, 504} or attempt >= self.retries:
                    raise
                time.sleep(2 ** attempt)
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("GEMINI_EMPTY_RESPONSE") from exc
