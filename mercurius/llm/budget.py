"""
Individual LLM Token and Cost Budget Enforcement for Mercury.
Enforces per-model / per-provider token quotas. When an individual LLM's budget
is exceeded, requests to that LLM are blocked until the user explicitly overwrites
the budget.
"""
from __future__ import annotations
import os, json, time
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional, Tuple, List, Any

@dataclass
class UserBudget:
    user_id: str
    max_daily_tokens: int = 100_000
    used_tokens_today: int = 0
    max_cost_usd: float = 10.0
    used_cost_usd: float = 0.0
    last_reset_day: int = field(default_factory=lambda: int(time.time() // 86400))

@dataclass
class LLMBudget:
    llm_id: str
    token_limit: Optional[int] = None  # None or 0 means unlimited
    used_tokens: int = 0
    total_requests: int = 0
    is_blocked: bool = False
    overwritten_at: Optional[float] = None
    overwritten_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LLMBudget:
        return cls(**data)

class BudgetTracker:
    def __init__(self, storage_path: str = "data/budgets.json"):
        self.storage_path = storage_path
        self.user_budgets: Dict[str, UserBudget] = {}
        self.llm_budgets: Dict[str, LLMBudget] = {}
        self._load()

    def _normalize_llm_id(self, llm_id: str) -> str:
        """Standardizes LLM identifiers (e.g. gpt-4o, chatllm:gpt-4o)."""
        return llm_id.strip().lower()

    def _load(self):
        """Loads persistent budget state from disk."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data.get("llm_budgets", []):
                        budget = LLMBudget.from_dict(item)
                        self.llm_budgets[budget.llm_id] = budget
            except Exception:
                pass

    def persist(self):
        """Saves current budget configuration and usage to disk."""
        try:
            os.makedirs(os.path.dirname(self.storage_path) or ".", exist_ok=True)
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump({
                    "llm_budgets": [b.to_dict() for b in self.llm_budgets.values()],
                    "updated_at": time.time()
                }, f, indent=2)
        except Exception:
            pass

    # --------------------------------------------------------------------------
    # Individual LLM Token Budget Methods
    # --------------------------------------------------------------------------

    def set_llm_budget(self, llm_id: str, token_limit: int) -> LLMBudget:
        """Sets or updates the token budget limit for a specific individual LLM."""
        norm_id = self._normalize_llm_id(llm_id)
        if norm_id not in self.llm_budgets:
            self.llm_budgets[norm_id] = LLMBudget(llm_id=norm_id, token_limit=token_limit)
        else:
            b = self.llm_budgets[norm_id]
            b.token_limit = token_limit
            # If the new limit exceeds current usage, automatically unblock
            if token_limit > b.used_tokens:
                b.is_blocked = False

        self.persist()
        return self.llm_budgets[norm_id]

    def get_llm_budget(self, llm_id: str) -> LLMBudget:
        """Retrieves the budget object for an individual LLM."""
        norm_id = self._normalize_llm_id(llm_id)
        if norm_id not in self.llm_budgets:
            self.llm_budgets[norm_id] = LLMBudget(llm_id=norm_id, token_limit=None)
        return self.llm_budgets[norm_id]

    def check_llm_budget(self, llm_id: str, requested_tokens: int = 1, allow_override: bool = False) -> Tuple[bool, str]:
        """
        Enforces token budget on an individual LLM.
        Returns (True, '') if request is allowed, or (False, reason) if blocked.
        """
        if allow_override:
            return True, "Override active for this request"

        norm_id = self._normalize_llm_id(llm_id)
        b = self.get_llm_budget(norm_id)

        # Check if already blocked
        if b.is_blocked:
            return False, (
                f"Token budget exceeded for LLM '{norm_id}' (Used: {b.used_tokens:,} / Limit: {b.token_limit:,} tokens). "
                f"Requests are blocked. Overwrite the budget via 'mercurius budget overwrite {norm_id} <new_limit>' to resume."
            )

        # Check if unlimited
        if b.token_limit is None or b.token_limit <= 0:
            return True, "Unlimited budget"

        # Check if this request would exceed quota
        if (b.used_tokens + requested_tokens) > b.token_limit:
            b.is_blocked = True
            self.persist()
            return False, (
                f"Token budget exceeded for LLM '{norm_id}' (Used: {b.used_tokens:,} / Limit: {b.token_limit:,} tokens, "
                f"requested: {requested_tokens:,}). Requests blocked. Overwrite the budget to continue."
            )

        return True, "Within budget"

    def record_llm_usage(self, llm_id: str, tokens: int) -> LLMBudget:
        """Records token usage for an individual LLM and updates blocked state."""
        norm_id = self._normalize_llm_id(llm_id)
        b = self.get_llm_budget(norm_id)
        b.used_tokens += tokens
        b.total_requests += 1

        if b.token_limit is not None and b.token_limit > 0:
            if b.used_tokens >= b.token_limit:
                b.is_blocked = True

        self.persist()
        return b

    def overwrite_llm_budget(
        self,
        llm_id: str,
        new_limit: Optional[int] = None,
        additional_tokens: Optional[int] = None
    ) -> LLMBudget:
        """
        Explicitly overwrites the budget for an individual LLM to unblock it and continue work.
        """
        norm_id = self._normalize_llm_id(llm_id)
        b = self.get_llm_budget(norm_id)

        if new_limit is not None:
            b.token_limit = new_limit
        elif additional_tokens is not None:
            base = max(b.used_tokens, b.token_limit or 0)
            b.token_limit = base + additional_tokens
        else:
            # Default overwrite: extend by 50,000 tokens beyond current usage
            b.token_limit = b.used_tokens + 50_000

        # Unblock because user explicitly requested budget overwrite
        b.is_blocked = False
        b.overwritten_at = time.time()
        b.overwritten_count += 1

        self.persist()
        return b

    def reset_llm_usage(self, llm_id: str) -> LLMBudget:
        """Resets token usage counter to 0 and unblocks the LLM."""
        norm_id = self._normalize_llm_id(llm_id)
        b = self.get_llm_budget(norm_id)
        b.used_tokens = 0
        b.is_blocked = False
        self.persist()
        return b

    def list_llm_budgets(self) -> List[Dict[str, Any]]:
        """Returns structured status of all tracked LLM budgets."""
        out = []
        for norm_id, b in self.llm_budgets.items():
            limit_str = f"{b.token_limit:,}" if b.token_limit else "Unlimited"
            remaining = (b.token_limit - b.used_tokens) if b.token_limit else "Unlimited"
            out.append({
                "llm_id": norm_id,
                "token_limit": b.token_limit,
                "limit_display": limit_str,
                "used_tokens": b.used_tokens,
                "remaining_tokens": remaining,
                "requests": b.total_requests,
                "is_blocked": b.is_blocked,
                "overwritten_count": b.overwritten_count
            })
        return out

    # --------------------------------------------------------------------------
    # Backward Compatibility User Budget Methods
    # --------------------------------------------------------------------------

    def get_or_create(self, user_id: str, daily_limit: int = 100_000, cost_limit: float = 10.0) -> UserBudget:
        today = int(time.time() // 86400)
        if user_id not in self.user_budgets:
            self.user_budgets[user_id] = UserBudget(user_id=user_id, max_daily_tokens=daily_limit, max_cost_usd=cost_limit, last_reset_day=today)
        b = self.user_budgets[user_id]
        if b.last_reset_day != today:
            b.used_tokens_today = 0
            b.used_cost_usd = 0.0
            b.last_reset_day = today
        return b

    def check_budget(self, user_id: str, requested_tokens: int = 100) -> bool:
        b = self.get_or_create(user_id)
        return (b.used_tokens_today + requested_tokens) <= b.max_daily_tokens

    def record_usage(self, user_id: str, tokens: int, cost_usd: float = 0.00001):
        b = self.get_or_create(user_id)
        b.used_tokens_today += tokens
        b.used_cost_usd += (tokens * cost_usd)
