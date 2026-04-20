# auto reload module changes
get_ipython().extension_manager.load_extension("autoreload")  # pyright: ignore
get_ipython().run_line_magic('autoreload', 'complete --print')  # pyright: ignore

from typing import Type
from pydantic import BaseModel, Field
import rich
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import BaseTool, tool
from langchain_llama_server import ChatLlamaServer

model = ChatLlamaServer(base_url="http://paxy:8012", api_key="")

messages = [
    HumanMessage("Hi my name is Wes"),
]


class GreeterToolInput(BaseModel):
    name: str = Field(description="Person's name to greet")

class GreeterTool(BaseTool):
    name: str = "Greeter"
    description: str = "Polite way to greet users"
    args_schema: Type[BaseModel] = GreeterToolInput

    def _run(self, name: str) -> str:
        return f"Hello {name}"








agent = create_agent(model, tools=[GreeterTool()])

from show import stream_messages
await stream_messages(agent, messages) # pyright: ignore
