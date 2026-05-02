from langchain.tools import ToolRuntime
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langgraph.types import Command

@tool(description="Execute a shell commandline and return its STDOUT.")
def run_command_command(tool_call_id: str, commandline: str) -> ToolMessage:
    import subprocess

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
    return ToolMessage(content=content, status=status, tool_call_id=tool_call_id)

# PRN try Command instead of ToolMessage:
#  return Command(update={"messages": [ToolMessage]})
#  that's what deepagent's task and write_todos tools do
#  def run_command_command(commandline: str) -> Command:
#      return Command(update={
#         "messages": [
#             ToolMessage(
#                 content=f"[custom] {x.upper()}",
#                 # tool_call_id will be injected if omitted
#             )
#         ]
#     })
