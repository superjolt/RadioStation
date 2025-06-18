import scratchattach as sa
import os
from dotenv import load_dotenv

load_dotenv()

SESSION_ID = os.getenv("SESSION_ID")
PROJECT_ID = os.getenv("PROJECT_ID")

if SESSION_ID is None:
    raise ValueError("SESSION_ID not set in .env")

session = sa.login_by_id(session_id=SESSION_ID, username="superjolt") #replace with your session_id and username
cloud = session.connect_cloud(PROJECT_ID)
client = cloud.requests()

@client.request
def ping(): #called when client receives request
    print("Ping request received")
    return "pong" #sends back 'pong' to the Scratch project


client.start(thread=True) # thread=True is an optional argument. It makes the cloud requests handler run in a thread