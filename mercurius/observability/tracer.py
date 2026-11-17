"""
Observability, Telemetry & Trajectory Exporter for Mercury.
Integrates W3C TraceContext generation, span timing, OpenTelemetry-compatible metrics,
and JSONL trajectory persistence for offline evaluation and reinforcement learning.
"""
from __future__ import annotations
import json, time, os, uuid
from typing import Dict, List, Any, Optional
from mercurius.core.types import Trajectory, ExecutionStep

class ObservabilityTracer:
    def __init__(self, export_path: str = "data/trajectories/trajectories.jsonl"):
        self.export_path = export_path
        os.makedirs(os.path.dirname(export_path), exist_ok=True)
        self.metrics: Dict[str, Any] = {
            "total_runs": 0,
            "successful_runs": 0,
            "tool_calls": 0,
            "total_latency_ms": 0.0,
            "active_spans": 0
        }
        self.spans: List[Dict[str, Any]] = []

    def start_span(self, name: str, parent_span_id: Optional[str] = None) -> Dict[str, Any]:
        span_id = uuid.uuid4().hex[:16]
        trace_id = uuid.uuid4().hex
        span = {
            "name": name,
            "trace_id": trace_id,
            "span_id": span_id,
            "parent_span_id": parent_span_id,
            "start_time": time.time(),
            "status": "active"
        }
        self.metrics["active_spans"] += 1
        return span

    def end_span(self, span: Dict[str, Any], status: str = "ok", error: Optional[str] = None):
        span["duration_ms"] = (time.time() - span["start_time"]) * 1000
        span["status"] = status
        if error:
            span["error"] = error
        self.metrics["active_spans"] = max(0, self.metrics["active_spans"] - 1)
        self.spans.append(span)
        if len(self.spans) > 200:
            self.spans = self.spans[-200:]

    def record_step(self, step: ExecutionStep):
        if step.action:
            self.metrics["tool_calls"] += 1

    def record_trajectory(self, traj: Trajectory):
        self.metrics["total_runs"] += 1
        if traj.success:
            self.metrics["successful_runs"] += 1

        payload = {
            "task_id": traj.task_id,
            "goal": traj.goal,
            "success": traj.success,
            "reward": traj.reward,
            "model_name": traj.model_name,
            "steps": [
                {
                    "step": s.step_number,
                    "thought": s.thought,
                    "action": s.action,
                    "action_input": s.action_input,
                    "observation": s.observation,
                    "reflection": s.reflection
                }
                for s in traj.steps
            ],
            "timestamp": traj.timestamp
        }
        try:
            with open(self.export_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload) + "\n")
        except Exception:
            pass

    def get_telemetry_summary(self) -> Dict[str, Any]:
        success_rate = (self.metrics["successful_runs"] / self.metrics["total_runs"] * 100) if self.metrics["total_runs"] > 0 else 100.0
        return {
            "total_runs": self.metrics["total_runs"],
            "successful_runs": self.metrics["successful_runs"],
            "success_rate_pct": round(success_rate, 2),
            "tool_calls": self.metrics["tool_calls"],
            "active_spans": self.metrics["active_spans"],
            "recorded_spans_count": len(self.spans)
        }
