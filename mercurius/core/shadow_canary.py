"""
Shadow Agent Canary Testing & Semantic Drift Detection Engine for Mercury.
Executes candidate prompt/model upgrades in shadow mode alongside production,
calculates semantic cosine drift between output trajectories, and flags regressions.
"""
from __future__ import annotations
import time
from typing import Dict, Any, List, Optional, Callable
from mercurius.memory.semantic import compute_dense_text_vector, cosine_similarity

class CanaryEvaluationResult:
    def __init__(
        self,
        query: str,
        prod_output: str,
        shadow_output: str,
        similarity: float,
        drift_percentage: float,
        regressed: bool,
        prod_latency_sec: float,
        shadow_latency_sec: float
    ):
        self.query = query
        self.prod_output = prod_output
        self.shadow_output = shadow_output
        self.similarity = similarity
        self.drift_percentage = drift_percentage
        self.regressed = regressed
        self.prod_latency_sec = prod_latency_sec
        self.shadow_latency_sec = shadow_latency_sec

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "similarity": round(self.similarity, 4),
            "drift_percentage": round(self.drift_percentage, 2),
            "regressed": self.regressed,
            "prod_latency_sec": round(self.prod_latency_sec, 4),
            "shadow_latency_sec": round(self.shadow_latency_sec, 4)
        }

class ShadowCanaryEngine:
    def __init__(self, max_allowed_drift: float = 25.0):
        self.max_allowed_drift = max_allowed_drift
        self.evaluations: List[CanaryEvaluationResult] = []

    def run_canary_evaluation(
        self,
        query: str,
        prod_agent_fn: Callable[[str], str],
        shadow_agent_fn: Callable[[str], str]
    ) -> CanaryEvaluationResult:
        # Run production agent
        t0 = time.time()
        prod_out = prod_agent_fn(query)
        prod_lat = time.time() - t0

        # Run shadow canary agent
        t1 = time.time()
        shadow_out = shadow_agent_fn(query)
        shadow_lat = time.time() - t1

        # Calculate semantic similarity and drift
        v_prod = compute_dense_text_vector(prod_out)
        v_shadow = compute_dense_text_vector(shadow_out)
        sim = cosine_similarity(v_prod, v_shadow)
        
        # Drift percentage is (1.0 - sim) * 100
        drift = max(0.0, (1.0 - sim) * 100.0)
        regressed = (drift > self.max_allowed_drift)

        eval_res = CanaryEvaluationResult(
            query=query,
            prod_output=prod_out,
            shadow_output=shadow_out,
            similarity=sim,
            drift_percentage=drift,
            regressed=regressed,
            prod_latency_sec=prod_lat,
            shadow_latency_sec=shadow_lat
        )
        self.evaluations.append(eval_res)
        return eval_res

    def get_summary_report(self) -> Dict[str, Any]:
        if not self.evaluations:
            return {"total_tests": 0, "regressions": 0, "avg_drift": 0.0}
        
        total = len(self.evaluations)
        regressions = sum(1 for e in self.evaluations if e.regressed)
        avg_drift = sum(e.drift_percentage for e in self.evaluations) / total
        
        return {
            "total_tests": total,
            "regressions": regressions,
            "pass_rate_percentage": round(((total - regressions) / total) * 100.0, 2),
            "avg_drift_percentage": round(avg_drift, 2),
            "canary_verdict": "SAFE_TO_PROMOTE" if regressions == 0 else "REGRESSION_DETECTED"
        }
