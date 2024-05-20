from ast_transform import language_client
import asyncio
import time
from threading import Thread, Event

class MyConversation(language_client.Conversation):
    def __init__(self, client, code):
        super().__init__(client, code)
        
    def on_new_code(self,value):
        print("on new code: "+value)        
    
    def on_done(self):
        print("on done")        

    def on_exception(self,value):
        print("on exception: "+value)        
    
    def on_return(self,value):
        print("on return: "+str(value))        
    
    def on_complete(self):
        print("on complete ")        
    
    def on_call(self,value):
        _fn=value["_fn"]
        _id = value["_id"]
        del value["_fn"]
        del value["_id"]
        result=None
        if _fn == "search_email":
            result = self.search_email(**value)
        elif _fn == "search_teams":
            result = self.search_teams(**value)
        elif _fn == "search_meetings":
            result = self.search_meetings(**value)
        elif _fn == "wrap_string":
            result = self.wrap_string(**value)
        return (_id, result)
     
    def search_email(self, a=0, b=0, c=0):
        return a+100
    
    def search_teams(self, a=0, b=0, c=0):
        return a+100
    
    def search_meetings(self, a=0, b=0, c=0):
        return a+100
    
    def wrap_string(self, a=0, b=0, c=0):
        return a+100


if __name__ == '__main__':
    async def main():
        config = {'functions':{
            'search_email':['a','b','c'],
            'search_teams':['a','b','c'],
            'search_meetings':['a','b','c'],
            'wrap_string':['a','b','c'],
            }, 'module_blacklist':['io']}

        client = language_client.ApiConductorClient(config)

        src = """
x=1
a=search_email(x)
if (a<3):
    y=search_email(a+5)
else:
    y=search_email(a+10)
return y
"""
        conversation = MyConversation(client, src)
        await conversation.task

        client.close()
        
    asyncio.run(main())
