# auto reload module changes
get_ipython().extension_manager.load_extension("autoreload")  # pyright: ignore
get_ipython().run_line_magic('autoreload', 'complete --print')  # pyright: ignore

from deepagents.backends import FilesystemBackend, LocalShellBackend
from langchain.agents.middleware import HumanInTheLoopMiddleware
from run_python import run_command
import show
from show import stream_messages

import rich
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_llama_server import ChatLlamaServer
from deepagents import SubAgent, create_deep_agent




model = ChatLlamaServer(base_url="http://paxy:8012", api_key="",
    # Qwen3.6 via llama-server
    # * disable thinking + give explicit instructions to gen parallel tool calls to Qwen3.6
    # extra_body={"chat_template_kwargs": { "enable_thinking": False }}, \
)

messages = [
    # HumanMessage("What tools do you have?"),
    HumanMessage("What is my hostname?"),
]

# worker: SubAgent = {
#     "name": "worker",
#     "description": "Command line access to execute commands.",
#     "system_prompt": "Execute commands from your supervisor.",
#     "tools": [run_command],
# }
agent = create_deep_agent(
    model=model,
    backend=FilesystemBackend(virtual_mode=False),

    # subagents=[ worker ],
    # backend=LocalShellBackend(virtual_mode=False)
    # tools = [run_command]
)

# %% 

events = await stream_messages(agent, messages) # pyright: ignore

