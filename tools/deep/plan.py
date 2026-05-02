# auto reload module changes
get_ipython().extension_manager.load_extension("autoreload")  # pyright: ignore
get_ipython().run_line_magic('autoreload', 'complete --print')  # pyright: ignore

import os
from langgraph.graph.state import RunnableConfig
import rich
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langchain_llama_server import ChatLlamaServer
from deepagents import SubAgent, create_deep_agent
from deepagents.backends import FilesystemBackend, LocalShellBackend

from run_python import run_command
from deep.run_command_command import run_command_command
import show
from show import stream_messages

client = MultiServerMCPClient({
    "fetch": {
        "transport": "stdio",
        "command": "uvx",
        "args": [
            "--directory",
            os.environ["HOME"] + "/repos/github/g0t4/mcp-servers/src/fetch",
            "mcp-server-fetch",
        ],
    }
})
mcp_tools = await client.get_tools()
qwen_nothink = ChatLlamaServer(base_url="http://paxy:8012", api_key="",
    extra_body={"chat_template_kwargs": { "enable_thinking": False }}, \
)

qwen = ChatLlamaServer(base_url="http://paxy:8012", api_key="")

gptoss = ChatLlamaServer(base_url="http://paxy:8013", api_key="")

web_researcher: SubAgent = {
    "name": "web-researcher",
    "description": "Access to browse the web and search to find information in response to questions.",
    "system_prompt": "Search the web to find answers for your supervisor. You can use any search engine you like. DO NOT GUESS links to pages, use a search engine.",
    "tools": mcp_tools,
    "model": gptoss,
}
command_runner: SubAgent = {
    "name": "command-runner",
    "description": "Command line access to execute commands.",
    "system_prompt": "Execute commands from your supervisor.",
    "tools": [run_command_command],
    "model": qwen_nothink,
}
agent = create_deep_agent(
    model=gptoss,
    subagents=[ 
        command_runner, 
        web_researcher 
    ],
    checkpointer = InMemorySaver()
    # no backends intentionally => no execute command => forces the use of subagents
)

          

messages = [ 
    # HumanMessage("What is your name? Then, ask ALL subagent types to return their name")
    # HumanMessage("show me a md table and `inline code blocks`")
    # HumanMessage("ask the web research to list its tools + arguments per tool")
    # * rich.print([e for e in events if e["event"] == "on_chat_model_end"][-1]["data"]["output"].content)
    
    # HumanMessage("Run the false command and let the exit code remain nonzero"),

    # HumanMessage("search for RTX 6000 Pro on amazon.com") # blocks

    # good demo of scratchpad b/w tool calls and reasoning/planning upfront as well as along the way
    #   thanks to repeating the same request of subagents 3 times and diffing the result
    HumanMessage(
"""
First, list the tools you have as the supervisor. 
Then, ask ALL subagent types to list its tools and report back a final list of all tools for all agents.
Do not make assumptions about what tools a given agent has, ask each one.
"""),

#     # HumanMessage("How much would it cost, in today's prices, to rebuild the machine you are running on right now?"),
#     HumanMessage("""Tell me about the hardware in my machine. 
# And links to the product page for ONE hardware item (NOT ALL OF THEM).
# Validate web links are functional.
#  """)

]

configs: RunnableConfig = {"recursion_limit": 200, "configurable":{ "thread_id": "test1", } }

events = await stream_messages(agent, messages, config=configs)  # pyright: ignore

