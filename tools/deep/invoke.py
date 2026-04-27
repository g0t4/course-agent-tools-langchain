# auto reload module changes
get_ipython().extension_manager.load_extension("autoreload")  # pyright: ignore
get_ipython().run_line_magic('autoreload', 'complete --print')  # pyright: ignore

from typing import Type
from deepagents.backends import FilesystemBackend, LocalShellBackend
from deepagents.backends.protocol import SandboxBackendProtocol
from langgraph.graph.state import RunnableConfig
from langgraph.pregel.main import queue
from langgraph.types import Command
from pydantic import BaseModel, Field
import rich
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool, tool
from langchain_llama_server import ChatLlamaServer
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from deepagents import create_deep_agent

model = ChatLlamaServer(base_url="http://paxy:8012", api_key="",
    # Qwen3.6 via llama-server
    # * disable thinking + give explicit instructions to gen parallel tool calls to Qwen3.6
    # extra_body={"chat_template_kwargs": { "enable_thinking": False }}, \
)

messages = [
    HumanMessage("""What is my hostname?"""),
]

agent = create_deep_agent(
    model=model,
)

import show
# show.last_events is populated even if you kill the trace (ctrl+c) or an exception interrupted it!
from show import stream_messages

events = await stream_messages(agent, messages) # pyright: ignore

# %% 

output = agent.invoke({"messages": messages})
rich.print(output)
