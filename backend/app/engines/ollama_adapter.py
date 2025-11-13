import os
import time
from typing import Dict, Any
import httpx
from .base import BaseEngine, JudgeResult

class OllamaAdapter(BaseEngine):
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config or {})
        self.base_url = self.config.get("base_url") or os.getenv("OLLAMA_URL")
        self.model = self.config.get("model") or self.config.get("name") or "ollama-model"
        self.model_version = f"ollama/{self.model}"

    async def evaluate(self, case: Dict[str, Any], prompt_template: str, schema: Dict[str, Any], timeout: int = 30, seed: int = 42) -> JudgeResult:
        start = time.time()
        # Build prompt from template (template may include placeholders)
        prompt = prompt_template.format(**case)
        # Ollama HTTP Inference (simple POST) - this is a best-effort stub; some deployments may differ
        if not self.base_url:
            # Fallback: return a simple structured response
            raw = {"tutor_response": "[ollama stub response] " + case.get("student_query", ""), "metrics": {}, "meta": {"note": "ollama not configured"}}
            latency_ms = int((time.time() - start) * 1000)
            return JudgeResult(raw_output=raw, model_version=self.model_version, latency_ms=latency_ms)

        url = f"{self.base_url}/generate"
        payload = {"model": self.model, "prompt": prompt, "max_tokens": 512, "temperature": 0.0}
        # Include seed if supported
        if seed is not None:
            payload["seed"] = seed
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                r = await client.post(url, json=payload)
                r.raise_for_status()
                out = r.json()
                # Attempt to extract text
                text = out.get("text") or out.get("generated_text") or str(out)
                raw = {"tutor_response": text, "engine_output": out, "meta": {"case_id": case.get("id")}}
                latency_ms = int((time.time() - start) * 1000)
                return JudgeResult(raw_output=raw, model_version=self.model_version, latency_ms=latency_ms)
            except Exception as e:
                raw = {"tutor_response": "[ollama error] " + str(e), "metrics": {}, "meta": {"case_id": case.get("id"), "error": str(e)}}
                latency_ms = int((time.time() - start) * 1000)
                return JudgeResult(raw_output=raw, model_version=self.model_version, latency_ms=latency_ms)
