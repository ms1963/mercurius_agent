"""
Hermes-Compatible Deliberation and Dual Tool Call Parser.
Supports:
1. <thought>...</thought> scratchpad extraction
2. Hermes XML <tool_call>{"name": ..., "arguments": ...}</tool_call>
3. Markdown code fence JSON tool calls
4. Native API tool_calls parameter
"""
from __future__ import annotations
import json
import re
from typing import Any, Dict, List, Optional, Tuple

class HermesParser:
    @staticmethod
    def extract_thought_and_content(text: str) -> Tuple[Optional[str], str]:
        """
        Extracts <thought> deliberation block if present and returns (thought, cleaned_text).
        """
        if not text:
            return None, ""
        
        thought_match = re.search(r"<thought>(.*?)</thought>", text, flags=re.DOTALL | re.IGNORECASE)
        thought = None
        cleaned_text = text

        if thought_match:
            thought = thought_match.group(1).strip()
            cleaned_text = re.sub(r"<thought>.*?</thought>", "", cleaned_text, flags=re.DOTALL | re.IGNORECASE).strip()

        return thought, cleaned_text

    @staticmethod
    def extract_tool_calls(
        message_content: Optional[str],
        api_tool_calls: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Extracts tool calls from either standard API tool_calls list OR text formats
        (Hermes <tool_call> XML tags or markdown ```json code blocks).
        Returns a list of standardized dicts: [{"id": str, "name": str, "arguments": dict}].
        """
        calls: List[Dict[str, Any]] = []

        # 1. First priority: Check native API tool_calls
        if api_tool_calls:
            for idx, tc in enumerate(api_tool_calls):
                fn = tc.get("function", {})
                name = fn.get("name", "")
                raw_args = fn.get("arguments", {})
                args = raw_args
                if isinstance(raw_args, str):
                    try:
                        args = json.loads(raw_args)
                    except Exception:
                        args = {"raw": raw_args}
                calls.append({
                    "id": tc.get("id", f"call_{idx+1}"),
                    "name": name,
                    "arguments": args
                })
            return calls

        if not message_content:
            return calls

        # 2. Check for Hermes XML syntax: <tool_call>{"name": "...", "arguments": {...}}</tool_call>
        xml_matches = re.findall(r"<tool_call>(.*?)</tool_call>", message_content, flags=re.DOTALL | re.IGNORECASE)
        for idx, block in enumerate(xml_matches):
            try:
                data = json.loads(block.strip())
                name = data.get("name") or data.get("tool")
                args = data.get("arguments") or data.get("args") or data.get("parameters") or {}
                if name:
                    calls.append({
                        "id": f"hermes_call_{idx+1}",
                        "name": name,
                        "arguments": args
                    })
            except Exception:
                pass

        if calls:
            return calls

        # 3. Check for Markdown json code block with tool name
        code_blocks = re.findall(r"```(?:json)?\s*(\{[^`]+?\})\s*```", message_content, flags=re.DOTALL)
        for idx, block in enumerate(code_blocks):
            try:
                data = json.loads(block.strip())
                if ("name" in data or "tool" in data) and ("arguments" in data or "args" in data or "parameters" in data):
                    name = data.get("name") or data.get("tool")
                    args = data.get("arguments") or data.get("args") or data.get("parameters") or {}
                    calls.append({
                        "id": f"block_call_{idx+1}",
                        "name": name,
                        "arguments": args
                    })
            except Exception:
                pass

        return calls
