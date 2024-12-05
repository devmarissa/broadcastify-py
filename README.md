Project Description:
--------------------
This project provides a Python-based client library to interact with Broadcastify's unofficial calls API. It allows users to fetch archived and live audio calls from various radio talkgroups, cache retrieved data, and manage API sessions. (Requires premium broadcastify account)

# Index
---
 1. [Key Features](#key-features)
 2. [Modules Overview](#modules-overview)
 3. [Usage](#usage-instructions)
    1. [Authentication](#authentication)
    2. [Fetching Archived Calls](#fetch-archived-calls)
    3. [Stream Live Calls](#stream-live-calls)
4. [Dependencies](#dependencies)
5. [Downloader.py Documentation](#downloader.py-documentation)

Key Features:
-------------
1. **Archived Call Retrieval**:
   - Retrieve archived audio calls for specific talkgroups within a time block.
   - Data includes call metadata like start time, duration, and audio file URL.

2. **Live Call Streaming**:
   - Establish a session to poll live calls from specific talkgroups.
   - Real-time updates with hooks for custom event handling.

3. **Session Management**:
   - Supports authentication with Broadcastify using session tokens.
   - Handles login, logout, and session initialization.

4. **Caching**:
   - Saves fetched data locally to reduce redundant API calls.
   - Expiration-based cache management.

Modules Overview:
-----------------
1. **call_utils.py**:
   - Contains helper functions like `get_archived_calls` to retrieve archived call data and `generate_session_token` for session initialization.

2. **Call.py**:
   - Defines the `Call` class to represent individual call metadata.
   - Includes a method to generate the audio file URL.

3. **LiveCalls.py**:
   - Implements the `LiveCalls` class for managing live call sessions.
   - Provides methods to initialize and poll live calls, with hooks for event-driven programming.

4. **Client.py**:
   - A high-level API client encapsulating functionality for authentication, call retrieval, and cache management.
   - Supports both archived and live call functionalities.

5. **utility.py**:
   - Provides utility functions like `floor_dt` and `floor_dt_s` for time rounding.

Usage Instructions:
-------------------
1. **Authentication**:
   - Instantiate a `Client` object with your Broadcastify credentials:
     ```python
     from broadcastify.Client import Client

     client = Client(username="your_username", password="your_password")
     client.login()
     ```

2. **Fetch Archived Calls**:
   - Retrieve calls for a specific system, talkgroup, and time block:
     ```python
     calls, start_time, end_time = client.get_archived_calls(call_system=123, talkgroup=456, time_block=timestamp) # 30 minute time blocks, e.g 13:27 would be contained in the 13:00 time block (POSIX time)
     for call in calls:
         print(call)
     ```

3. **Stream Live Calls**:
   - Initialize and poll live calls:
     ```python
     live_session = client.get_livecall_session(call_system=123, talkgroup=456)
     initial_calls = live_session.init_session()
     print(initial_calls)
     while True:
        new_calls = live_session.poll()
        if new_calls:
            print(new_calls)
        time.sleep(5)
     ```

4. **Cache Management**:
   - Cached data is automatically saved and loaded to reduce API usage.
   - Configure cache directory and expiration in `Client` settings.

Dependencies:
-------------
- `requests`: For HTTP communication with Broadcastify's API.
- `pickle`: For cache serialization.
- Python >= 3.8


Example:
--------
```python
from broadcastify.Client import Client

# Initialize client and login
client = Client(username="user", password="pass")
client.login()

# Fetch archived calls
calls, st, et = client.get_archived_calls(call_system=1, talkgroup=2, time_block=1622470422)
for call in calls:
    print(call)

# Stream live calls
live_session = client.get_livecall_session(call_system=1, talkgroup=2)
live_session.init_session()
while True:
    live_calls = live_session.poll()
    print(live_calls)
```

# **Downloader.py Documentation**

`downloader.py` is a command-line utility designed to download and process call recordings from the Broadcastify service. The utility provides an interactive menu-based system for the user to specify parameters such as system ID, talkgroup ID, the type of calls to download, and other options.

## **How to Run**
This script does not take any command-line arguments. Instead, all configurations are performed interactively after running the script. Use the following command to execute the script:

```bash
python3 downloader.py
```
 > Before running, please create a file called `login.txt` containing your broadcastify credentials in `username:password` format
---

## **Interactive Inputs**

### 1. **Enter Call System ID**
- **Prompt:** `Enter call system ID:`
- **Description:** Specify the numeric system ID for the desired Broadcastify system from which the calls are to be downloaded. This is a required field.

---

### 2. **Enter Talkgroup ID**
- **Prompt:** `Enter talkgroup ID:`
- **Description:** Provide the talkgroup ID associated with the system ID. This identifies the specific group or channel for which recordings are to be retrieved.

---

### 3. **Pull Data From**
- **Prompt:** 
  ```
  Pull data from:
  > Live Calls
    Archived Calls
  ```
- **Options:**
  - `Live Calls`: Downloads the last 25 calls on a talkgroup
  - `Archived Calls`: Downloads previously recorded calls.

- **Navigation:** Use arrow keys to highlight the desired option and press `Enter`.

---

### 4. **Transcribe Calls**
- **Prompt:** `Transcribe calls (y/N):`
- **Description:** Select whether the utility should transcribe the downloaded calls. (Uses OpenAI whisper)
  - `y`: Enables transcription.
  - `N`: Disables transcription (default).

---

### 5. **Specify Day for Archived Calls**
- **Prompt:** `Enter day in YYYY-MM-DD format:`
- **Description:** When retrieving archived calls, input the date (in the format `YYYY-MM-DD`) for which the calls should be downloaded. This step is skipped for live calls.

---

### 6. **Select Time Block**
- **Prompt:** 
  ```
  Select time block:
  17:30 --> 17:59
  18:00 --> 18:29
  ...
  > 21:30 --> 21:59
  ```
- **Description:** For archived calls, choose the specific 30-minute time block to download. Use the arrow keys to select the desired time block and press `Enter`.

---

## **Output**
- If a call recording has already been downloaded, the utility will skip it and display a message similar to:
  ```
  Call <call_id>-<talkgroup_id> already downloaded, skipping...
  ```

---

## **Features**
- Interactive parameter selection for flexibility.
- Ability to choose between live and archived calls.
- Support for downloading specific time blocks for archived calls.
- Option to enable or disable transcription of calls.

---

## **Notes**
- Ensure you have the correct system and talkgroup IDs to avoid errors.
- The transcription feature is optional and disabled by default.
- For archived calls, only one date and time block can be selected per execution. Run the script multiple times if you need multiple time blocks.
- Before running, please create a file called `login.txt` containing your broadcastify credentials in `username:password` format

