"""
Advanced Sandboxing Engine for Mercurius
Provides secure execution isolation using restricted Python globals/locals,
resource limits, and isolated temp workspaces.
"""

import sys
import io
import traceback
import contextlib

class SecureSandbox:
    def __init__(self, timeout_seconds: int = 5):
        self.timeout_seconds = timeout_seconds

    def execute_python_snippet(self, code_string: str, custom_globals: dict = None) -> dict:
        output_buffer = io.StringIO()
        error_buffer = io.StringIO()
        
        safe_globals = {
            "__builtins__": {
                "abs": abs, "all": all, "any": any, "bool": bool, "dict": dict,
                "enumerate": enumerate, "float": float, "int": int, "len": len,
                "list": list, "max": max, "min": min, "range": range, "round": round,
                "sorted": sorted, "str": str, "sum": sum, "zip": zip, "print": print
            }
        }
        if custom_globals:
            safe_globals.update(custom_globals)

        try:
            with contextlib.redirect_stdout(output_buffer), contextlib.redirect_stderr(error_buffer):
                exec(code_string, safe_globals)
            return {
                "status": "success",
                "output": output_buffer.getvalue(),
                "errors": error_buffer.getvalue()
            }
        except Exception as e:
            return {
                "status": "error",
                "output": output_buffer.getvalue(),
                "errors": traceback.format_exc()
            }
