# auto reload module changes
get_ipython().extension_manager.load_extension("autoreload")  # pyright: ignore
get_ipython().run_line_magic('autoreload', 'complete --print')  # pyright: ignore

import show
from show import stream_messages

from langgraph.graph.state import RunnableConfig
import rich
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_llama_server import ChatLlamaServer
from langgraph.checkpoint.memory import InMemorySaver

# tools:
from run_python import run_command, run_python

model = ChatLlamaServer(base_url="http://paxy:8012", api_key="",
    # Qwen3.6 via llama-server
    # * disable thinking + give explicit instructions to gen parallel tool calls to Qwen3.6
    extra_body={"chat_template_kwargs": { "enable_thinking": False }}, \
    # tool calling is often much more interesting w/o reasoning enabled :)
)

messages = [
    # HumanMessage("Run two commands one at a time, run the first and get the result before the second: run_command(hostname) and run_python(add code to get timestamp)"),
    HumanMessage("""Run two commands one at a time, run the first and get the result before the second:
                 hostname
                 date
                 """),
]

from deepagents import create_deep_agent

checkpointer = InMemorySaver()
agent = create_deep_agent(
    checkpointer=checkpointer,
    model=model,
    # tools=[run_python, run_command],
    system_prompt="Follow the user request exactly as written and do not reinterpret or optimize it.",
)

agent.get_graph().print_ascii()

config: RunnableConfig = {
    "configurable": {
        "thread_id": "thread123"
    },
}

events = await stream_messages(agent, messages, config=config) # pyright: ignore

# %%

events = await stream_messages(agent, None, config=config) # pyright: ignore
