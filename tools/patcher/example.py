# auto reload module changes
get_ipython().extension_manager.load_extension("autoreload")  # pyright: ignore
get_ipython().run_line_magic('autoreload', 'complete --print')  # pyright: ignore

import rich
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_llama_server import ChatLlamaServer

import show # for show.last_events
from show import stream_messages

model = ChatLlamaServer(
    base_url="http://paxy:8013",
    api_key="",
    # Qwen3.6 via llama-server
    # extra_body={"chat_template_kwargs": { "enable_thinking": False }}, \
)

messages = [
    HumanMessage("Make me a hello world lua module using apply_patch, then run it")
]

from run_python import run_command, run_python
from patcher.patcher import apply_patch
tools = [run_python, run_command, apply_patch]

agent = create_agent(model, tools=tools)

config = {"recursion_limit": 50}
events = await stream_messages(agent, messages, config=config) # pyright: ignore
