import datetime
import requests

from broadcastify.calls.Call import Call
from broadcastify.calls.call_utils import generate_session_token

class LiveCalls:
    def __init__(self, call_system, talkgroup, session_token, **kwargs) -> None:
        self.config = {
            "call_system": call_system,
            "talkgroup": talkgroup,
            "credential_key": session_token,
            "session_token": generate_session_token(),
            "position": datetime.datetime.now().timestamp(),
            **kwargs
        }
        self.calls = []
        self.hooks = {}
        self.session_initalized = False
    
    def on(self, event: str, callback: function) -> None:
        if event not in self.hooks:
            self.hooks[event] = []
        self.hooks[event].extend(callback)

    def _invoke(self, event: str, *args, **kwargs) -> None:
        if event not in self.hooks:
            return
        for hook in self.hooks[event]:
            hook(*args, **kwargs)

    def __make_livecall_request(self, payload) -> None:
        cookies = {
            "bcfyuser1": self.config["credential_key"]
        }
        with requests.post("https://www.broadcastify.com/calls/apis/live-calls", data=payload, cookies=cookies) as response:
            if not response.ok:
                raise Exception(f"Failed to get live calls - server error {response.status_code}")
            return response.json()
    
    def __invoke_poll(self, init=0) -> list[Call]:
        if not self.session_initalized and init == 0:
            raise Exception("Session not initialized")

        payload = {
            "groups[]": f"{self.config['call_system']}-{self.config['talkgroup']}",
            "pos": self.config["position"],
            "doInit": init,
            "systemId": 0,
            "sid": 0,
            "sessionKey": self.config["session_token"]
        }
        res = self.__make_livecall_request(payload)
        delta_calls = [Call(**call) for call in res["calls"]]
        self.calls.extend(delta_calls)
        self._invoke("update", delta_calls)
        last_call = delta_calls[-1]
        self.config["position"] = last_call.start_time + 1
        return delta_calls
    
    def init_session(self) -> list[Call]:
        calls = self.__invoke_poll(init=1)
        self.session_initalized = True
        return calls

    def poll(self) -> list[Call]:
        return self.__invoke_poll()