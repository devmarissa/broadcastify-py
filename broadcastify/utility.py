from datetime import datetime, timedelta

def floor_dt(dt: int, delta: timedelta) -> datetime:
    dt = datetime.fromtimestamp(dt)
    return dt - (dt - datetime.min) % delta

def floor_dt_s(dt: int, delta: timedelta) -> int:
    return floor_dt(dt, delta).timestamp()
