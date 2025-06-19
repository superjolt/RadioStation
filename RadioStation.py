import scratchattach as sa
import os
from dotenv import load_dotenv
import requests, threading, time
import numpy as np
from pydub import AudioSegment
import io
from pydub.utils import which

os.environ["PATH"] = os.environ["PATH"] + f":{os.path.expanduser('~/mybin')}"

load_dotenv()

SESSION_ID = os.getenv("SESSION_ID")
PROJECT_ID = os.getenv("PROJECT_ID")

AudioSegment.converter = which("ffmpeg")
AudioSegment.ffprobe   = which("ffprobe")

print("ffmpeg:", AudioSegment.converter)
print("ffprobe:", AudioSegment.ffprobe)

if SESSION_ID is None or PROJECT_ID is None:
    raise ValueError("SESSION_ID and PROJECT_ID must be set in the environment variables.")

session = sa.login_by_id(session_id=SESSION_ID, username="superjolt")
cloud = session.connect_cloud(PROJECT_ID)
client = cloud.requests()

radioStations = {
    "lofi": "https://ice1.somafm.com/groovesalad-128-mp3",
}

connectedStation = None
streaming = False

@client.event
def on_ready():
    print("Request handlers work")

@client.request
def ping():
    print("pong!")
    return "pong"

@client.request
def connect_radio(station, username):
    global connectedStation, streaming
    if station not in radioStations:
        return "Station not found!"
    connectedStation = station
    if not streaming:
        threading.Thread(target=stream_and_analyze, daemon=True).start()
        streaming = True
    return f"{username} connected to {station}!"


def chunk_to_frequency(chunk):
    try:
        # Wrap chunk in BytesIO and decode as MP3
        audio_segment = AudioSegment.from_file(io.BytesIO(chunk), format="mp3")
        samples = np.array(audio_segment.get_array_of_samples())

        if len(samples) < 2:
            return 0

        fft = np.fft.fft(samples)
        freqs = np.fft.fftfreq(len(fft), 1 / audio_segment.frame_rate)
        idx = np.argmax(np.abs(fft[:len(fft)//2]))
        freq = abs(freqs[idx])
        return freq
    except Exception as e:
        print("Decode error:", e)
        return 0

def freq_to_midi(freq):
    if freq <= 0:
        return 0
    midi = int(69 + 12 * np.log2(freq / 440))
    return max(30, min(midi, 90))  # limit range

def stream_and_analyze():
    global connectedStation
    while True:
        if connectedStation:
            url = radioStations[connectedStation]
            print(f"streaming {connectedStation}")
            response = requests.get(url, stream=True)
            for chunk in response.iter_content(chunk_size=1024):
                if connectedStation is None:
                    break
                if chunk:
                    freq = chunk_to_frequency(chunk)
                    midi = freq_to_midi(freq)
                    print(f"freq: {freq:.2f} hz -> MIDI {midi}")
                    client.send(midi)  # send raw int, no hex
                time.sleep(0.05)

client.start(thread=True)
