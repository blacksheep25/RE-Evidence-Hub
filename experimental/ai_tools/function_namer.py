import json
import os


NETWORK_APIS = {
    "connect": "Network_Connect",
    "socket": "Socket_Create",
    "send": "Network_Send",
    "recv": "Network_Receive",
    "recvfrom": "Network_ReceiveFrom",
    "sendto": "Network_SendTo",
    "htons": "Network_PortConvert",
    "WSAGetLastError": "Network_ErrorHandler"
}


class FunctionNamer:


    def __init__(self, export_path):

        self.export_path = export_path


    def analyze(self, fn):

        text = json.dumps(
            fn
        )


        name = fn.get(
            "name",
            ""
        )


        if not name.startswith(
            "FUN_"
        ):

            return name


        tags = []


        for api,label in NETWORK_APIS.items():

            if api in text:

                tags.append(
                    label
                )


        if tags:

            if "Network_Connect" in tags:

                if "Network_Receive" in tags:

                    return "NET_Client_Connection_Handshake"


                return "NET_Client_Connect"



            if "Network_Send" in tags:

                return "NET_Packet_Send"


            if "Network_Receive" in tags:

                return "NET_Packet_Receive"



        calls = fn.get(
            "calls",
            []
        )


        call_names = " ".join(
            [
                c.get("name","")
                for c in calls
                if isinstance(c,dict)
            ]
        )


        if "malloc" in call_names:

            return "MEM_Allocation"



        return name
