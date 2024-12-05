import datetime
import requests
import pickle
import os

from broadcastify.utility import floor_dt, floor_dt_s
from broadcastify.calls import Call, LiveCalls, get_archived_calls

class Client:
    def __init__(self, **kwargs):
        self.config = {
            "username": None,
            "password": None,
            "credential_key": None,
            "auto_logout": True,
            "save_cache": True,
            "cache_dir": ".bc_cache",
            "cache_expire": datetime.timedelta(days=1),
            **kwargs
        }
        self.cache = {}
        self.__load_cache()

        self.logged_in = self.config["credential_key"] is not None

    def __cache_archives(self, call_system: int, talkgroup: int, time_block: int, calls: list[Call], start_time: int, end_time: int):
        if call_system not in self.cache:
            self.cache[call_system] = {}
        if talkgroup not in self.cache[call_system]:
            self.cache[call_system][talkgroup] = {}
        self.cache[call_system][talkgroup][time_block] = {
            "calls": calls,
            "start_time": start_time,
            "end_time": end_time
        }
    
    def __get_cached_archives(self, call_system: int, talkgroup: int, time_block: int) -> tuple[list[Call], int, int]:
        if call_system not in self.cache:
            return None
        if talkgroup not in self.cache[call_system]:
            return None
        if time_block not in self.cache[call_system][talkgroup]:
            return None
        data = self.cache[call_system][talkgroup][time_block]

        return data["calls"], data["start_time"], data["end_time"]

    def __load_cache(self):
        if not self.config["save_cache"]:
            return
        
        os.makedirs(self.config["cache_dir"], exist_ok=True)

        cache_file = os.path.join(self.config["cache_dir"], "cache.pickle")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "rb") as f:
                    self.cache = pickle.load(f)
            except Exception as e:
                print(f"Failed to load cache: {e}")
        
        # Check if cache has expired
        if "cache_expire" in self.cache:
            if self.cache["cache_expire"] < datetime.datetime.now():
                self.cache = {}
                self.__save_cache()
    
    def __save_cache(self):
        if not self.config["save_cache"]:
            return
        
        if "cache_expire" not in self.cache:
            self.cache["cache_expire"] = datetime.datetime.now() + self.config["cache_expire"]
        
        os.makedirs(self.config["cache_dir"], exist_ok=True)
        cache_file = os.path.join(self.config["cache_dir"], "cache.pickle")
        with open(cache_file, "wb") as f:
            pickle.dump(self.cache, f)

    def login(self):
        if self.logged_in:
            return
        
        url = "https://www.broadcastify.com/login/"
        payload = {
            "username": self.config["username"],
            "password": self.config["password"],
            "action": "auth",
            "redirect": "https://www.broadcastify.com"
        }
        with requests.post(url, data=payload, allow_redirects=False) as response:
            if not response.ok:
                # Login failed by server error
                raise Exception(f"Login failed - server error {response.status_code}")
            with open("login.html", "w") as f:
                f.write(response.text)
            location_header = response.headers.get("Location")
            if "failed=1" in location_header:
                # Login failed by incorrect credentials
                raise Exception("Login failed - incorrect credentials")
            if "Set-Cookie" not in response.headers:
                # Login failed by unknown error
                print(response.headers)
                raise Exception("Login failed - unknown error")
            
            cookies = response.headers.get("Set-Cookie").rstrip().split("; ")
            if not "bcfyuser1" in cookies[0]:
                raise Exception("Login failed - unknown error (bcfyuser cookie not found)")
            
            self.logged_in = True
            self.config["credential_key"] = cookies[0].split("=")[1]

    def logout(self):
        if not self.logged_in:
            return
        
        url = "https://www.broadcastify.com/account/?action=logout"
        cookies = {
            "bcfyuser1": self.config["credential_key"]
        }
        with requests.get(url, cookies=cookies) as response:
            if not response.ok:
                raise Exception(f"Logout failed - server error {response.status_code}")
    
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.config["auto_logout"]:
            self.logout()
            self.logged_in = False
            self.credential_key = None
        if self.config["save_cache"]:
            self.__save_cache()
    
    def get_archived_calls(self, call_system: int, talkgroup: int, time_block: int) -> tuple[list[Call], int, int]:
        if not self.logged_in:
            raise Exception("Not logged in")
        
        # Round time block to nearest 30 minutes
        time_block = floor_dt_s(time_block, datetime.timedelta(minutes=30))

        # Check if calls are cached
        if cached := self.__get_cached_archives(call_system, talkgroup, time_block):
            return cached
        
        # Get archived calls and cache them
        calls, st, et = get_archived_calls(call_system, talkgroup, time_block, self.config["credential_key"])
        self.__cache_archives(call_system, talkgroup, time_block, calls, st, et)
        return calls, st, et

    def get_livecall_session(self, call_system: int, talkgroup: int, **kwargs) -> LiveCalls:
        if not self.logged_in:
            raise Exception("Not logged in")
        
        return LiveCalls(call_system, talkgroup, self.config["credential_key"], **kwargs)