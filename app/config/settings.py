from pydantic import BaseModel
from typing import Optional


class ContainerConfig(BaseModel):
    cpu_limit: int = 2
    memory_limit: str = "1g"
    timeout: int = 300
    max_file_size: int = 10485760
    network_disabled: bool = True
    privileged_mode: bool = False


class WorkflowConfig(BaseModel):
    total_budget: float = 100.0
    max_reflection_count: int = 2
    default_timeout: int = 300


class SafetyConfig(BaseModel):
    block_dangerous_patterns: bool = True
    allowed_extensions: list = []
    max_repo_size: int = 104857600
