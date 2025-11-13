from typing import Dict, Any

# In-memory registry for engines; in production this should be persisted in DB
_registry: Dict[str, Dict[str, Any]] = {}


def register_engine(name: str, engine_type: str, config: Dict[str, Any]):
    _registry[name] = {"name": name, "type": engine_type, "config": config}


def list_engines():
    return list(_registry.values())


def get_engine(name: str):
    return _registry.get(name)

# Pre-register a mock engine
register_engine("mock", "mock", {})
