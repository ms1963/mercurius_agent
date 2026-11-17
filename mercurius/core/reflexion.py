"""
Reflexion and Actor-Critic Self-Correction Engine for Mercury.
Provides automated critique, evaluation scoring (0-100), and iterative refinement loops.
"""
from __future__ import annotations
import re, json
from typing import Any, Dict, List, Optional
from mercurius.core.types import ExecutionStep, Trajectory

class ReflexionEngine:
    def __init__(self, jev_client=None, llm_client=None):
        self.jev = jev_client
        self.llm = llm_client

    def critique_step(self, goal: str, step: ExecutionStep) -> Dict[str, Any]:
        """
        Critiques an individual step based on goal alignment and observation quality.
        Returns score (0-100), critiques, and suggestions.
        """
        score = 100
        critiques = []
        suggestions = []

        # Check for tool errors
        if step.observation and ("error:" in step.observation.lower() or "exception:" in step.observation.lower()):
            score -= 40
            critiques.append("Step execution encountered an error or exception.")
            suggestions.append("Verify arguments, handle null values, or try an alternative tool.")

        # Check for empty observation
        if not step.observation or step.observation.strip() in ("", "None", "{}"):
            score -= 30
            critiques.append("Observation is empty; tool returned no useful data.")
            suggestions.append("Verify query parameters or check data source availability.")

        # Goal relevance heuristic
        if goal and step.observation:
            goal_words = set(re.findall(r'\w{4,}', goal.lower()))
            obs_words = set(re.findall(r'\w{4,}', step.observation.lower()))
            overlap = goal_words.intersection(obs_words)
            if goal_words and len(overlap) == 0 and len(step.observation) < 200:
                score -= 15
                critiques.append("Observation has low semantic keyword overlap with the master goal.")
                suggestions.append("Ensure the tool invocation directly addresses the target question.")

        score = max(0, min(100, score))
        return {
            "score": score,
            "passed": score >= 70,
            "critiques": critiques,
            "suggestions": suggestions
        }

    def evaluate_response(self, goal: str, response: str, trajectory: Optional[Trajectory] = None) -> Dict[str, Any]:
        """
        Evaluates the final agent response against the original goal.
        """
        if not response or len(response.strip()) == 0:
            return {
                "score": 0,
                "passed": False,
                "verdict": "FAIL",
                "critique": "Response is completely empty."
            }

        score = 80  # Baseline
        critiques = []

        # Check length / detail
        if len(response.strip()) < 20:
            score -= 20
            critiques.append("Response is very terse or potentially unhelpful.")

        # Check for refusal / failure keywords
        refusal_patterns = [
            r"i cannot", r"i am unable to", r"as an ai", r"i do not have access",
            r"error:", r"failed to"
        ]
        for pat in refusal_patterns:
            if re.search(pat, response.lower()):
                score -= 25
                critiques.append(f"Response contains hesitation or failure pattern: '{pat}'")
                break

        # Check trajectory step health if available
        if trajectory and trajectory.steps:
            errors = sum(1 for s in trajectory.steps if s.observation and "error:" in s.observation.lower())
            if errors > 0:
                score -= (10 * errors)
                critiques.append(f"Encountered {errors} step-level errors during execution.")

        score = max(0, min(100, score))
        passed = score >= 70
        return {
            "score": score,
            "passed": passed,
            "verdict": "PASS" if passed else "NEEDS_REFINEMENT",
            "critique": "; ".join(critiques) if critiques else "Response meets quality standards."
        }

    def formulate_refinement_prompt(self, goal: str, prior_response: str, critique: Dict[str, Any]) -> str:
        """Constructs a targeted prompt to refine and correct an inadequate response."""
        return (
            f"Original Goal: {goal}\n\n"
            f"Prior Attempt: {prior_response}\n\n"
            f"Critique & Identified Flaws: {critique.get('critique', 'Needs improvement')}\n"
            f"Suggestions: {critique.get('suggestions', ['Address identified flaws directly'])}\n\n"
            "Please revise the answer to completely resolve all issues and produce an accurate, comprehensive solution."
        )
