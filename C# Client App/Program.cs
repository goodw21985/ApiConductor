using static ApiConductorClient;

class MyConversation : ApiConductorClient.Conversation
{
    public MyConversation(ApiConductorClient client, string code) : base(client, code) { }

    protected override void on_return(object value)
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

class Program
{
    static async Task Main(string[] args)
    {
        var config = new ApiConductorClient.Config
        {
            ModuleBlacklist = new List<string> { "io", "sockets", "sys" },
            StatementWhiteList = new List<string> { "if", "for", "return","pass" }
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



        var client = new ApiConductorClient(config, typeof(MyConversation));

        await client.ConnectAsync();

        var conversation = new MyConversation(client, src);
        await conversation.Wait();

        await client.CloseAsync();
    }
}

