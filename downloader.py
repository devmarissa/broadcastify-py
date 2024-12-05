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

def prompt_settings_archive() -> int:
    options = [
        iq_day_query(),
        iq_time_block_query()
    ]
    answers = inquirer.prompt(options)

    day = answers["day"]
    time_block = answers["time_block"]
    time_block = time_block_and_day_to_seconds(day, time_block)
    return int(time_block)

def prompt_initial_settings() -> tuple[int, int]:
    options = [
        inquirer.Text("call_system", message="Enter call system ID", default=7804),
        inquirer.Text("talkgroup", message="Enter talkgroup ID", default=2451),
        inquirer.List("calls_type", message="Pull data from", choices=["Live Calls", "Archived Calls"]),
        inquirer.Confirm("do_transcribe", message="Transcribe calls", default=False)
    ]

    answers = inquirer.prompt(options)
    call_system = int(answers["call_system"])
    talkgroup = int(answers["talkgroup"])
    
    return call_system, talkgroup, answers["calls_type"], answers["do_transcribe"]

def handle_archives(client: broadcastify.Client, call_system, talkgroup, time_block) -> tuple[list[broadcastify.calls.Call], int, int]:
    with client:
        calls, start_time, end_time = client.get_archived_calls(call_system, talkgroup, time_block)
        print(f"Start time: {format_unix_timestamp(start_time)}")
        print(f"End time: {format_unix_timestamp(end_time)}")
        return calls, start_time, end_time

def handle_live(client: broadcastify.Client, call_system, talkgroup) -> list[broadcastify.calls.Call]:
    with client:
        live_calls = client.get_livecall_session(call_system, talkgroup)
        return live_calls.init_session()

def average_logprob(transcription: dict) -> float:
    if "segments" not in transcription or len(transcription["segments"]) == 0:
        return
    return sum([x["avg_logprob"] for x in transcription['segments']]) / len(transcription['segments'])

def clamp(val, min_val, max_val):
    return max(min(val, max_val), min_val)

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

    call_system, talkgroup, calls_type, do_transcribe = prompt_initial_settings()
    if calls_type == "Archived Calls":
        time_block = prompt_settings_archive()
        calls, start_time, end_time = handle_archives(client, call_system, talkgroup, time_block)
    else:
        calls = handle_live(client, call_system, talkgroup)
        start_time = calls[0].start_time
        end_time = calls[-1].start_time

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
    
    if not do_transcribe:
        return

    print("Transcribing calls...")
    model = whisper.load_model("medium.en")
    
    if not os.path.exists("transcriptions.txt"):
        with open("transcriptions.txt", "w") as f:
            f.write(f"Transcriptions for calls from {format_unix_timestamp(start_time)} to {format_unix_timestamp(end_time)} - Talkgroup {calls[0].tg_name}\n")

    with open("transcriptions.txt", "a+") as f:
        last_call_id: int
        skip = 0
        manual_transcriptions = []
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
                    try:
                        alp = average_logprob(transcripton)
                        if alp and alp < -0.85:
                            manual_transcriptions.append((call_path, transcripton["text"], format_unix_timestamp(call.start_time), call.unit_radioid), )
                    except KeyError:
                        print(transcripton)

        except KeyboardInterrupt:
            print("Transcription interrupted")
            with open("last_call_id.txt", "w") as f2:
                f2.write(str(last_call_id))
    
    if manual_transcriptions:
        with open("transcriptions.txt", "r") as f:
            contents = f.read()

        a = inquirer.prompt([inquirer.Confirm("manual_transcribe", message="Would you like to manually transcribe these calls?", default=False)])

        print("Manual transcriptions reccomended:")        
        try:
            for call_path, transcription, start_time, unit_radioid in manual_transcriptions:
                identifier = f"{start_time} (RadioID {unit_radioid}): {transcription}"
                print(f"Call {call_path} - {identifier}")
                if a["manual_transcribe"]:
                    input_transcription = input("Enter transcription: ")
                    new_identifier = f"{start_time} (RadioID {unit_radioid}): {input_transcription}"
                    contents = contents.replace(identifier, new_identifier)
        except KeyboardInterrupt:
            print("Manual transcription interrupted")
        with open("transcriptions.txt", "w") as f:
            f.write(contents)


if __name__ == "__main__":
    main()