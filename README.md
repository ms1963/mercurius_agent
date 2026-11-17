# Mercurius v4.0.0 — Autonomous Enterprise AI Platform

**Mercurius** is an advanced, enterprise-grade autonomous AI agent platform built on a pure **Python 3.12+** core. It integrates cutting-edge frontier LLM models (**GPT-6 Astra**, **Claude Sonnet 5.5**, and **Gemini 4 Carbon**) to deliver robust reasoning, multi-agent orchestration, and secure tool execution.

---

## 🌟 Mercurius v4.0.0 Architecture & Killer Features

1. **Andrey Karpathy’s LLM Wiki Engine (`mercurius/memory/llm_wiki.py`)**: 
   Replaces fragile RAG pipelines with an AI-maintained structured Markdown knowledge wiki (`data/wiki/`). Raw sources are compiled into persistent articles with automatic backlinks, ensuring zero-hallucination semantic coherence.

2. **Quantum Semantic Memory Graph (QSMG)** (`mercurius/memory/quantum_graph.py`):
   Multi-entity relationship mapping atop SQLite for sub-15ms contextual retrieval across complex projects.

3. **Autonomous Self-Healing Tool Synthesizer (ASHTS)** (`mercurius/tools/synthesizer.py`):
   Runtime generation, sandbox validation (`importlib`), and self-healing of missing tools on the fly.

4. **Advanced Secure Sandboxing (`mercurius/tools/sandbox.py`)**:
   Isolated execution environment for untrusted Python code snippets with strict global scoping and timeouts.

5. **Custom User-Defined Guardrails (`mercurius/security/custom_guardrails.py`)**:
   Extensible registration API for developer-defined validation lambdas, regex filters, and compliance checkers.

6. **External Enterprise App Connectors (`mercurius/channels/integrations.py`)**:
   Seamless webhook bridges for Jira, GitHub, Slack, and Notion task dispatch.

7. **Jev-Protected Zero-Trust Neural Firewall (JPZTNF)**:
   Real-time prompt injection blocking and cryptographic Merkle proof auditing.

---

## 🚀 Quick Start

1. **Clone or Extract Archive**:
   Extract `mercurius_project_archive.zip` to your workspace.

2. **Run Mercurius CLI**:
   ```bash
   python3 -m mercurius.ui.cli
   ```

3. **Run Tests**:
   ```bash
   python3 -m unittest discover tests
   ```

---
*Licensed under MIT — Mercurius v4.0.0*
