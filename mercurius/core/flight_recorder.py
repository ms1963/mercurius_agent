"""
Deterministic Time-Travel & Flight Recorder Engine for Mercurius Agent.
Captures every incoming event, tool invocation, observation, and state mutation as an
immutable event-sourced sequence. Supports deterministic replay and branching.
"""
from __future__ import annotations
import copy, time, json, hashlib
from typing import Dict, Any, List, Optional, Callable

class FlightEvent:
    def __init__(
        self,
        step_index: int,
        event_type: str,  # 'USER_INPUT', 'TOOL_CALL', 'TOOL_OBSERVATION', 'LLM_REASONING', 'STATE_DELTA'
        payload: Dict[str, Any],
        state_snapshot: Dict[str, Any],
        timestamp: Optional[float] = None
    ):
        self.step_index = step_index
        self.event_type = event_type
        self.payload = copy.deepcopy(payload)
        self.state_snapshot = copy.deepcopy(state_snapshot)
        self.timestamp = timestamp or time.time()
        self.hash = self._compute_hash()

    def _compute_hash(self) -> str:
        s = f"{self.step_index}:{self.event_type}:{json.dumps(self.payload, sort_keys=True)}:{json.dumps(self.state_snapshot, sort_keys=True)}"
        return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_index": self.step_index,
            "event_type": self.event_type,
            "payload": self.payload,
            "state_snapshot": self.state_snapshot,
            "timestamp": self.timestamp,
            "hash": self.hash
        }

class FlightRecorder:
    """
    Append-only Event-Sourced Flight Recorder and Time-Travel Debugger.
    """
    def __init__(self, session_id: str = "default_session"):
        self.session_id = session_id
        self.events: List[FlightEvent] = []
        self.current_state: Dict[str, Any] = {}

    def record_step(self, event_type: str, payload: Dict[str, Any], state_mutations: Optional[Dict[str, Any]] = None) -> FlightEvent:
        if state_mutations:
            self.current_state.update(state_mutations)
        
        evt = FlightEvent(
            step_index=len(self.events),
            event_type=event_type,
            payload=payload,
            state_snapshot=self.current_state
        )
        self.events.append(evt)
        return evt

    def get_event(self, step_index: int) -> Optional[FlightEvent]:
        if 0 <= step_index < len(self.events):
            return self.events[step_index]
        return None

    def time_travel_rewind(self, target_step: int) -> Dict[str, Any]:
        """
        Rewinds the state to exactly after target_step completed.
        Returns the restored state snapshot.
        """
        if target_step < 0 or target_step >= len(self.events):
            raise IndexError(f"Target step {target_step} out of bounds (0..{len(self.events)-1})")
        
        target_evt = self.events[target_step]
        self.current_state = copy.deepcopy(target_evt.state_snapshot)
        return copy.deepcopy(self.current_state)

    def branch_execution(self, from_step: int, new_action_payload: Dict[str, Any]) -> FlightRecorder:
        """
        Forks a new timeline from target step with modified action payload.
        """
        branched = FlightRecorder(session_id=f"{self.session_id}_branch_step{from_step}")
        branched.events = copy.deepcopy(self.events[:from_step + 1])
        branched.current_state = copy.deepcopy(self.events[from_step].state_snapshot)
        
        # Record modified action in branched timeline
        branched.record_step("BRANCHED_OVERRIDE", new_action_payload)
        return branched

    def export_timeline(self) -> List[Dict[str, Any]]:
        return [e.to_dict() for e in self.events]
