# auto reload module changes
get_ipython().extension_manager.load_extension("autoreload")  # pyright: ignore
get_ipython().run_line_magic('autoreload', 'complete --print')  # pyright: ignore

import rich
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_llama_server import ChatLlamaServer
from show import stream_messages
model = ChatLlamaServer(base_url="http://paxy:8012", api_key="")



from langchain_community.tools import YouTubeSearchTool

youtube_search_tool = YouTubeSearchTool()
youtube_search_tool.run("Wes Higbee gpt-oss, 3")










# %% 





messages = [
    HumanMessage("What videos has Wes Higbee produced about gpt-oss"),
]


tools = [youtube_search_tool]
agent = create_agent(model, tools=tools)

await stream_messages(agent, messages) # pyright: ignore

