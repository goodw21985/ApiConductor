namespace C__Orchestrator
{
    using System;
    using System.Diagnostics;
    using IronPython.Hosting;
    using Microsoft.Scripting.Hosting;

    class Program
    {
        static void Main()
        {
            // Set up the Python runtime and engine
            ScriptEngine engine = Python.CreateEngine();
            ScriptScope scope = engine.CreateScope();

            Stopwatch stopwatch = Stopwatch.StartNew();
            // Load the Python script
            engine.ExecuteFile("script.py", scope);
            var v1 = stopwatch.ElapsedMilliseconds;

            // Load the Python script
            engine.ExecuteFile("script.py", scope);
            var v2 = stopwatch.ElapsedMilliseconds-v1;
            engine.ExecuteFile("script.py", scope);
            var v3 = stopwatch.ElapsedMilliseconds-v2-v1;
            // Invoke Python functions from C#
            dynamic addFunc = scope.GetVariable("add_numbers");
            int result = addFunc(5, 3);
            Console.WriteLine($"The result of adding is: {result}");

            dynamic greetFunc = scope.GetVariable("greet");
            string greeting = greetFunc("Alice");
            Console.WriteLine(greeting);

            // C# function to be called from Python
            Func<string, string> shout = str => str.ToUpper() + "!!!";
            scope.SetVariable("shout", shout);

            // Python code calling the C# function
            string pythonCode = @"
def call_shout():
    return shout('hello from python')
";
            dynamic callShout = engine.Execute(pythonCode, scope).GetVariable("call_shout");
            Console.WriteLine(callShout());
        }
    }
}
