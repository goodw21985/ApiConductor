using System;
using IronPython.Hosting;
using Microsoft.Scripting.Hosting;

class Program
{
    static void Main()
    {
        // Your Python code in a string
        string pythonCode = @"
x = 42
print(x)";

        string safePythonCode = "import orchestrator\n" + pythonCode;

        string escapedPythonCode = safePythonCode
    .Replace("\r", "")
    .Replace("\\", "\\\\") // Escape backslashes
    .Replace("\"", "\\\"") // Escape double quotes
    .Replace("\n", "\\n"); // Escape newlines

        string executePythonCode = $"import ast; ast.parse(\"{escapedPythonCode}\")";


        // Create a Python engine
        var engine = Python.CreateEngine();

        // Execute Python code to build the AST
        dynamic ast = engine.Execute(executePythonCode);

        // Print the AST
        Console.WriteLine(ast);
    }
}
