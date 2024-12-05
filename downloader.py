import broadcastify
import datetime
import requests
import inquirer
import whisper
import tqdm
import os

from pprint import pprint
from broadcastify.utility import floor_dt

def format_unix_timestamp(unix_timestamp: int) -> str:
    return datetime.datetime.fromtimestamp(unix_timestamp).strftime("%Y-%m-%d %H:%M:%S")

def download_file(url, directory=".", chunk_size=8192):
    # Construct local path
    local_filename = url.split('/')[-1]
    local_path = os.path.join(directory, local_filename)

    # Create directory if it doesn't exist
    os.makedirs(directory, exist_ok=True)

    # Download file
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                f.write(chunk)
    return local_path

def prompt_default(prompt, default_val):
    val = input(f"{prompt} [{default_val}]: ")
    if not val:
        return default_val
    return val

def iq_day_query() -> inquirer.Text:
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    return inquirer.Text("day", message="Enter day in YYYY-MM-DD format", default=today)

def iq_time_block_query() -> inquirer.List:
    options = []
    for i in range(0, 48):
        mins = i * 30
        options.append(f"{mins // 60:02}:{mins % 60:02} --> {(mins + 29) // 60:02}:{(mins + 29) % 60:02}")
    now = datetime.datetime.now()
    closest_time_block = floor_dt(now.timestamp(), datetime.timedelta(minutes=30))
    closest_time_block_offset = (closest_time_block + datetime.timedelta(minutes=29))
    default_time_block = closest_time_block.strftime("%H:%M") + " --> " + closest_time_block_offset.strftime("%H:%M")

    return inquirer.List("time_block", message="Select time block", choices=options, default=default_time_block)

def time_block_and_day_to_seconds(day: str, time_block: str) -> int:
    day_formatted = datetime.datetime.strptime(day, "%Y-%m-%d")

    time_block = time_block.split(" --> ")[0]
    hours, mins = map(int, time_block.split(":")[0:2])
    seconds = (hours * 60 + mins) * 60
    return day_formatted.timestamp() + seconds

def prompt_settings() -> tuple[int, int, int]:
    options = [
        inquirer.Text("call_system", message="Enter call system ID", default=7804),
        inquirer.Text("talkgroup", message="Enter talkgroup ID", default=2451),
        iq_day_query(),
        iq_time_block_query()
    ]

    answers = inquirer.prompt(options)
    call_system = int(answers["call_system"])
    talkgroup = int(answers["talkgroup"])
    day = answers["day"]
    time_block = answers["time_block"]

    time_block = time_block_and_day_to_seconds(day, time_block)

    return call_system, talkgroup, int(time_block)

def main():
    cred_key = None
    if os.path.exists("broadcastify_creds.txt"):
        cred_key = open("broadcastify_creds.txt", "r").read()

    username, password = open("login.txt", "r").read().rstrip().split(":")

    client = broadcastify.Client(
        username=username,
        password=password,
        credential_key=cred_key,
        auto_logout=False
    )
    client.login()
    with open("broadcastify_creds.txt", "w") as f:
        f.write(client.config["credential_key"])

    with client:
        calls, start_time, end_time = client.get_archived_calls(*prompt_settings())
        print(f"Start time: {format_unix_timestamp(start_time)}")
        print(f"End time: {format_unix_timestamp(end_time)}")

        calls_dir = "calls"

        for call in calls:
            if os.path.exists(os.path.join(calls_dir, f"{call.filename}.mp3")):
                print(f"Call {call.filename} already downloaded, skipping...")
                continue
            print(f"Downloading call: {call}...")
            try:
                download_file(call.get_media_url(), calls_dir)
            except requests.exceptions.HTTPError as e:
                print(f"Failed to download call {call.filename}: {e}")
                continue
    
    print("Transcribing calls...")
    model = whisper.load_model("medium.en")
    
    if not os.path.exists("transcriptions.txt"):
        with open("transcriptions.txt", "w") as f:
            f.write(f"Transcriptions for calls from {format_unix_timestamp(start_time)} to {format_unix_timestamp(end_time)} - Talkgroup {calls[0].tg_name}\n")

    with open("transcriptions.txt", "a") as f:
        last_call_id: int
        skip = 0
        try:
            # Skip to last call ID if it exists
            if os.path.exists("last_call_id.txt"):
                skip = int(open("last_call_id.txt", "r").read())

            # Transcribe calls
            with tqdm.tqdm(total=len(calls), ncols=80) as pbar:
                for last_call_id, call in enumerate(calls):
                    pbar.update(1)
                    if last_call_id <= skip:
                        continue

                    call_path = os.path.join(calls_dir, f"{call.filename}.mp3")
                    transcripton = model.transcribe(call_path, fp16=False, language="en")
                    f.write(f"{format_unix_timestamp(call.start_time)} (RadioID {call.unit_radioid}): {transcripton['text']}\n")
                    f.flush()

        except KeyboardInterrupt:
            print("Transcription interrupted")
            with open("last_call_id.txt", "w") as f:
                f.write(str(last_call_id))

if __name__ == "__main__":
    main()