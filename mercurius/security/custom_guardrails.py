"""
Custom User-Defined Guardrails Engine for Mercurius
Allows engineers and administrators to register custom validation rules,
regex filters, and safety hooks before tool execution or LLM prompt dispatch.
"""

import re
from typing import Callable, List

class CustomGuardrailsManager:
    def __init__(self):
        self.rules: List[Callable[[str], bool]] = []
        self._load_default_rules()

    def _load_default_rules(self):
        # Default security guardrail: block forbidden keywords or API key leaks
        self.add_rule(lambda text: "API_KEY_SECRET" not in text, "Block raw secret leaks")

    def add_rule(self, rule_fn: Callable[[str], bool], description: str):
        self.rules.append((rule_fn, description))

    def validate_content(self, content: str) -> tuple[bool, str]:
        for fn, desc in self.rules:
            try:
                if not fn(content):
                    return False, f"Guardrail violated: {desc}"
            except Exception as e:
                return False, f"Guardrail error in [{desc}]: {str(e)}"
        return True, "Passed all guardrails"
