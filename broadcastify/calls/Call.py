class Call:
    def __init__(self, **kwargs):
        self.talkgroup: int    # talkgroup ID
        self.duration: int     # call duration in seconds
        self.start_time: int   # call start time in unix timestamp
        self.filename: str     # call filename on Broadcastify CDN
        self.tg_name: str      # talkgroup name
        self.tg_group: str     # talkgroup group (e.g Fire, Police, EMS)
        self.system_id: int    # system ID
        self.unit_radioid: int # unit radio ID
        self.hash: str         # call hash

        kv_map = {
            "call_tg": "talkgroup",
            "call_duration": "duration",
            "ts": "start_time",
            "filename": "filename",
            "display": "tg_name",
            "grouping": "tg_group",
            "systemId": "system_id",
            "call_src": "unit_radioid",
            "hash": "hash"  
        }
        for k, v in kwargs.items():
            if k not in kv_map:
                continue
            setattr(self, kv_map[k], v)

    def get_media_url(self) -> str:
        return f"https://calls.broadcastify.com/{self.hash}/{self.system_id}/{self.filename}.mp3"

    def __repr__(self) -> str:
        return f"Call(tg={self.talkgroup}, dur={self.duration}s, start_time={self.start_time}, fn={self.filename}, tg_name={self.tg_name}, tg_group={self.tg_group}, sys_id={self.system_id}, unit_id={self.unit_radioid})"