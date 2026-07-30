import asyncio # To know when to get the tool box for asynchronous programming in python.
import websockets #Connection library

#Host is the device or component on a network that sends or receives data
#Port is a number that identifies a spcific application or service running on a computer
HOST, PORT = "localhost", 8765

async def handle(ws):
    print("Client connected")
    chunk_count = 0
    try:
        async for message in ws:          # each message = one audio chunk (bytes)
            chunk_count += 1
            if chunk_count % 50 == 0:
                print(f"Received {chunk_count} chunks ({len(message)} bytes each)")
 
            # TODO #1 — THE ECHO: send this same chunk straight back to the client.
            await ws.send(message) #To send each chunks of audio data received
 
    except websockets.ConnectionClosed:
        print(f"Client left after {chunk_count} chunks")  # To know the number of chunks received before the client disconnected
 
async def main(): # To create the websockets server,cause it to listen on the host and port for it to receive clients
    async with websockets.serve(handle, HOST, PORT):#This create the websockets server for it to handle connections when a client connects on local host on that port.Async because starting and ending a websocket server are asynchronous operations.
        print(f"Echo server listening on ws://{HOST}:{PORT}") # To show that the server is listening already
        await asyncio.Future()   # run forever pauses main()
 
if __name__ == "__main__":
    asyncio.run(main())
