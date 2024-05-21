import asyncio
from urllib.request import parse_keqv_list
import websockets
import json
import ast
import time
import concurrent
from ast_transform import astor_fork
from ast_transform import transform
from ast_transform import scope_analyzer
from ast_transform import rewriter
from ast_transform import common
import orchestrator
import threading

class Conversation:
    def __init__(self, conversation_id, ws, code):
        self.conversation_id=conversation_id
        self.ws=ws
        self.code=code
        self.globals_dict = None


class ApiConductorServer:
    def __init__(self, config, port=8765):
        self.time_out=10
        self.port=port
        self.config=config
        self.ws_config = {}
        self.conversations={}
        self.server=None
        
        
    async def start(self):
        self.server = await websockets.serve(self.message, "localhost", self.port)

    async def start_and_wait(self):
        self.server = await websockets.serve(self.message, "localhost", self.port)
        await self.server.wait_closed()

    async def wait_for_close(self):
        await self.server.wait_closed()
        
    def close(self):
        if self.server != None:
            self.server.close()
        
    def run_exec(self, code, globals_dict):
        asyncio.set_event_loop(self.loop)
        try:
            exec(code, globals_dict)
            return None
        except Exception as e:
            return type(e).__name__+": "+str(e)

    async def execute_with_timeout(self, code, globals_dict, timeout):
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = self.loop.run_in_executor(executor, self.run_exec, code, globals_dict)
                try:
                    return await asyncio.wait_for(future, timeout)
                except asyncio.TimeoutError as e:
                    globals_dict["orchestrator"]._kill()
                    print("Execution timed out")
                    return type(e).__name__+": "+str(e)
                                
    async def run_code(self, data, ws):
        conversation_id = data["conversation_id"]
        code = data["code"]
        
        print()
        print()
        print(code)
        print()
        print()

        conversation = Conversation(conversation_id, ws, code)
        self.conversations[conversation_id]=conversation
        config = self.config
        if ws in self.ws_config:
            config = self.ws_config[ws]
        new_tree = transform.Transform(config).modify_code(conversation.code)
        conversation.new_code = astor_fork.to_source(new_tree)
        request = {
            "conversation_id": conversation_id,
            "new_code": conversation.new_code
        }
        send1 =  ws.send(json.dumps(request))
        await send1
        orchestror = orchestrator.Orchestrator(self, conversation_id)

        print()
        print()
        print( conversation.new_code)
        print()
        print()

                
        globals_dict = {'orchestrator': orchestror}
        conversation.globals_dict=globals_dict
        err=await self.execute_with_timeout(conversation.new_code, globals_dict, self.time_out)
        if err != None:
            request = {
                "conversation_id": conversation_id,
                "exception": err
            }
            send1 =  ws.send(json.dumps(request))
            await send1

        request = {
                    "conversation_id": conversation_id,
                    "done": None
                }
        
        del self.conversations[conversation_id]
        send2 =  ws.send(json.dumps(request))
        await send2


    def set_config(self, ws, data):
        config = common.Config()
        config.awaitable_functions = data["functions"]
        config.module_blacklist=None
        if "module_blacklist" in data:
            config.module_blacklist=data["module_blacklist"]
        config.wrap_in_function_def =False
        config.single_function=True
        self.ws_config[ws]=config
        
    def complete(self, data):
        conversation_id = data["conversation_id"]
        action_id = data["action_id"]
        result = data["result"]
        conversation= self.conversations[conversation_id]
        # modifying values being used by code that is running within exec() 
        conversation.globals_dict["orchestrator"].call_completion(action_id,result)
        

    async def message(self, ws, path):
        self.loop = asyncio.get_running_loop()
        async for message in ws:
            print(str(message))
            data = json.loads(message)
            if "code" in data:
                 task = asyncio.create_task(self.run_code(data, ws)) 
            elif "functions" in data:
                self.set_config(ws, data)
            elif "action_id" in data:
                self.complete(data)
            else:
                pass
            
    # if function paramaters are listed without keys, insert the keys
    # if we know what they should be.
    # i.e. search(3,4,5,x=8) => search(a=3,b=4,c=5,x=8)        
    def fix_parms(self, parms, conversation):
        if conversation.ws in self.ws_config:
            functions = self.ws_config[conversation.ws].awaitable_functions
            fn = parms[rewriter.Rewriter.FUNCTIONNAME]
            if fn in functions:
                new_parms={}
                plist = functions[fn]
                for key in parms.keys():
                    if isinstance(key, (int, float, complex)) and key<len(plist):
                        new_parms[plist[key]]=parms[key]
                    else:
                        new_parms[key]=parms[key]
                return new_parms
        return parms 
                
    def _return(self, conversation_id, val):
        conversation = self.conversations[conversation_id]
        
        request = {
                    "conversation_id": conversation_id,
                    "return": val
                }
        
        future = asyncio.run_coroutine_threadsafe(conversation.ws.send(json.dumps(request)), self.loop)
        _= future.result()
        
    def _call(self, conversation_id, parms):
        conversation = self.conversations[conversation_id]
        
        request = {
                    "conversation_id": conversation_id,
                    "call": self.fix_parms(parms, conversation)
                }
        
        future = asyncio.run_coroutine_threadsafe(conversation.ws.send(json.dumps(request)), self.loop)
        _= future.result()
                