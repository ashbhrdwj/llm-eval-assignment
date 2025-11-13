from typing import Dict, Any, TypedDict
import abc

class JudgeResult(TypedDict):
    raw_output: Dict[str, Any]
    model_version: str
    latency_ms: int

class BaseEngine(abc.ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abc.abstractmethod
    async def evaluate(self, case: Dict[str, Any], prompt_template: str, schema: Dict[str, Any], timeout: int, seed: int) -> JudgeResult:
        """Evaluate a single test case. Returns a JudgeResult containing raw_output and metadata."""
        raise NotImplementedError()
