# auto reload module changes
get_ipython().extension_manager.load_extension("autoreload")  # pyright: ignore
get_ipython().run_line_magic('autoreload', 'complete --print')  # pyright: ignore

import show
from show import stream_messages

import rich
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_llama_server import ChatLlamaServer
from deepagents import create_deep_agent




model = ChatLlamaServer(base_url="http://paxy:8012", api_key="",
    # Qwen3.6 via llama-server
    # * disable thinking + give explicit instructions to gen parallel tool calls to Qwen3.6
    extra_body={"chat_template_kwargs": { "enable_thinking": False }}, \
)

messages = [
    HumanMessage("What is my hostname?"),
]

agent = create_deep_agent(
    model=model,
    system_prompt="Follow the user request exactly as written and do not reinterpret or optimize it.",
)

events = await stream_messages(agent, messages) # pyright: ignore

# %% 

output = agent.invoke({"messages": messages})
rich.print(output)
