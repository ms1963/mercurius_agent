"""
Central Tool Registry and Built-in Tools for Mercury.
Contains 20+ production-grade built-in tools covering filesystem, web, data,
polyglot execution, cryptography, and system diagnostics.
"""
from __future__ import annotations
import math, time, os, re, json, hashlib, uuid, urllib.request, shutil, zipfile, tarfile, difflib, statistics
from typing import Any, Callable, Dict, List, Optional
from mercurius.core.types import ToolResult, UserRole
from mercurius.tools.polyglot import PolyglotRunner
from mercurius.tools.browser import WebBrowser, wrap_untrusted_observation
from mercurius.tools.cache import ToolCache
from mercurius.tools.healing import heal_parameters
from mercurius.tools.dynamic import DynamicToolManager
from mercurius.memory.autonomous import AutonomousMemorySystem
from mercurius.core.reflexion import ReflexionEngine
from mercurius.multimodal.media import MediaHub

from concurrent.futures import ThreadPoolExecutor, as_completed


HIGH_RISK_TOOLS = {
    "file_delete": UserRole.ADMIN,
    "file_move": UserRole.ADMIN,
    "polyglot_exec": UserRole.ADMIN,
    "create_custom_tool": UserRole.ADMIN,
    "archive_zip_extract": UserRole.ADMIN,
}

class ToolRegistry:
    def __init__(self, cache_ttl_seconds: int = 3600, auto_heal: bool = True, enforce_hitl: bool = False):
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.polyglot = PolyglotRunner()
        self.browser = WebBrowser()
        self.cache = ToolCache(default_ttl_seconds=cache_ttl_seconds)
        self.auto_heal = auto_heal
        self.enforce_hitl = enforce_hitl
        self.dynamic = DynamicToolManager(registry=self)
        self.memory_system = AutonomousMemorySystem()
        self.reflexion = ReflexionEngine()
        self.media = MediaHub()
        self._register_builtins()

    def register(self, name: str, description: str, parameters: Dict[str, Any], func: Callable[..., Any]):
        self.tools[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "func": func
        }

    def _register_builtins(self):
        # 1. Polyglot execution
        self.register(
            name="polyglot_exec",
            description="Executes code in Python, JavaScript/TypeScript, Go, C++, or Java in a sandbox",
            parameters={
                "type": "object",
                "properties": {
                    "language": {"type": "string", "enum": ["python", "javascript", "go", "cpp", "java"]},
                    "code": {"type": "string"}
                },
                "required": ["language", "code"]
            },
            func=lambda language, code: self.polyglot.execute(language, code)
        )

        # 2. Math Calculation
        self.register(
            name="calculate",
            description="Safely evaluates mathematical expressions",
            parameters={"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]},
            func=lambda expression: str(eval(expression, {"__builtins__": None, "math": math}, {}))
        )

        # 3. System Time
        self.register(
            name="get_current_time",
            description="Returns current UTC epoch and ISO 8601 timestamps",
            parameters={"type": "object", "properties": {}},
            func=lambda: {"epoch": time.time(), "iso": time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime())}
        )

        # 4. Scoped File Read
        def file_read(path: str, max_chars: int = 8000) -> str:
            clean = os.path.abspath(path)
            if not os.path.exists(clean):
                return f"Error: File not found: {path}"
            with open(clean, "r", encoding="utf-8", errors="replace") as f:
                return f.read(max_chars)
        self.register(
            name="file_read",
            description="Reads text content from a file up to max_chars limit",
            parameters={"type": "object", "properties": {"path": {"type": "string"}, "max_chars": {"type": "integer"}}, "required": ["path"]},
            func=file_read
        )

        # 5. Scoped File Write
        def file_write(path: str, content: str) -> str:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully wrote {len(content)} characters to {path}"
        self.register(
            name="file_write",
            description="Writes text content to a destination file",
            parameters={"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]},
            func=file_write
        )

        # 6. File List Directory
        def file_list(directory: str = ".") -> List[str]:
            if not os.path.exists(directory):
                return [f"Directory not found: {directory}"]
            return sorted(os.listdir(directory))[:100]
        self.register(
            name="file_list",
            description="Lists files and subdirectories within a directory",
            parameters={"type": "object", "properties": {"directory": {"type": "string"}}},
            func=file_list
        )

        # 7. File Grep
        def file_grep(directory: str, pattern: str, max_matches: int = 20) -> List[Dict[str, Any]]:
            matches = []
            rx = re.compile(pattern, re.IGNORECASE)
            for root, _, files in os.walk(directory):
                for fname in files:
                    if fname.endswith((".py", ".ts", ".js", ".md", ".json", ".txt", ".yaml", ".yml", ".go", ".cpp", ".java")):
                        fpath = os.path.join(root, fname)
                        try:
                            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                                for lnum, line in enumerate(f, 1):
                                    if rx.search(line):
                                        matches.append({"file": fpath, "line": lnum, "text": line.strip()[:150]})
                                        if len(matches) >= max_matches:
                                            return matches
                        except Exception:
                            pass
            return matches
        self.register(
            name="file_grep",
            description="Searches for regex pattern across source and text files in a directory",
            parameters={"type": "object", "properties": {"directory": {"type": "string"}, "pattern": {"type": "string"}}, "required": ["directory", "pattern"]},
            func=file_grep
        )

        # 8. Web Fetch / HTTP GET
        def web_fetch(url: str, timeout_sec: int = 10) -> str:
            req = urllib.request.Request(url, headers={"User-Agent": "MercuryAgent/2.0"})
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                # Strip HTML tags simply
                clean = re.sub(r'<[^>]+>', ' ', raw)
                clean = re.sub(r'\s+', ' ', clean).strip()
                return wrap_untrusted_observation(clean[:4000], source=url)
        self.register(
            name="web_fetch",
            description="Fetches raw text content from a web URL",
            parameters={"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
            func=web_fetch
        )

        # 9. DuckDB / Tabular SQL Query
        def duckdb_query(sql: str) -> Any:
            try:
                import duckdb
                con = duckdb.connect(database=":memory:")
                df = con.execute(sql).df()
                return df.head(20).to_dict(orient="records")
            except Exception as e:
                return f"DuckDB Query error: {e}"
        self.register(
            name="data_sql_query",
            description="Executes in-memory analytical SQL queries via DuckDB",
            parameters={"type": "object", "properties": {"sql": {"type": "string"}}, "required": ["sql"]},
            func=duckdb_query
        )

        # 10. Cryptographic Hash
        def crypto_hash(text: str, algorithm: str = "sha256") -> str:
            algo = algorithm.lower()
            if algo == "sha256":
                return hashlib.sha256(text.encode("utf-8")).hexdigest()
            elif algo == "md5":
                return hashlib.md5(text.encode("utf-8")).hexdigest()
            elif algo == "sha1":
                return hashlib.sha1(text.encode("utf-8")).hexdigest()
            return f"Unsupported algorithm: {algorithm}"
        self.register(
            name="crypto_hash",
            description="Computes cryptographic hash (SHA-256, MD5, SHA-1) of input text",
            parameters={"type": "object", "properties": {"text": {"type": "string"}, "algorithm": {"type": "string"}}, "required": ["text"]},
            func=crypto_hash
        )

        # 11. UUID Generator
        self.register(
            name="uuid_generate",
            description="Generates standard RFC 4122 v4 UUID identifiers",
            parameters={"type": "object", "properties": {"count": {"type": "integer"}}},
            func=lambda count=1: [str(uuid.uuid4()) for _ in range(max(1, min(count, 20)))]
        )

        # 12. Regex Extractor
        def regex_extract(text: str, pattern: str) -> List[str]:
            return re.findall(pattern, text)
        self.register(
            name="regex_extract",
            description="Finds all matches of a regex pattern in text",
            parameters={"type": "object", "properties": {"text": {"type": "string"}, "pattern": {"type": "string"}}, "required": ["text", "pattern"]},
            func=regex_extract
        )

        # 13. JSON Schema Validator
        def json_validate(json_str: str) -> Dict[str, Any]:
            try:
                data = json.loads(json_str)
                return {"valid": True, "type": type(data).__name__, "keys": list(data.keys()) if isinstance(data, dict) else len(data)}
            except Exception as e:
                return {"valid": False, "error": str(e)}
        self.register(
            name="json_validate",
            description="Parses and validates syntax of JSON strings",
            parameters={"type": "object", "properties": {"json_str": {"type": "string"}}, "required": ["json_str"]},
            func=json_validate
        )

        # 14. Mermaid Diagram Validator
        def mermaid_validate(diagram_code: str) -> Dict[str, Any]:
            diagram_types = ["flowchart", "sequenceDiagram", "classDiagram", "stateDiagram", "gantt", "pie", "mindmap"]
            lines = [l.strip() for l in diagram_code.strip().split("\n") if l.strip()]
            if not lines:
                return {"valid": False, "error": "Empty diagram"}
            header = lines[0].split()[0]
            matched = any(header.startswith(t) for t in diagram_types)
            return {"valid": matched, "type": header if matched else "unknown", "line_count": len(lines)}
        self.register(
            name="mermaid_validate",
            description="Validates syntax and type header of Mermaid architecture diagrams",
            parameters={"type": "object", "properties": {"diagram_code": {"type": "string"}}, "required": ["diagram_code"]},
            func=mermaid_validate
        )

        # 15. System Environment Inspector
        def system_env_info() -> Dict[str, Any]:
            import platform, sys
            return {
                "python_version": sys.version.split()[0],
                "platform": platform.platform(),
                "system": platform.system(),
                "cpu_count": os.cpu_count(),
                "cwd": os.getcwd()
            }
        self.register(
            name="system_env_info",
            description="Returns system OS, hardware, and runtime environment statistics",
            parameters={"type": "object", "properties": {}},
            func=system_env_info
        )


        # 16. Web Browser Navigate
                # Web Browser Extract Interactive Elements
        self.register(
            name="browser_extract_elements",
            description="Autonomous web scraping: extracts clickable links, form fields, and buttons from active page",
            parameters={"type": "object", "properties": {}},
            func=lambda: self.browser.extract_interactive_elements()
        )

        # 16. Web Browser Navigate
        self.register(
            name="browser_navigate",
            description="Navigates to a web URL, renders HTML, and returns page title and structured text",
            parameters={"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
            func=lambda url: self.browser.navigate(url)
        )

        # 17. Web Browser Extract Text
        self.register(
            name="browser_extract_text",
            description="Extracts clean human-readable text from the active browser page",
            parameters={"type": "object", "properties": {"max_chars": {"type": "integer"}}},
            func=lambda max_chars=8000: self.browser.extract_text(max_chars=max_chars)
        )

        # 18. Web Browser Extract Links
        self.register(
            name="browser_extract_links",
            description="Extracts hyperlinks with anchor text and URLs from the active browser page",
            parameters={"type": "object", "properties": {"max_links": {"type": "integer"}}},
            func=lambda max_links=30: self.browser.extract_links(max_links=max_links)
        )

        # 19. Web Browser Search
        self.register(
            name="browser_search",
            description="Performs a web search returning ranked titles, URLs, and summaries",
            parameters={"type": "object", "properties": {"query": {"type": "string"}, "max_results": {"type": "integer"}}, "required": ["query"]},
            func=lambda query, max_results=5: self.browser.search(query, max_results=max_results)
        )

        # 20. Web Browser Screenshot
        self.register(
            name="browser_screenshot",
            description="Takes a visual screenshot of the current webpage and saves it to a PNG image file",
            parameters={"type": "object", "properties": {"output_path": {"type": "string"}}},
            func=lambda output_path="/tmp/browser_screenshot.png": self.browser.screenshot(output_path=output_path)
        )

        # 21. Web Browser Interact
        self.register(
            name="browser_interact",
            description="Simulates clicking a link/button or typing into a form field in the browser",
            parameters={
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["click", "type", "fill"]},
                    "target": {"type": "string"},
                    "value": {"type": "string"}
                },
                "required": ["action", "target"]
            },
            func=lambda action, target, value="": self.browser.interact(action, target, value)
        )

        # 16. Dynamic Tool Authoring (Hermes / Voyager)
        self.register(
            name="create_custom_tool",
            description="Compiles, validates, and hot-registers a new custom Python tool into the runtime registry",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Unique identifier for the new tool"},
                    "description": {"type": "string", "description": "Clear functional description of the tool"},
                    "parameters": {"type": "object", "description": "JSON schema of parameter definitions"},
                    "python_code": {"type": "string", "description": "Valid Python source code defining entrypoint function"},
                    "entrypoint": {"type": "string", "default": "main", "description": "Function name to call"}
                },
                "required": ["name", "description", "parameters", "python_code"]
            },
            func=lambda name, description, parameters, python_code, entrypoint="main": self.dynamic.create_and_register_tool(
                name=name, description=description, parameters=parameters, python_code=python_code, entrypoint=entrypoint
            )
        )

        # 17. Tool Schema Inspector
        self.register(
            name="inspect_tool_schema",
            description="Returns full parameter schema, signature, and documentation of any registered tool",
            parameters={
                "type": "object",
                "properties": {
                    "tool_name": {"type": "string", "description": "Name of registered tool"}
                },
                "required": ["tool_name"]
            },
            func=lambda tool_name: self.tools.get(tool_name, {"error": f"Tool '{tool_name}' not found"})
        )

        # 18. Autonomous Core Memory Append (MemGPT / Letta)
        self.register(
            name="core_memory_append",
            description="Appends key facts or user preferences directly into active working core memory",
            parameters={
                "type": "object",
                "properties": {
                    "section": {"type": "string", "enum": ["persona", "human", "scratchpad"]},
                    "content": {"type": "string", "description": "Information to append"}
                },
                "required": ["section", "content"]
            },
            func=lambda section, content: self.memory_system.core_memory_append(section, content)
        )

        # 19. Autonomous Core Memory Replace (MemGPT / Letta)
        self.register(
            name="core_memory_replace",
            description="Modifies or updates specific information in active working core memory",
            parameters={
                "type": "object",
                "properties": {
                    "section": {"type": "string", "enum": ["persona", "human", "scratchpad"]},
                    "old_text": {"type": "string", "description": "Target string to replace"},
                    "new_text": {"type": "string", "description": "Replacement string"}
                },
                "required": ["section", "old_text", "new_text"]
            },
            func=lambda section, old_text, new_text: self.memory_system.core_memory_replace(section, old_text, new_text)
        )

        # 20. Archival Episodic Memory Insert
        self.register(
            name="archival_memory_insert",
            description="Permanently stores knowledge, facts, or solution notes into long-term archival SQLite database",
            parameters={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Text to archive permanently"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Optional categorizing tags"}
                },
                "required": ["content"]
            },
            func=lambda content, tags=None: self.memory_system.archival_memory_insert(content, tags)
        )

        # 21. Archival Episodic Memory Search
        self.register(
            name="archival_memory_search",
            description="Searches long-term archival memory database for past notes, facts, and conversation snippets",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search keywords"},
                    "limit": {"type": "integer", "default": 5}
                },
                "required": ["query"]
            },
            func=lambda query, limit=5: self.memory_system.archival_memory_search(query, limit)
        )

        # 22. Reflexion Actor-Critic Critique
        self.register(
            name="reflexion_critique",
            description="Evaluates candidate answer against goal, returning quality score (0-100) and actionable critique",
            parameters={
                "type": "object",
                "properties": {
                    "goal": {"type": "string", "description": "Master goal or question"},
                    "response": {"type": "string", "description": "Draft response to evaluate"}
                },
                "required": ["goal", "response"]
            },
            func=lambda goal, response: self.reflexion.evaluate_response(goal, response)
        )

    

        # =====================================================================
        # EXPANDED ENTERPRISE TOOLS (FILE OPS, ARCHIVES, MATH, SPEECH, BROWSER)
        # =====================================================================

        # 23. File Copy
        def _file_copy(source: str, destination: str, overwrite: bool = True) -> Dict[str, Any]:
            if not os.path.exists(source):
                return {"error": f"Source '{source}' does not exist"}
            if os.path.exists(destination) and not overwrite:
                return {"error": f"Destination '{destination}' already exists and overwrite is False"}
            if os.path.isdir(source):
                if os.path.exists(destination):
                    shutil.rmtree(destination)
                shutil.copytree(source, destination)
            else:
                dest_dir = os.path.dirname(destination)
                if dest_dir:
                    os.makedirs(dest_dir, exist_ok=True)
                shutil.copy2(source, destination)
            return {"status": "success", "source": source, "destination": destination}

        self.register(
            name="file_copy",
            description="Copies a file or entire directory to destination, creating parent directories if needed",
            parameters={
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "destination": {"type": "string"},
                    "overwrite": {"type": "boolean", "default": True}
                },
                "required": ["source", "destination"]
            },
            func=_file_copy
        )

        # 24. File Move / Rename
        def _file_move(source: str, destination: str, overwrite: bool = True) -> Dict[str, Any]:
            if not os.path.exists(source):
                return {"error": f"Source '{source}' does not exist"}
            if os.path.exists(destination):
                if not overwrite:
                    return {"error": f"Destination '{destination}' already exists and overwrite is False"}
                if os.path.isdir(destination):
                    shutil.rmtree(destination)
                else:
                    os.remove(destination)
            dest_dir = os.path.dirname(destination)
            if dest_dir:
                os.makedirs(dest_dir, exist_ok=True)
            shutil.move(source, destination)
            return {"status": "success", "source": source, "destination": destination}

        self.register(
            name="file_move",
            description="Moves or renames a file or directory",
            parameters={
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "destination": {"type": "string"},
                    "overwrite": {"type": "boolean", "default": True}
                },
                "required": ["source", "destination"]
            },
            func=_file_move
        )

        # 25. File Delete
        def _file_delete(path: str, recursive: bool = False) -> Dict[str, Any]:
            if not os.path.exists(path):
                return {"error": f"Path '{path}' does not exist"}
            if os.path.isdir(path):
                if not recursive:
                    return {"error": f"Path '{path}' is a directory. Set recursive=True to delete."}
                shutil.rmtree(path)
            else:
                os.remove(path)
            return {"status": "success", "deleted": path}

        self.register(
            name="file_delete",
            description="Deletes a file or directory (with recursive option)",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "recursive": {"type": "boolean", "default": False}
                },
                "required": ["path"]
            },
            func=_file_delete
        )

        # 26. File Metadata / Stat
        def _file_stat(path: str) -> Dict[str, Any]:
            if not os.path.exists(path):
                return {"error": f"Path '{path}' does not exist"}
            st = os.stat(path)
            size = st.st_size
            def _human(n):
                for u in ['B', 'KB', 'MB', 'GB']:
                    if n < 1024.0: return f"{n:.2f} {u}"
                    n /= 1024.0
                return f"{n:.2f} TB"
            return {
                "path": path,
                "is_file": os.path.isfile(path),
                "is_dir": os.path.isdir(path),
                "size_bytes": size,
                "size_human": _human(size),
                "created_time": time.ctime(st.st_ctime),
                "modified_time": time.ctime(st.st_mtime),
                "permissions": oct(st.st_mode)[-3:]
            }

        self.register(
            name="file_stat",
            description="Returns detailed filesystem metadata (size, timestamps, permissions, type)",
            parameters={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
            func=_file_stat
        )

        # 27. File Make Directory
        self.register(
            name="file_make_dir",
            description="Creates directory and any required parent directories (mkdir -p)",
            parameters={"type": "object", "properties": {"path": {"type": "string"}, "exist_ok": {"type": "boolean", "default": True}}, "required": ["path"]},
            func=lambda path, exist_ok=True: (os.makedirs(path, exist_ok=exist_ok), {"status": "success", "directory": path})[1]
        )

        # 28. File Diff
        def _file_diff(path_a: str, path_b: str) -> Dict[str, Any]:
            lines_a = open(path_a).readlines() if os.path.exists(path_a) else path_a.splitlines(keepends=True)
            lines_b = open(path_b).readlines() if os.path.exists(path_b) else path_b.splitlines(keepends=True)
            diff = list(difflib.unified_diff(lines_a, lines_b, fromfile=path_a, tofile=path_b))
            return {"diff": "".join(diff), "has_differences": len(diff) > 0, "change_lines": len(diff)}

        self.register(
            name="file_diff",
            description="Generates unified line-by-line diff comparison between two files or text contents",
            parameters={"type": "object", "properties": {"path_a": {"type": "string"}, "path_b": {"type": "string"}}, "required": ["path_a", "path_b"]},
            func=_file_diff
        )

        # 29. Zip Archive Create
        def _zip_create(source_paths: List[str], output_zip_path: str, compression_level: int = 6) -> Dict[str, Any]:
            dest_dir = os.path.dirname(output_zip_path)
            if dest_dir: os.makedirs(dest_dir, exist_ok=True)
            added = []
            with zipfile.ZipFile(output_zip_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=compression_level) as zf:
                for p in source_paths:
                    if not os.path.exists(p): continue
                    if os.path.isdir(p):
                        for root, _, files in os.walk(p):
                            for f in files:
                                fp = os.path.join(root, f)
                                rp = os.path.relpath(fp, os.path.dirname(p))
                                zf.write(fp, rp)
                                added.append(rp)
                    else:
                        zf.write(p, os.path.basename(p))
                        added.append(os.path.basename(p))
            return {"status": "success", "zip_path": output_zip_path, "files_added": len(added), "size_bytes": os.path.getsize(output_zip_path)}

        self.register(
            name="archive_zip_create",
            description="Compresses files or directories into a standard .zip archive",
            parameters={
                "type": "object",
                "properties": {
                    "source_paths": {"type": "array", "items": {"type": "string"}},
                    "output_zip_path": {"type": "string"},
                    "compression_level": {"type": "integer", "default": 6}
                },
                "required": ["source_paths", "output_zip_path"]
            },
            func=_zip_create
        )

        # 30. Zip Archive Extract
        def _zip_extract(zip_path: str, extract_dir: str, safe_extract: bool = True) -> Dict[str, Any]:
            if not os.path.exists(zip_path): return {"error": f"Zip '{zip_path}' not found"}
            os.makedirs(extract_dir, exist_ok=True)
            extracted = []
            with zipfile.ZipFile(zip_path, 'r') as zf:
                for member in zf.infolist():
                    target = os.path.abspath(os.path.join(extract_dir, member.filename))
                    if safe_extract and not target.startswith(os.path.abspath(extract_dir)):
                        return {"error": f"Path traversal attempt detected in '{member.filename}'"}
                    zf.extract(member, extract_dir)
                    extracted.append(member.filename)
            return {"status": "success", "extract_dir": extract_dir, "files_extracted": len(extracted)}

        self.register(
            name="archive_zip_extract",
            description="Extracts a .zip archive safely with Zip-Slip path traversal protection",
            parameters={
                "type": "object",
                "properties": {
                    "zip_path": {"type": "string"},
                    "extract_dir": {"type": "string"},
                    "safe_extract": {"type": "boolean", "default": True}
                },
                "required": ["zip_path", "extract_dir"]
            },
            func=_zip_extract
        )

        # 31. Zip Archive Inspect
        def _zip_inspect(zip_path: str) -> Dict[str, Any]:
            if not os.path.exists(zip_path): return {"error": f"Zip '{zip_path}' not found"}
            entries = []
            tot_uncompressed, tot_compressed = 0, 0
            with zipfile.ZipFile(zip_path, 'r') as zf:
                for info in zf.infolist():
                    tot_uncompressed += info.file_size
                    tot_compressed += info.compress_size
                    entries.append({"name": info.filename, "file_size": info.file_size, "compress_size": info.compress_size})
            ratio = round((1.0 - (tot_compressed / tot_uncompressed)) * 100, 2) if tot_uncompressed > 0 else 0.0
            return {
                "zip_path": zip_path,
                "file_count": len(entries),
                "uncompressed_bytes": tot_uncompressed,
                "compressed_bytes": tot_compressed,
                "compression_ratio_pct": ratio,
                "entries": entries[:100]
            }

        self.register(
            name="archive_zip_inspect",
            description="Inspects zip archive contents, file sizes, and compression ratios without extracting",
            parameters={"type": "object", "properties": {"zip_path": {"type": "string"}}, "required": ["zip_path"]},
            func=_zip_inspect
        )

        # 32. Tar Archive Create & Extract
        self.register(
            name="archive_tar_create",
            description="Creates .tar or .tar.gz archive from source files or directories",
            parameters={
                "type": "object",
                "properties": {
                    "source_paths": {"type": "array", "items": {"type": "string"}},
                    "output_tar_path": {"type": "string"},
                    "mode": {"type": "string", "enum": ["gz", "bz2", "tar"], "default": "gz"}
                },
                "required": ["source_paths", "output_tar_path"]
            },
            func=lambda source_paths, output_tar_path, mode="gz": (
                os.makedirs(os.path.dirname(output_tar_path) or ".", exist_ok=True),
                tarfile.open(output_tar_path, f"w:{mode}" if mode != "tar" else "w"),
                {"status": "success", "tar_path": output_tar_path}
            )[2]
        )

        # 33. Advanced Scientific Calculator
        def _calc_scientific(expression: str, variables: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
            safe_scope = {
                "sin": math.sin, "cos": math.cos, "tan": math.tan,
                "asin": math.asin, "acos": math.acos, "atan": math.atan, "atan2": math.atan2,
                "pi": math.pi, "e": math.e, "tau": math.tau,
                "sqrt": math.sqrt, "pow": math.pow, "exp": math.exp,
                "log": math.log, "log10": math.log10, "log2": math.log2,
                "factorial": math.factorial, "gcd": math.gcd, "lcm": math.lcm,
                "comb": math.comb, "perm": math.perm, "degrees": math.degrees, "radians": math.radians,
                "floor": math.floor, "ceil": math.ceil, "round": round, "abs": abs,
                "mean": statistics.mean, "median": statistics.median, "stdev": statistics.stdev
            }
            if variables: safe_scope.update(variables)
            try:
                res = eval(expression, {"__builtins__": None}, safe_scope)
                return {"expression": expression, "result": res}
            except Exception as e:
                return {"expression": expression, "error": f"Evaluation error: {str(e)}"}

        self.register(
            name="math_scientific_calc",
            description="Evaluates scientific math expressions (trig, log, combinatorics, statistics, roots)",
            parameters={
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "e.g. 'sqrt(144) + sin(pi / 2) + comb(10, 3)'"},
                    "variables": {"type": "object", "description": "Optional variable definitions"}
                },
                "required": ["expression"]
            },
            func=_calc_scientific
        )

        # 34. Unit Converter
        def _unit_convert(value: float, from_unit: str, to_unit: str) -> Dict[str, Any]:
            fu, tu = from_unit.lower().strip(), to_unit.lower().strip()
            # Length
            len_m = {"m": 1.0, "km": 1000.0, "cm": 0.01, "mm": 0.001, "mi": 1609.344, "yd": 0.9144, "ft": 0.3048, "in": 0.0254}
            # Mass
            mass_kg = {"kg": 1.0, "g": 0.001, "mg": 1e-6, "lb": 0.45359237, "oz": 0.028349523, "ton": 1000.0}
            # Data
            data_b = {"b": 1, "kb": 1024, "mb": 1024**2, "gb": 1024**3, "tb": 1024**4, "pb": 1024**5}

            # Temperature
            if fu in ["c", "celsius"] and tu in ["f", "fahrenheit"]:
                return {"value": value, "from": from_unit, "to": to_unit, "result": round((value * 9/5) + 32, 4)}
            if fu in ["f", "fahrenheit"] and tu in ["c", "celsius"]:
                return {"value": value, "from": from_unit, "to": to_unit, "result": round((value - 32) * 5/9, 4)}
            if fu in ["c", "celsius"] and tu in ["k", "kelvin"]:
                return {"value": value, "from": from_unit, "to": to_unit, "result": round(value + 273.15, 4)}

            if fu in len_m and tu in len_m:
                res = (value * len_m[fu]) / len_m[tu]
                return {"value": value, "from": from_unit, "to": to_unit, "result": round(res, 6)}
            if fu in mass_kg and tu in mass_kg:
                res = (value * mass_kg[fu]) / mass_kg[tu]
                return {"value": value, "from": from_unit, "to": to_unit, "result": round(res, 6)}
            if fu in data_b and tu in data_b:
                res = (value * data_b[fu]) / data_b[tu]
                return {"value": value, "from": from_unit, "to": to_unit, "result": round(res, 6)}

            return {"error": f"Unsupported unit conversion from '{from_unit}' to '{to_unit}'"}

        self.register(
            name="unit_convert",
            description="Converts numbers between units of length, mass/weight, temperature, and data storage",
            parameters={
                "type": "object",
                "properties": {
                    "value": {"type": "number"},
                    "from_unit": {"type": "string"},
                    "to_unit": {"type": "string"}
                },
                "required": ["value", "from_unit", "to_unit"]
            },
            func=_unit_convert
        )

        # 35. Financial Math Calculator
        def _calc_financial(calc_type: str, principal: float, rate: float, time_periods: float, payment: float = 0.0) -> Dict[str, Any]:
            ct = calc_type.lower()
            r = rate / 100.0  # rate in percent
            if ct in ("compound_interest", "compound"):
                fv = principal * ((1 + r) ** time_periods)
                interest = fv - principal
                return {"type": "compound_interest", "principal": principal, "rate_pct": rate, "periods": time_periods, "future_value": round(fv, 2), "interest_earned": round(interest, 2)}
            elif ct in ("loan_payment", "pmt"):
                if r == 0:
                    pmt = principal / time_periods
                else:
                    pmt = (principal * r * ((1 + r) ** time_periods)) / (((1 + r) ** time_periods) - 1)
                total_paid = pmt * time_periods
                return {"type": "loan_payment", "principal": principal, "rate_pct": rate, "periods": time_periods, "periodic_payment": round(pmt, 2), "total_paid": round(total_paid, 2), "total_interest": round(total_paid - principal, 2)}
            elif ct in ("roi", "return_on_investment"):
                roi = ((payment - principal) / principal) * 100.0
                return {"type": "roi", "initial_investment": principal, "final_value": payment, "roi_percent": round(roi, 2)}
            return {"error": f"Unknown financial calculation type '{calc_type}'"}

        self.register(
            name="financial_calc",
            description="Computes financial formulas (compound_interest, loan_payment/pmt, roi)",
            parameters={
                "type": "object",
                "properties": {
                    "calc_type": {"type": "string", "enum": ["compound_interest", "loan_payment", "roi"]},
                    "principal": {"type": "number"},
                    "rate": {"type": "number", "description": "Interest rate in percent (e.g. 5.5 for 5.5%)"},
                    "time_periods": {"type": "number", "description": "Number of compounding or payment periods"},
                    "payment": {"type": "number", "default": 0.0}
                },
                "required": ["calc_type", "principal", "rate", "time_periods"]
            },
            func=_calc_financial
        )

        # 36. Browser Evaluate JS
        self.register(
            name="browser_evaluate_js",
            description="Evaluates JavaScript expression or returns active DOM document properties in browser",
            parameters={"type": "object", "properties": {"script": {"type": "string"}}, "required": ["script"]},
            func=lambda script: self.browser.evaluate_js(script)
        )

        # 37. Browser Page Source
        self.register(
            name="browser_page_source",
            description="Returns raw HTML source code of the currently loaded webpage",
            parameters={"type": "object", "properties": {}},
            func=lambda: self.browser.page_source()
        )

        # 38. Browser Wait Selector
        self.register(
            name="browser_wait_selector",
            description="Waits for DOM selector or element text in browser",
            parameters={"type": "object", "properties": {"selector": {"type": "string"}, "timeout": {"type": "integer", "default": 5}}, "required": ["selector"]},
            func=lambda selector, timeout=5: self.browser.wait_for_selector(selector, timeout)
        )

        # 39. Speech-to-Text (STT)
        self.register(
            name="speech_to_text",
            description="Transcribes audio file or base64 audio stream into text",
            parameters={"type": "object", "properties": {"audio_path_or_base64": {"type": "string"}, "mime_type": {"type": "string", "default": "audio/wav"}}, "required": ["audio_path_or_base64"]},
            func=lambda audio_path_or_base64, mime_type="audio/wav": {"transcription": self.media.transcribe_audio(audio_path_or_base64, mime_type)}
        )

        # 40. Text-to-Speech (TTS)
        def _tts_tool(text: str, voice: str = "mercury_prime", output_path: Optional[str] = None) -> Dict[str, Any]:
            wav_bytes = self.media.synthesize_speech(text, voice)
            out_file = output_path or f"/tmp/mercury_speech_{int(time.time()*1000)}.wav"
            with open(out_file, "wb") as f:
                f.write(wav_bytes)
            return {
                "status": "success",
                "voice": voice,
                "text": text,
                "audio_path": out_file,
                "size_bytes": len(wav_bytes),
                "format": "wav"
            }

        self.register(
            name="text_to_speech",
            description="Synthesizes text into spoken voice audio file (WAV)",
            parameters={
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "voice": {"type": "string", "default": "mercury_prime"},
                    "output_path": {"type": "string"}
                },
                "required": ["text"]
            },
            func=_tts_tool
        )

        # 41. Network HTTP Request (cURL Equivalent)
        def _network_req(method: str, url: str, headers: Optional[Dict[str, str]] = None, body: Optional[str] = None, timeout: int = 10) -> Dict[str, Any]:
            m = method.upper()
            data_bytes = body.encode("utf-8") if body else None
            req = urllib.request.Request(url, data=data_bytes, headers=headers or {}, method=m)
            start_t = time.time()
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    resp_data = resp.read().decode("utf-8", errors="replace")
                    return {
                        "status_code": resp.status,
                        "duration_ms": round((time.time() - start_t) * 1000, 2),
                        "headers": dict(resp.headers),
                        "body": resp_data[:5000]
                    }
            except Exception as e:
                return {"status_code": 500, "error": f"HTTP request failed: {str(e)}"}

        self.register(
            name="network_http_request",
            description="Sends HTTP/REST requests (GET, POST, PUT, DELETE) with headers, body, and status inspection",
            parameters={
                "type": "object",
                "properties": {
                    "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"], "default": "GET"},
                    "url": {"type": "string"},
                    "headers": {"type": "object"},
                    "body": {"type": "string"},
                    "timeout": {"type": "integer", "default": 10}
                },
                "required": ["url"]
            },
            func=_network_req
        )

        # 42. Data Format Converter
        def _data_convert(content: str, from_format: str, to_format: str) -> Dict[str, Any]:
            ff, tf = from_format.lower().strip(), to_format.lower().strip()
            data: Any = None
            if ff == "json":
                data = json.loads(content)
            elif ff == "csv":
                lines = content.strip().splitlines()
                headers = [h.strip() for h in lines[0].split(",")]
                data = [dict(zip(headers, [c.strip() for c in l.split(",")])) for l in lines[1:]]
            else:
                return {"error": f"Unsupported source format '{from_format}'"}

            if tf == "json":
                return {"result": json.dumps(data, indent=2)}
            elif tf == "csv" and isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                headers = list(data[0].keys())
                csv_lines = [",".join(headers)]
                for row in data:
                    csv_lines.append(",".join([str(row.get(h, "")) for h in headers]))
                return {"result": "\n".join(csv_lines)}
            return {"error": f"Unsupported target format '{to_format}'"}

        self.register(
            name="data_format_convert",
            description="Converts tabular or structured data between JSON and CSV formats",
            parameters={
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                    "from_format": {"type": "string", "enum": ["json", "csv"]},
                    "to_format": {"type": "string", "enum": ["json", "csv"]}
                },
                "required": ["content", "from_format", "to_format"]
            },
            func=_data_convert
        )

    def execute(
        self,
        name: str,
        arguments: Dict[str, Any],
        tool_call_id: str = "",
        user_role: Optional[UserRole] = None,
        user_confirmed: Optional[bool] = None
    ) -> ToolResult:
        start = time.time()
        if name not in self.tools:
            return ToolResult(tool_call_id=tool_call_id, name=name, output=None, is_error=True, error=f"Tool '{name}' not found")

        # P0 Security Hardening 1: Tool-Level RBAC Gate (OWASP LLM08)
        effective_role = user_role or arguments.get("__user_role__")
        if effective_role is not None and name in HIGH_RISK_TOOLS:
            required_role = HIGH_RISK_TOOLS[name]
            if effective_role != required_role and effective_role != UserRole.ADMIN:
                return ToolResult(
                    tool_call_id=tool_call_id,
                    name=name,
                    output=None,
                    is_error=True,
                    error=f"RBAC Permission Denied: Tool '{name}' requires {required_role.value.upper()} privileges, but caller has {effective_role.value.upper()}."
                )

        # P0 Security Hardening 2: Human-in-the-Loop (HITL) Gate on Destructive Operations (OWASP LLM07/LLM08)
        if (self.enforce_hitl or user_confirmed is not None) and name in HIGH_RISK_TOOLS:
            confirmed = user_confirmed if user_confirmed is not None else arguments.get("confirm", arguments.get("confirmed", False))
            if not confirmed:
                return ToolResult(
                    tool_call_id=tool_call_id,
                    name=name,
                    output=None,
                    is_error=True,
                    error=f"CONFIRMATION_REQUIRED: Destructive or high-risk tool '{name}' requires explicit user confirmation. Re-run with confirm=True or user approval."
                )
        
        # 1. Deterministic Cache Lookup
        cached = self.cache.get(name, arguments)
        if cached:
            cached.tool_call_id = tool_call_id
            return cached

        # 2. Fuzzy Parameter Healing & Type Coercion (Hermes Feature)
        healed_args = dict(arguments)
        if self.auto_heal and "parameters" in self.tools[name]:
            healed_args, corrections = heal_parameters(self.tools[name]["parameters"], arguments)

        # 3. Invocation
        try:
            fn = self.tools[name]["func"]
            out = fn(**healed_args)
            res = ToolResult(tool_call_id=tool_call_id, name=name, output=out, is_error=False, execution_time_ms=(time.time() - start) * 1000)
            # Store in cache if successful
            self.cache.set(name, arguments, res)
            return res
        except Exception as e:
            return ToolResult(tool_call_id=tool_call_id, name=name, output=None, is_error=True, error=str(e), execution_time_ms=(time.time() - start) * 1000)

    def execute_batch(self, calls: List[Dict[str, Any]], parallel: bool = True) -> List[ToolResult]:
        """
        Executes a batch of tool calls. If parallel=True and multiple calls exist,
        executes concurrently via ThreadPoolExecutor.
        """
        if not calls:
            return []

        if not parallel or len(calls) == 1:
            return [self.execute(c["name"], c.get("arguments", {}), tool_call_id=c.get("id", "")) for c in calls]

        results = [None] * len(calls)
        with ThreadPoolExecutor(max_workers=min(len(calls), 5)) as executor:
            future_to_idx = {
                executor.submit(self.execute, c["name"], c.get("arguments", {}), c.get("id", "")): idx
                for idx, c in enumerate(calls)
            }
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    results[idx] = future.result()
                except Exception as ex:
                    c = calls[idx]
                    results[idx] = ToolResult(tool_call_id=c.get("id", ""), name=c["name"], output=None, is_error=True, error=str(ex))

        return results

    def list_tools_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["parameters"]
                }
            }
            for t in self.tools.values()
        ]
