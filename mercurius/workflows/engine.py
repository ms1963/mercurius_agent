"""
Multi-Agent Workflow Collaboration Engine for Mercury.
Supports Pipeline, Coordinator-Worker (sequential & parallel), Blackboard,
and Hierarchical Tree Decomposition.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional
from mercurius.core.types import WorkflowPattern

class WorkflowEngine:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator

    def run_coordinator_worker(self, objective: str, worker_specs: List[Dict[str, str]], parallel: bool = True, max_workers: int = 5) -> str:
        """
        Spawns worker subagents to evaluate the objective concurrently or sequentially,
        collects their individual reports, and spawns an Executive Coordinator to synthesize.
        """
        reports = []

        def execute_worker(spec: Dict[str, str]) -> str:
            role = spec.get("role", "Worker")
            prompt = spec.get("prompt", "Analyze the objective.")
            worker = self.orchestrator.spawn_subagent(role=role, system_prompt=prompt)
            out = worker.run(objective)
            return f"=== Subagent Report [{role}] ===\n{out}"

        if parallel and len(worker_specs) > 1:
            with ThreadPoolExecutor(max_workers=min(len(worker_specs), max_workers)) as executor:
                future_to_spec = {executor.submit(execute_worker, s): s for s in worker_specs}
                for f in as_completed(future_to_spec):
                    reports.append(f.result())
        else:
            for spec in worker_specs:
                reports.append(execute_worker(spec))

        synthesis_input = f"Objective: {objective}\n\n" + "\n\n".join(reports)
        coordinator = self.orchestrator.spawn_subagent(
            role="Executive Coordinator",
            system_prompt=(
                "You are an Executive Coordinator. Review the parallel reports from "
                "the specialized subagents, resolve any contradictions, and produce "
                "a unified, actionable, executive-level synthesis."
            )
        )
        return coordinator.run(synthesis_input)

    def run_pipeline(self, initial_input: str, stages: List[Dict[str, str]]) -> str:
        """Sequential stage-by-stage data transformation pipeline."""
        current_data = initial_input
        for idx, stage in enumerate(stages):
            name = stage.get("name", f"Stage_{idx+1}")
            prompt = stage.get("prompt", "Process the given input.")
            agent = self.orchestrator.spawn_subagent(role=name, system_prompt=prompt)
            current_data = agent.run(current_data)
        return current_data

    def run_blackboard(self, problem: str, expert_roles: List[str], max_rounds: int = 2) -> str:
        """Shared blackboard repository where diverse experts asynchronously read and post insights."""
        blackboard_state = [f"Initial Problem: {problem}"]
        for round_idx in range(max_rounds):
            round_notes = []
            for role in expert_roles:
                agent = self.orchestrator.spawn_subagent(
                    role=role, 
                    system_prompt=f"You are a specialized {role}. Review current blackboard state and contribute insights."
                )
                board_summary = "\n".join(blackboard_state)
                note = agent.run(board_summary)
                round_notes.append(f"[{role} - Round {round_idx+1}]: {note}")
            blackboard_state.extend(round_notes)

        synthesizer = self.orchestrator.spawn_subagent(
            role="LeadSynthesizer", 
            system_prompt="Consolidate blackboard into final solution."
        )
        return synthesizer.run("\n".join(blackboard_state))

    def run_tree(self, goal: str, subtasks: List[str]) -> str:
        """Hierarchical tree decomposition: decomposes a master goal into subtasks, delegates, and aggregates."""
        subtask_results = []
        for i, subtask in enumerate(subtasks, 1):
            leaf_agent = self.orchestrator.spawn_subagent(
                role=f"SubtaskWorker_{i}",
                system_prompt=f"Execute focused subtask {i} of the master plan."
            )
            subtask_results.append(f"Subtask {i} ({subtask}):\n" + leaf_agent.run(subtask))

        aggregator = self.orchestrator.spawn_subagent(
            role="TreeAggregator",
            system_prompt="Synthesize decomposed subtask results into completed master deliverable."
        )
        return aggregator.run(f"Master Goal: {goal}\n\n" + "\n\n".join(subtask_results))
