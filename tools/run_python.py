import rich
from datetime import datetime
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langchain_llama_server import ChatLlamaServer
from show import show_messages

model = ChatLlamaServer(base_url="http://paxy:8013", api_key="")

def run_python(code: str):
    """ Execute a python script and return STDOUT
        FYI you can use subprocess to run system commmands too!
    """
    # raise NotImplementedError()
    import io
    import contextlib
    import traceback
    stdout = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout):
            exec(code, {})
    except Exception:
        return traceback.format_exc()
    # FYI, we could return more than just STDOUT!
    return stdout.getvalue()

@tool(description="Execute a shell commandline and return its STDOUT.")
def run_command(commandline: str):
    import subprocess

    # block ls -R
    if commandline.strip().startswith("ls -R"):
        return "COMMAND BLOCKED. Recursive listing with `ls -R` is blocked because `ls` has no default mechanism to exclude directories like node_modules, .venv, etc. This leads to an explosion of output. Use `fd --type file` to recursively list files."

    result = subprocess.run(
        commandline,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }

# %%

# messages = [
#     HumanMessage("List files in the current directory in a format like ls -al"),
# ]
#
# agent = create_agent(model, tools=[run_python])
# thread = agent.invoke({"messages": messages})  # pyright: ignore
#
# show_messages(thread["messages"])
