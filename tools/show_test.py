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
    extra_body={"chat_template_kwargs": { "enable_thinking": False }}, \
    # comment out to test how reasoning displays

)

messages = [
    SystemMessage("test"),
    HumanMessage("Run two commands in parallel: run_command(hostname) and run_command(date)"),
    AIMessage("NO"),
    HumanMessage("NOW!"),

    # * demo recursion limit quickly (esp. w/ thinking off)
    # HumanMessage("I want you to run the date command 30 times, ONE run_command at a time, echo the value you get each time and then repeat."),
    # GraphRecursionError: Recursion limit of 25 reached without hitting a stop condition. You can increase the limit by setting the `recursion_limit` config key.
    # For troubleshooting, visit: https://docs.langchain.com/oss/python/langgraph/errors/GRAPH_RECURSION_LIMIT
]

from run_python import run_command, run_python

agent = create_agent(model, tools=[run_python, run_command])

import show
# show.last_events is populated even if you kill the trace (ctrl+c) or an exception interrupted it!
from show import stream_messages

events = await stream_messages(agent, messages) # pyright: ignore
