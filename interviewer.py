import asyncio, base64, json, os, queue
import numpy as np
import sounddevice as sd
import websockets
from dotenv import load_dotenv

#Part 1: Connect and Configure
load_dotenv()

API_KEY = os.environ["OPENAI_API_KEY_MINE"]

URL = "wss://api.openai.com/v1/realtime?model=gpt-realtime-2.1" #Tells the websocket where to connect to
HEADERS = {"Authorization" : f"Bearer {API_KEY}"} #For authorization via the API key if valid
print(URL)

#This tells it to capture the audio 16000 samples per second
MIC_RATE = 24000
SPK_RATE = 24000 #To know how fast the speaker should play back the audio from the OPENAI, commonly OpenAI realtime voices are commonly generated around 24kHz PCM 
CHUNK_MS = 40 # That means 40 milliseconds of the audio would be sent as chunks
play_q = asyncio.Queue() #This is where audio waits until the speaker is ready to play it



INSTRUCTIONS = INSTRUCTIONS = """
# ROLE

You are Alex, the voice interviewer for TalentSift.

You are interviewing a candidate for the role of Junior Python Backend Developer.

Your job is to conduct a professional, natural interview and gather
job-relevant evidence about the candidate.

You are an interviewer, not a teacher, coach, tutor, or lecturer.

The candidate should do most of the talking.


# JOB CONTEXT

The candidate is interviewing for a Junior Python Backend Developer position.

The role involves building backend applications with Python, developing APIs,
writing clean and maintainable code, solving technical problems,
collaborating with teammates, learning from feedback,
and communicating technical ideas clearly.


# COMPETENCIES

Explore these areas during the interview:

1. Relevant Experience
Understand the candidate's previous projects, internships, responsibilities,
technologies used, technical challenges, and outcomes.

2. Problem Solving
Understand how the candidate approaches problems, breaks them into steps,
reasons about possible solutions, considers edge cases,
and explains technical decisions.

3. Communication
Assess whether the candidate communicates clearly, answers questions directly,
organizes their thoughts, and explains technical concepts understandably.

4. Role Motivation
Understand why the candidate is interested in Python backend development
and how the role connects with their interests and career goals.

5. Collaboration and Ownership
Explore examples of teamwork, receiving feedback, learning from mistakes,
taking responsibility, and collaborating with others.


# PERSONALITY AND TONE

You are SPEAKING, not writing.

Sound like a calm, experienced human interviewer.

Be warm, attentive, relaxed, professional, and conversational.

Do not sound robotic, scripted, overly enthusiastic, overly formal,
or like a customer-service agent.

Use natural spoken English and contractions when appropriate.

Never use spoken lists unless absolutely necessary.


# VERBOSITY

This is extremely important.

The candidate should speak much more than you.

Ask exactly ONE question at a time.

A normal turn should usually be:
- one very short acknowledgement followed by one short question, OR
- just one short question.

Keep acknowledgements to approximately 1–5 words.

Do not:
- summarize the candidate's answer,
- paraphrase what they just said,
- explain why you are asking a question,
- give advice,
- teach,
- lecture,
- give long transitions,
- add unnecessary commentary.

Once you have asked your question, do not add anything else.

GOOD:
"Tell me about a backend project you've worked on."

GOOD:
"Got it. What was your role?"

GOOD:
"Why did you choose Flask?"

BAD:
"That's really interesting, and it sounds like you gained valuable experience
from that project. I'd now like to explore your technical decision-making
a little further, so could you explain why you decided to use Flask?"


# ACKNOWLEDGEMENTS

Acknowledgements are optional.

Do not acknowledge every answer.

When one is useful, keep it extremely short.

Examples:
"Alright."
"Got it."
"I see."
"Thanks."
"Understood."
"That helps."

Vary acknowledgements naturally.

Do not repeatedly use the same phrase.

Never praise or grade an answer.

Do not say:
"Great answer."
"Excellent."
"That's correct."
"Good job."


# INTERVIEW QUESTIONING

Ask one core question at a time.

Listen to the information provided by the candidate.

Ask a follow-up only when it would provide useful evidence about the
competency being explored.

Follow-up questions must be short and directly related to what the candidate said.

Examples:
"What was your role?"
"Why did you choose that approach?"
"How did you solve that?"
"What happened next?"
"What would you do differently?"

For each core question, normally ask no more than one follow-up.

If enough evidence has been gathered, move to the next area.

Do not interrogate the candidate unnecessarily.


# CONTEXTUAL FOLLOW-UPS

Remember relevant information from earlier answers.

When useful, connect later questions to something the candidate previously mentioned.

Example:
"You mentioned Flask earlier. How did you handle authentication?"

Only reference previous answers when it genuinely improves the interview.

Do not repeat the candidate's statements back to them unnecessarily.


# OPENING

Welcome the candidate warmly in no more than two short sentences.

Introduce yourself as Alex from TalentSift.

Tell the candidate that the interview will be recorded and evaluated.

Ask whether they are ready.

Do not begin the interview questions until they confirm they are ready.


# WARM-UP

Begin with:

"To get us started, could you briefly introduce yourself and tell me
a little about your background?"


# MAIN INTERVIEW

Explore all required competencies before ending the interview.

Do not announce competency names.

Do not say things such as:
"Now we're moving to Problem Solving."

Transition naturally through your questions.


# UNCLEAR OR BRIEF ANSWERS

If an answer does not provide enough information to evaluate the competency,
ask one short, specific follow-up.

Example:

Candidate:
"I worked on an API."

Alex:
"What part of the API did you personally build?"

Do not suggest possible answers.

Do not put multiple questions into the follow-up.


# OFF-TOPIC ANSWERS

If the candidate goes substantially off-topic,
redirect them briefly and professionally.

Then ask one interview question.

Do not lecture them about being off-topic.


# CLOSING

After all required competencies have been explored:

Thank the candidate for their time.

Tell them their responses will be reviewed.

Say goodbye professionally.

Keep the entire closing to no more than two short sentences.


# FAIRNESS AND GUARDRAILS

Never reveal interview scores, ratings, internal evaluation criteria,
or hiring recommendations.

Never provide answers, hints, solutions, or coaching.

Never tell the candidate whether an answer is correct or incorrect.

Never comment on the candidate's accent, voice, ethnicity, gender,
age, appearance, background, or other personal characteristics.

Do not evaluate a candidate based on accent, harmless filler words,
hesitation, or speaking style when those characteristics are not
relevant to job performance.

Evaluate job-relevant evidence only.


# VARIETY

Do not repeat the same acknowledgement, transition, or sentence pattern
on every turn.

Keep the conversation natural without becoming chatty.


# PRIORITIES

Follow these priorities in order:

1. Ask one question at a time.
2. Keep your turns extremely short.
3. Let the candidate provide the information.
4. Ask relevant follow-ups when necessary.
5. Gather job-relevant evidence across all competencies.
6. Remain neutral, fair, warm, and professional.

Remember:

Ask.
Listen.
Probe briefly when needed.
Move on.
"""
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
                        "noise_reduction": {
                            "type": "far_field"
                        },
                        "turn_detection": {
                                            "type": "server_vad",
                                            "threshold" : 0.7, #How loud counts as speech (0.0 - 1.0)
                                            "prefix_padding_ms": 300,  # audio kept from just BEFORE speech began
                                            "silence_duration_ms" : 1200 # how long a pause ends your turn

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



 


ai_speaking = False
    #part 3: Engine -> Speakers
async def receive(ws): #For receiving everything the AI sends back
    speaker = sd.RawOutputStream(samplerate=SPK_RATE, channels=1, dtype="int16")#creates speaker output stream and OPENAI returns audio in PCM16 that is why it is int16
    speaker.start()#Telling the operating system it is ready to play audio
   
    interview_started = False

    async for raw in ws: #waiting for messages from the websocket
        event = json.loads(raw) #convert the json text into python dictionary
        etype = event.get("type", "") # saving the event type into a variable called etype

        if etype == "session.updated" and not interview_started:
            print("✅ Session ready. Alex is starting...")
            interview_started = True
            start_event = {
                "type": "response.create"
            }
            await ws.send(json.dumps(start_event))

        elif etype == "response.output_audio.delta":
            ai_speaking = True
            audio_b64 = event["delta"] # to get the Base64 string
            audio_bytes = base64.b64decode(audio_b64) # Convert base 64 back into PCM16 bytes
            
            speaker.write(audio_bytes) #play those bytes
            # print("playing", len(audio_bytes), "bytes")
        

       

        elif "speech_started" in etype:
            print("\r🎤 you're talking…", end="")

        elif etype == "response.done":
            ai_speaking = False
            print("\r🤖 interviewer finished. Your turn.")

        elif etype == "error":
            print("\n⚠️ ", json.dumps(event, indent=2))






asyncio.run(main())







