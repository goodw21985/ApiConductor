import asyncio
import threading
import websockets
import json
import uuid
import time

class Action:
    def __init__(self, ev, value):
        self.ev = ev
        self.value = value

class Conversation:
    def __init__(self, client, code):
        self._event = asyncio.Event()
        self._queue = asyncio.Queue()
        self._done = False

        self.client = client
        self.conversation_id = str(uuid.uuid4())  # Generate a random GUID       
        self.code = code

    def enqueue(self, value):
        self._queue.put_nowait(value)
        self._event.set()

    async def dispatch_async(self):
        self._event.set()
        while not self._done or not self._queue.empty():
            await self._event.wait()

            while not self._queue.empty():
                value = await self._queue.get()
                yield value
                self._queue.task_done()
            self._event.clear()

    def dispatch(self):
        coroutine = self.dispatch_async()
        while True:
            future = asyncio.run_coroutine_threadsafe(coroutine.__anext__(), self.client.loop)
            try:
                result = future.result()
                yield result  # Yield the result to the caller
            except StopAsyncIteration:
                break

    def stop(self):
        self._done = True
        self._event.set()

    def complete(self, action_id, result):
        message = {
            "conversation_id": self.conversation_id,
            "action_id": action_id,
            "result": result
        }
        asyncio.run_coroutine_threadsafe(self.client.send_message(message), self.client.loop)

class ApiConductorClient:
    def __init__(self, uri="ws://localhost:8765"):
        self.conversations = {}
        self.uri = uri
        self.websocket = None
        self.ready_event = threading.Event()
        self.thread = threading.Thread(target=self.start_event_loop)
        self.thread.start()
        self.ready_event.wait()

    def start_event_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.connect())
        self.ready_event.set()  # Signal that the thread is ready
        self.loop.run_forever()

    async def connect(self):
        self.websocket = await websockets.connect(self.uri)
        print(f"Connected to {self.uri}")
        # Start the listening task
        self.loop.create_task(self.listen())

    async def listen(self):
        async for message in self.websocket:
            response_data = json.loads(message)
            print(f"Received: {response_data}")
            conversation_id = response_data["conversation_id"]
            if conversation_id in self.conversations:
                conversation = self.conversations[conversation_id]
                if "new_code" in response_data:
                    conversation.enqueue(Action("new_code", response_data["new_code"]))
                else:
                    pass

    async def send_message(self, message):
        await self.websocket.send(json.dumps(message))
        print(f"Sent: {message}")

    async def start_conversation_task(self, code):
        conversation = Conversation(self, code)
        self.conversations[conversation.conversation_id] = conversation

        message = {
            "conversation_id": conversation.conversation_id,
            "code": conversation.code
        }

        await self.websocket.send(json.dumps(message))
        print(f"Sent: {message}")
        return conversation

    def start_conversation(self, code):
        future = asyncio.run_coroutine_threadsafe(self.start_conversation_task(code), self.loop)
        conversation = future.result()
        print(f"Started conversation with ID: {conversation.conversation_id}")

        return conversation

    def stop(self):
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join()

def process_conversation(client, src):
    conversation = client.start_conversation(src)
    for action in conversation.dispatch():
        print("*******")
        print(f"Consumed action: {action.ev}, value: {action.value}")
        print("*******")

if __name__ == '__main__':
    client = ApiConductorClient()

    src = """
x=0
a=search_email(x)
if (a<3):
    y=search_email(a+5)
else:
    y=search_email(a+10)
return y
"""
    process_conversation(client, src)

    time.sleep(5)  # Use time.sleep instead of asyncio.sleep in synchronous code
    client.stop()
