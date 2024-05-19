import asyncio
import websockets
import json
import ast
import concurrent
from ast_transform import astor_fork
from ast_transform import transform
from ast_transform import scope_analyzer
from ast_transform import common
import orchestrator
import threading

class Conversation:
    def __init__(self, conversation_id, websocket, code):
        self.conversation_id=conversation_id
        self.websocket=websocket
        self.code=code
        self.waiting = []


class ApiConductorServer:
    def __init__(self, config, port=8765):
        self.time_out=10
        self.config=config
        self.conversations={}
        self.lock = threading.Lock()
        asyncio.run(self.start(port))
        
    def run_exec(self, code, globals_dict):
        try:
            exec(code, globals_dict)
            return None
        except Exception as e:
            return type(e).__name__+": "+str(e)

    async def execute_with_timeout(self, code, globals_dict, timeout):
            loop = asyncio.get_running_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = loop.run_in_executor(executor, self.run_exec, code, globals_dict)
                try:
                    return await asyncio.wait_for(future, timeout)
                except asyncio.TimeoutError as e:
                    globals_dict["orchestrator"]._kill()
                    print("Execution timed out")
                    return type(e).__name__+": "+str(e)
                                
    async def run_code(self, data, websocket):
        conversation_id = data["conversation_id"]
        code = data["code"]
        conversation = Conversation(conversation_id, websocket, code)
        self.conversations[conversation_id]=conversation
        new_tree = transform.Transform(self.config).modify_code(conversation.code)
        conversation.new_code = astor_fork.to_source(new_tree)
        print(f"Received: {data}")
        request = {
            "conversation_id": conversation_id,
            "new_code": conversation.new_code
        }
        with self.lock:
            send1 =  websocket.send(json.dumps(request))
            conversation.waiting.append(send1)
        orchestror = orchestrator.Orchestrator(self, conversation_id)
                
        globals_dict = {'orchestrator': orchestror}
        err=await self.execute_with_timeout(conversation.new_code, globals_dict, self.time_out)
        if err != None:
            request = {
                "conversation_id": conversation_id,
                "exception": err
            }
            with self.lock:
                send1 =  websocket.send(json.dumps(request))
                conversation.waiting.append(send1)

            sende = conversation.websocket.send(request)
            conversation.waiting.append(sende)
            print("******")
            print(request)
        
            print("******")
                    
        print("********exec done*********")

        
    async def message(self, websocket, path):
        async for message in websocket:
            data = json.loads(message)
            print(data)
            if "code" in data:
                 task = asyncio.create_task(self.run_code(data, websocket)) 
            else:
                pass
            
            print("************done************")
            
    def _call(self, conversation_id, parms):
        asyncio.run(self._call_task(conversation_id,parms) )
        
    async def _call_task(self, conversation_id, parms):
        conversation = self.conversations[conversation_id]
        request = {
                    "conversation_id": conversation_id,
                    "call": parms
                }
        with self.lock:
            task= conversation.websocket.send(request)
            conversation.waiting.append(task)
        print("******")
        print(request)
        
        print("******")
        
    async def start(self, port=8765):
        self.server = await websockets.serve(self.message, "localhost", port)
        await self.server.wait_closed()


if __name__ == '__main__':
    config = common.Config()
    config.awaitable_functions = ["search_email", "search_teams", "search_meetings", "create_dict", "wrap_string"]
    config.module_blacklist=None
    config.wrap_in_function_def =False
    config.single_function=True
    server = ApiConductorServer(config)
