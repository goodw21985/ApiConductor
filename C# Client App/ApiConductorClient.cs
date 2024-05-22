using System.Collections.Concurrent;
using System.Net.WebSockets;
using System.Reflection;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;

public class ApiConductorClient
{
    private readonly Uri _uri;
    private readonly ClientWebSocket _webSocket;
    private readonly CancellationTokenSource _cancellationTokenSource;
    private Task? _receiveTask = null;
    private readonly Config _config;
    private Dictionary<string, Conversation> _conversations = new Dictionary<string, Conversation>();
    Dictionary<string, MethodInfo> _function_lookup = new Dictionary<string, MethodInfo>();

    public ApiConductorClient(Config config, Type type, string uri = "ws://localhost:8765")
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
        this._receiveTask = Task.Run(ReceiveMessagesAsync);
    }

    public async Task SendMessageAsync(Conversation conversation)
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
    }

    public async Task SendMessageAsync(string message)
    {
        var buffer = Encoding.UTF8.GetBytes(message);
        var segment = new ArraySegment<byte>(buffer);
        await _webSocket.SendAsync(segment, WebSocketMessageType.Text, true, _cancellationTokenSource.Token);
        Console.WriteLine("started connection");
    }

    private async Task ReceiveMessagesAsync()
    {
        Console.WriteLine("listening");
        var buffer = new byte[1024 * 64];
        while (!_cancellationTokenSource.Token.IsCancellationRequested)
        {
            WebSocketReceiveResult? result = null;
            try
            {
                Array.Clear(buffer, 0, buffer.Length);
                result = await _webSocket.ReceiveAsync(new ArraySegment<byte>(buffer), _cancellationTokenSource.Token);
            }
            catch (WebSocketException ex)
            {
                Console.WriteLine($"WebSocket error: {ex.Message}");
                break;
            }

            if (result.MessageType == WebSocketMessageType.Close)
            {
                await _webSocket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Closing", _cancellationTokenSource.Token);
                Console.WriteLine("WebSocket closed");
                break;
            }

            string message = Encoding.UTF8.GetString(buffer, 0, result.Count);
            JsonDocument document = JsonDocument.Parse(message);
            JsonElement root = document.RootElement;

            var response = JsonUtilities.JsonElementToObject(root) as IDictionary<string, object?>;
            if (response == null)
            {
                continue;
            }

            if (response.TryGetValue("conversation_id", out var conversation_id))
            {
                if (this._conversations.TryGetValue(conversation_id?.ToString() ?? "", out Conversation? conversation))
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
    }

    public async Task CloseAsync()
    {
        _cancellationTokenSource.Cancel();
        try
        {
            await _webSocket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Closing", CancellationToken.None);
            if (_receiveTask != null)
            {
                await _receiveTask;
            }
        }
        catch { }
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
        public readonly object _value;
        public Action(string ev, object? val)
        {
            this._ev = ev;
            this._value = val??new object();
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
        public readonly ApiConductorClient _client;
        public readonly string _code;
        private Task _backgroundTask;
        private CancellationTokenSource _cancellationTokenSource;
        private bool _disposed = false;
        private readonly AsyncQueue<Action?> _messageQueue = new AsyncQueue<Action?>();
        public string _conversation_id = Guid.NewGuid().ToString();


        public Conversation(ApiConductorClient client, string code)
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
                            this.on_new_code(action._value.ToString()??"");
                            break;

                        case "call":
                            (string action_id, object result) = this.on_call(action._value);
                            var message = new Dictionary<string, object>
                            {
                                { "conversation_id", this._conversation_id },
                                { "action_id", action_id },
                                { "result", result},
                            };

                            string jsonString = JsonSerializer.Serialize(message, new JsonSerializerOptions { WriteIndented = true });
                            await this._client.SendMessageAsync(jsonString);
                            break;

                        case "return":
                            this.on_return(action._value);
                            break;

                        case "done":
                            this.EnqueueTerminate();
                            break;

                        case "exception":
                            this.on_exception(action._value.ToString()??"");
                            break;

                    }
                }

                this.on_complete();
            }
            catch (Exception ex)
            {
                this.on_exception(ex.Message);
            }
        }

        protected virtual (string action_id, object result) on_call(object desc)
        {
            var dict = desc as Dictionary<string, object?>; 
            if (dict==null)
            {
                throw new ArgumentException("malformed call description");
            }

            if (!dict.TryGetValue("_fn", out var fno) || !(fno is string fn) || !this._client._function_lookup.TryGetValue(fn, out var methodInfo))
            {
                throw new ArgumentException("missing function name");
            }

            if (!dict.TryGetValue("_id", out var ido) || !(ido is string action_id))
            {
                throw new ArgumentException("missing function id");
            }

            ParameterInfo[] paramInfos = methodInfo.GetParameters();
            if (paramInfos == null)
            {
                throw new ArgumentException("missing parameters for managed function");
            }
            else
            {
                object[] paramValues = new object[paramInfos.Length];

                // Populate the parameter values from the dictionary
                for (int i = 0; i < paramInfos.Length; i++)
                {
                    if (dict.TryGetValue(paramInfos[i].Name ?? "", out object? value))
                    {
                        paramValues[i] = Convert.ChangeType(value ?? new object(), paramInfos[i].ParameterType);
                    }
                    else if (paramInfos[i].HasDefaultValue)
                    {
                        paramValues[i] = paramInfos[i].DefaultValue;
                    }
                    else
                    {
                        throw new ArgumentException($"Missing parameter: {paramInfos[i].Name}");
                    }
                }

                // Invoke the method
                var result = methodInfo.Invoke(this, paramValues) ?? new object();
                return (action_id, result);
            }
        }

        protected virtual void on_return(object value)
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

    public static class JsonUtilities
    {
        public static object? JsonElementToObject(JsonElement element)
        {
            
            return element.ValueKind switch
            {
                JsonValueKind.Object => JsonElementToDictionary(element),
                JsonValueKind.Array => JsonElementToList(element),
                JsonValueKind.String => element.GetString(),
                JsonValueKind.Number => GetNumberValue(element),
                JsonValueKind.True => true,
                JsonValueKind.False => false,
                JsonValueKind.Null => null,
                _ => throw new InvalidOperationException($"Unsupported JsonValueKind: {element.ValueKind}"),
            };
        }

        private static IDictionary<string, object?> JsonElementToDictionary(JsonElement element)
        {
            var dictionary = new Dictionary<string, object?>();

            foreach (JsonProperty property in element.EnumerateObject())
            {
                dictionary[property.Name] = JsonElementToObject(property.Value);
            }

            return dictionary;
        }

        private static IList<object?> JsonElementToList(JsonElement element)
        {
            var list = new List<object?>();

            foreach (var item in element.EnumerateArray())
            {
                list.Add(JsonElementToObject(item));
            }

            return list;
        }

        private static object GetNumberValue(JsonElement element)
        {
            if (element.TryGetInt32(out int intValue))
                return intValue;
            if (element.TryGetInt64(out long longValue))
                return longValue;
            if (element.TryGetDouble(out double doubleValue))
                return doubleValue;
            return element.GetDecimal();
        }
    }
}

