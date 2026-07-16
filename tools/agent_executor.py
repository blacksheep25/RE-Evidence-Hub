"""
agent_executor.py

Executes AI planned investigations.

Flow:

1. Receive AI action
2. Execute tool
3. Return evidence
4. Repeat
"""


import json


from ai_planner import AIPlanner



class AgentExecutor:


    def __init__(
            self,
            tools):


        self.tools = tools

        self.planner = AIPlanner(

            tools

        )



    # -------------------------------------------------
    # Run one step
    # -------------------------------------------------

    def step(
            self,
            ai_response):


        action = self.planner.parse_action(

            ai_response

        )


        if not action:


            return {

                "error":

                    "Invalid AI action"

            }



        evidence = self.planner.execute(

            action

        )



        return {


            "action":

                action,


            "evidence":

                evidence

        }



    # -------------------------------------------------
    # Format evidence
    # -------------------------------------------------

    def summarize(
            self,
            result):


        return json.dumps(

            result,

            indent=2

        )
