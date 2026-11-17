"""
Mercurius Agentic System - Core Types
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable
import time, uuid

class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"

class WorkflowPattern(str, Enum):
    RE_ACT = "react"
    PLAN_AND_SOLVE = "plan_and_solve"
    PLAN_AND_EXECUTE = "plan_and_execute"
    REFLECT = "reflect"
    SELF_REFINE = "self_refine"
    PIPELINE = "pipeline"
    COORDINATOR_WORKER = "coordinator_worker"
    BLACKBOARD = "blackboard"
    TREE = "tree"
    CUSTOM = "custom"

class UserRole(str, Enum):
    ADMIN = "admin"
    REGULAR = "regular"
    ANONYMOUS = "anonymous"

@dataclass
class Attachment:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    filename: str = ""
    mime_type: str = "text/plain"
    path: Optional[str] = None
    data_bytes: Optional[bytes] = None
    data_text: Optional[str] = None
    url: Optional[str] = None
    is_stream: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]

@dataclass
class ToolResult:
    tool_call_id: str
    name: str
    output: Any
    is_error: bool = False
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    artifacts: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class ChatMessage:
    role: MessageRole
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None
    attachments: List[Attachment] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "role": self.role.value if isinstance(self.role, MessageRole) else str(self.role),
            "content": self.content
        }
        if self.name:
            d["name"] = self.name
        if self.tool_calls:
            d["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.name, "arguments": tc.arguments}
                }
                for tc in self.tool_calls
            ]
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        return d

@dataclass
class AgentPersonality:
    name: str = "Mercurius Prime"
    description: str = "Sharp, professional, witty agentic AI"
    system_prompt: str = "You are Mercury, an advanced autonomous agentic AI system."
    tone: str = "sharp, professional, witty"
    temperature: float = 0.7
    max_tokens: int = 4096
    model_override: Optional[str] = None
    rules: List[str] = field(default_factory=list)

@dataclass
class ExecutionStep:
    step_number: int
    thought: str = ""
    action: Optional[str] = None
    action_input: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None
    reflection: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    duration_ms: float = 0.0
    is_final: bool = False

@dataclass
class Trajectory:
    task_id: str
    goal: str
    steps: List[ExecutionStep] = field(default_factory=list)
    success: bool = False
    reward: float = 0.0
    total_tokens: int = 0
    model_name: str = ""
    timestamp: float = field(default_factory=time.time)

@dataclass
class RunContext:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = "default_user"
    user_role: UserRole = UserRole.REGULAR
    token_budget: Optional[int] = None
    current_tokens: int = 0
    max_subagents: int = 5
    current_depth: int = 0
    attachments: List[Attachment] = field(default_factory=list)
    target_llm: Optional[str] = None
    allow_budget_override: bool = False
    cancel_requested: bool = False
    workflow: WorkflowPattern = WorkflowPattern.RE_ACT
    metadata: Dict[str, Any] = field(default_factory=dict)
