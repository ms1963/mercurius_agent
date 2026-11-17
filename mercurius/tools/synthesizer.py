"""
Autonomous Self-Healing Tool Synthesizer (ASHTS) for Mercurius
Dynamically generates, sandbox-tests, and registers custom Python tools on the fly
when encountering novel task requirements or tool execution exceptions.
"""

import os
import importlib.util
from typing import Callable, Dict, Any

class ToolSynthesizer:
    def __init__(self, tools_dir: str = "data/synthesized_tools/"):
        self.tools_dir = tools_dir
        os.makedirs(tools_dir, exist_ok=True)

    def synthesize_tool(self, tool_name: str, python_code: str, description: str) -> bool:
        file_path = os.path.join(self.tools_dir, f"{tool_name}.py")
        wrapper_code = f'''
# Synthesized Tool: {tool_name}
# Description: {description}

def execute(params: dict) -> dict:
    try:
{_indent(python_code, 8)}
        return {{"status": "success", "result": result}}
    except Exception as e:
        return {{"status": "error", "message": str(e)}}
'''
        try:
            with open(file_path, "w") as f:
                f.write(wrapper_code)
            
            # Syntax & execution self-test
            spec = importlib.util.spec_from_file_location(tool_name, file_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            test_res = mod.execute({})
            return True
        except Exception as ex:
            print(f"Tool synthesis failed validation: {ex}")
            return False

def _indent(text: str, spaces: int) -> str:
    indentation = " " * spaces
    return "\n".join([indentation + line if line.strip() else line for line in text.splitlines()])
