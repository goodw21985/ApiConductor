import asyncio
from urllib.request import parse_keqv_list
import websockets
import json
import ast
import time
import concurrent
from ast_transform import transform
from ast_transform import scope_analyzer
from ast_transform import rewriter
from ast_transform import common, orchestrator as orchestrator_module
import threading
import logging
import traceback


class Conversation:
    def __init__(self, conversation_id, ws, code):
        self.conversation_id=conversation_id
        self.ws=ws
        self.code=code
        self.globals_dict = None


class ApiConductorServer:
    def __init__(self, config, logger=None, port=8765):
        self.time_out=10
        self.port=port
        self.config=config
        self.ws_config = {}
        self.conversations={}
        self.server=None
        self.logger = logger or self._create_default_logger()        
        self.is_ready=False
        self.is_healthy=True
        
    async def start(self):
        try:
            self.server = await websockets.serve(self.message, "localhost", self.port)
            self.is_ready=True
            self.logger.info(f"websockets started")
        except Exception as e:
            self.logger.error(f"Failed to start WebSocket server: {e}")
            self.is_healthy = False

    async def start_and_wait(self):
        self.start()
        await self.server.wait_closed()

    async def wait_for_close(self):
        if self.server:
            await self.server.wait_closed()
            self.is_ready=False
            self.logger.info(f"websockets stopped")
        
    def _create_default_logger(self):
        logger = logging.getLogger('ApiConductorServer')
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    def get_health(self):
        self.logger.info(f"is_healthy = {self.is_healthy}")
        return self.is_healthy
    
    def get_readiness(self):
        self.logger.info(f"is_ready = {self.is_ready}")
        return self.is_ready
    
        
    def close(self):
        if self.server != None:
            self.is_ready=False
            self.logger.info("Closing the server")
            self.server.close()
        
    def run_exec(self, compiled_code, globals_dict, completion_event):
        asyncio.set_event_loop(self.loop)
        try:
            self.logger.info(f"exec code started")
            exec(compiled_code, globals_dict)
            self.logger.info(f"exec code complete")
            return None
        except Exception as e:
            self.logger.error(f"code execution exception: {e}")
            stack_trace = traceback.format_exc()
            self.logger.error(stack_trace)
            return type(e).__name__+": "+str(e)+ " -- " + stack_trace
        finally:
            completion_event.set()

    async def execute_with_timeout(self, compiled_code, globals_dict, timeout):
            completion_event = threading.Event()    
            with concurrent.futures.ThreadPoolExecutor() as executor:
                try:
                    future = self.loop.run_in_executor(executor, self.run_exec, compiled_code, globals_dict, completion_event)
                    try:
                        return await asyncio.wait_for(future, timeout)
                    except asyncio.TimeoutError as e:
                        self.logger.error(f"code timeout: {e}")
                        globals_dict["orchestrator"]._kill()
                        completion_event.wait()
                        return type(e).__name__+": "+str(e)
                except Exception as e2:
                    pass
                                
    async def run_code(self, data, ws):
        conversation_id = data["conversation_id"]
        code = data["code"]
        self.logger.info(f"received code: {code}")


        
        conversation = Conversation(conversation_id, ws, code)
        self.conversations[conversation_id]=conversation
        config = self.config
        if ws in self.ws_config:
            config = self.ws_config[ws]
        new_tree = transform.Transform(config).modify_code(conversation.code)
        conversation.new_code = ast.unparse(new_tree).strip()
        conversation.compiled_code = compile(new_tree, filename="<ast>", mode="exec")
        request = {
            "conversation_id": conversation_id,
            "new_code": conversation.new_code
            
        }
        send1 =  ws.send(json.dumps(request))
        await send1
        self.logger.info(f"generated code: {conversation.new_code}")

        orchestrator = orchestrator_module.Orchestrator(self, conversation_id)
                
        globals_dict = {'orchestrator': orchestrator}
        if self.config.built_ins_module:
            globals_dict.update({name: getattr(self.config.built_ins_module, name) for name in dir(self.config.built_ins_module) if not name.startswith('__')})

            if hasattr(self.config.built_ins_module, '__setup__'):
                setup_result = self.config.built_ins_module.__setup__(orchestrator)
                if setup_result:
                    globals_dict.update(setup_result)
            # Update the globals for each function in the globals_dict
            for name, func in globals_dict.items():
                if callable(func):
                    func.__globals__.update(globals_dict)
        conversation.globals_dict=globals_dict
        err=await self.execute_with_timeout(conversation.compiled_code, globals_dict, self.time_out)
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
        config.exposed_functions=None
        if "exposed_functions" in data:
            config.exposed_functions=data["exposed_functions"]
        config.statement_whitelist=None
        if "statement_whitelist" in data:
            config.statement_whitelist=data["statement_whitelist"]
        config.function_blacklist=None
        if "function_blacklist" in data:
            config.function_blacklist=data["function_blacklist"]
        config.wrap_in_function_def =False
        config.single_function=True
        self.ws_config[ws]=config
        
    def complete(self, data):
        conversation_id = data["conversation_id"]
        action_id = data["action_id"]
        result = data["result"]
        self.logger.info(f"completion {action_id}: {result}")

        conversation= self.conversations[conversation_id]
        # modifying values being used by code that is running within exec() 
        conversation.globals_dict["orchestrator"].call_completion(action_id,result)
        

    async def message(self, ws, path):
        self.loop = asyncio.get_running_loop()
        try:
            async for message in ws:
                data = json.loads(message)
                if "code" in data:
                     task = asyncio.create_task(self.run_code(data, ws)) 
                elif "functions" in data:
                    self.set_config(ws, data)
                elif "action_id" in data:
                    self.complete(data)
                else:
                    pass
        except Exception as e:
            stack_trace = traceback.format_exc()
            self.logger.error(f"WebSocket error: {e} -- {stack_trace}")
            self.is_healthy = False
            
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
        self.logger.info(f"return: {val}")

        request = {
                    "conversation_id": conversation_id,
                    "return": val
                }
        
        future = asyncio.run_coroutine_threadsafe(conversation.ws.send(json.dumps(request)), self.loop)
        _= future.result()
        
    def format_function_call(self, call_dict):
        # Extract the _id and _fn from the dictionary
        _id = call_dict.pop('_id')
        _fn = call_dict.pop('_fn')
    
        # Format the parameters part
        params = ', '.join(f'{key}={value}' for key, value in call_dict.items())
    
        # Format the final function call string
        formatted_call = f"{_id} = {_fn}({params})"
    
        return formatted_call

    def _call(self, conversation_id, parms):
        conversation = self.conversations[conversation_id]
        fixed_parms = self.fix_parms(parms, conversation)

        request = {
                    "conversation_id": conversation_id,
                    "call": fixed_parms
                }
        
        self.logger.info(f"call request: {self.format_function_call(dict(fixed_parms))}")

        future = asyncio.run_coroutine_threadsafe(conversation.ws.send(json.dumps(request)), self.loop)
        _= future.result()
                