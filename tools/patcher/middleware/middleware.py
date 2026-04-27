# auto reload module changes
get_ipython().extension_manager.load_extension("autoreload")  # pyright: ignore
get_ipython().run_line_magic('autoreload', 'complete --print')  # pyright: ignore

from typing import Any, Sequence
from langgraph.runtime import Runtime
from langgraph.types import Overwrite
import rich
from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import ResponseT, StateT, ContextT
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from patcher.patcher import apply_patch

class AddApplyPatchToolMiddleware(AgentMiddleware):
    tools = [apply_patch]

class ApplyPatchHooksMiddleware(AddApplyPatchToolMiddleware):

    def before_agent(self, state: StateT, runtime: Runtime[ContextT]) -> dict[str, Any] | None:
        rich.print("[deep_pink1 bold]BEFORE_AGENT[/]")
        return {
            'messages': Overwrite([HumanMessage(content='Goodbye!', additional_kwargs={}, response_metadata={}, id='b8585dcb-9082-4d4b-9244-1e9d15c57227')]),
        }

    def after_agent(self, state: StateT, runtime: Runtime[ContextT]) -> dict[str, Any] | None:
        rich.print("[deep_pink1 bold]AFTER_AGENT[/]")
        # PRN demo return

    def before_model(self, state: StateT, runtime: Runtime[ContextT]) -> dict[str, Any] | None:
        rich.print("[deep_pink1 bold]BEFORE_MODEL[/]")

    def after_model(self, state: StateT, runtime: Runtime[ContextT]) -> dict[str, Any] | None:
        rich.print("[deep_pink1 bold]AFTER_MODEL[/]")

    # TODO other middleware examples?
    # wrap tool calls, model calls
