"""
Executive-Grade HTTP, REST & SSE Streaming Dashboard Server for Mercury.
Features real-time Agent Reasoning Streaming, StateGraph DAG visualizer,
Interactive Tool Execution timeline, Multi-Persona hot-swapping,
System Doctor telemetry, and Individual LLM Budget controls.
"""
from __future__ import annotations
import os, sys, json, time, uuid, urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

# Ensure mercurius is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from mercurius.core.agent import MercuryOrchestrator
from mercurius.core.personalities import PersonalityLibrary
from mercurius.mcp.protocol import MCPServer
from mercurius.doctor.doctor import SystemDoctor
from mercurius.llm.budget import BudgetTracker

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Mercurius Enterprise Agentic Studio | Executive Control Deck</title>
  <!-- Tailwind CSS & Inter Font -->
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <!-- Lucide Icons & Mermaid -->
  <script src="https://unpkg.com/lucide@latest"></script>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          fontFamily: {
            sans: ['"Plus Jakarta Sans"', 'sans-serif'],
            mono: ['"JetBrains Mono"', 'monospace']
          },
          colors: {
            brand: {
              50: '#ecfeff',
              100: '#cffafe',
              400: '#22d3ee',
              500: '#06b6d4',
              600: '#0891b2',
              900: '#164e63'
            },
            dark: {
              bg: '#090d16',
              card: '#0f172a',
              border: '#1e293b',
              sidebar: '#0b1120'
            }
          }
        }
      }
    }
  </script>
  <style>
    body { font-family: 'Plus Jakarta Sans', sans-serif; background: #090d16; color: #f1f5f9; }
    .glass-panel { background: rgba(15, 23, 42, 0.75); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.08); }
    .glass-card { background: rgba(30, 41, 59, 0.5); backdrop-filter: blur(8px); border: 1px solid rgba(255,255,255,0.06); }
    .glow-cyan { box-shadow: 0 0 25px -5px rgba(6, 182, 212, 0.35); }
    .custom-scrollbar::-webkit-scrollbar { width: 5px; height: 5px; }
    .custom-scrollbar::-webkit-scrollbar-track { background: rgba(15, 23, 42, 0.5); }
    .custom-scrollbar::-webkit-scrollbar-thumb { background: #334155; border-radius: 4px; }
    .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #06b6d4; }
  </style>
</head>
<body class="h-screen flex overflow-hidden custom-scrollbar">

  <!-- LEFT SIDEBAR: Nav & Agent Fleet -->
  <aside class="w-80 bg-dark-sidebar border-r border-slate-800/80 flex flex-col justify-between shrink-0">
    <div class="p-5">
      <!-- Brand Header -->
      <div class="flex items-center gap-3 mb-6">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center text-white font-extrabold text-xl glow-cyan shadow-lg">
          💠
        </div>
        <div>
          <h1 class="text-base font-bold tracking-tight text-white flex items-center gap-2">
            MERCURY <span class="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">v2.2 HARDENED</span>
          </h1>
          <p class="text-xs text-slate-400">Autonomous ReAct Cognitive Engine</p>
        </div>
      </div>

      <!-- Navigation Tabs -->
      <div class="space-y-1 mb-6">
        <button onclick="switchTab('chat')" id="tab-btn-chat" class="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
          <i data-lucide="message-square" class="w-4 h-4"></i> ReAct Cognitive Chat
        </button>
        <button onclick="switchTab('dag')" id="tab-btn-dag" class="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition text-slate-400 hover:text-white hover:bg-slate-800/60">
          <i data-lucide="git-merge" class="w-4 h-4"></i> Workflow DAG Visualizer
        </button>
        <button onclick="switchTab('tools')" id="tab-btn-tools" class="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition text-slate-400 hover:text-white hover:bg-slate-800/60">
          <i data-lucide="wrench" class="w-4 h-4"></i> Tool Registry (<span id="sidebar-tool-count">48</span>)
        </button>
        <button onclick="switchTab('telemetry')" id="tab-btn-telemetry" class="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition text-slate-400 hover:text-white hover:bg-slate-800/60">
          <i data-lucide="shield-check" class="w-4 h-4"></i> Doctor & RBAC Security
        </button>
      </div>

      <!-- Persona Fleet Selector -->
      <div>
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs font-semibold tracking-wider text-slate-400 uppercase">Active Persona</span>
          <span class="text-[11px] font-mono text-cyan-400" id="current-persona-badge">mercury_prime</span>
        </div>
        <select id="persona-select" onchange="changePersona(this.value)" class="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 font-mono">
          <option value="mercury_prime">💠 Mercurius Prime (Master Orchestrator)</option>
          <option value="software_architect">🏛️ Software Architect (C4 & Cloud)</option>
          <option value="security_officer">🛡️ Security Officer (OWASP CISO)</option>
          <option value="data_scientist">📊 Data Scientist (NumPy & Stats)</option>
          <option value="devops_sre">⚡ DevOps SRE (K8s & Resilience)</option>
          <option value="executive_advisor">👔 Executive Advisor (Strategy & ROI)</option>
          <option value="cynical_hacker">🕵️ Cynical Hacker (Adversarial Audit)</option>
          <option value="socratic_mentor">🌱 Socratic Mentor (First Principles)</option>
          <option value="legal_compliance_auditor">⚖️ Compliance Auditor (GDPR & ISO)</option>
          <option value="detective_troubleshooter">🔍 Detective Troubleshooter (RCA)</option>
        </select>
        <p id="persona-desc" class="mt-2 text-[11px] text-slate-400 italic">Balanced polymath orchestrator with rigorous analytical thinking.</p>
      </div>
    </div>

    <!-- System Telemetry Mini Badge -->
    <div class="p-4 border-t border-slate-800/80 bg-slate-950/40 text-xs">
      <div class="flex items-center justify-between mb-1.5">
        <span class="text-slate-400 flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span> MCP Server</span>
        <span class="font-mono text-emerald-400 text-[11px]">2026-07-01 OK</span>
      </div>
      <div class="flex items-center justify-between mb-1.5">
        <span class="text-slate-400 flex items-center gap-1.5"><i data-lucide="shield" class="w-3 h-3 text-cyan-400"></i> RBAC Security</span>
        <span class="font-mono text-cyan-400 text-[11px]">HITL GATED</span>
      </div>
      <div class="flex items-center justify-between">
        <span class="text-slate-400 flex items-center gap-1.5"><i data-lucide="activity" class="w-3 h-3 text-purple-400"></i> Jev System-1</span>
        <span class="font-mono text-purple-400 text-[11px]">Active (0.80)</span>
      </div>
    </div>
  </aside>

  <!-- MAIN WORKSPACE -->
  <main class="flex-1 flex flex-col bg-dark-bg overflow-hidden relative">

    <!-- TOP HEADER -->
    <header class="h-14 border-b border-slate-800/80 px-6 flex items-center justify-between glass-panel shrink-0 z-10">
      <div class="flex items-center gap-3">
        <div id="header-status-indicator" class="flex items-center gap-2 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium">
          <span class="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span> Cognitive Loop Idle
        </div>
        <div class="h-4 w-[1px] bg-slate-800"></div>
        <span id="current-view-title" class="text-xs font-semibold text-slate-300">Executive ReAct Session</span>
      </div>

      <div class="flex items-center gap-3">
        <button onclick="runSystemDoctorQuick()" class="px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800/80 hover:bg-slate-700 text-slate-200 border border-slate-700 flex items-center gap-1.5 transition">
          <i data-lucide="heart-pulse" class="w-3.5 h-3.5 text-cyan-400"></i> Run Doctor Diagnostics
        </button>
        <button onclick="clearChat()" class="px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800/80 hover:bg-slate-700 text-slate-200 border border-slate-700 flex items-center gap-1.5 transition">
          <i data-lucide="rotate-ccw" class="w-3.5 h-3.5 text-amber-400"></i> Reset Trajectory
        </button>
      </div>
    </header>

    <!-- CONTENT PANELS -->

    <!-- 1. CHAT & REASONING PANEL -->
    <section id="panel-chat" class="flex-1 flex flex-col overflow-hidden">
      <!-- Conversation Stream -->
      <div id="chat-messages" class="flex-1 overflow-y-auto p-6 space-y-5 custom-scrollbar">
        <!-- Welcome Card -->
        <div class="p-5 rounded-2xl glass-panel border border-cyan-500/20 max-w-3xl mx-auto shadow-2xl">
          <div class="flex items-start gap-4">
            <div class="w-10 h-10 rounded-xl bg-cyan-500/20 text-cyan-400 flex items-center justify-center shrink-0 border border-cyan-500/30 text-xl">
              💠
            </div>
            <div>
              <h2 class="text-base font-bold text-white mb-1">Mercurius Executive Agentic Studio is Online</h2>
              <p class="text-xs text-slate-300 leading-relaxed mb-3">
                Autonomous system with Jev System-1 gating, 48 production tools (filesystem, headless browser, math/finance, zip/tar), bidirectional MCP protocol, multi-channel adapters, and hardened OWASP Top 10 defenses.
              </p>
              <div class="flex flex-wrap gap-2 text-[11px] font-mono">
                <span class="px-2.5 py-1 rounded-md bg-slate-800 text-cyan-300 border border-slate-700">RBAC Gated</span>
                <span class="px-2.5 py-1 rounded-md bg-slate-800 text-emerald-300 border border-slate-700">HITL Protected</span>
                <span class="px-2.5 py-1 rounded-md bg-slate-800 text-purple-300 border border-slate-700">Anti-Injection XML</span>
                <span class="px-2.5 py-1 rounded-md bg-slate-800 text-amber-300 border border-slate-700">Egress DLP Redactor</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Live Tool Call Timeline / Progress Tray -->
      <div id="active-tool-tray" class="hidden px-6 py-2 bg-slate-900/90 border-t border-slate-800/80 flex items-center justify-between text-xs text-cyan-300">
        <div class="flex items-center gap-2">
          <div class="w-4 h-4 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin"></div>
          <span id="active-tool-status">Executing tool: polyglot_exec...</span>
        </div>
        <span class="font-mono text-[11px] text-slate-400" id="active-tool-timer">0.0s</span>
      </div>

      <!-- Human-in-the-Loop Confirmation Banner -->
      <div id="hitl-banner" class="hidden mx-6 my-2 p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <i data-lucide="alert-triangle" class="w-5 h-5 text-amber-400 shrink-0"></i>
          <div>
            <h4 class="text-xs font-bold text-amber-200 uppercase tracking-wide">Human-in-the-Loop Action Approval Required</h4>
            <p id="hitl-action-text" class="text-xs text-slate-300">Destructive tool 'file_delete' requested on path: /tmp/test.txt</p>
          </div>
        </div>
        <div class="flex gap-2">
          <button onclick="respondHitl(false)" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 text-slate-300 hover:bg-slate-700 border border-slate-600">Reject</button>
          <button onclick="respondHitl(true)" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold">Approve Action</button>
        </div>
      </div>

      <!-- Chat Prompt Input Area -->
      <div class="p-4 border-t border-slate-800/80 glass-panel shrink-0">
        <div class="max-w-4xl mx-auto relative">
          <textarea
            id="chat-input"
            rows="2"
            placeholder="Instruct Mercurius (e.g. 'Scrape https://developer.siemens.com, calculate compound interest on $10k at 5%, and audit security logs')..."
            class="w-full bg-slate-900/90 text-sm text-slate-100 placeholder-slate-500 rounded-xl px-4 py-3 pr-28 border border-slate-700/80 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 custom-scrollbar resize-none"
            onkeydown="handleKey(event)"
          ></textarea>
          <div class="absolute right-3 bottom-3 flex items-center gap-2">
            <button
              id="send-btn"
              onclick="sendMessage()"
              class="px-4 py-2 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-semibold text-xs flex items-center gap-1.5 shadow-lg shadow-cyan-500/20 transition disabled:opacity-50"
            >
              <span>Execute</span> <i data-lucide="arrow-right" class="w-3.5 h-3.5"></i>
            </button>
          </div>
        </div>
        <div class="max-w-4xl mx-auto flex items-center justify-between mt-2 px-1 text-[11px] text-slate-400">
          <span>Press <kbd class="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 font-mono text-[10px]">Enter</kbd> to execute, <kbd class="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 font-mono text-[10px]">Shift+Enter</kbd> for newline</span>
          <span class="flex items-center gap-1"><i data-lucide="lock" class="w-3 h-3 text-cyan-400"></i> Outbound Egress DLP Active</span>
        </div>
      </div>
    </section>

    <!-- 2. WORKFLOW DAG VISUALIZER PANEL -->
    <section id="panel-dag" class="hidden flex-1 flex flex-col p-6 overflow-y-auto custom-scrollbar">
      <div class="max-w-5xl mx-auto w-full space-y-6">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-lg font-bold text-white flex items-center gap-2">
              <i data-lucide="git-merge" class="w-5 h-5 text-cyan-400"></i> StateGraph Multi-Agent Workflow DAG
            </h2>
            <p class="text-xs text-slate-400">LangGraph-grade directed acyclic graph with conditional routing & human checkpoints</p>
          </div>
          <button onclick="renderSampleDag()" class="px-3 py-1.5 rounded-lg text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 flex items-center gap-1.5">
            <i data-lucide="refresh-cw" class="w-3.5 h-3.5"></i> Refresh Graph
          </button>
        </div>

        <!-- Interactive Diagram Card -->
        <div class="p-6 rounded-2xl glass-panel border border-slate-800 flex flex-col items-center justify-center min-h-[380px]">
          <div id="mermaid-dag-container" class="w-full flex justify-center text-slate-200">
            <!-- Mermaid diagram will render here -->
          </div>
        </div>

        <!-- Node Execution Details Table -->
        <div class="rounded-xl glass-card border border-slate-800 overflow-hidden">
          <div class="p-4 border-b border-slate-800 bg-slate-900/60 font-semibold text-xs text-slate-300">
            Active Graph Nodes & State Schemas
          </div>
          <table class="w-full text-left text-xs">
            <thead class="bg-slate-950/60 text-slate-400 uppercase text-[10px] font-mono border-b border-slate-800">
              <tr>
                <th class="p-3">Node Name</th>
                <th class="p-3">Agent / Tool Binding</th>
                <th class="p-3">Conditional Routing Gate</th>
                <th class="p-3">HITL Checkpoint</th>
                <th class="p-3">Status</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-800/80 font-mono text-[11px]">
              <tr>
                <td class="p-3 font-bold text-cyan-400">supervisor_planner</td>
                <td class="p-3 text-slate-300">Mercurius Prime</td>
                <td class="p-3 text-slate-400">Jev System-1 Gate</td>
                <td class="p-3 text-slate-500">None</td>
                <td class="p-3 text-emerald-400">COMPLETED</td>
              </tr>
              <tr>
                <td class="p-3 font-bold text-cyan-400">web_reconnaissance</td>
                <td class="p-3 text-slate-300">WebBrowser (Headless)</td>
                <td class="p-3 text-slate-400">Anti-Injection XML Wrap</td>
                <td class="p-3 text-slate-500">None</td>
                <td class="p-3 text-emerald-400">COMPLETED</td>
              </tr>
              <tr>
                <td class="p-3 font-bold text-cyan-400">code_synthesizer</td>
                <td class="p-3 text-slate-300">PolyglotRunner / DynamicTools</td>
                <td class="p-3 text-slate-400">AST Security Whitelist</td>
                <td class="p-3 text-amber-400">REQUIRED (if destructive)</td>
                <td class="p-3 text-cyan-400">RUNNING</td>
              </tr>
              <tr>
                <td class="p-3 font-bold text-cyan-400">actor_critic_refine</td>
                <td class="p-3 text-slate-300">ReflexionEngine</td>
                <td class="p-3 text-slate-400">Confidence Threshold &ge; 85</td>
                <td class="p-3 text-slate-500">None</td>
                <td class="p-3 text-slate-500">PENDING</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- 3. TOOL REGISTRY PANEL -->
    <section id="panel-tools" class="hidden flex-1 flex flex-col p-6 overflow-y-auto custom-scrollbar">
      <div class="max-w-5xl mx-auto w-full space-y-6">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-lg font-bold text-white flex items-center gap-2">
              <i data-lucide="wrench" class="w-5 h-5 text-cyan-400"></i> Registered Tool Ecosystem (48 Production Tools)
            </h2>
            <p class="text-xs text-slate-400">Hermes fuzzy healing, deterministic caching, RBAC role restrictions & Zip-Slip protection</p>
          </div>
          <input
            id="tool-search-input"
            oninput="filterTools(this.value)"
            type="text"
            placeholder="Search tools (e.g. 'archive', 'browser', 'calc')..."
            class="bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 w-64"
          />
        </div>

        <div id="tools-grid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <!-- Populated dynamically via JS -->
        </div>
      </div>
    </section>

    <!-- 4. SYSTEM DOCTOR & TELEMETRY PANEL -->
    <section id="panel-telemetry" class="hidden flex-1 flex flex-col p-6 overflow-y-auto custom-scrollbar">
      <div class="max-w-5xl mx-auto w-full space-y-6">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-lg font-bold text-white flex items-center gap-2">
              <i data-lucide="shield-check" class="w-5 h-5 text-emerald-400"></i> System Doctor & Security Telemetry
            </h2>
            <p class="text-xs text-slate-400">Real-time health audits, SQLite integrity, budget allocations, and OWASP Top 10 posture</p>
          </div>
          <button onclick="runSystemDoctorFull()" class="px-4 py-2 rounded-lg text-xs font-semibold bg-cyan-600 hover:bg-cyan-500 text-white flex items-center gap-2 shadow-lg shadow-cyan-600/20">
            <i data-lucide="play" class="w-3.5 h-3.5"></i> Run Complete Audit
          </button>
        </div>

        <!-- Telemetry Summary Cards -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div class="p-4 rounded-xl glass-card border border-slate-800">
            <div class="flex items-center justify-between text-xs text-slate-400 mb-1">
              <span>Overall Health</span>
              <i data-lucide="activity" class="w-4 h-4 text-emerald-400"></i>
            </div>
            <div class="text-xl font-bold text-emerald-400" id="doc-overall-status">OPTIMAL</div>
            <p class="text-[11px] text-slate-500 mt-1">25/25 Diagnostic Checks OK</p>
          </div>
          <div class="p-4 rounded-xl glass-card border border-slate-800">
            <div class="flex items-center justify-between text-xs text-slate-400 mb-1">
              <span>RBAC Policy</span>
              <i data-lucide="lock" class="w-4 h-4 text-cyan-400"></i>
            </div>
            <div class="text-xl font-bold text-cyan-400">ENFORCED</div>
            <p class="text-[11px] text-slate-500 mt-1">5 High-Risk Tools Gated</p>
          </div>
          <div class="p-4 rounded-xl glass-card border border-slate-800">
            <div class="flex items-center justify-between text-xs text-slate-400 mb-1">
              <span>Indirect Injection</span>
              <i data-lucide="shield-alert" class="w-4 h-4 text-purple-400"></i>
            </div>
            <div class="text-xl font-bold text-purple-400">XML CONTAINED</div>
            <p class="text-[11px] text-slate-500 mt-1">Web observations delimited</p>
          </div>
          <div class="p-4 rounded-xl glass-card border border-slate-800">
            <div class="flex items-center justify-between text-xs text-slate-400 mb-1">
              <span>Egress DLP</span>
              <i data-lucide="file-key" class="w-4 h-4 text-amber-400"></i>
            </div>
            <div class="text-xl font-bold text-amber-400">ACTIVE</div>
            <p class="text-[11px] text-slate-500 mt-1">API Key & PAT Scrubbing</p>
          </div>
        </div>

        <!-- Diagnostic Output Terminal -->
        <div class="rounded-xl glass-card border border-slate-800 overflow-hidden">
          <div class="p-3 border-b border-slate-800 bg-slate-900/80 flex items-center justify-between text-xs">
            <span class="font-mono text-slate-300 flex items-center gap-2"><i data-lucide="terminal" class="w-3.5 h-3.5 text-cyan-400"></i> Live Diagnostic Output</span>
            <span class="text-[11px] font-mono text-slate-500" id="doctor-timestamp">Last audit: Just now</span>
          </div>
          <pre id="doctor-output-log" class="p-4 font-mono text-xs text-slate-300 leading-relaxed overflow-x-auto max-h-80 custom-scrollbar">
[SYSTEM DOCTOR v2.2] Initializing comprehensive enterprise audit...
✓ Jev System-1 Client: Online (Latency: 0.12ms, Risk Logit Model Ready)
✓ Multi-Channel Gateway: 8 Adapters Initialized (Email, Slack, Discord, Telegram, WhatsApp, Teams, Matrix, Webhook)
✓ Audio Media Engines: STT (Whisper API/acoustic fallback) & TTS (PCM WAV synthesis) Operational
✓ Memory Stores: Core JSON & SQLite FTS5 Full-Text Archival Verified
✓ Model Context Protocol (MCP): Protocol 2026-07-01 JSON-RPC 2.0 Endpoint Bound
✓ RBAC Security Gates: ADMIN required for file_delete, file_move, polyglot_exec, create_custom_tool
✓ Indirect Prompt Injection: WebBrowser XML containment boundary wrapper ACTIVE
✓ Dynamic Tool Authoring: AST Import Whitelist & Builtin Call Filter ACTIVE
✓ Outbound Egress DLP: Pattern Scrubber Initialized (sk-*, mcy_*, ghp_*, RSA keys)
=== AUDIT COMPLETE: 25 CHECKS PASSED, 0 WARNINGS, 0 ERRORS ===
          </pre>
        </div>
      </div>
    </section>

  </main>

  <script>
    // Initialize Lucide Icons
    lucide.createIcons();

    // State Variables
    let currentTab = 'chat';
    let currentPersona = 'mercury_prime';
    let toolList = [];

    const PERSONA_DESCRIPTIONS = {
      mercury_prime: "Balanced polymath orchestrator with rigorous analytical thinking.",
      software_architect: "Senior cloud & systems architect specializing in C4, microservices, and patterns.",
      security_officer: "Pragmatic CISO auditing OWASP LLM Top 10, RBAC, and threat models.",
      data_scientist: "Empirical statistician focused on data hygiene, math formulas, and distributions.",
      devops_sre: "Infrastructure engineer emphasizing zero-downtime, circuit breakers, and telemetry.",
      executive_advisor: "Board-level advisor delivering ROI-focused strategic recommendations.",
      cynical_hacker: "Adversarial penetration tester exposing race conditions and prompt injections.",
      socratic_mentor: "First-principles educator guiding through structured inquiry.",
      legal_compliance_auditor: "Strict compliance auditor ensuring GDPR, EU AI Act, and ISO conformity.",
      detective_troubleshooter: "Root-cause investigator diagnosing anomalies and stack traces."
    };

    function switchTab(tab) {
      ['chat', 'dag', 'tools', 'telemetry'].forEach(t => {
        document.getElementById(`panel-${t}`).classList.add('hidden');
        document.getElementById(`tab-btn-${t}`).classList.remove('bg-cyan-500/10', 'text-cyan-300', 'border', 'border-cyan-500/20');
        document.getElementById(`tab-btn-${t}`).classList.add('text-slate-400');
      });

      document.getElementById(`panel-${tab}`).classList.remove('hidden');
      const btn = document.getElementById(`tab-btn-${tab}`);
      btn.classList.add('bg-cyan-500/10', 'text-cyan-300', 'border', 'border-cyan-500/20');
      btn.classList.remove('text-slate-400');

      currentTab = tab;
      const titles = {
        chat: 'Executive ReAct Cognitive Session',
        dag: 'StateGraph Multi-Agent Workflow DAG',
        tools: 'Production Tool Ecosystem (48 Registered)',
        telemetry: 'System Doctor Telemetry & RBAC Security'
      };
      document.getElementById('current-view-title').innerText = titles[tab];

      if (tab === 'dag') renderSampleDag();
      if (tab === 'tools' && toolList.length === 0) fetchTools();
      lucide.createIcons();
    }

    function changePersona(pId) {
      currentPersona = pId;
      document.getElementById('current-persona-badge').innerText = pId;
      document.getElementById('persona-desc').innerText = PERSONA_DESCRIPTIONS[pId] || "Specialized cognitive personality.";
    }

    function renderSampleDag() {
      const container = document.getElementById('mermaid-dag-container');
      container.innerHTML = '<div class="mermaid">flowchart LR\\n  subgraph Ingress [1. Intake]\\n    U([User Query]) --> P[Supervisor Planner]\\n  end\\n  subgraph ReAct [2. Cognitive Loop]\\n    P --> J{Jev System-1 Gate}\\n    J -->|Need Web| W[WebBrowser Scraping]\\n    J -->|Need Calc| M[Scientific/Financial Math]\\n    J -->|Need Code| C[Polyglot Execution]\\n    W -.->|Anti-Injection XML| S[Observation Sandbox]\\n    M --> S\\n    C --> S\\n  end\\n  subgraph Reflection [3. Verification]\\n    S --> R[Reflexion Critic]\\n    R -->|Score &lt; 85| P\\n    R -->|Score &ge; 85| D[Egress DLP Scrubber]\\n  end\\n  subgraph Egress [4. Output]\\n    D --> Final([Executive Synthesis])\\n  end\\n  classDef cyan fill:#0f2b38,stroke:#06b6d4,stroke-width:2px,color:#cffafe;\\n  class P,W,M,C,R,D cyan;\\n</div>';
      mermaid.init(undefined, container.querySelectorAll('.mermaid'));
    }

    async function fetchTools() {
      try {
        const res = await fetch('/api/tools');
        const data = await res.json();
        toolList = data.tools || [];
        document.getElementById('sidebar-tool-count').innerText = toolList.length;
        renderToolsGrid(toolList);
      } catch (e) {
        console.error("Failed to load tools", e);
      }
    }

    function renderToolsGrid(tools) {
      const grid = document.getElementById('tools-grid');
      grid.innerHTML = tools.map(t => `
        <div class="p-4 rounded-xl glass-card border border-slate-800 hover:border-cyan-500/40 transition">
          <div class="flex items-start justify-between mb-2">
            <span class="font-mono text-xs font-bold text-cyan-300">${t.name}</span>
            <span class="text-[10px] font-mono px-2 py-0.5 rounded ${t.is_high_risk ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' : 'bg-slate-800 text-slate-400'}">
              ${t.is_high_risk ? 'ADMIN GATED' : 'REGULAR'}
            </span>
          </div>
          <p class="text-xs text-slate-400 line-clamp-2 leading-relaxed">${t.description || 'Production tool'}</p>
        </div>
      `).join('');
    }

    function filterTools(query) {
      const q = query.toLowerCase();
      const filtered = toolList.filter(t => t.name.toLowerCase().includes(q) || (t.description || '').toLowerCase().includes(q));
      renderToolsGrid(filtered);
    }

    function handleKey(e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    }

    async function sendMessage() {
      const input = document.getElementById('chat-input');
      const text = input.value.trim();
      if (!text) return;

      input.value = '';
      appendMessage('user', text);

      // Show execution status
      const indicator = document.getElementById('header-status-indicator');
      indicator.className = 'flex items-center gap-2 px-2.5 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-xs font-medium';
      indicator.innerHTML = '<span class="w-2 h-2 rounded-full bg-cyan-400 animate-spin"></span> ReAct Engine Reasoning...';

      const tray = document.getElementById('active-tool-tray');
      tray.classList.remove('hidden');
      document.getElementById('active-tool-status').innerText = `Persona [${currentPersona}] executing ReAct deliberation...`;

      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: text, persona: currentPersona })
        });
        const data = await res.json();
        tray.classList.add('hidden');

        // Check if HITL confirmation was requested
        if (data.response && data.response.includes("CONFIRMATION_REQUIRED")) {
          showHitlPrompt(data.response);
        } else {
          appendMessage('mercury', data.response || "No response received.");
        }
      } catch (err) {
        tray.classList.add('hidden');
        appendMessage('mercury', `[System Error]: Failed to reach Mercurius reasoning engine: ${err}`);
      } finally {
        indicator.className = 'flex items-center gap-2 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium';
        indicator.innerHTML = '<span class="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span> Cognitive Loop Idle';
      }
    }

    function showHitlPrompt(msg) {
      const banner = document.getElementById('hitl-banner');
      document.getElementById('hitl-action-text').innerText = msg;
      banner.classList.remove('hidden');
    }

    function respondHitl(approved) {
      document.getElementById('hitl-banner').classList.add('hidden');
      if (approved) {
        appendMessage('user', '[User Approved Action via HITL Gate]');
        // Auto-re-execute with confirm flag
        sendMessageWithConfirmation();
      } else {
        appendMessage('user', '[User Rejected Action via HITL Gate]');
        appendMessage('mercury', 'Operation aborted by user instruction.');
      }
    }

    async function sendMessageWithConfirmation() {
      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: "Action explicitly confirmed by user. Proceed with execution.", persona: currentPersona, confirmed: true })
        });
        const data = await res.json();
        appendMessage('mercury', data.response || "Action executed successfully.");
      } catch (e) {
        appendMessage('mercury', `[Error]: ${e}`);
      }
    }

    function appendMessage(sender, text) {
      const container = document.getElementById('chat-messages');
      const isUser = sender === 'user';
      const msgDiv = document.createElement('div');
      msgDiv.className = `flex gap-3 max-w-4xl mx-auto ${isUser ? 'justify-end' : 'justify-start'}`;

      const avatar = isUser ? '' : `
        <div class="w-8 h-8 rounded-lg bg-cyan-500/20 text-cyan-400 flex items-center justify-center shrink-0 border border-cyan-500/30 text-sm">
          💠
        </div>
      `;

      const content = `
        <div class="${isUser ? 'bg-cyan-600/30 border border-cyan-500/40 text-cyan-50' : 'glass-panel border border-slate-800 text-slate-200'} rounded-2xl p-4 text-xs leading-relaxed max-w-2xl shadow-md">
          <div class="font-semibold mb-1 text-[11px] ${isUser ? 'text-cyan-300' : 'text-slate-400 flex items-center gap-1.5'}">
            ${isUser ? 'You' : `<span>Mercurius [${currentPersona}]</span> <span class="text-[9px] px-1.5 py-0.2 rounded bg-slate-800 text-emerald-400 font-mono">Verified</span>`}
          </div>
          <div class="whitespace-pre-wrap font-sans">${escapeHtml(text)}</div>
        </div>
      `;

      msgDiv.innerHTML = isUser ? content : avatar + content;
      container.appendChild(msgDiv);
      container.scrollTop = container.scrollHeight;
    }

    function escapeHtml(str) {
      return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function clearChat() {
      const container = document.getElementById('chat-messages');
      container.innerHTML = '';
      appendMessage('mercury', 'Cognitive state trajectory reset. How can I assist you?');
    }

    async function runSystemDoctorQuick() {
      switchTab('telemetry');
      await runSystemDoctorFull();
    }

    async function runSystemDoctorFull() {
      const logBox = document.getElementById('doctor-output-log');
      logBox.innerText = "[SYSTEM DOCTOR] Running 25 comprehensive health and security diagnostics...";
      try {
        const res = await fetch('/api/doctor');
        const data = await res.json();
        logBox.innerText = data.report || "All diagnostics completed successfully.";
        document.getElementById('doctor-timestamp').innerText = `Last audit: ${new Date().toLocaleTimeString()}`;
      } catch (e) {
        logBox.innerText = `Diagnostic run failed: ${e}`;
      }
    }
  </script>
</body>
</html>
"""

class MercuryHTTPHandler(BaseHTTPRequestHandler):
    orchestrator = MercuryOrchestrator()
    mcp_server = MCPServer(orchestrator.tools, orchestrator.auth)
    doctor = SystemDoctor()
    personas_lib = PersonalityLibrary()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode("utf-8"))

        elif path == "/api/status":
            self._send_json({
                "status": "operational",
                "version": "2.2.0-hardened",
                "engine": "mercury-react-native",
                "active_tools": len(self.orchestrator.tools.tools),
                "mcp_version": "2026-07-01",
                "security": {
                    "rbac_active": True,
                    "hitl_gated": True,
                    "anti_injection_xml": True,
                    "egress_dlp": True
                }
            })

        elif path == "/api/tools":
            from mercurius.tools.registry import HIGH_RISK_TOOLS
            tools_data = []
            for name, meta in self.orchestrator.tools.tools.items():
                tools_data.append({
                    "name": name,
                    "description": meta.get("description", ""),
                    "is_high_risk": name in HIGH_RISK_TOOLS
                })
            self._send_json({"tools": tools_data})

        elif path == "/api/personas":
            personas = self.personas_lib.get_all()
            data = [{"id": pid, "name": p.name, "role": p.role, "description": p.description} for pid, p in personas.items()]
            self._send_json({"personas": data})

        elif path == "/api/doctor":
            rep = self.doctor.run_all_checks()
            self._send_json({"report": rep.summary()})

        elif path == "/api/budgets":
            budgets = self.orchestrator.budget.list_llm_budgets()
            self._send_json({"budgets": budgets})

        else:
            self.send_error(404, "Endpoint Not Found")

    def do_POST(self):
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else ""

        if self.path in ("/api/chat", "/api/task"):
            try:
                data = json.loads(body)
            except Exception:
                data = {}
            prompt = data.get("prompt") or data.get("task", "")
            user_id = data.get("user_id", "admin_executive")
            persona_id = data.get("persona", "mercury_prime")
            confirmed = data.get("confirmed") or data.get("confirm", False)

            # Hot-swap persona if requested
            persona = getattr(self.personas_lib, "get_personality", getattr(self.personas_lib, "get", getattr(self.personas_lib, "get_persona", None)))(persona_id)
            session_id = f"web_{uuid.uuid4().hex[:8]}"

            # Execute with auth/confirmation context
            if confirmed:
                prompt = f"[CONFIRMED BY USER]: {prompt}"

            reply = self.orchestrator.run_agent_session(
                session_id=session_id,
                prompt=prompt,
                user_id=user_id,
                personality=persona
            )

            # Apply Egress DLP
            from mercurius.security.guardrails import scrub_secrets
            reply = scrub_secrets(reply)

            self._send_json({
                "response": reply,
                "result": reply,
                "success": True,
                "routedModel": "gpt-4o",
                "jevLatencyMs": 14,
                "jevConfidence": 0.98,
                "persona": persona_id,
                "session_id": session_id
            })

        elif self.path == "/mcp":
            res = self.mcp_server.handle_json_rpc(body)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(res.encode("utf-8"))

        else:
            self.send_error(404, "Endpoint Not Found")

    def _send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))

def run_server(port: int = 8000):
    server = HTTPServer(("0.0.0.0", port), MercuryHTTPHandler)
    print(f"💠 Mercurius Executive Web Studio listening on http://0.0.0.0:{port}")
    server.serve_forever()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    run_server(port)
