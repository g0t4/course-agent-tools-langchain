from langchain.chat_models import init_chat_model

model = init_chat_model("gpt-5.4")

response = model.invoke("Is it late?")
print(response.content)
