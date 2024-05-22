using static ApiConductorClientNew;

class MyConversation : ApiConductorClientNew.Conversation
{
    public MyConversation(ApiConductorClientNew client, string code) : base(client, code) { }

    protected override void on_call(dynamic value)
    {
        Console.WriteLine($"on call {value}");
    }

    protected override void on_return(dynamic value)
    {
        Console.WriteLine($"on_return {value}");
    }

    protected override void on_complete()
    {
        Console.WriteLine($"on_complete");
    }

    protected override void on_new_code(string code)
    {
        Console.WriteLine($"on_new_code: {code}");
    }

    protected override void on_exception(string exc)
    {
        Console.WriteLine($"on_exception {exc}");
    }

    [ManagedFunction]
    public int search_email(int a = 0, int b = 0, int c = 0)
    {
        return a + 100;
    }

    [ManagedFunction]
    public int search_teams(int a = 0, int b = 0, int c = 0)
    {
        return a + 100;
    }

    [ManagedFunction]
    public int search_meetings(int a = 0, int b = 0, int c = 0)
    {
        return a + 100;
    }
}

class NewProgram
{
    static async Task Main(string[] args)
    {
        var config = new ApiConductorClientNew.Config
        {
            ModuleBlacklist = new List<string> { "io", "sockets", "sys" }
        };

        string src = @"
x = 2
a = search_email(x)
if (a < 3):
    y = search_email(a + 5)
else:
    y = search_email(a + 10)
return y
";



        var client = new ApiConductorClientNew(config, typeof(MyConversation));

        await client.ConnectAsync();
        //await client.TestTestSendMessagesAsync();

        var conversation = new MyConversation(client, src);
        await conversation.Wait();

        Console.WriteLine("Press any key to close the connection...");
        Console.ReadKey();

        await client.CloseAsync();
    }
}

