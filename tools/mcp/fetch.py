# auto reload module changes
get_ipython().extension_manager.load_extension("autoreload")  # pyright: ignore
get_ipython().run_line_magic('autoreload', 'complete --print')  # pyright: ignore

import rich
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langchain_llama_server import ChatLlamaServer
from show import stream_messages
model = ChatLlamaServer(base_url="http://paxy:8012", api_key="")





from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent

client = MultiServerMCPClient({
    # https://github.com/g0t4/mcp-servers
    "fetch": {

    }
})



messages = [
    HumanMessage("Tell me the world news"),
]


tools = await client.get_tools()
agent = create_agent(model, tools=tools)

await stream_messages(agent, messages) # pyright: ignore

