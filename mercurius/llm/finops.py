"""
Multi-Tenant Enterprise FinOps & Token Amortization Engine for Mercury.
Tracks departmental spending, manages token budgets per task, enforces hard/soft caps,
and enables autonomous model tier downgrading when intermediate task budgets deplete.
"""
from __future__ import annotations
import time
from typing import Dict, Any, List, Optional

# Cost per 1K tokens in USD for tier references
MODEL_COSTS_PER_1K: Dict[str, Dict[str, float]] = {
    "frontier": {"input": 0.005, "output": 0.015},      # e.g. GPT-4o / Claude 3.5 Sonnet
    "balanced": {"input": 0.0005, "output": 0.0015},    # e.g. GPT-4o-mini / Haiku
    "local": {"input": 0.0, "output": 0.0}              # Llama 3.3 self-hosted
}

class DepartmentBudget:
    def __init__(self, dept_name: str, monthly_limit_usd: float, soft_limit_ratio: float = 0.85):
        self.dept_name = dept_name
        self.monthly_limit_usd = monthly_limit_usd
        self.soft_limit_usd = monthly_limit_usd * soft_limit_ratio
        self.total_spent_usd: float = 0.0
        self.total_tokens_used: int = 0
        self.ledger: List[Dict[str, Any]] = []

    def record_usage(self, task_id: str, tier: str, prompt_tokens: int, completion_tokens: int) -> float:
        tier_costs = MODEL_COSTS_PER_1K.get(tier, MODEL_COSTS_PER_1K["balanced"])
        cost = (prompt_tokens / 1000.0 * tier_costs["input"]) + (completion_tokens / 1000.0 * tier_costs["output"])
        
        self.total_spent_usd += cost
        self.total_tokens_used += (prompt_tokens + completion_tokens)
        self.ledger.append({
            "task_id": task_id,
            "tier": tier,
            "tokens": prompt_tokens + completion_tokens,
            "cost_usd": cost,
            "timestamp": time.time()
        })
        return cost

    def is_soft_cap_exceeded(self) -> bool:
        return self.total_spent_usd >= self.soft_limit_usd

    def is_hard_cap_exceeded(self) -> bool:
        return self.total_spent_usd >= self.monthly_limit_usd

class FinOpsEngine:
    def __init__(self):
        self.departments: Dict[str, DepartmentBudget] = {}

    def register_department(self, dept_name: str, monthly_limit_usd: float) -> DepartmentBudget:
        dept = DepartmentBudget(dept_name, monthly_limit_usd)
        self.departments[dept_name] = dept
        return dept

    def get_department(self, dept_name: str) -> DepartmentBudget:
        if dept_name not in self.departments:
            self.departments[dept_name] = DepartmentBudget(dept_name, 1000.0) # default $1k
        return self.departments[dept_name]

    def select_downgraded_tier_if_needed(self, dept_name: str, requested_tier: str, task_budget_remaining_usd: float) -> str:
        """
        Dynamically throttles or downgrades intermediate reasoning model if budget constraints are met.
        """
        dept = self.get_department(dept_name)
        if dept.is_hard_cap_exceeded():
            raise PermissionError(f"Department '{dept_name}' has exceeded its hard budget limit of ${dept.monthly_limit_usd:.2f}")

        # If departmental soft cap is exceeded or task budget remaining is low (< $0.05), downgrade frontier to balanced
        if (dept.is_soft_cap_exceeded() or task_budget_remaining_usd < 0.05) and requested_tier == "frontier":
            return "balanced"
        
        return requested_tier

    def amortize_task_cost(self, dept_name: str, task_id: str, tier: str, prompt_tokens: int, completion_tokens: int) -> Dict[str, Any]:
        dept = self.get_department(dept_name)
        cost = dept.record_usage(task_id, tier, prompt_tokens, completion_tokens)
        return {
            "department": dept_name,
            "task_id": task_id,
            "tier": tier,
            "cost_usd": round(cost, 6),
            "department_total_spent_usd": round(dept.total_spent_usd, 6),
            "budget_remaining_usd": round(max(0.0, dept.monthly_limit_usd - dept.total_spent_usd), 6),
            "status": "HARD_CAP_EXCEEDED" if dept.is_hard_cap_exceeded() else ("SOFT_CAP_EXCEEDED" if dept.is_soft_cap_exceeded() else "HEALTHY")
        }
