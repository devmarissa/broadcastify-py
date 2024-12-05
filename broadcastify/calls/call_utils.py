import requests
import random

from broadcastify.calls.Call import Call

def get_archived_calls(call_system: int, talkgroup: int, time_block: int, credential_key: str) -> tuple[list[Call], int, int]:
    # https://www.broadcastify.com/calls/apis/archivecall.php
    url = "https://www.broadcastify.com/calls/apis/archivecall.php"
    payload = {
        "group": f"{call_system}-{talkgroup}",
        "s": time_block
    }
    cookies = {
        "bcfyuser1": credential_key
    }
    with requests.get(url, params=payload, cookies=cookies) as response:
        if not response.ok:
            raise Exception(f"Failed to get archived calls - server error {response.status_code}")
        res_decoded = response.json()
        if "calls" not in res_decoded:
            raise Exception("Failed to get archived calls - calls key not found in response")
        
        start_time, end_time = res_decoded["start"], res_decoded["end"]

        return [Call(**call) for call in res_decoded["calls"]], start_time, end_time

def generate_session_token():
    return f"{random.randint(0,0xFFFFFFFF):08x}-{''.join(hex(random.randint(0,15) & 0x3 | 0x8)[2:] for _ in range(4))}"