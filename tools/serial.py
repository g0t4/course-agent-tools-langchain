import rich
from datetime import datetime
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langchain_llama_server import ChatLlamaServer
from show import show_messages

model = ChatLlamaServer(base_url="http://paxy:8013", api_key="")

def get_the_time():
    """ Returns the local time in HH:MM AM/PM format"""
    return datetime.now().strftime("%I:%M %p")
    # return datetime.now() # surprise with date too

@tool(description="get the date in YYYY-mm-dd format")
def lookup_date():
    return datetime.now().strftime("%Y-%m-%d")

# %%

messages = [
    HumanMessage("Get me a unix timestamp for right now?"),
]

agent = create_agent(model, tools=[get_the_time, lookup_date])
thread = agent.invoke({"messages": messages})  # pyright: ignore

show_messages(thread["messages"])
