"""
Central Enterprise Configuration and Environment Settings for Mercurius v2.2.
Provides strongly typed settings, environment variable overrides, and production defaults.
"""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class EnterpriseSettings:
    # Environment & Host
    env: str = field(default_factory=lambda: os.getenv("MERCURIUS_ENV", "production"))
    app_name: str = "Mercurius Enterprise Agentic Studio"
    version: str = "2.2.0-hardened"
    host: str = field(default_factory=lambda: os.getenv("MERCURIUS_HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("MERCURIUS_PORT", "8000")))

    # Security & Guardrails
    secret_key: str = field(default_factory=lambda: os.getenv("MERCURIUS_SECRET_KEY", "mcy_live_sec_master_2026"))
    enforce_hitl: bool = field(default_factory=lambda: os.getenv("MERCURIUS_ENFORCE_HITL", "true").lower() == "true")
    jev_risk_threshold: float = field(default_factory=lambda: float(os.getenv("MERCURIUS_JEV_THRESHOLD", "0.80")))
    enable_egress_dlp: bool = True
    session_token_ttl_sec: int = 86400

    # Model Context Protocol (MCP)
    mcp_protocol_version: str = "2026-07-01"
    mcp_endpoint: str = "/mcp"

    # Persistence & Paths
    data_dir: str = field(default_factory=lambda: os.getenv("MERCURIUS_DATA_DIR", "data"))
    memory_db_path: str = field(default_factory=lambda: os.path.join(os.getenv("MERCURIUS_DATA_DIR", "data"), "memory/mercury_memory.sqlite"))
    trajectory_log_path: str = field(default_factory=lambda: os.path.join(os.getenv("MERCURIUS_DATA_DIR", "data"), "trajectories/trajectories.jsonl"))

    # Tool Cache & Concurrency
    tool_cache_ttl_sec: int = field(default_factory=lambda: int(os.getenv("MERCURIUS_TOOL_CACHE_TTL", "3600")))
    max_parallel_workers: int = field(default_factory=lambda: int(os.getenv("MERCURIUS_MAX_WORKERS", "8")))

    # LLM Router Defaults
    primary_model: str = "gpt-6.1-sol"
    fast_model: str = "gpt-6.1-terra"
    deep_reasoning_model: str = "o1-preview"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "env": self.env,
            "version": self.version,
            "enforce_hitl": self.enforce_hitl,
            "jev_threshold": self.jev_risk_threshold,
            "mcp_version": self.mcp_protocol_version,
            "cache_ttl_sec": self.tool_cache_ttl_sec,
            "primary_model": self.primary_model
        }

settings = EnterpriseSettings()
