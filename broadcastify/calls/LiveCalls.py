import datetime
import requests

from broadcastify.calls.Call import Call
from broadcastify.calls.call_utils import generate_session_token

class LiveCalls:
    def __init__(self, call_system, talkgroup, credential_key, **kwargs) -> None:
        self.config = {
            "call_system": call_system,
            "talkgroup": talkgroup,
            "credential_key": credential_key,
            "session_token": generate_session_token(),
            "position": datetime.datetime.now().timestamp(),
            **kwargs
        }
        self.calls = []
        self.hooks = {}
        self.session_initalized = False
    
    def on(self, event: str, callback) -> None:
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
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "en-US,en;q=0.5",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": "https://www.broadcastify.com",
            "Referer": f"https://www.broadcastify.com/calls/tg/{self.config['call_system']}/{self.config['talkgroup']}",
        }
        print(f"Making request with payload: {payload}")
        print(f"Using credential key: {self.config['credential_key']}")
        
        # First, try to load the talkgroup page to get any necessary tokens
        with requests.get(
            f"https://www.broadcastify.com/calls/tg/{self.config['call_system']}/{self.config['talkgroup']}", 
            cookies=cookies,
            headers=headers
        ) as response:
            if not response.ok:
                print(f"Failed to load talkgroup page: {response.status_code}")
                print(response.text)
        
        # Now make the actual API request
        with requests.post(
            f"https://www.broadcastify.com/calls/ajax/update", 
            data=payload, 
            cookies=cookies,
            headers=headers
        ) as response:
            if not response.ok:
                print(f"Response headers: {response.headers}")
                print(f"Response content: {response.text}")
                raise Exception(f"Failed to get live calls - server error {response.status_code}")
            return response.json()
    
    def __invoke_poll(self, init=0) -> list[Call]:
        if not self.session_initalized and init == 0:
            raise Exception("Session not initialized")

        payload = {
            "systemId": self.config['call_system'],
            "talkgroupId": self.config['talkgroup'],
            "lastUpdate": str(int(self.config["position"])),
            "mode": "gettalkgroups" if init == 1 else "getupdate"
        }
        print(f"Polling with config: {self.config}")
        res = self.__make_livecall_request(payload)
        print(f"Received response: {res}")
        if "calls" in res:
            delta_calls = [Call(**call) for call in res["calls"]]
            print(f"Extracted {len(delta_calls)} calls")
            self.calls.extend(delta_calls)
            self._invoke("update", delta_calls)
            if delta_calls:
                last_call = delta_calls[-1]
                if hasattr(last_call, 'start_time'):
                    self.config["position"] = last_call.start_time
        return self.calls

    def init_session(self) -> list[Call]:
        calls = self.__invoke_poll(init=1)
        self.session_initalized = True
        return calls

    def poll(self) -> list[Call]:
        return self.__invoke_poll()