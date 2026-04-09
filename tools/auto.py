from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage

model = init_chat_model("gpt-5.4")

def get_the_time():
    """ Returns the local time """
    from datetime import datetime
    return datetime.now()

# %%
from langchain_core.utils.function_calling import convert_to_openai_tool

messages = [
    HumanMessage("Is it late?"),
]

tools = [convert_to_openai_tool(get_the_time)]

response1 = model.invoke(messages, tools=tools)
print(response1.content)

# %%

from langchain.agents import create_agent

agent = create_agent(model, tools=[get_the_time])
thread = agent.invoke({"messages": messages})
