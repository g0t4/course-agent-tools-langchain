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
    """ Execute a python script and return STDOUT """
    import io
    import contextlib
    import traceback
    stdout = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout):
            exec(code, {})
    except Exception:
        return traceback.format_exc()
    return stdout.getvalue()

def run_command(commandline: str) -> dict[str, str | int]:
    """Execute a shell commandline and return its STDOUT."""
    import subprocess
    result = subprocess.run(
        commandline,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return {
        "stdout": result.stdout,
        "returncode": result.returncode,
    }

# %%

messages = [
    HumanMessage("Get me a unix timestamp for right now?"),
]

agent = create_agent(model, tools=[run_python, run_command])
thread = agent.invoke({"messages": messages})  # pyright: ignore

show_messages(thread["messages"])
