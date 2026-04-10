import rich
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
# from langchain_openai import ChatOpenAI
from langchain_llama_server import ChatLlamaServer

# model = init_chat_model("gpt-5.4")
# model = ChatLlamaServer(base_url="http://paxy.lan:8013", api_key="")
model = init_chat_model("anthropic:claude-sonnet-4-6")

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

# %%

def show_messages(messages):
    for m in messages:
        if isinstance(m, HumanMessage):
            rich.print(f'[bold slate_blue1]Human[/]', end="")
            print(f': {m.content}')
        elif isinstance(m, AIMessage):
            if m.content:
                rich.print(f'[bold deep_sky_blue3]AI[/]', end="")
                print(f': {m.content}')
            if m.tool_calls:
                for call in m.tool_calls:
                    rich.print(f'[bold deep_sky_blue3]Tool call[/]', end="")
                    print(": " + call["name"], end="")
                    print(f'({call["args"]})')
        elif isinstance(m, ToolMessage):
            rich.print(f'[bold slate_blue1]Tool[/]', end="")
            print(f': {m.content}')
        else:
            rich.print(f"unexpected message type: {m}")

show_messages(thread["messages"])
