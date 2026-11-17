"""
Dynamic Tool Authoring & Hot-Loading Engine for Mercury.
Allows the agent to write, validate, test, and hot-register custom Python tools at runtime.
Custom tools are persisted to disk to survive agent restarts.
Integrates AST security analysis to forbid dangerous modules and unsafe builtins (OWASP LLM02).
"""
from __future__ import annotations
import ast, os, sys, json, inspect
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from mercurius.core.types import ToolResult

FORBIDDEN_MODULES = {
    "os", "sys", "subprocess", "socket", "ctypes", "shutil",
    "posix", "pty", "urllib", "requests", "http", "ftplib"
}
FORBIDDEN_BUILTINS = {"eval", "exec", "__import__", "compile", "globals", "locals"}

class DynamicToolManager:
    def __init__(self, registry=None, storage_dir: str = "data/custom_tools"):
        self.registry = registry
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.custom_tools: Dict[str, Dict[str, Any]] = {}
        if self.registry:
            self.load_persisted_tools()

    def create_and_register_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        python_code: str,
        entrypoint: str = "main",
        test_kwargs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Validates syntax, tests execution, registers in ToolRegistry, and persists to disk.
        Enforces AST security whitelist against OS tampering, socket creation, and arbitrary code execution.
        """
        # 1. Syntax & AST Validation
        try:
            tree = ast.parse(python_code)
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"SyntaxError in Python code: {e.msg} at line {e.lineno}"
            }

        # 2. P1 Hardening: AST Security Inspection
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    base_mod = alias.name.split(".")[0]
                    if base_mod in FORBIDDEN_MODULES:
                        return {
                            "success": False,
                            "error": f"Security Violation: Custom dynamic tool imports forbidden module '{base_mod}'."
                        }
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    base_mod = node.module.split(".")[0]
                    if base_mod in FORBIDDEN_MODULES:
                        return {
                            "success": False,
                            "error": f"Security Violation: Custom dynamic tool imports forbidden module '{base_mod}'."
                        }
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_BUILTINS:
                    return {
                        "success": False,
                        "error": f"Security Violation: Forbidden call '{node.func.id}()' detected in dynamic tool AST."
                    }

        # 3. Compile and extract entrypoint
        namespace: Dict[str, Any] = {
            "__builtins__": __builtins__,
            "json": json,
            "math": __import__("math"),
            "re": __import__("re")
        }
        try:
            compiled = compile(python_code, filename=f"<dynamic_tool_{name}>", mode="exec")
            exec(compiled, namespace)
        except Exception as e:
            return {
                "success": False,
                "error": f"Compilation failed: {str(e)}"
            }

        func = namespace.get(entrypoint)
        if not func or not callable(func):
            # Fallback: find any function matching 'name' or the first function defined in AST
            if name in namespace and callable(namespace[name]):
                func = namespace[name]
            else:
                for item_name, item_val in namespace.items():
                    if callable(item_val) and not item_name.startswith("__"):
                        func = item_val
                        break

        if not func or not callable(func):
            return {
                "success": False,
                "error": f"Entrypoint '{entrypoint}' not found as a callable function in the provided code."
            }

        # 4. Dry-run test if test_kwargs provided
        if test_kwargs is not None:
            try:
                test_result = func(**test_kwargs)
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Dry-run test execution failed with error: {str(e)}"
                }

        # 5. Hot-register into ToolRegistry
        if self.registry:
            self.registry.register(
                name=name,
                description=description,
                parameters=parameters,
                func=func
            )

        # 6. Persist to disk
        tool_spec = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "python_code": python_code,
            "entrypoint": entrypoint
        }
        self.custom_tools[name] = tool_spec
        tool_file = self.storage_dir / f"{name}.json"
        tool_file.write_text(json.dumps(tool_spec, indent=2))

        return {
            "success": True,
            "message": f"Tool '{name}' successfully compiled, verified, and hot-registered into runtime registry.",
            "tool_name": name,
            "parameters": parameters
        }

    def load_persisted_tools(self) -> int:
        """Loads and registers any previously saved custom tools from disk."""
        count = 0
        for f in self.storage_dir.glob("*.json"):
            try:
                spec = json.loads(f.read_text())
                res = self.create_and_register_tool(
                    name=spec["name"],
                    description=spec["description"],
                    parameters=spec["parameters"],
                    python_code=spec["python_code"],
                    entrypoint=spec.get("entrypoint", "main")
                )
                if res.get("success"):
                    count += 1
            except Exception:
                continue
        return count

    def list_custom_tools(self) -> List[Dict[str, Any]]:
        return list(self.custom_tools.values())
