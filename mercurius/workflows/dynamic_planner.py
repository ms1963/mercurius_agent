"""
Dynamic Graph Planner & Adaptive Distributed DAG Engine for Mercury.
Features:
1. Parallel node scheduling across topological levels.
2. Dynamic Re-planning on intermediate tool or node failure.
3. Branch condition pruning and cycle detection.
4. Comprehensive node execution tracing and state handoff.
"""
from __future__ import annotations
import concurrent.futures, logging, time
from typing import Dict, Any, List, Optional, Callable, Set

logger = logging.getLogger("mercury.dynamic_planner")

class PlanNode:
    def __init__(
        self,
        node_id: str,
        action: str,
        handler: Callable[[Dict[str, Any]], Any],
        dependencies: Optional[List[str]] = None,
        fallback_handler: Optional[Callable[[Dict[str, Any], Exception], Any]] = None,
        condition: Optional[Callable[[Dict[str, Any]], bool]] = None
    ):
        self.node_id = node_id
        self.action = action
        self.handler = handler
        self.dependencies: List[str] = dependencies or []
        self.fallback_handler = fallback_handler
        self.condition = condition
        self.status = "PENDING"  # PENDING, RUNNING, COMPLETED, FAILED, SKIPPED
        self.result: Any = None
        self.error: Optional[str] = None
        self.execution_time: float = 0.0

class DynamicGraphPlanner:
    def __init__(self, max_parallel_workers: int = 4):
        self.nodes: Dict[str, PlanNode] = {}
        self.max_parallel_workers = max_parallel_workers

    def add_node(
        self,
        node_id: str,
        action: str,
        handler: Callable[[Dict[str, Any]], Any],
        dependencies: Optional[List[str]] = None,
        fallback_handler: Optional[Callable[[Dict[str, Any], Exception], Any]] = None,
        condition: Optional[Callable[[Dict[str, Any]], bool]] = None
    ) -> DynamicGraphPlanner:
        node = PlanNode(
            node_id=node_id,
            action=action,
            handler=handler,
            dependencies=dependencies,
            fallback_handler=fallback_handler,
            condition=condition
        )
        self.nodes[node_id] = node
        return self

    def _validate_acyclic(self):
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(node_id: str):
            visited.add(node_id)
            rec_stack.add(node_id)
            for dep in self.nodes.get(node_id, PlanNode("", "", lambda x: None)).dependencies:
                if dep not in visited:
                    if dfs(dep):
                        return True
                elif dep in rec_stack:
                    return True
            rec_stack.remove(node_id)
            return False

        for nid in self.nodes:
            if nid not in visited:
                if dfs(nid):
                    raise ValueError(f"Cyclic dependency detected in dynamic graph at node '{nid}'")

    def execute(self, initial_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executes DAG nodes in topological order with parallel batching.
        Supports dynamic branch condition pruning and fallback re-planning.
        """
        self._validate_acyclic()
        context = dict(initial_context or {})
        pending_nodes = set(self.nodes.keys())
        completed_nodes: Set[str] = set()
        skipped_nodes: Set[str] = set()

        while pending_nodes:
            # Find nodes whose dependencies are all satisfied
            ready_nodes = []
            for nid in pending_nodes:
                node = self.nodes[nid]
                deps_satisfied = all((d in completed_nodes or d in skipped_nodes) for d in node.dependencies)
                if deps_satisfied:
                    ready_nodes.append(nid)

            if not ready_nodes:
                # If nodes remain but none ready, broken dependency path
                unresolved = {nid: self.nodes[nid].dependencies for nid in pending_nodes}
                raise RuntimeError(f"Deadlock in graph execution. Unresolved dependencies: {unresolved}")

            # Check conditions and partition into runnable vs skipped
            to_run = []
            for nid in ready_nodes:
                node = self.nodes[nid]
                if node.condition and not node.condition(context):
                    node.status = "SKIPPED"
                    skipped_nodes.add(nid)
                    pending_nodes.remove(nid)
                    logger.info(f"Node '{nid}' skipped by branch condition")
                else:
                    to_run.append(nid)

            if not to_run:
                continue

            # Execute runnable batch in parallel thread pool
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(self.max_parallel_workers, len(to_run))) as executor:
                futures = {}
                for nid in to_run:
                    node = self.nodes[nid]
                    node.status = "RUNNING"
                    futures[executor.submit(self._run_node, node, context)] = nid

                for future in concurrent.futures.as_completed(futures):
                    nid = futures[future]
                    node = self.nodes[nid]
                    success, res, err = future.result()
                    if success:
                        node.status = "COMPLETED"
                        node.result = res
                        context[nid] = res
                        completed_nodes.add(nid)
                    else:
                        node.status = "FAILED"
                        node.error = err
                        raise RuntimeError(f"DAG Execution failed at node '{nid}': {err}")
                    pending_nodes.remove(nid)

        return context

    def _run_node(self, node: PlanNode, context: Dict[str, Any]):
        start = time.time()
        try:
            res = node.handler(context)
            node.execution_time = time.time() - start
            return True, res, None
        except Exception as e:
            logger.warning(f"Node '{node.node_id}' failed: {e}. Attempting dynamic fallback re-plan.")
            if node.fallback_handler:
                try:
                    fallback_res = node.fallback_handler(context, e)
                    node.execution_time = time.time() - start
                    return True, fallback_res, None
                except Exception as fe:
                    node.execution_time = time.time() - start
                    return False, None, str(fe)
            node.execution_time = time.time() - start
            return False, None, str(e)
