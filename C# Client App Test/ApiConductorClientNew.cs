using System;
using System.Collections.Concurrent;
using System.Net.WebSockets;
using System.Text;
using System.Text.Json.Serialization;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using System.Reflection;

public class ApiConductorClientNew
{
    private readonly Uri _uri;
    private readonly ClientWebSocket _webSocket;
    private readonly CancellationTokenSource _cancellationTokenSource;
    private Task? _receiveTask = null;
    private readonly Config _config;
    private Dictionary<string, Conversation> _conversations = new Dictionary<string, Conversation>();
    Dictionary<string, MethodInfo> _function_lookup = new Dictionary<string, MethodInfo>();


    public ApiConductorClientNew(Config config, Type type, string uri = "ws://localhost:8765")
    {
        _config = config;
        _uri = new Uri(uri);
        _webSocket = new ClientWebSocket();
        _cancellationTokenSource = new CancellationTokenSource();

        this.BuildFunctionTable(type);

    }

    private void BuildFunctionTable(Type type)
    {
        var methodsWithManagedFunctionAttribute = type
            .GetMethods(BindingFlags.Public | BindingFlags.Instance | BindingFlags.DeclaredOnly)
            .Where(m => m.GetCustomAttribute<ManagedFunctionAttribute>() != null)
            .ToList();

        _config.Functions = new Dictionary<string, List<string>>();
        foreach (var method in methodsWithManagedFunctionAttribute)
        {
            var parameterNames = method.GetParameters()
                                                   .Select(p => p.Name ?? "<Unnamed>")
                                                   .ToList();
            var functionName = method.Name;
            _config.Functions[functionName] = parameterNames;
            _function_lookup[functionName] = method;
        }
    }


    public async Task ConnectAsync()
    {
        await _webSocket.ConnectAsync(_uri, _cancellationTokenSource.Token);
        Console.WriteLine("Connected to WebSocket server");
        var msg = this._config.ToString();
        await this.SendMessageAsync(msg);
        // Start the task to receive messages asynchronously
        this._receiveTask = ReceiveMessagesAsync();
    }

#pragma warning disable CS1998 // Async method lacks 'await' operators and will run synchronously
    public async Task CloseAsync()
#pragma warning restore CS1998 // Async method lacks 'await' operators and will run synchronously
    {
    }


#pragma warning disable CS1998 // Async method lacks 'await' operators and will run synchronously
    public async Task SendMessageAsync(Conversation conversation)
#pragma warning restore CS1998 // Async method lacks 'await' operators and will run synchronously
    {
        this._conversations[conversation._conversation_id] = conversation;
        var message = new Dictionary<string, string>
        {
            { "conversation_id", conversation._conversation_id },
            { "code", conversation._code }
        };

        string jsonString = JsonSerializer.Serialize(message, new JsonSerializerOptions { WriteIndented = true });


        var buffer = Encoding.UTF8.GetBytes(jsonString);
        var segment = new ArraySegment<byte>(buffer);
        await _webSocket.SendAsync(segment, WebSocketMessageType.Text, true, _cancellationTokenSource.Token);
        Console.WriteLine("started conversation");

//    await TestTestSendMessagesAsync();
    }


    public async Task TestTestSendMessagesAsync()
    {
        var message2 = @"{
  ""conversation_id"": ""5e28b5eb-c741-4458-b5a1-46aafe555283"",
  ""code"": ""\r\nx = 2\r\na = search_email(x)\r\nif (a \u003C 3):\r\n    y = search_email(a \u002B 5)\r\nelse:\r\n    y = search_email(a \u002B 10)\r\nreturn y\r\n""
}
";

        // Send the second message
        await SendMessageAsync(message2);
        Console.WriteLine($"Sent: {message2}");

        // Wait for the receive task to complete
        await this._receiveTask;

        await _webSocket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Closing", CancellationToken.None);
    }

    private async Task SendMessageAsync(string message)
    {
        var bytes = Encoding.UTF8.GetBytes(message);
        var buffer = new ArraySegment<byte>(bytes);
        await _webSocket.SendAsync(buffer, WebSocketMessageType.Text, true, CancellationToken.None);
    }

    private async Task ReceiveMessagesAsync()
    {
        Console.WriteLine("listening");
        var buffer = new byte[1024 * 64];

        while (_webSocket.State == WebSocketState.Open)
        {
            WebSocketReceiveResult? result = null;
            try
            {

                Array.Clear(buffer, 0, buffer.Length);
                result = await _webSocket.ReceiveAsync(new ArraySegment<byte>(buffer), CancellationToken.None);
            }
            catch (WebSocketException ex)
            {
                Console.WriteLine($"WebSocket error: {ex.Message}");
                break;
            }

            if (result.MessageType == WebSocketMessageType.Close)
            {
                await _webSocket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Closing", CancellationToken.None);
                break;
            }

            var message = Encoding.UTF8.GetString(buffer, 0, result.Count);
            Dictionary<string, object>? response = JsonSerializer.Deserialize<Dictionary<string, object>>(message);
            if (response == null)
            {
                continue;
            }
                if (response.TryGetValue("conversation_id", out var conversation_id) && this._conversations.TryGetValue(conversation_id?.ToString()??"", out var conversation))
            {
                if (response.TryGetValue("new_code", out var new_code))
                {
                    conversation.Enqueue(new Action("new_code", new_code));
                }
                else if (response.TryGetValue("exception", out var exception))
                {
                    conversation.Enqueue(new Action("exception", exception));
                }
                else if (response.TryGetValue("call", out var call))
                {
                    conversation.Enqueue(new Action("call", call));
                }
                else if (response.TryGetValue("done", out var done))
                {
                    conversation.Enqueue(new Action("done", done));
                }
                else if (response.TryGetValue("return", out var returnVal))
                {
                    conversation.Enqueue(new Action("return", returnVal));
                }
            }
        }
    }

    [AttributeUsage(AttributeTargets.Method, Inherited = false)]
    public class ManagedFunctionAttribute : Attribute
    {
        public ManagedFunctionAttribute()
        {
        }
    }

    public class Action
    {
        public readonly string _ev;
        public readonly dynamic _value;
        public Action(string ev, dynamic value)
        {
            this._ev = ev;
            this._value = value;
        }
    }

    public class AsyncQueue<T>
    {
        private readonly ConcurrentQueue<T> queue = new ConcurrentQueue<T>();
        private readonly SemaphoreSlim semaphore = new SemaphoreSlim(0);

        public void Enqueue(T item)
        {
            queue.Enqueue(item);
            semaphore.Release();
        }

        public async Task<T?> DequeueAsync(CancellationToken cancellationToken = default)
        {
            await semaphore.WaitAsync(cancellationToken);
            queue.TryDequeue(out T? item);
            return item;
        }
    }

    public class Conversation : IDisposable
    {
        public readonly ApiConductorClientNew _client;
        public readonly string _code;
        private Task _backgroundTask;
        private CancellationTokenSource _cancellationTokenSource;
        private bool _disposed = false;
        private readonly AsyncQueue<Action?> _messageQueue = new AsyncQueue<Action?>();
        public string _conversation_id = Guid.NewGuid().ToString();


        public Conversation(ApiConductorClientNew client, string code)
        {
            _client = client;
            _code = code;
            _cancellationTokenSource = new CancellationTokenSource();
            _backgroundTask = Task.Run(() => RunBackgroundTask(_cancellationTokenSource.Token));


        }

        public async Task Wait()
        {
            await _backgroundTask.ConfigureAwait(false);
        }


        public void Enqueue(Action message)
        {
            _messageQueue.Enqueue(message);
        }

        public void EnqueueTerminate()
        {
            _messageQueue.Enqueue(null);
        }

        private async Task RunBackgroundTask(CancellationToken token)
        {
            await this._client.SendMessageAsync(this);
            try
            {
                while (!token.IsCancellationRequested)
                {
                    var action = await _messageQueue.DequeueAsync(token);
                    if (action == null)
                    {
                        break; // Exit the loop if null is enqueued
                    }
                    switch (action._ev)
                    {
                        case "new_code":
                            this.on_new_code(action._value);
                            break;

                        case "call":
                            this.on_call(action._value);
                            break;

                        case "return":
                            this.on_return(action._value);
                            break;

                        case "done":
                            this.EnqueueTerminate();
                            break;

                        case "exception":
                            this.on_exception(action._value);
                            break;

                    }
                    // Process the message
                    Console.WriteLine($"Processing message: {action}");

                    // Example hook call
                    this.on_call(action);
                }

                this.on_complete();
            }
            catch (Exception ex)
            {
                this.on_exception(ex.Message);
            }
        }

        protected virtual void on_call(dynamic value)
        {
        }

        protected virtual void on_return(dynamic value)
        {
        }

        protected virtual void on_complete()
        {
        }

        protected virtual void on_new_code(string code)
        {
        }

        protected virtual void on_exception(string code)
        {
        }

        public void Stop()
        {
            if (_cancellationTokenSource != null)
            {
                _cancellationTokenSource.Cancel();
                _backgroundTask.Wait();
            }
        }

        // Dispose pattern to clean up resources
        protected virtual void Dispose(bool disposing)
        {
            if (!_disposed)
            {
                if (disposing)
                {
                    Stop();
                    _cancellationTokenSource.Dispose();
                }
                _disposed = true;
            }
        }

        public void Dispose()
        {
            Dispose(true);
            GC.SuppressFinalize(this);
        }
    }

    public class Config
    {
        [JsonPropertyName("functions")]
        public Dictionary<string, List<string>> Functions { get; set; } = new Dictionary<string, List<string>>();

        [JsonPropertyName("module_blacklist")]
        public List<string> ModuleBlacklist { get; set; } = new List<string>();

        public override string ToString()
        {
            string r = JsonSerializer.Serialize(this, new JsonSerializerOptions { WriteIndented = false });
            return r;
        }

    }
}
