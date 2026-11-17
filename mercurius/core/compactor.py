"""
Dynamic Context Compactor and Virtual Sliding Window for Mercury.
Prevents context window exhaustion, reduces token latency, and
preserves critical working memory across long multi-turn agent threads.
"""
from __future__ import annotations
from typing import List, Optional
from mercurius.core.types import ChatMessage, MessageRole

class ContextCompactor:
    def __init__(self, max_tokens: int = 12000, max_tool_output_chars: int = 2500):
        self.max_tokens = max_tokens
        self.max_tool_output_chars = max_tool_output_chars

    def compact_tool_output(self, output: str) -> str:
        """
        Compresses overly verbose tool results (e.g. huge scraped web pages),
        preserving key beginning and ending structures with a notice.
        """
        if not output or len(output) <= self.max_tool_output_chars:
            return output

        head_len = int(self.max_tool_output_chars * 0.6)
        tail_len = int(self.max_tool_output_chars * 0.4)
        truncated_chars = len(output) - (head_len + tail_len)

        return (
            output[:head_len] +
            f"\n\n[... {truncated_chars} characters compacted by Mercurius ContextCompactor ...]\n\n" +
            output[-tail_len:]
        )

    def compact_messages(self, messages: List[ChatMessage], system_prompt_reserve: int = 2000) -> List[ChatMessage]:
        """
        Applies a virtual sliding window compaction:
        - Always preserves System Prompt (index 0)
        - Always preserves the latest User instruction and recent tool context
        - Compacts intermediate turns into a synthetic executive summary if token limit is exceeded
        """
        if len(messages) <= 4:
            return messages

        total_chars = sum(len(m.content or "") for m in messages)
        estimated_tokens = total_chars // 4

        if estimated_tokens <= self.max_tokens:
            return messages

        sys_msg = messages[0] if messages[0].role == MessageRole.SYSTEM else None
        non_sys = messages[1:] if sys_msg else messages[:]

        preserved_tail = non_sys[-3:]
        middle_to_compact = non_sys[:-3]

        summary_points = []
        for m in middle_to_compact:
            role = m.role.value
            snippet = (m.content or "")[:120].replace("\n", " ").strip()
            if snippet:
                summary_points.append(f"- [{role}]: {snippet}...")

        summary_content = (
            "[Context Compaction Summary of Earlier Steps]:\n" +
            "\n".join(summary_points[:8])
        )

        compacted = []
        if sys_msg:
            compacted.append(sys_msg)
        compacted.append(ChatMessage(role=MessageRole.SYSTEM, content=summary_content))
        compacted.extend(preserved_tail)

        return compacted
