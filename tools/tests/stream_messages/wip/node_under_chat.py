# auto reload module changes
get_ipython().extension_manager.load_extension("autoreload")  # pyright: ignore
get_ipython().run_line_magic('autoreload', 'complete --print')  # pyright: ignore

import builtins
from typing import Any, Callable, Sequence
from deepagents.backends import FilesystemBackend, LocalShellBackend
from langchain_core.language_models.base import LanguageModelInput
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
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
    extra_body={"chat_template_kwargs": { "enable_thinking": False }}, \
)

messages = [
    # successful, NOT subagent parallel tool calls
    HumanMessage("Run two commands in parallel: run_command(hostname) and run_command(date)"),
]

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration

class RefiningChatModel(BaseChatModel):

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        # This is not what I want yet, just spiking ideas for nested nodes under chat_model node... however this is just a series of generations... not nested  
        draft = model.invoke(messages)
        critique = model.invoke(
            messages + [AIMessage(content=f"Critique this:\n{draft.content}")]
        )
        final = model.invoke(
            messages + [AIMessage(content=f"Rewrite this, fixing issues:\n{draft.content}\n\n{critique.content}")]
        )
        return ChatResult(
            generations=[
                ChatGeneration(message=final)
            ]
        )

    @property
    def _llm_type(self):
        return "refining_chat_model"

    def bind_tools(self, tools: Sequence[builtins.dict[str, Any] | type | Callable | BaseTool], *, tool_choice: str | None = None, **kwargs: Any) -> Runnable[LanguageModelInput, AIMessage]:
        # return model.bind_tools(tools, tool_choice=tool_choice, **kwargs)
        return self
 

agent = create_deep_agent(
    model=RefiningChatModel(),
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

