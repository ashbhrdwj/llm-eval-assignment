import os
import time
from typing import Dict, Any
import httpx
from .base import BaseEngine, JudgeResult

class HuggingFaceAdapter(BaseEngine):
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config or {})
        self.api_token = self.config.get("api_token") or os.getenv("HF_API_TOKEN")
        self.model = self.config.get("model") or self.config.get("name") or "mistral"
        self.model_version = f"hf/{self.model}"

    async def evaluate(self, case: Dict[str, Any], prompt_template: str, schema: Dict[str, Any], timeout: int = 30, seed: int = 42) -> JudgeResult:
        start = time.time()
        prompt = prompt_template.format(**case)
        if not self.api_token:
            raw = {"tutor_response": "[hf stub response] " + case.get("student_query", ""), "metrics": {}, "meta": {"note": "hf not configured"}}
            latency_ms = int((time.time() - start) * 1000)
            return JudgeResult(raw_output=raw, model_version=self.model_version, latency_ms=latency_ms)

        url = f"https://api-inference.huggingface.co/models/{self.model}"
        headers = {"Authorization": f"Bearer {self.api_token}"}
        payload = {"inputs": prompt, "parameters": {"max_new_tokens": 512, "temperature": 0.0}}
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                r = await client.post(url, headers=headers, json=payload)
                r.raise_for_status()
                out = r.json()
                # HF often returns a list with generated_text
                if isinstance(out, list) and len(out) > 0 and "generated_text" in out[0]:
                    text = out[0]["generated_text"]
                else:
                    text = str(out)
                raw = {"tutor_response": text, "engine_output": out, "meta": {"case_id": case.get("id")}}
                latency_ms = int((time.time() - start) * 1000)
                return JudgeResult(raw_output=raw, model_version=self.model_version, latency_ms=latency_ms)
            except Exception as e:
                raw = {"tutor_response": "[hf error] " + str(e), "metrics": {}, "meta": {"case_id": case.get("id"), "error": str(e)}}
                latency_ms = int((time.time() - start) * 1000)
                return JudgeResult(raw_output=raw, model_version=self.model_version, latency_ms=latency_ms)
