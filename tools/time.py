from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage

model = init_chat_model("gpt-5.4")

response = model.invoke("Is it late?")
print(response.content)

# %%

messages = [
    HumanMessage("Is it late?"),
    response,
    HumanMessage("How do I get the local time with python?")
]

response2 = model.invoke(messages)
print(response2.content)

# %% 
from datetime import datetime

local_time = datetime.now()
print(local_time)

# %% 
messages.append(response2)
messages.append(HumanMessage("the time is 2026-04-09 16:32:31.313067 "))

response3 = model.invoke(messages)
print(response3.content)
