"""
Human-in-the-Loop (HITL) Interruption, Review & Approval Engine for Mercurius.
Provides first-class execution suspension, checkpoint persistence,
interactive human review/approval, and audit trails.
"""
from __future__ import annotations

import enum
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class HITLDecision(str, enum.Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"
    TIMEOUT = "timeout"


@dataclass
class HITLInterrupt:
    interrupt_id: str
    task_id: str
    action_type: str        # e.g., 'TOOL_INVOCATION', 'CRITICAL_STATE_TRANSITION', 'FINOPS_OVERDRAFT'
    description: str
    payload: Dict[str, Any]
    suggested_remedy: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    decision: Optional[HITLDecision] = None
    reviewer_comment: Optional[str] = None
    resolved_at: Optional[float] = None
    modified_payload: Optional[Dict[str, Any]] = None

    def resolve(self, decision: HITLDecision, comment: Optional[str] = None, modified_payload: Optional[Dict[str, Any]] = None):
        self.decision = decision
        self.reviewer_comment = comment
        self.modified_payload = modified_payload
        self.resolved_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "interrupt_id": self.interrupt_id,
            "task_id": self.task_id,
            "action_type": self.action_type,
            "description": self.description,
            "payload": self.payload,
            "suggested_remedy": self.suggested_remedy,
            "created_at": self.created_at,
            "decision": self.decision.value if self.decision else None,
            "reviewer_comment": self.reviewer_comment,
            "resolved_at": self.resolved_at,
            "modified_payload": self.modified_payload
        }


class HITLManager:
    """
    Manages active interrupts and human sign-offs across autonomous execution loops.
    """
    def __init__(self):
        self.pending_interrupts: Dict[str, HITLInterrupt] = {}
        self.history: List[HITLInterrupt] = []

    def request_approval(
        self,
        task_id: str,
        action_type: str,
        description: str,
        payload: Dict[str, Any],
        suggested_remedy: Optional[str] = None
    ) -> HITLInterrupt:
        interrupt_id = f"hitl_{uuid.uuid4().hex[:12]}"
        interrupt = HITLInterrupt(
            interrupt_id=interrupt_id,
            task_id=task_id,
            action_type=action_type,
            description=description,
            payload=payload,
            suggested_remedy=suggested_remedy
        )
        self.pending_interrupts[interrupt_id] = interrupt
        return interrupt

    def approve(self, interrupt_id: str, comment: Optional[str] = None) -> HITLInterrupt:
        interrupt = self.pending_interrupts.pop(interrupt_id, None)
        if not interrupt:
            raise KeyError(f"Interrupt {interrupt_id} not found or already resolved.")
        interrupt.resolve(HITLDecision.APPROVED, comment=comment)
        self.history.append(interrupt)
        return interrupt

    def reject(self, interrupt_id: str, reason: str) -> HITLInterrupt:
        interrupt = self.pending_interrupts.pop(interrupt_id, None)
        if not interrupt:
            raise KeyError(f"Interrupt {interrupt_id} not found or already resolved.")
        interrupt.resolve(HITLDecision.REJECTED, comment=reason)
        self.history.append(interrupt)
        return interrupt

    def modify_and_approve(self, interrupt_id: str, modified_payload: Dict[str, Any], comment: Optional[str] = None) -> HITLInterrupt:
        interrupt = self.pending_interrupts.pop(interrupt_id, None)
        if not interrupt:
            raise KeyError(f"Interrupt {interrupt_id} not found or already resolved.")
        interrupt.resolve(HITLDecision.MODIFIED, comment=comment, modified_payload=modified_payload)
        self.history.append(interrupt)
        return interrupt
