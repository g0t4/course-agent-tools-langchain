# auto reload module changes
get_ipython().extension_manager.load_extension("autoreload")  # pyright: ignore
get_ipython().run_line_magic('autoreload', 'complete --print')  # pyright: ignore

import rich
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langchain_llama_server import ChatLlamaServer

from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper

wikipedia = WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper())

# wikipedia.run("AMD consumer CPUs")


# %% 

from run_python import run_command, run_python

model = ChatLlamaServer(base_url="http://paxy:8012", api_key="")

messages = [
    HumanMessage("What are some modern AMD consumer CPUs?"),
]

agent = create_agent(model, tools=[run_python, run_command, wikipedia])

from show import stream_messages
await stream_messages(agent, messages) # pyright: ignore
