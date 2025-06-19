import scratchattach as sa
import os
import requests, subprocess, numpy as np, threading
from dotenv import load_dotenv

load_dotenv()

SESSION_ID = os.getenv("SESSION_ID")
PROJECT_ID = os.getenv("PROJECT_ID")

if PROJECT_ID is None or SESSION_ID is None:
    print(".env should contain PROJECT_ID and SESSION_ID!")
    exit(1)
else:
    print(".env contains everything!")

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
    print("Request handler ready!")

@client.request
def ping():
    print("pong!")
    return "pong"

@client.request
def get_stations():
    return list(radioStations.keys())

def freq_to_midi(freq):
    if freq <= 0:
        return 0
    midi = int(69 + 12 * np.log2(freq / 440))
    return max(30, min(midi, 90))

def stream_station(name, url):
    print(f"[▶️] Starting stream for {name}")
    process = subprocess.Popen([
        "ffmpeg",
        "-i", url,
        "-f", "s16le",
        "-acodec", "pcm_s16le",
        "-ac", "1",
        "-ar", "44100",
        "-"
    ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    while True:
        raw = process.stdout.read(8192)
        if not raw:
            break

        pcm = np.frombuffer(raw, np.int16)
        if len(pcm) == 0:
            continue

        fft = np.fft.fft(pcm)
        freqs = np.fft.fftfreq(len(fft), 1 / 44100)

        mag = np.abs(fft[:len(fft)//2])
        pos_freqs = np.abs(freqs[:len(fft)//2])

        top_idxs = np.argpartition(mag, -MAX_NOTES)[-MAX_NOTES:]
        top_freqs = pos_freqs[top_idxs]

        midi_notes = sorted({freq_to_midi(f) for f in top_freqs if f > 20 and f < 10000})
        midi_notes = midi_notes[:MAX_NOTES]

        command = ",".join(map(str, midi_notes))
        # Send to a unique cloud var per station:
        client.set_var(f"{name}_data", command)

# Start a stream thread for each station:
for station_name, station_url in radioStations.items():
    threading.Thread(target=stream_station, args=(station_name, station_url), daemon=True).start()

client.start(thread=True)
