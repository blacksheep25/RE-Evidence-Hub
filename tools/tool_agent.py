"""Interactive reverse-engineering agent with evidence-backed tools."""

from __future__ import annotations

import json
import sys

import requests

try:
    from tools.evidence_tools import EvidenceTools
    from tools.investigation_memory import InvestigationMemory
except ImportError:
    from evidence_tools import EvidenceTools
    from investigation_memory import InvestigationMemory


class ToolAgent:
    def __init__(self, export_path, api_url, model):
        self.export_path = export_path
        self.api_url = api_url
        self.model = model
        self.tools = EvidenceTools(export_path)
        self.memory = InvestigationMemory(export_path)

    def tool_definitions(self):
        return self.tools.tool_definitions()

    def execute_tool(self, name, args):
        return self.tools.execute_tool(name, args)

    def system_prompt(self):
        return """
You are an expert reverse engineer working from a Ghidra static-analysis export.

Use tools before conclusions. Prefer lookup over bare function reads because it
returns accepted annotations, raw names, concrete evidence, and relationships.
Accepted annotations are active semantic names; raw FUN_* names are only Ghidra
identifiers. Asset/control/packet and semantic results are leads until concrete
evidence confirms them.

When you need evidence, return ONLY JSON in this shape:
{"tool":"lookup","arguments":{"address":"00401000"}}

When you have enough evidence, answer normally with addresses, evidence,
confidence, and whether each semantic name is accepted or raw.

Available tools:
{}

Previous investigation:
{}
""".format(
            json.dumps(self.tool_definitions(), indent=2),
            self.memory.context(),
        )

    def call_model(self, messages):
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
        }
        response = requests.post(self.api_url, json=payload, timeout=300)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _message_content(response):
        if "message" in response:
            return response["message"].get("content", "")
        choices = response.get("choices") or []
        if choices:
            return choices[0].get("message", {}).get("content", "")
        return ""

    @staticmethod
    def _tool_request(content):
        try:
            action = json.loads(content)
        except json.JSONDecodeError:
            return None
        if isinstance(action, dict) and "tool" in action:
            return action
        return None

    def ask(self, question):
        messages = [
            {"role": "system", "content": self.system_prompt()},
            {"role": "user", "content": question},
        ]

        while True:
            response = self.call_model(messages)
            content = self._message_content(response)
            print()
            print(content)

            action = self._tool_request(content)
            if not action:
                return content

            result = self.execute_tool(action["tool"], action.get("arguments", {}) or {})
            messages.append({"role": "assistant", "content": content})
            messages.append({"role": "tool", "content": json.dumps(result, ensure_ascii=False)})


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("""
Usage:

python tools/tool_agent.py <export folder> <api url> <model>

Example:

python tools/tool_agent.py %USERPROFILE%\\ghidra_ai_exports\\sample_program.exe http://localhost:11434/api/chat llama3
""")
        sys.exit(1)

    agent = ToolAgent(sys.argv[1], sys.argv[2], sys.argv[3])
    while True:
        question = input("\n> ")
        if question.lower() == "exit":
            break
        agent.ask(question)
