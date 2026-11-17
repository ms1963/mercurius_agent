from __future__ import annotations
from mercurius.core.selflearning import SelfLearningEngine
"""
Mercurius Core Agent and Orchestrator.
Integrates ReAct loop, Plan-and-Solve, Jev System-1 gating, Memory, Tools, Skills, and Reflection.
"""
import json, time, uuid
from typing import Any, Dict, List, Optional
from mercurius.core.types import (
    UserRole,
    ChatMessage, MessageRole, AgentPersonality, RunContext,
    ExecutionStep, Trajectory, ToolCall, ToolResult, WorkflowPattern
)
from mercurius.jev.client import JevDecisionClient
from mercurius.llm.client import UnifiedLLMClient
from mercurius.llm.router import LLMRouter
from mercurius.llm.budget import BudgetTracker
from mercurius.memory.manager import MemoryManager
from mercurius.tools.registry import ToolRegistry
from mercurius.skills.manager import SkillManager
from mercurius.security.guardrails import GuardrailEngine
from mercurius.security.auth import AuthManager
from mercurius.observability.tracer import ObservabilityTracer
from mercurius.core.parser import HermesParser
from mercurius.core.compactor import ContextCompactor
from mercurius.core.checkpoint import CheckpointManager

class MercuryAgent:
    def __init__(
        self,
        personality: Optional[AgentPersonality] = None,
        llm_client: Optional[UnifiedLLMClient] = None,
        jev_client: Optional[JevDecisionClient] = None,
        memory_manager: Optional[MemoryManager] = None,
        tool_registry: Optional[ToolRegistry] = None,
        skill_manager: Optional[SkillManager] = None,
        guardrails: Optional[GuardrailEngine] = None,
        budget_tracker: Optional[BudgetTracker] = None,
        tracer: Optional[ObservabilityTracer] = None
    ):
        self.personality = personality or AgentPersonality()
        self.jev = jev_client or JevDecisionClient()
        self.llm = llm_client or UnifiedLLMClient()
        self.memory = memory_manager or MemoryManager()
        self.tools = tool_registry or ToolRegistry()
        self.skills = skill_manager or SkillManager()
        self.guardrails = guardrails or GuardrailEngine(self.jev)
        self.budget = budget_tracker or BudgetTracker()
        self.tracer = tracer or ObservabilityTracer()
        self.compactor = ContextCompactor()
        self.checkpoints = CheckpointManager()

    def run(self, prompt: str, context: Optional[RunContext] = None) -> str:
        ctx = context or RunContext()

        # 1. Guardrail & Security Inspection
        is_safe, reason = self.guardrails.validate_prompt(prompt)
        if not is_safe:
            return f"[Security Block]: {reason}"

        # 2. Token Budget Gate
        if not self.budget.check_budget(ctx.user_id, requested_tokens=100):
            return "[Budget Exceeded]: Daily token quota has been reached for this user."

        task_id = f"task_{uuid.uuid4().hex[:8]}"
        traj = Trajectory(task_id=task_id, goal=prompt, model_name=f"{self.llm.provider}:{self.llm.model}")

        # 3. Memory Recall & Context Assembly
        past_episodes = self.memory.search_episodic(prompt, limit=3)
        context_notes = "\n".join(e["content"] for e in past_episodes)

        sys_content = f"{self.personality.system_prompt}\nTone: {self.personality.tone}\nRelevant Memory:\n{context_notes}"
        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content=sys_content),
            ChatMessage(role=MessageRole.USER, content=prompt)
        ]

        # 4. ReAct Execution Loop (max 5 iterations)
        final_answer = ""
        for step_idx in range(1, 6):
            # Save state checkpoint before step
            self.checkpoints.save_checkpoint(step_idx, messages)

            # Compact messages to prevent context exhaustion
            messages = self.compactor.compact_messages(messages)

            step = ExecutionStep(step_number=step_idx)

            # Jev System-1 Tool Pre-Selection / Gating check
            jev_gate = self.jev.decide_choice(
                state=f"Goal: {prompt}\nStep: {step_idx}",
                question="Should the agent call a tool or synthesize the final answer?",
                options=["call_tool", "synthesize_final"]
            )

            if jev_gate.choice == "synthesize_final" and step_idx > 1:
                step.thought = "Synthesizing final answer based on accumulated observations."
                step.is_final = True
                final_answer = self._generate_response(messages)
                step.reflection = "Final answer generated successfully."
                traj.steps.append(step)
                break

            # Call LLM with tool schema
            tools_schema = self.tools.list_tools_schema()
            completion = self.llm.chat_completion(messages, tools=tools_schema)
            self.budget.record_usage(ctx.user_id, tokens=completion.get("usage", {}).get("total_tokens", 100))

            choice = completion["choices"][0]["message"]
            msg_content = choice.get("content") or ""

            # Extract Hermes-style deliberation <thought> and clean content
            thought, cleaned_content = HermesParser.extract_thought_and_content(msg_content)
            if thought:
                step.thought = thought

            # Dual Tool Call Parser: handles native API, Hermes XML <tool_call>, and Markdown JSON blocks
            parsed_calls = HermesParser.extract_tool_calls(cleaned_content, choice.get("tool_calls"))

            if parsed_calls:
                # Concurrent Batch Execution across parallel workers
                tool_results = self.tools.execute_batch(parsed_calls, parallel=True)

                observations = []
                for idx, res in enumerate(tool_results):
                    call_spec = parsed_calls[idx]
                    t_name = call_spec["name"]
                    t_args = call_spec.get("arguments", {})

                    if not step.thought:
                        step.thought = f"Calling tool {t_name}"
                    step.action = t_name
                    step.action_input = t_args

                    obs_str = str(res.output) if not res.is_error else f"Error: {res.error}"
                    # Truncate & compact verbose outputs
                    compacted_obs = self.compactor.compact_tool_output(obs_str)
                    observations.append(compacted_obs)

                    # Append tool exchange to messages
                    messages.append(ChatMessage(role=MessageRole.ASSISTANT, content=f"Executing {t_name}"))
                    messages.append(ChatMessage(
                        role=MessageRole.TOOL,
                        content=compacted_obs,
                        tool_call_id=res.tool_call_id or f"tc_{step_idx}_{idx+1}"
                    ))

                combined_observation = "\n".join(observations)
                step.observation = combined_observation

                # Post-tool reflection
                score = self.jev.score_completion(prompt, step.observation)
                step.reflection = f"Step completion confidence: {score.confidence:.2f}"
                traj.steps.append(step)
                self.tracer.record_step(step)

                if score.score >= 0.95:
                    final_answer = f"Task completed: {step.observation}"
                    break
            else:
                final_answer = cleaned_content
                if not step.thought:
                    step.thought = "Direct response formulated"
                step.observation = final_answer
                step.is_final = True
                traj.steps.append(step)
                break

        traj.success = bool(final_answer)
        traj.reward = 1.0 if traj.success else 0.0
        self.tracer.record_trajectory(traj)

        # 5. GEPA++: Self-learning skill distillation
        if len(traj.steps) >= 2 and traj.success:
            self.skills.synthesize_from_trajectory(traj)

        # 6. Save Episode to Memory
        self.memory.save_chat_message(ctx.session_id, ChatMessage(role=MessageRole.USER, content=prompt))
        self.memory.save_chat_message(ctx.session_id, ChatMessage(role=MessageRole.ASSISTANT, content=final_answer))

        return final_answer

    def _generate_response(self, messages: List[ChatMessage]) -> str:
        comp = self.llm.chat_completion(messages)
        return comp["choices"][0]["message"].get("content", "Task processed.")

class MercuryOrchestrator:
    """Manages agents, subagents, and multi-agent workflows."""
    def __init__(self):
        self.jev = JevDecisionClient()
        self.memory = MemoryManager()
        self.tools = ToolRegistry()
        self.skills = SkillManager()
        self.guardrails = GuardrailEngine(self.jev)
        self.budget = BudgetTracker()
        self.tracer = ObservabilityTracer()
        self.auth = AuthManager()
        self.root_agent = MercuryAgent(
            personality=AgentPersonality(name="Mercurius Orchestrator"),
            jev_client=self.jev,
            memory_manager=self.memory,
            tool_registry=self.tools,
            skill_manager=self.skills,
            guardrails=self.guardrails,
            budget_tracker=self.budget,
            tracer=self.tracer
        )

    def spawn_subagent(self, role: str, system_prompt: str) -> MercuryAgent:
        personality = AgentPersonality(name=role, system_prompt=system_prompt)
        return MercuryAgent(
            personality=personality,
            jev_client=self.jev,
            memory_manager=self.memory,
            tool_registry=self.tools,
            skill_manager=self.skills,
            guardrails=self.guardrails,
            budget_tracker=self.budget,
            tracer=self.tracer
        )

    def run_agent_session(self, session_id: str, prompt: str, user_id: str = "default_user", personality: Optional[AgentPersonality] = None) -> str:
        ctx = RunContext(session_id=session_id, user_id=user_id)
        if personality:
            self.root_agent.personality = personality
        return self.root_agent.run(prompt, context=ctx)


class MercurySystem:
    """
    Unified high-level entrypoint matching TypeScript MercurySystem (src/index.ts).
    Exposes unified facade across JEV, Tools, Memory, ReAct, MCP, Security, Auth, and Budgets.
    """
    def __init__(
        self,
        config: Optional[EnterpriseSettings] = None,
        tool_registry: Optional[ToolRegistry] = None,
        user_role: UserRole = UserRole.ADMIN
    ):
        from mercurius.config.settings import settings
        from mercurius.jev.client import JevDecisionClient
        from mercurius.memory.manager import MemoryManager
        from mercurius.memory.autonomous import AutonomousMemorySystem
        from mercurius.mcp.protocol import MCPServer, MCPClient
        from mercurius.security.guardrails import GuardrailEngine
        from mercurius.security.auth import AuthManager
        from mercurius.llm.budget import BudgetTracker
        from mercurius.skills.manager import SkillManager
        from mercurius.observability.tracer import ObservabilityTracer
        from mercurius.scheduler.scheduler import TaskScheduler
        from mercurius.i18n.i18n import I18nEngine

        self.settings = config or settings
        self.tools = tool_registry or ToolRegistry(enforce_hitl=self.settings.enforce_hitl)
        self.jev = JevDecisionClient()
        self.memory = MemoryManager()
        self.autonomous_memory = AutonomousMemorySystem(
            core_path=f"{self.settings.data_dir}/memory/core_memory.json",
            db_path=self.settings.memory_db_path
        )
        self.skills = SkillManager()
        self.tracer = ObservabilityTracer(export_path=self.settings.trajectory_log_path)
        self.security = GuardrailEngine()
        self.auth = AuthManager(secret_key=self.settings.secret_key)
        self.budget = BudgetTracker(storage_path=f"{self.settings.data_dir}/budgets.json")
        self.scheduler = TaskScheduler()
        self.i18n = I18nEngine()
        self.agent = MercuryAgent(
            tool_registry=self.tools,
            memory_manager=self.memory,
            skill_manager=self.skills,
            guardrails=self.security,
            budget_tracker=self.budget,
            tracer=self.tracer
        )
        
        # Declarative Engine: auto-load declarative configs (tools, personalities, skills, channels, coordinations)
        from mercurius.core.declarative import DeclarativeLoader
        from mercurius.core.personalities import PersonalityLibrary
        from mercurius.channels.hub import ChannelHub
        from mercurius.multiagent.swarm import SwarmCoordinator

        self.personality_library = PersonalityLibrary()
        self.channels = ChannelHub()
        self.swarm = SwarmCoordinator()
        self.declarative = DeclarativeLoader(
            base_dir=self.settings.base_dir if hasattr(self.settings, "base_dir") else "/workspace/files/personal_files/mercury",
            tool_registry=self.tools,
            personality_library=self.personality_library,
            skill_manager=self.skills,
            channel_hub=self.channels,
            swarm_coordinator=self.swarm
        )
        try:
            self.declarative.load_all_declarations()
        except Exception:
            pass

    def run_task(self, task: str, user_role: UserRole = UserRole.ADMIN) -> Dict[str, Any]:
        """Runs end-to-end task with security guardrails, JEV routing, ReAct execution and tracing."""
        # 1. Security Ingress Guardrail
        guard = self.security.scan_input(task)
        if not guard.get("allowed", True):
            return {
                "success": False,
                "result": f"Security Guardrail Alert: {guard.get('reason', 'Policy violation detected.')}",
                "guard": guard
            }

        # 2. JEV System-1 Fast Routing
        route = self.jev.classify_intent(task)

        # 3. Span Tracing
        span = self.tracer.start_span("run_task")

        # 4. ReAct Execution
        try:
            output = self.agent.run(task)
            self.tracer.end_span(span, status="ok")
            return {
                "success": True,
                "routed_model": self.settings.primary_model,
                "jev_intent": route,
                "result": output,
                "steps": len(self.agent.scratchpad)
            }
        except Exception as e:
            self.tracer.end_span(span, status="error", error=str(e))
            return {
                "success": False,
                "error": str(e)
            }

    def start_server(self, port: Optional[int] = None):
        """Launches the full executive web cockpit server."""
        from mercurius.ui.server import start_server
        p = port or self.settings.port
        start_server(host=self.settings.host, port=p)
