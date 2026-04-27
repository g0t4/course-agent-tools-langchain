# auto reload module changes
get_ipython().extension_manager.load_extension("autoreload")  # pyright: ignore
get_ipython().run_line_magic('autoreload', 'complete --print')  # pyright: ignore

from typing import Type
from langgraph.graph.state import RunnableConfig
from langgraph.types import Command
from pydantic import BaseModel, Field
import rich
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool, tool
from langchain_llama_server import ChatLlamaServer
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver

# tools:
from run_python import run_command, run_python

model = ChatLlamaServer(base_url="http://paxy:8012", api_key="",
    # Qwen3.6 via llama-server
    # * disable thinking + give explicit instructions to gen parallel tool calls to Qwen3.6
    extra_body={"chat_template_kwargs": { "enable_thinking": False }}, \
)

messages = [
    SystemMessage("Follow the user request exactly as written and do not reinterpret or optimize it."),
    HumanMessage("Run two commands one at a time, run the first and get the result before the second: run_command(hostname) and run_python(add code to get timestamp)"),
]

checkpointer = InMemorySaver()
agent = create_agent(
    model=model,
    tools=[run_python, run_command],
    checkpointer=checkpointer,
)

config: RunnableConfig = {
    "configurable": {
        "thread_id": "thread123"
    },
}

def dump_checkpoints():
    for what in checkpointer.list(config):
        rich.print(what)
dump_checkpoints()

# %%

import show
# show.last_events is populated even if you kill the trace (ctrl+c) or an exception interrupted it!
from show import stream_messages

events = await stream_messages(agent, messages, config=config) # pyright: ignore





















# %%

events = await stream_messages(agent, # pyright:ignore 
    None,
    config=config,
) 

































# %%

# events = await stream_messages(agent, # pyright:ignore 
#     Command(resume={}),
#     config=config,
# ) 



# dump_checkpoints()
#
# # "current" vs "history":
# checkpointer.get_tuple(config)
checkpointer.get_tuple(config) == [c for c in checkpointer.list(config)][0] # TRUE
#
#
# # "current" vs "history"
# rich.print([h for h in agent.get_state_history(config)])
agent.get_state(config) == [h for h in agent.get_state_history(config)][0]  # TRUE
#
# checkpoints are largely to preserve list of messages (w.r.t. agent graphs)
#  you could also just pass the messages list every time and manage it yourself, basically achieve same thing
#  but this is builtin so you don't have to
#  and makes it possible to resume after interrupt for approvals (HITL)
#
#
# # compare "current":
# rich.print(agent.get_state(config))
# checkpointer.get_tuple(config)
#
# # compare "history":
# rich.print([c for c in checkpointer.list(config)])
# rich.print([h for h in agent.get_state_history(config)])
#
# # can show "graph" of nodes that checkpointer operates on:
# # re-run w/ and w/o the HITL middleware and compare diff (separate tabs)
# rich.print(agent.get_graph())
#
# rich.print([sub for sub in agent.get_subgraphs()])  # fodder for later in course
#
# docs graph v checkpoint APIs: https://docs.langchain.com/oss/python/langgraph/add-memory#checkpointer-api
#
#
# BTW store vs state... good examples of memory via stores:
# - https://docs.langchain.com/oss/python/langgraph/persistence#super-steps
# - InMemoryStore
# from langgraph.store.memory import InMemoryStore
# store = InMemoryStore()
# agent  = create_agent (..., store = store)
