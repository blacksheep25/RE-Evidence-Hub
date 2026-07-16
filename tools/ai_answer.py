import json


class AIAnswer:


    def __init__(
        self,
        hybrid
    ):

        self.hybrid = hybrid



    def ask(
        self,
        question
    ):

        context = self.hybrid.context(
            question
        )


        answer = []

        answer.append(
            "===== AI BINARY ANALYSIS ANSWER ====="
        )


        answer.append(
            "\nQuestion:\n" +
            question
        )


        answer.append(
            "\nFindings:"
        )


        # Keep context size manageable

        answer.append(
            context[:12000]
        )


        return "\n".join(
            answer
        )
