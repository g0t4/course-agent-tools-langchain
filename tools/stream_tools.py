# auto reload module changes
get_ipython().extension_manager.load_extension("autoreload")  # pyright: ignore
get_ipython().run_line_magic('autoreload', 'complete --print')  # pyright: ignore

import rich
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langchain_llama_server import ChatLlamaServer

# TODO demo changes to this setup (but do it in your run_python.py "notebook")

model = ChatLlamaServer(base_url="http://paxy:8012", api_key="")

messages = [
    HumanMessage("List files in the current directory in a format like ls -al"),
    # HumanMessage("Tell me about the hardware in my computer"),
]

from run_python import run_command, run_python
agent = create_agent(model, tools=[run_python, run_command])

from show import stream_messages
await stream_messages(agent, messages) # pyright: ignore
