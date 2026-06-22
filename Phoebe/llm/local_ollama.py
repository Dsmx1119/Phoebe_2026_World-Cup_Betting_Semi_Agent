from __future__ import annotations

import json
from typing import Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

from sportmira.config import Settings
from sportmira.llm.prompts import REPORT_SYSTEM_PROMPT


class LocalOllamaClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def generate(self, prompt: str, timeout: float = 4.0) -> Optional[str]:
        url = self.settings.ollama_base_url.rstrip("/") + "/api/generate"
        payload = json.dumps(
            {
                "model": self.settings.ollama_model,
                "prompt": f"{REPORT_SYSTEM_PROMPT}\n\n{prompt}",
                "stream": False,
                "options": {"temperature": 0.1},
            }
        ).encode("utf-8")
        request = Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request, timeout=timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (URLError, TimeoutError, OSError, json.JSONDecodeError):
            return None
        text = data.get("response")
        if not isinstance(text, str) or not text.strip():
            return None
        return text.strip()

    def available(self) -> bool:
        return self.generate("Return exactly: ok", timeout=2.0) is not None
