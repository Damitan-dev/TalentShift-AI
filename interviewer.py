import asyncio, base64, json, os, queue
import numpy as np
import sounddevice as sd
import websockets
from dotenv import load_dotenv

#Part 1: Connect and Configure
load_dotenv()

API_KEY = os.environ["OPENAI_API_KEY"]

URL = "wss://api.openai.com/v1/realtime?model=gpt-realtime-2.1" #Tells the websocket where to connect to
HEADERS = {"Authorization" : f"Bearer {API_KEY}"} #For authorization via the API key if valid
print(URL)

#This tells it to capture the audio 16000 samples per second
MIC_RATE = 24000
SPK_RATE = 24000 #To know how fast the speaker should play back the audio from the OPENAI, commonly OpenAI realtime voices are commonly generated around 24kHz PCM 
CHUNK_MS = 40 # That means 40 milliseconds of the audio would be sent as chunks




INSTRUCTIONS = "You are a friendly assistant." 

async def main():
    async with websockets.connect(URL, additional_headers=HEADERS) as ws:
        # TODO #1 — build the session-configuration event.
        # From the current docs, find the event that updates the session, and set:
        #   a) input and output audio format  (16-bit PCM)
        #   b) turn detection = server-side VAD (the engine detects when you stop)
        #   c) a voice you like from the available list
        #   d) instructions = INSTRUCTIONS
        session_config = {
            "type": "session.update",          # the session-update event type
            "session": {
                "type" : "realtime",
                "audio": {
                    "input": {
                        "format": {
                            "type": "audio/pcm",
                            "rate": MIC_RATE
                        },
                        "turn_detection": {
                                            "type": "server_vad"
                                        }
                    },

                    "output": {
                        "format": {
                            "type": "audio/pcm",
                            "rate": SPK_RATE
                        },
                        "voice": "cedar"
                    }
                },
                
                "instructions": INSTRUCTIONS
            },
        }
        await ws.send(json.dumps(session_config)) #convert to json and wait till it sends
        print("✓ Session configured. Listening for events…") #Tells me on my terminal


        mic = sd.RawInputStream(samplerate=MIC_RATE, channels=1, dtype="int16",
                          blocksize=CHUNK_SAMPLES, callback=on_mic) #setting the mic stream


        mic.start() #start recording
        await asyncio.gather(send_mic(ws), receive(ws))  


        

    # part 2: mic -> engine

CHUNK_SAMPLES = MIC_RATE * CHUNK_MS // 1000
mic_q = queue.Queue() #It acts like a buffer

def on_mic(indata, frames, t, status): #To receive every chunk audio from the microphone and place it into the queue
    mic_q.put(bytes(indata)) 


async def send_mic(ws): #To continuously send microphone chunks to OpenAI
    while True:
        chunk = await asyncio.to_thread(mic_q.get) #To wait for a chunk in another thread 
        audio_b64 = base64.b64encode(chunk).decode("utf-8") #converts the chunk to base64 then strings
        event = {
                    "type": "input_audio_buffer.append",
                    "audio": audio_b64
                    }
            #client event for OpenAI to know this is another microphone audio chunk

        await ws.send(json.dumps(event)) #convert to Json and send

    #part 3: Engine -> Speakers
async def receive(ws): #For receiving everything the AI sends back
    speaker = sd.RawOutputStream(samplerate=SPK_RATE, channels=1, dtype="int16")#creates speaker output stream and OPENAI returns audio in PCM16 that is why it is int16
    speaker.start()#Telling the operating system it is ready to play audio
    async for raw in ws: #waiting for messages from the websocket
        event = json.loads(raw) #convert the json text into python dictionary
        etype = event.get("type", "") # saving the event type into a variable called etype


        if etype == "response.output_audio.delta":
            audio_b64 = event["delta"] # to get the Base64 string
            audio_bytes = base64.b64decode(audio_b64) # Convert base 64 back into PCM16 bytes
            speaker.write(audio_bytes) #play those bytes

        elif "speech_started" in etype:
            print("\r🎤 you're talking…", end="")
        elif "response" in etype and etype.endswith("done"):
            print("\r🤖 interviewer finished. Your turn.")
        elif etype == "error":
            print("\n⚠️ ", json.dumps(event, indent=2))



 




asyncio.run(main())







