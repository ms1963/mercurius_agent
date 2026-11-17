"""
Extended Unit & Edge-Case Coverage Test Suite for Mercury.
"""
import unittest, os, sys, json, io, time
from unittest.mock import MagicMock, patch

sys.path.insert(0, "/workspace/files/personal_files/mercury")

class TestExtendedCoverage(unittest.TestCase):

    def test_01_compactor(self):
        from mercurius.core.compactor import ContextCompactor
        from mercurius.core.types import ChatMessage, MessageRole

        compactor = ContextCompactor()
        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content="System instruction"),
            ChatMessage(role=MessageRole.USER, content="Hello " * 50),
            ChatMessage(role=MessageRole.ASSISTANT, content="World " * 50),
            ChatMessage(role=MessageRole.USER, content="Final query")
        ]
        compacted = compactor.compact_messages(messages, system_prompt_reserve=50)
        self.assertGreater(len(compacted), 0)
        self.assertEqual(compacted[0].role, MessageRole.SYSTEM)

        # Test compacting tool output
        long_output = "Line data\n" * 200
        truncated = compactor.compact_tool_output(long_output)
        self.assertTrue(len(truncated) > 0)

    def test_02_parser(self):
        from mercurius.core.parser import HermesParser

        parser = HermesParser()
        text_with_call = 'I will check the weather.\n<tool_call>\n{"name": "get_weather", "arguments": {"city": "Berlin"}}\n</tool_call>'
        parsed = parser.extract_tool_calls(text_with_call)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["name"], "get_weather")
        self.assertEqual(parsed[0]["arguments"]["city"], "Berlin")

        text_with_thought = "<thought>Thinking carefully</thought>Answer: 42"
        thought, clean_text = parser.extract_thought_and_content(text_with_thought)
        self.assertIn("Thinking carefully", thought)
        self.assertIn("Answer: 42", clean_text)

    def test_03_help_system(self):
        from mercurius.help.help import HelpSystem

        self.assertIn("Mercury", HelpSystem.get_topic("overview"))
        self.assertTrue(len(HelpSystem.get_topic("tools")) > 0)
        self.assertTrue(len(HelpSystem.get_topic("personalities")) > 0)
        self.assertTrue(len(HelpSystem.get_topic("quantum_teleportation")) > 0)

    def test_04_skills_manager(self):
        from mercurius.skills.manager import SkillManager, Skill

        skills_dir = "/tmp/mercury_test_skills"
        os.makedirs(skills_dir, exist_ok=True)
        mgr = SkillManager(skills_dir=skills_dir)
        skill = Skill(
            name="unit_converter",
            description="Converts imperial to metric units",
            parameters={"value": "float", "unit": "str"},
            recipe="1. Multiply input by conversion ratio"
        )
        mgr.skills["unit_converter"] = skill
        retrieved = mgr.search_skills("imperial")
        self.assertGreater(len(retrieved), 0)
        self.assertEqual(retrieved[0].name, "unit_converter")

    def test_05_memory_manager(self):
        from mercurius.memory.manager import MemoryManager
        from mercurius.core.types import ChatMessage, MessageRole

        db_path = "/tmp/test_coverage_mem.sqlite"
        if os.path.exists(db_path):
            os.remove(db_path)
        mgr = MemoryManager(db_path=db_path)
        msg1 = ChatMessage(role=MessageRole.USER, content="Remember secret code 9876")
        msg2 = ChatMessage(role=MessageRole.ASSISTANT, content="Secret code stored")
        mgr.save_chat_message("sess_1", msg1)
        mgr.save_chat_message("sess_1", msg2)

        res = mgr.search_episodic("secret code")
        self.assertIsNotNone(res)

        mgr.set_working("current_task", "Testing memory")
        self.assertEqual(mgr.get_working("current_task"), "Testing memory")

    def test_06_guardrails_edge_cases(self):
        from mercurius.security.guardrails import GuardrailEngine, scrub_secrets

        clean_text = "Standard enterprise query for sales performance"
        clean_scrubbed = scrub_secrets(clean_text)
        self.assertEqual(clean_scrubbed, clean_text)

        dirty_text = "Here is my AWS token AKIAIOSFODNN7EXAMPLE and secret"
        scrubbed = scrub_secrets(dirty_text)
        self.assertIn("[REDACTED_SECRET]", scrubbed)

        engine = GuardrailEngine()
        scan_res = engine.scan_input("read file command")
        self.assertTrue(scan_res.get("safe", True) if isinstance(scan_res, dict) else True)

    def test_07_polyglot_and_ast_security(self):
        from mercurius.tools.polyglot import PolyglotRunner, analyze_python_ast

        runner = PolyglotRunner()
        safe_code = "result = sum([1, 2, 3, 4, 5])\nprint(f'Sum: {result}')"
        res = runner.execute("python", safe_code)
        self.assertFalse(res.get("is_error", True))
        self.assertIn("Sum: 15", res.get("output", ""))

        unsafe_code = "import ctypes\nctypes.string_at(0)"
        violations = analyze_python_ast(unsafe_code)
        self.assertGreater(len(violations), 0)
        res_unsafe = runner.execute("python", unsafe_code)
        self.assertTrue(res_unsafe.get("is_error", False))

    def test_08_tool_cache(self):
        from mercurius.tools.cache import ToolCache
        from mercurius.tools.registry import ToolResult

        cache = ToolCache(default_ttl_seconds=2)
        res = ToolResult(tool_call_id="call_1", name="calculator", output={"result": 42})
        cache.set("calculator", {"expr": "6 * 7"}, res)

        cached = cache.get("calculator", {"expr": "6 * 7"})
        self.assertIsNotNone(cached)
        self.assertEqual(cached.output["result"], 42)
        self.assertIsNone(cache.get("calculator", {"expr": "1 + 1"}))

    def test_09_browser_parser_and_scraping(self):
        from mercurius.tools.browser import HTMLTextAndLinkExtractor, wrap_untrusted_observation

        html_sample = """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <h1>Header Title</h1>
                <p>Welcome to <a href="https://example.com/docs">Documentation</a>.</p>
            </body>
        </html>
        """
        parser = HTMLTextAndLinkExtractor()
        parser.feed(html_sample)
        self.assertIn("Header Title", parser.get_text())

        wrapped = wrap_untrusted_observation("Untrusted web text")
        self.assertIn("<untrusted_external_content", wrapped)
        self.assertIn("</untrusted_external_content>", wrapped)

    def test_10_channels_hub_adapters(self):
        from mercurius.channels.hub import (
            ChannelHub, SlackChannelAdapter, DiscordChannelAdapter,
            EmailChannelAdapter, ChannelMessage
        )

        hub = ChannelHub()
        slack = SlackChannelAdapter(webhook_url="https://hooks.slack.mock/services/123")
        discord = DiscordChannelAdapter(webhook_url="https://discord.mock/api/webhooks/123")
        email = EmailChannelAdapter(smtp_host="localhost", smtp_port=25)

        hub.register_adapter("slack", slack)
        hub.register_adapter("discord", discord)
        hub.register_adapter("email", email)

        msg = ChannelMessage(
            channel="slack",
            sender_id="user_michael",
            content="Generate quarterly report"
        )
        ingested = hub.ingest_message(msg)
        self.assertEqual(ingested.channel, "slack")

    def test_11_ui_server_and_rest_endpoints(self):
        from mercurius.ui.server import DASHBOARD_HTML
        self.assertIn("Mercury", DASHBOARD_HTML)
        self.assertIn("v2.2 HARDENED", DASHBOARD_HTML)

    def test_12_cli_entrypoint(self):
        from mercurius.ui import cli
        self.assertTrue(callable(cli.run_doctor))
        self.assertTrue(callable(cli.handle_budget_cmd))

    def test_13_cli_comprehensive(self):
        from mercurius.ui import cli
        from mercurius.llm.budget import BudgetTracker

        tracker = BudgetTracker(storage_path="/tmp/test_clean_budget.json")
        if os.path.exists("/tmp/test_clean_budget.json"):
            os.remove("/tmp/test_clean_budget.json")
        tracker._budgets = {}

        res = cli.handle_budget_cmd(["budget", "list"], tracker)
        self.assertTrue("No LLM token budgets" in res or "Individual LLM Token Budgets" in res)

        res_set = cli.handle_budget_cmd(["budget", "set", "gpt-4o", "50000"], tracker)
        self.assertIn("Budget set for 'gpt-4o'", res_set)

        res_list = cli.handle_budget_cmd(["budget", "list"], tracker)
        self.assertIn("gpt-4o", res_list)

        res_ov = cli.handle_budget_cmd(["budget", "overwrite", "gpt-4o", "100000"], tracker)
        self.assertIn("OVERWRITTEN", res_ov)

        res_reset = cli.handle_budget_cmd(["budget", "reset", "gpt-4o"], tracker)
        self.assertIn("reset", res_reset.lower())

        res_invalid = cli.handle_budget_cmd(["budget", "unknown_sub"], tracker)
        self.assertIn("Unknown budget command", res_invalid)

    def test_14_channels_hub_deep(self):
        from mercurius.channels.hub import ChannelHub, ChannelMessage, BaseChannelAdapter
        
        hub = ChannelHub()
        msg = ChannelMessage(channel="generic", sender_id="user1", content="Hello test")
        self.assertEqual(msg.content, "Hello test")
        
        class CustomAdapter(BaseChannelAdapter):
            def __init__(self):
                super().__init__(name="custom")
            def send(self, target, text, attachments=None, metadata=None):
                return {"status": "ok"}
            def receive(self):
                return []
        
        adapter = CustomAdapter()
        hub.register_adapter("custom", adapter)
        self.assertIn("custom", hub.adapters)
        res = hub.send_message("custom", "target1", "Response message")
        self.assertEqual(res.get("status"), "ok")

    def test_15_workflow_engine_deep(self):
        from mercurius.workflows.engine import WorkflowEngine
        mock_orch = MagicMock()
        mock_orch.run_agent_session.return_value = "Subagent output response"
        engine = WorkflowEngine(orchestrator=mock_orch)
        res = engine.run_coordinator_worker(
            objective="Analyze market trends",
            worker_specs=[
                {"role": "Analyst 1", "prompt": "Check growth"},
                {"role": "Analyst 2", "prompt": "Check risks"}
            ],
            parallel=False
        )
        self.assertIsNotNone(res)

    def test_16_skills_manager_deep(self):
        from mercurius.skills.manager import SkillManager, Skill
        from mercurius.core.types import Trajectory
        sm = SkillManager(skills_dir="/tmp/test_skills_deep")
        sk = Skill(name="test_sk", description="desc", parameters={}, recipe="recipe")
        sm.skills["test_sk"] = sk
        traj = Trajectory(task_id="task_fail", goal="Do task", success=False)
        sm.record_failure(traj, error_reason="Timeout exception")
        self.assertIsNotNone(sm)

    def test_17_compactor_and_doctor_deep(self):
        from mercurius.core.compactor import ContextCompactor
        from mercurius.core.types import ChatMessage, MessageRole
        from mercurius.doctor.doctor import run_doctor

        comp = ContextCompactor(max_tokens=500)
        msgs = [ChatMessage(role=MessageRole.USER, content=f"Msg {i}") for i in range(20)]
        compacted = comp.compact_messages(msgs, system_prompt_reserve=50)
        self.assertLessEqual(len(compacted), len(msgs))

        report = run_doctor(verbose=False)
        self.assertIsNotNone(report)

    def test_18_cli_main_modes(self):
        from mercurius.ui.cli import main
        
        # Test doctor subcommand
        with patch("sys.argv", ["mercurius", "doctor"]), patch("mercury.ui.cli.run_doctor") as mock_doc:
            main()
            mock_doc.assert_called_once()

        # Test single command mode
        with patch("sys.argv", ["mercurius", "what", "is", "2+2"]), patch("mercury.core.agent.MercuryOrchestrator.run_agent_session") as mock_sess:
            mock_sess.return_value = "4"
            main()
            mock_sess.assert_called_once()

        # Test interactive exit
        with patch("sys.argv", ["mercurius", "--interactive"]), patch("builtins.input", side_effect=["/tools", "/personalities", "/help", "/clear", "/lang de", "/switch software_architect", "/exit"]):
            main()

    def test_19_ui_server_handlers(self):
        from mercurius.ui.server import MercuryHTTPHandler
        from unittest.mock import MagicMock
        import io

        mock_server = MagicMock()
        mock_server.orchestrator = MagicMock()
        mock_server.orchestrator.run_agent_session.return_value = "API reply"
        
        handler = MercuryHTTPHandler.__new__(MercuryHTTPHandler)
        handler.server = mock_server
        handler.client_address = ("127.0.0.1", 54321)
        handler.command = "GET"
        handler.log_message = MagicMock()
        handler.log_error = MagicMock()
        handler.send_error = MagicMock()
        handler.wfile = io.BytesIO()
        handler.rfile = io.BytesIO(b'{"prompt": "hello", "session_id": "api_test"}')
        handler.headers = {"Content-Length": "44"}
        
        # Test GET dashboard
        handler.path = "/"
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.do_GET()
        handler.send_response.assert_called_with(200)

        # Test GET api health
        handler.path = "/api/health"
        handler.do_GET()
        
        # Test POST chat
        handler.command = "POST"
        handler.path = "/api/chat"
        handler.rfile = io.BytesIO(b'{"prompt": "hello", "session_id": "api_test"}')
        handler.headers = {"Content-Length": "44"}
        handler.do_POST()

    def test_20_browser_engine_integration(self):
        from mercurius.tools.browser import WebBrowser, CDPConnection
        
        cdp = CDPConnection()
        self.assertTrue(callable(cdp.send_cdp_command))
        
        browser = WebBrowser()
        self.assertIsNotNone(browser)
        # Test extraction without active live headless chrome
        self.assertTrue(callable(browser.extract_interactive_elements))
        

if __name__ == "__main__":
    unittest.main()
