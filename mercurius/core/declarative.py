"""
Declarative Declarations Engine for Mercurius Agent.
Allows Users, Admins, and Developers to declare:
- Tools (HTTP endpoints, bash/python script commands, python expressions, MCP servers)
- Personalities (system prompts, tone, style, constraints, POSA/architecture guidelines)
- Skills (reusable prompt templates, workflows, inputs, parameter schemas)
- External Channels / Apps (webhooks, slack, telegram, discord, teams, email with endpoints & secrets)
- Multi-Agent Coordination Topologies (supervisor-worker, peer-to-peer handoff, sequential pipeline, consensus voting, dialectic debate)

Supports JSON, YAML (when available), and native Python dict declarations,
with hot-reloading from `data/declarations/` or custom paths.
"""
from __future__ import annotations
import os, sys, json, re, logging, uuid
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable

logger = logging.getLogger("mercury.declarative")

class DeclarativeLoader:
    """
    Central Declarative Engine that parses declarative configs and registers
    them into ToolRegistry, PersonalityLibrary, SkillManager, ChannelHub, and SwarmCoordinator.
    """
    def __init__(
        self,
        base_dir: str = "/workspace/files/personal_files/mercury",
        tool_registry: Any = None,
        personality_library: Any = None,
        skill_manager: Any = None,
        channel_hub: Any = None,
        swarm_coordinator: Any = None
    ):
        self.base_dir = base_dir
        self.declarations_dir = os.path.join(base_dir, "data", "declarations")
        os.makedirs(self.declarations_dir, exist_ok=True)
        
        self.tool_registry = tool_registry
        self.personality_library = personality_library
        self.skill_manager = skill_manager
        self.channel_hub = channel_hub
        self.swarm_coordinator = swarm_coordinator
        
        self.declared_tools: Dict[str, Any] = {}
        self.declared_personalities: Dict[str, Any] = {}
        self.declared_skills: Dict[str, Any] = {}
        self.declared_channels: Dict[str, Any] = {}
        self.declared_coordinations: Dict[str, Any] = {}

    def load_declarations_from_file(self, filepath: str) -> Dict[str, Any]:
        """Load and apply declarations from a JSON or YAML file."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Declaration file not found: {filepath}")
        
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            
        data: Dict[str, Any] = {}
        if filepath.endswith(".json"):
            data = json.loads(content)
        else:
            try:
                import yaml
                data = yaml.safe_load(content)
            except ImportError:
                data = json.loads(content)
                
        return self.apply_declarations(data)

    def load_all_declarations(self) -> Dict[str, Any]:
        """Scan declarations directory and load all .json/.yaml files."""
        results = {"tools": 0, "personalities": 0, "skills": 0, "channels": 0, "coordinations": 0}
        if not os.path.exists(self.declarations_dir):
            return results
            
        for fname in sorted(os.listdir(self.declarations_dir)):
            if fname.endswith(".json") or fname.endswith(".yaml") or fname.endswith(".yml"):
                p = os.path.join(self.declarations_dir, fname)
                try:
                    res = self.load_declarations_from_file(p)
                    for k in results:
                        results[k] += len(res.get(k, []))
                except Exception as e:
                    logger.error(f"Failed to load declaration file {fname}: {e}")
        return results

    def apply_declarations(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a declarative specification dictionary."""
        applied = {
            "tools": [],
            "personalities": [],
            "skills": [],
            "channels": [],
            "coordinations": []
        }
        
        # 1. Tools
        for tool_spec in spec.get("tools", []):
            t_name = self.declare_tool(tool_spec)
            applied["tools"].append(t_name)
            
        # 2. Personalities
        for persona_spec in spec.get("personalities", []):
            p_name = self.declare_personality(persona_spec)
            applied["personalities"].append(p_name)
            
        # 3. Skills
        for skill_spec in spec.get("skills", []):
            s_name = self.declare_skill(skill_spec)
            applied["skills"].append(s_name)
            
        # 4. Channels / Apps
        for ch_spec in spec.get("channels", []):
            c_name = self.declare_channel(ch_spec)
            applied["channels"].append(c_name)
            
        # 5. Multi-Agent Coordination Topologies
        for coord_spec in spec.get("coordinations", []):
            m_name = self.declare_coordination(coord_spec)
            applied["coordinations"].append(m_name)
            
        return applied

    # --- Tool Declarations ---
    def declare_tool(self, spec: Dict[str, Any]) -> str:
        name = spec.get("name")
        if not name:
            raise ValueError("Tool declaration requires 'name'")
            
        desc = spec.get("description", f"Declarative tool: {name}")
        params = spec.get("parameters", {})
        tool_type = spec.get("type", "expression") # 'expression', 'bash', 'http', 'python'
        
        def tool_executor(**kwargs):
            if tool_type == "expression":
                expr = spec.get("expression", "None")
                # Safe eval with restricted globals
                safe_globals = {"abs": abs, "min": min, "max": max, "len": len, "sum": sum, "round": round}
                safe_locals = dict(kwargs)
                return str(eval(expr, safe_globals, safe_locals))
                
            elif tool_type == "python":
                code = spec.get("code", "")
                locs = dict(kwargs)
                exec(code, {}, locs)
                return locs.get("result", locs.get("output", "Success"))
                
            elif tool_type == "bash":
                import subprocess
                cmd_template = spec.get("command", "")
                for k, v in kwargs.items():
                    cmd_template = cmd_template.replace(f"{{{k}}}", str(v))
                res = subprocess.run(cmd_template, shell=True, capture_output=True, text=True, timeout=15)
                return res.stdout if res.returncode == 0 else f"Error ({res.returncode}): {res.stderr}"
                
            elif tool_type == "http":
                import urllib.request
                url_template = spec.get("url", "")
                for k, v in kwargs.items():
                    url_template = url_template.replace(f"{{{k}}}", str(v))
                method = spec.get("method", "GET").upper()
                req = urllib.request.Request(url_template, method=method)
                headers = spec.get("headers", {})
                for hk, hv in headers.items():
                    req.add_header(hk, hv)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    return resp.read().decode("utf-8", errors="replace")
                    
            return f"Unknown tool type: {tool_type}"

        self.declared_tools[name] = {
            "name": name,
            "description": desc,
            "parameters": params,
            "type": tool_type,
            "executor": tool_executor
        }
        
        if self.tool_registry and hasattr(self.tool_registry, "register"):
            self.tool_registry.register(name, desc, params, tool_executor)
            
        return name

    # --- Personality Declarations ---
    def declare_personality(self, spec: Dict[str, Any]) -> str:
        key = spec.get("id") or spec.get("key") or spec.get("name")
        if not key:
            raise ValueError("Personality declaration requires 'id' or 'name'")
            
        name = spec.get("name", key)
        role = spec.get("role", "Specialist Advisor")
        system_prompt = spec.get("system_prompt") or spec.get("prompt", "")
        tone = spec.get("tone", "Professional and sharp")
        style_guide = spec.get("style_guide", [])
        constraints = spec.get("constraints", [])
        posa_patterns = spec.get("posa_patterns", [])

        full_prompt = system_prompt
        if posa_patterns:
            full_prompt += f"\nPOSA Guidelines: {', '.join(posa_patterns)}."
        if constraints:
            full_prompt += f"\nConstraints: {'; '.join(constraints)}."
            
        persona_obj = {
            "id": key,
            "name": name,
            "role": role,
            "tone": tone,
            "system_prompt": full_prompt,
            "style_guide": style_guide,
            "constraints": constraints,
            "posa_patterns": posa_patterns
        }
        
        self.declared_personalities[key] = persona_obj
        
        if self.personality_library:
            from mercurius.core.personalities import Persona
            persona_inst = Persona(
                id=key,
                name=name,
                description=role,
                tone=tone,
                temperature=spec.get("temperature", 0.7),
                system_prompt=full_prompt,
                preferred_tools=spec.get("preferred_tools", []),
                suggested_models=spec.get("suggested_models", [])
            )
            if hasattr(self.personality_library, "register_custom_persona"):
                self.personality_library.register_custom_persona(persona_inst)
        return key

    # --- Skill Declarations ---
    def declare_skill(self, spec: Dict[str, Any]) -> str:
        name = spec.get("name")
        if not name:
            raise ValueError("Skill declaration requires 'name'")
            
        description = spec.get("description", "")
        template = spec.get("prompt_template") or spec.get("template", "")
        parameters = spec.get("inputs") or spec.get("parameters", {})
        
        def run_skill(**kwargs):
            out = template
            for k, v in kwargs.items():
                out = out.replace(f"{{{k}}}", str(v))
            return out

        skill_obj = {
            "name": name,
            "description": description,
            "template": template,
            "parameters": parameters,
            "execute": run_skill
        }
        self.declared_skills[name] = skill_obj
        return name

    # --- External Channels / Apps Declarations ---
    def declare_channel(self, spec: Dict[str, Any]) -> str:
        name = spec.get("name") or spec.get("channel_type")
        if not name:
            raise ValueError("Channel declaration requires 'name' or 'channel_type'")
            
        c_type = spec.get("channel_type", name).lower()
        webhook_url = spec.get("webhook_url", "")
        secret = spec.get("secret_key", "")
        auto_dlp = spec.get("enable_dlp", True)
        
        ch_meta = {
            "name": name,
            "channel_type": c_type,
            "webhook_url": webhook_url,
            "secret_key": secret,
            "enable_dlp": auto_dlp,
            "active": spec.get("active", True)
        }
        self.declared_channels[name] = ch_meta
        return name

    # --- Multi-Agent Coordination Topologies Declarations ---
    def declare_coordination(self, spec: Dict[str, Any]) -> str:
        name = spec.get("name")
        pattern = spec.get("pattern", "pipeline").lower() # 'supervisor', 'pipeline', 'consensus', 'debate', 'handoff'
        agents = spec.get("agents", [])
        
        coord_obj = {
            "name": name,
            "pattern": pattern,
            "agents": agents,
            "config": spec.get("config", {})
        }
        self.declared_coordinations[name] = coord_obj
        return name
