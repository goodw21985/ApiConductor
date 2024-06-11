from ast_transform import language_client
import asyncio


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
    
    @language_client.managed_function
    def search_email(self, a=0, b=0, c=0):
        return a+100
    
    @language_client.managed_function
    def search_teams(self, a=0, b=0, c=0):
        return a+100
    
    @language_client.managed_function
    def search_meetings(self, a=0, b=0, c=0):
        return a+100
    
    @language_client.managed_function
    def wrap_string(self, a=0, b=0, c=0):
        return a+100


if __name__ == '__main__':
    async def main():
        config = {'module_blacklist':['io'], 'statement_whitelist':['if','for','return', 'pass']}

        client = language_client.ApiConductorClient(config, MyConversation)

        src = """
x=1
a=search_email(sum(x,2))
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
