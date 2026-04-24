import rich
from datetime import datetime
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langchain_llama_server import ChatLlamaServer
from show import show_messages

model = ChatLlamaServer(base_url="http://paxy:8012", api_key="", max_tokens=4096,
    # Qwen3.6 via llama-server
    extra_body={"chat_template_kwargs": { "enable_thinking": False }}, \
)

@tool("run_python")
def run_python__corrupted_time_time(code: str):
    """ Execute a python script and return STDOUT """
    import io
    import contextlib
    import traceback

    if "time.time" in code:
        return "ERROR - time.time module is corrupted"

    stdout = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout):
            exec(code, {})
    except Exception:
        return traceback.format_exc()
    # FYI, we could return more than just STDOUT!
    return stdout.getvalue()

messages = [
    HumanMessage("Get me a unix timestamp for right now!")
    # HumanMessage("Get ma  unix timestamp for right now!") # reasoning loop (sometimes)
]

agent = create_agent(model, tools=[run_python__corrupted_time_time])

from show import stream_messages
events = await stream_messages(agent, messages) # pyright: ignore

