import scratchattach as sa
import os
import requests, subprocess, numpy as np, threading
from flask import Flask
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
    print("Request handlers work")

@client.request
def ping():
    print("pong!")
    return "pong"

@client.request
def connect_radio(station, username):
    global connectedStation, streaming
    if station not in radioStations:
        return f"Station {station} not found"
    connectedStation = station
    if not streaming:
        threading.Thread(target=stream_and_analyze, daemon=True).start()
        streaming = True
    return f"{username} connected to {station}"

@client.request
def get_stations():
    return list(radioStations.keys())

def freq_to_midi(freq):
    if freq <= 0:
        return 0
    midi = int(69 + 12 * np.log2(freq / 440))
    return max(30, min(midi, 90))

def stream_and_analyze():
    global connectedStation
    while True:
        if connectedStation:
            url = radioStations[connectedStation]
            print(f"streaming: {connectedStation}")

            # Start ffmpeg process: decode stream to raw PCM
            process = subprocess.Popen([
                "ffmpeg",
                "-i", url,
                "-f", "s16le",  # raw PCM 16-bit little endian
                "-acodec", "pcm_s16le",
                "-ac", "1",     # mono
                "-ar", "44100", # sample rate
                "-"
            ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

            while True:
                raw = process.stdout.read(4096)
                if not raw:
                    break

                pcm = np.frombuffer(raw, np.int16)
                if len(pcm) == 0:
                    continue

                fft = np.fft.fft(pcm)
                freqs = np.fft.fftfreq(len(fft), 1 / 44100)
                idx = np.argmax(np.abs(fft[:len(fft)//2]))
                freq = abs(freqs[idx])

                midi = freq_to_midi(freq)
                print(f"Freq: {freq:.2f} Hz -> MIDI {midi}")
                client.send(midi)

app = Flask(__name__)

@app.route("/")
def home():
    return "RadioStation is RUNNING!"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

threading.Thread(target=run_flask, daemon=True).start()

client.start()