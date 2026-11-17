"""
Comprehensive Interactive Help and Diagnostic System for Mercury.
Covers all subsystems, commands, architectures, and health checks.
"""
from typing import Dict, List, Any

class HelpSystem:
    TOPICS: Dict[str, str] = {
        "overview": (
            "=== Mercurius Agentic AI System (v2.0.0) ===\n"
            "An enterprise-grade autonomous agentic framework in Python 3.12+.\n"
            "Key Innovations:\n"
            "  * Jev System-1 Calibrated Decision Model (<500ms typed decisions)\n"
            "  * July 2026 Model Context Protocol (MCP) Server & Client\n"
            "  * Polyglot Sandbox (Python, Node/TS, Go, C++, Java)\n"
            "  * 5-Tier Memory with SQLite FTS5 Full-Text Indexing\n"
            "  * Multi-Agent Topologies: Pipeline, Coordinator-Worker, Blackboard, Tree\n"
            "  * Enterprise Guardrail Harness (Anti-Injection, Token Budgets, RBAC)\n"
        ),
        "tools": (
            "=== Built-in Tools Catalog ===\n"
            "Mercurius provides 15+ production built-in tools:\n"
            "  * polyglot_exec: Compiles & executes Python, JS, Go, C++, Java\n"
            "  * calculate: Safe mathematical formula evaluator\n"
            "  * file_read / file_write / file_list / file_grep: Scoped filesystem operations\n"
            "  * web_fetch: HTTP text retrieval with automatic tag stripping\n"
            "  * data_sql_query: In-memory DuckDB analytical SQL query runner\n"
            "  * crypto_hash: SHA-256 / MD5 / SHA-1 checksum generator\n"
            "  * uuid_generate: RFC 4122 v4 UUID generator\n"
            "  * regex_extract: Pattern matching and group extraction\n"
            "  * json_validate: JSON syntax and structure verification\n"
            "  * mermaid_validate: Architecture diagram syntax validator\n"
            "  * system_env_info: Hardware, OS, and Python environment inspect\n"
        ),
        "personalities": (
            "=== Agent Personality Library ===\n"
            "Switch or spawn agents with distinct operational personas:\n"
            "  * mercury_prime: Lead orchestrator (sharp, witty, decisive)\n"
            "  * software_architect: POSA/GoF patterns, microservices, decoupling\n"
            "  * security_officer: Zero-trust, pen-testing, anti-injection auditor\n"
            "  * data_scientist: Statistical analysis, tabular SQL, data validation\n"
            "  * devops_sre: Docker, K8s, CI/CD, telemetry, fault resilience\n"
            "  * executive_advisor: Board-ready synthesis, risk/reward matrices\n"
            "  * research_analyst: Citation-grounded technical literature review\n"
            "  * creative_engineer: Lateral thinking, innovative concept design\n"
        ),
        "workflows": (
            "=== Multi-Agent Collaboration Topologies ===\n"
            "  * Pipeline: Sequential stage-by-stage data refinement\n"
            "  * Coordinator-Worker: Parallel subagent dispatch and executive synthesis\n"
            "  * Blackboard: Shared state where diverse experts post and vote\n"
            "  * Tree Decomposition: Hierarchical recursive divide-and-conquer\n"
        ),
        "mcp": (
            "=== July 2026 Model Context Protocol (MCP) ===\n"
            "Mercurius functions as both an MCP Client and an MCP Server:\n"
            "  * Server endpoint: POST /mcp (JSON-RPC 2.0)\n"
            "  * Methods: initialize, tools/list, tools/call, resources/list\n"
            "  * Client: Connects to external MCP servers via stdio or HTTP/SSE\n"
        ),
        "memory": (
            "=== 5-Tier Unified Memory Engine ===\n"
            "  1. Working Memory: In-memory context scratchpad\n"
            "  2. Episodic Memory: SQLite FTS5 Porter-tokenized conversation search\n"
            "  3. Semantic Memory: Vector and BM25 RAG document knowledge base\n"
            "  4. Procedural Memory: GEPA++ auto-synthesized skills in Markdown\n"
            "  5. Core Memory: Identity, user preferences, and immutable decisions\n"
        ),
        "security": (
            "=== Security Harness & Guardrails ===\n"
            "  * Anti-Injection: Regex patterns and Jev System-1 safety logits\n"
            "  * Polyglot Containment: Blocked fork-bombs, destructive shell commands\n"
            "  * Token Quotas: Daily user limits and hard cap enforcement\n"
            "  * RBAC: Cryptographic API keys, JWT tokens, Admin vs Regular role\n"
        ),
        "cli": (
            "=== Interactive CLI Usage ===\n"
            "  mercurius [prompt]                 Execute single prompt and exit\n"
            "  mercurius -i / --interactive       Start full interactive REPL\n"
            "  /help [topic]                    Show help for topic\n"
            "  /exit                            Quit REPL session\n"
        )
    }

    @classmethod
    def get_topic(cls, topic: str = "overview") -> str:
        t = topic.lower().strip()
        if t in cls.TOPICS:
            return cls.TOPICS[t]
        avail = ", ".join(cls.TOPICS.keys())
        return f"Unknown topic '{topic}'.\nAvailable topics: {avail}"

    @classmethod
    def list_topics(cls) -> List[str]:
        return list(cls.TOPICS.keys())
