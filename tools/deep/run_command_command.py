import subprocess
from langchain.tools import ToolRuntime
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langgraph.types import Command

@tool(description="Execute a shell commandline and return its STDOUT.")
# def run_command_command(tool_call_id: str, commandline: str) -> ToolMessage:
# def run_command_command(runtime: ToolRuntime, commandline: str) -> ToolMessage:
def run_command_command(runtime: ToolRuntime, commandline: str) -> Command:

    # block ls -R
    if commandline.strip().startswith("ls -R"):
        explain = "COMMAND BLOCKED. Recursive listing with `ls -R` is blocked because `ls` has no default mechanism to exclude directories like node_modules, .venv, etc. This leads to an explosion of output. Use `fd --type file` to recursively list files."
        return ToolMessage(content=explain)

    result = subprocess.run(
        commandline,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    content = {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }
    status = "success" if result.returncode == 0 else "error"
    # FYI content value is slightly different as a result of passing ToolMessage but has all the same info
    # return ToolMessage(content=content, status=status, tool_call_id=tool_call_id)
    # return ToolMessage(content=content, status=status, tool_call_id=runtime.tool_call_id)
    return Command(update={
        #  FYI this is what deepagent's task and write_todos tools do
        "messages": [
            ToolMessage(content=content, status=status, tool_call_id=runtime.tool_call_id),
        ]
    })
