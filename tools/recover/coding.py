# auto reload module changes
get_ipython().extension_manager.load_extension("autoreload")  # pyright: ignore
get_ipython().run_line_magic('autoreload', 'complete --print')  # pyright: ignore

import rich
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_llama_server import ChatLlamaServer

model = ChatLlamaServer(base_url="http://paxy:8013", api_key="",
    # Qwen3.6 via llama-server
    # extra_body={"chat_template_kwargs": { "enable_thinking": False }}, \
)

messages = [
    # HumanMessage("Can you run show.lua for me?"), # Qwen3.6 runs `lua show.lua` and that fails => so it `ls -l` and corrects to find `show.py`
    SystemMessage("Do not use slow commands like `ls -R`"),
    HumanMessage("Explain this project, in the ~/repos/github/g0t4/mcp-server-commands"),
    # HumanMessage("Read show.py and investigate how I display the tool call ID value... add a function to shorten the ID to a max of first 6 chars and use that to show the ID"),
    # HumanMessage("What does the code in `cat show.lua` do?"),
]

from run_python import run_command, run_python

agent = create_agent(model, tools=[run_python, run_command])

import show
# show.last_events is populated even if you kill the trace (ctrl+c) or an exception interrupted it!
from show import stream_messages

events = await stream_messages(agent, messages) # pyright: ignore
