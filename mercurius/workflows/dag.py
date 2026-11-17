"""
Executive Directed Acyclic Graph (DAG) & StateGraph Workflow Engine for Mercury.
Provides LangGraph-grade multi-agent execution with typed state schemas, conditional edge branching,
Human-in-the-Loop checkpoints, cycle loop guards, and Mermaid visualization generation.
"""
from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional, Set, Union
import copy, time

class StateGraph:
    """Enterprise DAG state machine engine with typed state routing and human checkpoints."""
    def __init__(self, state_schema: Optional[type] = None):
        self.state_schema = state_schema or dict
        self.nodes: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}
        self.edges: Dict[str, List[str]] = {}
        self.conditional_edges: Dict[str, Dict[str, Any]] = {}
        self.checkpoints: Set[str] = set()
        self.entry_point: Optional[str] = None
        self.finish_point: Optional[str] = None

    def add_node(self, name: str, func: Callable[[Dict[str, Any]], Dict[str, Any]]) -> StateGraph:
        self.nodes[name] = func
        if name not in self.edges:
            self.edges[name] = []
        return self

    def set_entry_point(self, name: str) -> StateGraph:
        if name not in self.nodes:
            raise ValueError(f"Entry point node '{name}' must be added before setting.")
        self.entry_point = name
        return self

    def set_finish_point(self, name: str) -> StateGraph:
        self.finish_point = name
        return self

    def add_edge(self, from_node: str, to_node: str) -> StateGraph:
        if from_node not in self.nodes:
            raise ValueError(f"Node '{from_node}' does not exist.")
        if to_node not in self.nodes and to_node != "END":
            raise ValueError(f"Target node '{to_node}' does not exist.")
        self.edges[from_node].append(to_node)
        return self

    def add_conditional_edges(
        self,
        source: Optional[str] = None,
        condition: Optional[Callable[[Dict[str, Any]], Any]] = None,
        path_map: Optional[Dict[Any, str]] = None,
        from_node: Optional[str] = None,
        router_func: Optional[Callable[[Dict[str, Any]], str]] = None
    ) -> StateGraph:
        node_name = source or from_node
        if not node_name:
            raise ValueError("Must provide either 'source' or 'from_node'.")

        if router_func:
            self.conditional_edges[node_name] = {"type": "direct", "func": router_func}
        elif condition and path_map:
            self.conditional_edges[node_name] = {"type": "mapped", "condition": condition, "path_map": path_map}
        elif condition:
            self.conditional_edges[node_name] = {"type": "direct", "func": condition}
        else:
            raise ValueError("Must provide condition logic for conditional edge.")

        return self

    def add_checkpoint(self, node_name: str) -> StateGraph:
        self.checkpoints.add(node_name)
        return self

    def compile(self) -> CompiledGraph:
        if not self.entry_point:
            raise ValueError("StateGraph cannot compile: Entry point has not been set.")
        return CompiledGraph(self)

    def to_mermaid(self) -> str:
        """Generates Mermaid flowchart diagram for UI rendering."""
        lines = ["flowchart TD"]
        for node in self.nodes.keys():
            if node in self.checkpoints:
                lines.append(f"  {node}[{node} ⚠️ Checkpoint]")
            else:
                lines.append(f"  {node}[{node}]")

        for src, targets in self.edges.items():
            for tgt in targets:
                lines.append(f"  {src} --> {tgt}")

        for src in self.conditional_edges.keys():
            lines.append(f"  {src} -.->|Conditional Route| Route_{src}{'{Decision}'}")

        return "\n".join(lines)


class CompiledGraph:
    """Compiled runnable workflow executor."""
    def __init__(self, graph: StateGraph):
        self.graph = graph

    def invoke(
        self,
        initial_state: Dict[str, Any],
        max_steps: int = 25,
        hitl_approvals: Optional[Dict[str, bool]] = None
    ) -> Dict[str, Any]:
        state = copy.deepcopy(initial_state)
        current_node = self.graph.entry_point
        step_count = 0
        approvals = hitl_approvals or {}
        history = []

        while current_node and current_node != "END" and step_count < max_steps:
            step_count += 1
            history.append(current_node)

            # 1. Human-in-the-Loop Checkpoint Gate
            if current_node in self.graph.checkpoints:
                if not approvals.get(current_node, False):
                    state["__interrupted__"] = True
                    state["__checkpoint_node__"] = current_node
                    state["__history__"] = history
                    state["__total_steps__"] = step_count
                    return state

            # 2. Node Execution
            node_fn = self.graph.nodes[current_node]
            node_output = node_fn(state)
            if isinstance(node_output, dict):
                state.update(node_output)

            # Check if finished
            if current_node == self.graph.finish_point:
                break

            # 3. Next Node Resolution
            if current_node in self.graph.conditional_edges:
                edge_def = self.graph.conditional_edges[current_node]
                if edge_def["type"] == "mapped":
                    cond_val = edge_def["condition"](state)
                    current_node = edge_def["path_map"].get(cond_val, "END")
                else:
                    current_node = edge_def["func"](state)
            elif self.graph.edges.get(current_node):
                current_node = self.graph.edges[current_node][0]
            else:
                break

        state["__interrupted__"] = False
        state["__history__"] = history
        state["__steps_executed__"] = step_count
        state["__total_steps__"] = step_count
        return state
