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

class GreeterToolInput(BaseModel):
    name: str = Field(description="Person's name to greet")

class GreeterTool(BaseTool):
    name: str = "Greeter"
    description: str = "Polite way to greet users"
    args_schema: Type[BaseModel] = GreeterToolInput

    def _run(self, name: str) -> str:
        return f"Hello {name}"


model = ChatLlamaServer(base_url="http://paxy:8012", api_key="",
    # Qwen3.6 via llama-server
    # * disable thinking + give explicit instructions to gen parallel tool calls to Qwen3.6
    extra_body={"chat_template_kwargs": { "enable_thinking": False }}, \
)

messages = [
    # HumanMessage("Run two commands in parallel: run_command(hostname) and run_command(date)"),
    SystemMessage(
        "This is a demonstration of LangChain human-in-the-loop approve/reject/edit. "
        "Follow the user request exactly as written and do not reinterpret or optimize it."
    ),
    # FYI ls -R / to demonstrate commands that are not wise!
    HumanMessage("Run two commands in parallel: run_command(ls -R /) and run_python(add code to get timestamp)"),
    # HumanMessage("Read show.py and investigate how I display the tool call ID value... add a function to shorten the ID to a max of first 6 chars and use that to show the ID"),
]

# FYI checkpointers: https://pypi.org/search/?q=langgraph-checkpoint
# import { PostgresStore } from "@langchain/langgraph-checkpoint-postgres/store";
checkpointer = InMemorySaver()
agent = create_agent(
    model=model,
    tools=[run_python, run_command, GreeterTool()],
    middleware=[
        HumanInTheLoopMiddleware(
            interrupt_on={
                "Greeter": False, # no approval needed
                "run_command": True,  # all allowed: approve, edit, reject
                "run_python": {"allowed_decisions": ["approve", "reject"]},  # cannot "edit"
            },
        ),
    ],
    checkpointer=checkpointer,
)

config: RunnableConfig = {
    "configurable": {
        "thread_id": "generate_a_thread_id_fawse234awe"
    },
}
# persist thread so we can resume with with the user's decision

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

events = await stream_messages(agent,
    Command(resume={"decisions": [
        # { "type": "approve" },
        # { "type": "reject" },

        # choose to edit run_command (note on_tool_start shows this new tool call instead)
        {
            "type": "edit",
            "edited_action": {
                "name": "run_command",
                "args": {
                    "commandline": "ls .",
                },
            }
        },
        { "type": "approve" },

    ]}),
    config=config,
)  # pyright: ignore







# %%




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
