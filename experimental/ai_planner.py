"""
ai_planner.py

Decision layer for AI reverse engineering agent.

Converts AI decisions into structured actions.

Supported actions:

- search
- get_function
- search_strings
- search_imports
- get_callers
- get_callees

The planner does not directly analyze binaries.
It decides what evidence to collect next.
"""


import json
import re



class AIPlanner:


    def __init__(
            self,
            tools):


        self.tools = tools



    # -------------------------------------------------
    # Parse AI response
    # -------------------------------------------------

    def parse_action(
            self,
            response):


        """
        Extract JSON action from model response.
        """


        try:


            return json.loads(

                response

            )


        except:


            match = re.search(

                r"\{.*\}",

                response,

                re.DOTALL

            )


            if match:


                return json.loads(

                    match.group()

                )



        return None



    # -------------------------------------------------
    # Execute action
    # -------------------------------------------------

    def execute(
            self,
            action):


        if not action:

            return {

                "error":

                    "No action supplied"

            }



        name = action.get(

            "action"

        )


        target = action.get(

            "target"

        )



        if name == "search":


            return self.tools.search(

                target

            )



        if name == "get_function":


            return self.tools.get_function(

                target

            )



        if name == "search_strings":


            return self.tools.search_strings(

                target

            )



        if name == "search_imports":


            return self.tools.search_imports(

                target

            )



        if name == "get_callers":


            return self.tools.get_callers(

                target

            )



        if name == "get_callees":


            return self.tools.get_callees(

                target

            )



        return {

            "error":

                "Unknown action"

        }



    # -------------------------------------------------
    # Build planner prompt
    # -------------------------------------------------

    def prompt(self):


        return """

You are a reverse engineering planning agent.

Your job is NOT to answer immediately.

Your job is to decide what evidence to collect.

Return ONLY JSON.

Format:

{
 "goal":"",
 "action":"",
 "target":"",
 "reason":""
}


Available actions:

search
get_function
search_strings
search_imports
get_callers
get_callees


Example:

{
 "goal":"Find login handler",
 "action":"search_strings",
 "target":"password",
 "reason":"Locate authentication indicators"
}

"""
