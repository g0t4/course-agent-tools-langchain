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
    HumanMessage("What is my hostname?"), # Qwen is reliably asking subagent to run hostname command first (that fails, so the subagent returns empty handed) then qwen reads file to get the hostname (WHEN using FilesystemBackend(virtual_mode=False))
]

agent = create_deep_agent(
    model=model,
    system_prompt="Always delegate commands and file system access to a subagent",
    permissions=[
        # FilesystemPermission(operations=["read"], paths=["/etc/hostname"]),
    ],
    # * be careful with backends (provides filesystem access and/or command execution)!
    # FYI default `backend=StateBackend()` is ephemeral in state (a virtual fs, not the real one)
    # docs to pick: https://docs.langchain.com/oss/python/deepagents/backends
    backend=FilesystemBackend(root_dir="/usr", virtual_mode=True),
    #
    # backend=FilesystemBackend(virtual_mode=False), # virtual_mode=False ==> everything (no commands)
    # backend=LocalShellBackend(virtual_mode=False), # same as FilesystemBackend + execute commands
)

events = await stream_messages(agent, messages) # pyright: ignore
