"""
title: Ghidra Binary Analyst
author: local
version: 0.1.0
description: Connects Ollama to exported Ghidra analysis data
"""


class Function:

    class Valves:
        GHIDRA_EXPORT_PATH = "X:/ghidra_exports"


    def __init__(self):
        self.name = "ghidra_binary_analyst"
        self.valves = self.Valves()


    async def pipe(
        self,
        body: dict,
        __user__: dict
    ):

        messages = body.get("messages", [])

        if not messages:
            return "No message received."

        user_message = messages[-1]["content"]

        return f"""
You are a reverse engineering assistant.

You have access to a Ghidra exported binary dataset.

Available:
- Decompiled functions
- Assembly
- Imports
- Exports
- Strings
- Call graph
- Datatypes
- Globals
- Memory map

User request:

{user_message}

Analyze the binary using reverse engineering techniques.
"""
