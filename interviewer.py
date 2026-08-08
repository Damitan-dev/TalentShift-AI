import asyncio, base64, json, os, queue
import numpy as np
import sounddevice as sd
import websockets
from dotenv import load_dotenv
import time #To measure the latency
import statistics # To help us calculate the median formus


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
CHUNK_BYTES = 960 # 20ms at 24kHz, PCM16, mono
INTERRUPT_GRACE_MS = 40
fade_requested = asyncio.Event()

INSTRUCTIONS = """
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

Speak with a calm, low-energy warmth.

Your voice should feel gentle and composed, never forceful.

Use smooth phrasing and slightly slower pacing.


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

Listen carefully to the information provided by the candidate.

Ask a follow-up only when it would provide useful job-relevant evidence
about the competency currently being explored.

Follow-up questions must be short and directly related to what
the candidate said.

Examples:

"What was your role?"
"Why did you choose that approach?"
"How did you solve that?"
"What happened next?"
"What would you do differently?"

Never ask more than ONE follow-up for the competency currently being explored.

If enough evidence has been gathered, move on.

Do not interrogate the candidate unnecessarily.


# FOLLOW-UP LOGIC

After each candidate answer, silently determine whether the answer is:

- CONCRETE
- VAGUE
- TOO-SHORT
- OFF-TOPIC

Never tell the candidate how their answer was classified.


## CONCRETE

An answer is CONCRETE when it provides useful job-relevant evidence.

Useful evidence may include:

- a specific example,
- something the candidate personally did,
- a decision they made,
- a challenge they handled,
- reasoning behind an approach,
- or a result or outcome.

If the answer is CONCRETE:

- Do not ask another follow-up merely to make the answer longer.
- Use a very short acknowledgement if it feels natural.
- Move to the next question or competency.


## VAGUE

An answer is VAGUE when it stays mostly at the level of general statements
without showing what the candidate personally did.

Signals may include:

- "usually",
- "normally",
- "generally",
- describing what "we" did without explaining their own contribution,
- describing what people should do instead of what they actually did,
- discussing a topic without giving a specific example.

If the answer is VAGUE:

- Ask exactly ONE short follow-up.
- Ask for a specific example or the candidate's personal contribution.
- Then move on regardless of the quality of the second answer.

Examples:

"Can you give me a specific example?"

"What did you personally do?"

"Tell me about one time you handled that."

Do not give the candidate examples of possible answers.


## TOO-SHORT

An answer is TOO-SHORT when it is one sentence or less AND does not provide
enough job-relevant evidence to understand the candidate's experience,
actions, reasoning, or contribution.

Do not classify an answer as TOO-SHORT simply because it contains only
one sentence.

If a short answer already provides useful concrete evidence,
accept it and move on.

Example of a short but CONCRETE answer:

"I built a Flask REST API for a student management system where I personally
implemented the CRUD endpoints and authentication."

That answer is short, but already contains useful evidence.

If the answer is TOO-SHORT:

- Ask exactly ONE short, neutral follow-up.
- Ask for more specific evidence.
- Do not suggest what the correct answer should contain.
- Then move on regardless of the second answer.

Example:

Candidate:
"I had an issue with an API."

Alex:
"What did you personally do to solve it?"


## OFF-TOPIC

An answer is OFF-TOPIC when it does not substantially address
the question being asked.

If the answer is OFF-TOPIC:

- Briefly restate or rephrase the original question once.
- Keep the redirect short and professional.
- Do not introduce a different question.
- If the candidate remains off-topic after that attempt, move on.

Do not lecture the candidate about being off-topic.


## GENERAL FOLLOW-UP RULES

Never ask more than ONE follow-up for the competency currently being explored.

Once that follow-up has been used, move on regardless of whether
the second answer is strong or weak.

Never repeatedly probe because an answer is weak.

Never explain the evaluation rubric.

Never tell the candidate that their answer was:
"concrete",
"vague",
"too short",
or "off-topic".

Never coach the candidate toward a stronger answer.

Never suggest examples of what the candidate could say.

Never provide hints that would help them improve their interview answer.


# CONTEXTUAL FOLLOW-UPS

Remember relevant information from earlier answers.

When useful, connect later questions to something the candidate
previously mentioned.

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

Do not rigidly follow a questionnaire when information from the candidate's
previous answer creates a useful and relevant next question.

However, make sure all required competencies are explored before closing.


# INTERRUPTIONS AND CLARIFICATION

If the candidate interrupts while you are speaking:

- If they begin answering the question, stop speaking and listen.
  Do not finish or repeat the interrupted question unnecessarily.

- If they say "wait", "hold on", "one moment", "give me a second",
  or something similar, respond with only a very brief natural
  acknowledgement such as "Sure." or "Of course.", then give them time.

- If they ask you to repeat the question, briefly acknowledge the request
  and repeat the full question clearly.

- If they say they did not understand the question, rephrase the same
  question without giving hints or suggesting an answer.

- If they ask for clarification about the question, answer only enough
  to clarify what is being asked, then return to the same question.

- Do not treat requests for repetition, clarification, waiting,
  or technical issues as interview answers.

- Do not automatically acknowledge every interruption.
  Respond according to what the candidate actually said.


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

Do not mistake confidence, verbosity, or polished language for
job competence.

A long answer is not automatically a strong answer.

A short answer is not automatically a weak answer.

Evaluate job-relevant evidence only.


# VARIETY

Do not repeat the same acknowledgement, transition,
follow-up wording, or sentence pattern on every turn.

Keep the conversation natural without becoming chatty.


# PRIORITIES

Follow these priorities in order:

1. Ask one question at a time.
2. Keep your turns extremely short.
3. Let the candidate provide the information.
4. Listen for job-relevant evidence.
5. Ask no more than one useful follow-up per competency.
6. Move on when enough evidence has been gathered.
7. Explore all required competencies.
8. Remain neutral, fair, warm, and professional.


# CORE INTERVIEW BEHAVIOR

Remember:

Ask.
Listen.
Assess the depth of the answer silently.
Probe once when necessary.
Move on.

"""

async def main():
    async with websockets.connect(
        URL,#OpenAI Realtime Websocket URL
        additional_headers=HEADERS , # Send your authorization and other required headers.
        ping_interval=20,  # Send a keepalive ping every 20 seconds.,
         ping_timeout=60,  # Give the connection up to 60 seconds to answer a ping before declaring it dead.
        ) as ws:
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
                            "type": "near_field"
                        },
                        "turn_detection": {
                                            "type": "server_vad",
                                            "threshold" : 0.7, #How loud counts as speech (0.0 - 1.0)
                                            "prefix_padding_ms": 300,  # audio kept from just BEFORE speech began
                                            "silence_duration_ms" : 800, # how long a pause ends your turn

                                            "create_response": True,
                                            "interrupt_response": True

                                        }
                    },

                    "output": {
                        "format": {
                            "type": "audio/pcm",
                            "rate": SPK_RATE
                        },
                        "voice": "marin"
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










async def graceful_stop(ws, speaker, playback_state):  # We need ws to send truncation and playback_state to know what was heard.

    await asyncio.sleep(
        INTERRUPT_GRACE_MS / 1000
    )  # Give Alex the tiny 40 ms graceful tail before stopping him.

    flush_playback()  # Delete all Alex audio that is still waiting inside our Python queue.

    await asyncio.to_thread(
        speaker.abort
    )  # Immediately stop audio that has already reached the sound device.

    await asyncio.to_thread(
        speaker.start
    )  # Restart the audio stream so Alex's next response can play normally.

    playback_state["playing"] = False  # Alex's interrupted local playback has now been stopped.

    item_id = playback_state["item_id"]  # Find out which Alex message the candidate was hearing.

    played_ms = int(
        playback_state["played_ms"]
    )  # Find approximately how many milliseconds of that message the candidate heard.

    if item_id is not None and played_ms > 0:  # Only truncate if we actually have an Alex message and some audio was heard.

        truncate_event = {  # Build the Realtime event that tells OpenAI where the candidate stopped hearing Alex.
            "type": "conversation.item.truncate",  # Tell OpenAI that we're shortening an earlier assistant audio message.
            "item_id": item_id,  # Identify the exact Alex message that was interrupted.
            "content_index": 0,  # OpenAI requires the audio content index to be 0 for this truncation event.
            "audio_end_ms": played_ms  # Keep only the amount of Alex audio the candidate actually heard.
        }

        await ws.send(
            json.dumps(truncate_event)
        )  # Send the truncation instruction to the OpenAI Realtime server.   


# For the from queue  to speaker
async def player(speaker, playback_state):  # Plays Alex's audio and tracks what the candidate actually hears.
    while True:  # Keep the playback worker alive throughout the interview.

        item_id, chunk = await play_q.get()  # Wait for the next Alex message ID + audio chunk.

        if playback_state["item_id"] != item_id:  # Check whether this chunk belongs to a new Alex message.
            playback_state["item_id"] = item_id  # Store the ID of the new Alex message.
            playback_state["played_ms"] = 0.0  # Reset heard duration because this is a new message.

        playback_state["playing"] = True  # Alex now has audio being played locally.

        await asyncio.to_thread(
            speaker.write,
            chunk
        )  # Send this PCM16 chunk to the speaker without blocking our async event loop.

        chunk_ms = (
            len(chunk) / (SPK_RATE * 2)
        ) * 1000  # Convert the number of PCM16 bytes in this chunk into milliseconds.

        playback_state["played_ms"] += chunk_ms  # Record that the candidate has now heard this additional audio.

        if (
            play_q.empty()
            and not playback_state["response_active"]
        ):  # Only call Alex finished when the queue is empty AND OpenAI has finished producing the response.

            playback_state["playing"] = False  # Alex is now genuinely finished with local playback.

#For flushing the queue when the candidate speak when the A.I is speaking
def flush_playback():
    while True:

        try:
            play_q.get_nowait()

        except asyncio.QueueEmpty:
            break

# To print the median,max and length of the latencies which is also the number of conversation between the A.I and the candidate
def print_latency_summary(latencies):
    if not latencies:
        return

    median_latency = statistics.median(latencies)
    worst_latency = max(latencies)

    print("\n--- LATENCY SUMMARY ---")
    print(f"Turns measured: {len(latencies)}")
    print(f"Median response gap: {median_latency:.0f} ms")
    print(f"Worst response gap: {worst_latency:.0f} ms")


ai_speaking = False
    #part 3: Engine -> Speakers
async def receive(ws): #For receiving everything the AI sends back
    speaker = sd.RawOutputStream(samplerate=SPK_RATE, channels=1, dtype="int16")#creates speaker output stream and OPENAI returns audio in PCM16 that is why it is int16
    speaker.start()  # Start the physical audio output stream.

    playback_state = {  # Shared information about the Alex audio currently being played.
        "item_id": None,  # No Alex message has been played yet when the interview starts.
        "played_ms": 0.0,  # The candidate has heard 0 ms of Alex so far.
        "playing": False,  # Alex is not currently playing through the speaker yet.
        "response_active": False  # True while OpenAI is still producing Alex's current response.
    }

    asyncio.create_task(
        player(speaker, playback_state)
    )  # Start the player in the background and give it access to our playback tracking information.


    interview_started = False
    interrupted = False

    turn_ended_at = None # Intially nobody as finished speaking
    waiting_first_delta =False #To tell if we are cuurrently waiting for the A.I's first audio
    latencies = [] #Where we'd save all the mesauremnts

    try:
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
                if waiting_first_delta and turn_ended_at is not None:  # Only measure the first Alex audio after the candidate's turn ended.
                    response_gap_ms = (time.monotonic() - turn_ended_at) * 1000  # Calculate the post-VAD response delay in milliseconds.

                    print(f"\n⏱️ Response gap: {response_gap_ms:.0f} ms")  # Show the latency during testing.

                    latencies.append(response_gap_ms)  # Save this latency so we can calculate the session summary later.

                    if len(latencies) == 10:  # Once we've collected ten exchanges...
                        print_latency_summary(latencies)  # ...show the median and worst latency.

                    waiting_first_delta = False  # We've measured the first delta, so don't measure the remaining chunks.


                if not interrupted:  # Only accept Alex audio if the candidate has NOT barged in.

                    audio_bytes = base64.b64decode(event["delta"])  # Convert OpenAI's Base64 audio back into raw PCM16 bytes.

                    item_id = event["item_id"]  # Get the ID of the exact Alex message this audio belongs to.

                    for i in range(0, len(audio_bytes), CHUNK_BYTES):  # Break the received audio into small chunks.

                        chunk = audio_bytes[i:i + CHUNK_BYTES]  # Take one small audio chunk.

                        play_q.put_nowait(
                            (item_id, chunk)
                        )  # Store BOTH the Alex message ID and audio together in the queue.

            elif etype == "input_audio_buffer.speech_started":  # VAD detected that the candidate has started speaking.

                print(
                    "\r🎤 you're talking…",
                    end=""
                )  # Show that candidate speech has been detected.


                if playback_state["playing"]:  # Check whether Alex is STILL locally audible when the candidate starts speaking.

                    interrupted = True  # This is genuine barge-in, so stop accepting new audio from Alex's interrupted response.

                    asyncio.create_task(
                        graceful_stop(
                            ws,  # Needed so graceful_stop can send conversation.item.truncate.
                            speaker,  # Needed so graceful_stop can stop the local speaker.
                            playback_state  # Needed to know which Alex message was playing and how much was heard.
                        )
                    )  # Run interruption handling in the background so receive() can keep processing WebSocket events.
                    print(
                        "\n✋ Alex yielding"
                    )  # Confirm that the candidate actually interrupted Alex.

                else:  # Alex had already finished speaking before the candidate began.

                    print(
                        "\r🎤 Normal candidate turn",
                        end=""
                    )  # This is ordinary conversation, so DO NOT abort, flush, or truncate Alex's previous question.
                                
            elif etype == "input_audio_buffer.speech_stopped":
                turn_ended_at = time.monotonic()# start tehs top watch now
                waiting_first_delta = True

            elif etype == "response.created":  # OpenAI has started creating a new Alex response.
                interrupted = False  # Allow audio from this new response into the playback queue.
                playback_state["response_active"] = True  # Remember that OpenAI is currently producing Alex's response.

            elif etype == "response.done":  # OpenAI has finished generating/sending Alex's current response.
                playback_state["response_active"] = False  # The server is no longer producing this Alex response.
                if play_q.empty():  # If there is also no remaining Alex audio waiting locally...
                    playback_state["playing"] = False  # ...then Alex is genuinely no longer audible.
                print("\r🤖 interviewer response generated.")

            elif etype == "conversation.item.truncated":  # OpenAI sends this when our truncate request succeeds.

                print(
                    f"\n✂️ Alex memory truncated at {event['audio_end_ms']} ms"
                )  # Show exactly where OpenAI says the assistant audio was truncated.

            elif etype == "error":
                print("\n⚠️ ", json.dumps(event, indent=2))


    except websockets.exceptions.ConnectionClosedError as e:
          # This runs only if the WebSocket unexpectedly disconnects,
        # such as from a keepalive ping timeout.

        print(
            f"\n❌ Realtime connection lost: {e}"
        )




asyncio.run(main())







