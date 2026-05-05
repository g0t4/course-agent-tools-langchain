# auto reload module changes
get_ipython().extension_manager.load_extension("autoreload")  # pyright: ignore
get_ipython().run_line_magic('autoreload', 'complete --print')  # pyright: ignore

from deepagents.backends import FilesystemBackend, LocalShellBackend
import rich
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_llama_server import ChatLlamaServer
from deepagents import FilesystemPermission, create_deep_agent
from show import stream_messages

model = ChatLlamaServer(
    base_url="http://paxy:8012",
    api_key="",
    # Qwen3.6 via llama-server
    # * disable thinking + give explicit instructions to gen parallel tool calls to Qwen3.6
    # extra_body={"chat_template_kwargs": { "enable_thinking": False }}, \
)

messages = [
    # successful, NOT subagent parallel tool calls
    HumanMessage("Run two commands in parallel: run_command(hostname) and run_command(date)"),
    # HumanMessage("Run two commands in parallel: run_command(ls -R) and run_command(date)"), # test truncated text output with `ls -R`
]

agent = create_deep_agent(
    model=model,
    system_prompt="Never delegate to a subagent", # PRN remove tool if I really don't want it doing this
    # * be careful with backends (provides filesystem access and/or command execution)!
    backend=LocalShellBackend(virtual_mode=False),
    # PRN add HumanInTheLoopMiddleware to play it safe
)

events = await stream_messages( # pyright: ignore
    agent,
    messages,
    # dump_events=True,
)  

