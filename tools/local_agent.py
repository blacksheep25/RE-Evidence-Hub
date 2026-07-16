"""Compatibility entry point for the evidence-backed interactive agent."""

from __future__ import annotations

import sys

try:
    from tools.tool_agent import ToolAgent
except ImportError:
    from tool_agent import ToolAgent


class LocalAgent(ToolAgent):
    """Older name retained for scripts that still invoke local_agent.py."""


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("""
Usage:

python tools/local_agent.py <export folder> <api url> <model>

Example:

python tools/local_agent.py %USERPROFILE%\\ghidra_ai_exports\\sample_program.exe http://localhost:11434/api/chat llama3
""")
        sys.exit(1)

    agent = LocalAgent(sys.argv[1], sys.argv[2], sys.argv[3])
    while True:
        question = input("\n> ")
        if question.lower() == "exit":
            break
        agent.ask(question)
