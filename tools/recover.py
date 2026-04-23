# auto reload module changes
get_ipython().extension_manager.load_extension("autoreload")  # pyright: ignore
get_ipython().run_line_magic('autoreload', 'complete --print')  # pyright: ignore

import rich
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_llama_server import ChatLlamaServer

model = ChatLlamaServer(base_url="http://paxy:8012", api_key="",
    # Qwen3.6 via llama-server
    # extra_body={"chat_template_kwargs": { "enable_thinking": False }}, \
)

messages = [
    HumanMessage("Read show.py and investigate how I display the tool call ID value... add a function to shorten the ID to a max of first 6 chars and use that to show the ID"),
    # HumanMessage("Explain this project, in the current directory"),
]

from run_python import run_command, run_python

agent = create_agent(model, tools=[run_python, run_command])

from show import stream_messages
await stream_messages(agent, messages) # pyright: ignore
