"""
Trajectory Checkpoint and State Time-Travel Manager for Mercury.
Enables agents to save snapshots of reasoning state, detect dead ends,
and rollback to previous stable steps with negative constraints.
"""
from __future__ import annotations
import copy
from typing import Any, Dict, List, Optional
from mercurius.core.types import ExecutionStep, ChatMessage

class Checkpoint:
    def __init__(self, step_index: int, messages: List[ChatMessage], variables: Dict[str, Any]):
        self.step_index = step_index
        self.messages = [copy.deepcopy(m) for m in messages]
        self.variables = copy.deepcopy(variables)

class CheckpointManager:
    def __init__(self, max_checkpoints: int = 10):
        self.max_checkpoints = max_checkpoints
        self.checkpoints: List[Checkpoint] = []
        self.rollbacks_performed = 0

    def save_checkpoint(self, step_index: int, messages: List[ChatMessage], variables: Optional[Dict[str, Any]] = None):
        if len(self.checkpoints) >= self.max_checkpoints:
            self.checkpoints.pop(0)
        self.checkpoints.append(Checkpoint(step_index, messages, variables or {}))

    def rollback(self, steps_back: int = 1) -> Optional[Checkpoint]:
        """
        Rolls back state by N steps. Returns the restored Checkpoint, or None if impossible.
        """
        if not self.checkpoints:
            return None

        target_idx = max(0, len(self.checkpoints) - 1 - steps_back)
        restored = self.checkpoints[target_idx]
        self.checkpoints = self.checkpoints[:target_idx + 1]
        self.rollbacks_performed += 1
        return restored

    def clear(self):
        self.checkpoints.clear()
