"""
Interactive Terminal CLI for Mercury.
Supports rich slash commands, multi-personality hot-swapping, REPL,
System Doctor diagnostics, and Individual LLM Token Budget management.
"""
from __future__ import annotations
import sys, argparse
from mercurius.core.agent import MercuryOrchestrator
from mercurius.core.personalities import PersonalityLibrary
from mercurius.help.help import HelpSystem
from mercurius.doctor import run_doctor
from mercurius.llm.budget import BudgetTracker

def handle_budget_cmd(parts: list[str], tracker: BudgetTracker) -> str:
    if len(parts) <= 1 or parts[1] in ("list", "show"):
        budgets = tracker.list_llm_budgets()
        if not budgets:
            return "No LLM token budgets currently restricted (all LLMs have unlimited access)."
        lines = ["\n[Individual LLM Token Budgets]"]
        lines.append(f"{'LLM Model/Tier':<25} {'Limit':<12} {'Used':<12} {'Remaining':<12} {'Status':<10}")
        lines.append("-" * 75)
        for b in budgets:
            status = "BLOCKED" if b["is_blocked"] else "ACTIVE"
            rem = f"{b['remaining_tokens']:,}" if isinstance(b['remaining_tokens'], int) else str(b['remaining_tokens'])
            lines.append(f"{b['llm_id']:<25} {b['limit_display']:<12} {b['used_tokens']:<12,} {rem:<12} {status:<10}")
        return "\n".join(lines)

    subcmd = parts[1].lower()
    if subcmd == "set":
        if len(parts) < 4:
            return "Usage: /budget set <llm_id> <token_limit> (e.g. /budget set chatllm:gpt-4o 50000)"
        llm_id = parts[2]
        try: limit = int(parts[3])
        except ValueError: return "Error: token_limit must be an integer."
        b = tracker.set_llm_budget(llm_id, limit)
        return f"Budget set for '{llm_id}': Limit = {b.token_limit:,} tokens (Used: {b.used_tokens:,}). Blocked: {b.is_blocked}"

    if subcmd in ("overwrite", "unblock", "extend"):
        if len(parts) < 3:
            return "Usage: /budget overwrite <llm_id> [new_limit] (e.g. /budget overwrite chatllm:gpt-4o 100000)"
        llm_id = parts[2]
        new_lim = int(parts[3]) if len(parts) >= 4 and parts[3].isdigit() else None
        b = tracker.overwrite_llm_budget(llm_id, new_limit=new_lim)
        return f"Budget successfully OVERWRITTEN for '{llm_id}'! New Limit: {b.token_limit:,} tokens (Used: {b.used_tokens:,}). Requests UNBLOCKED."

    if subcmd == "reset":
        if len(parts) < 3:
            return "Usage: /budget reset <llm_id>"
        llm_id = parts[2]
        b = tracker.reset_llm_usage(llm_id)
        return f"Budget usage for '{llm_id}' reset to 0. Requests UNBLOCKED."

    return "Unknown budget command. Usage: /budget [list|set|overwrite|reset]"

def main():
    parser = argparse.ArgumentParser(description="Mercurius Agentic AI System")
    parser.add_argument("command", nargs="*", help="Initial prompt or command (e.g. doctor, budget, or prompt)")
    parser.add_argument("--interactive", "-i", action="store_true", help="Start interactive REPL")
    parser.add_argument("--personality", "-p", default="mercury_prime", help="Default personality")
    args = parser.parse_args()

    orchestrator = MercuryOrchestrator()
    budget_tracker = orchestrator.budget
    current_personality = PersonalityLibrary.get(args.personality)

    # Subcommand handling: mercurius doctor
    if args.command and args.command[0].lower() in ("doctor", "diagnose", "check"):
        run_doctor(verbose=True)
        return

    # Subcommand handling: mercurius budget ...
    if args.command and args.command[0].lower() == "budget":
        print(handle_budget_cmd(args.command, budget_tracker))
        return

    if args.command and not args.interactive:
        query = " ".join(args.command)
        print(f"\n[Mercurius Run]: {query}")
        ans = orchestrator.run_agent_session(session_id="cli_single", prompt=query, personality=current_personality)
        print(f"\n[Mercurius Response]:\n{ans}\n")
        return

    print("=" * 65)
    print(" 💠 Mercurius Agentic AI System (v2.0.0)")
    print(f" Active Personality: {current_personality.name} ({current_personality.tone})")
    print(" Commands: /doctor, /budget, /help, /tools, /personalities, /switch <name>, /exit")
    print("=" * 65)

    session_id = "cli_interactive"
    while True:
        try:
            prompt = input(f"\nmercurius [{current_personality.name}]> ").strip()
            if not prompt: 
                continue
            if prompt in ("/exit", "exit", "quit"): 
                break
            if prompt.startswith("/doctor"):
                run_doctor(verbose=True)
                continue
            if prompt.startswith("/budget"):
                parts = prompt.split()
                print(handle_budget_cmd(parts, budget_tracker))
                continue
            if prompt.startswith("/help"):
                parts = prompt.split()
                topic = parts[1] if len(parts) > 1 else "overview"
                print(f"\n{HelpSystem.get_topic(topic)}")
                continue
            if prompt == "/tools":
                print(f"\n{HelpSystem.get_topic('tools')}")
                continue
            if prompt == "/personalities":
                print(f"\n{HelpSystem.get_topic('personalities')}")
                continue
            if prompt in ("/clear", "clear"):
                import os
                os.system('cls' if os.name == 'nt' else 'clear')
                continue
            if prompt.startswith("/lang"):
                parts = prompt.split()
                if len(parts) > 1:
                    from mercurius.i18n.i18n import I18nEngine
                    i18n = I18nEngine(parts[1])
                    print(f"Language set to: {parts[1]}")
                else:
                    print("Usage: /lang <en|de|fr|es|zh|ja>")
                continue
            if prompt.startswith("/switch"):
                parts = prompt.split(maxsplit=1)
                if len(parts) > 1:
                    target = parts[1].strip()
                    current_personality = PersonalityLibrary.get(target)
                    print(f"\n[Switched to Personality]: {current_personality.name}")
                    print(f"Role: {current_personality.description}")
                else:
                    print("\nUsage: /switch <personality_name> (e.g. /switch software_architect)")
                continue

            resp = orchestrator.run_agent_session(
                session_id=session_id, 
                prompt=prompt,
                personality=current_personality
            )
            print(f"\n{resp}")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting Mercury.")
            break

if __name__ == "__main__":
    main()
