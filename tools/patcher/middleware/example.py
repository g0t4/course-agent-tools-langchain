# auto reload module changes
get_ipython().extension_manager.load_extension("autoreload")  # pyright: ignore
get_ipython().run_line_magic('autoreload', 'complete --print')  # pyright: ignore

import rich
from langchain_llama_server import ChatLlamaServer
from deepagents import create_deep_agent

from patcher.middleware.middleware import AddApplyPatchToolMiddleware, ApplyPatchHooksMiddleware
import show
# show.last_events is populated even if you kill the trace (ctrl+c) or an exception interrupted it!
from show import *

model = ChatLlamaServer(
    base_url="http://paxy:8012",
    api_key="",
    # Qwen3.6 via llama-server
    # * disable thinking + give explicit instructions to gen parallel tool calls to Qwen3.6
    # extra_body={"chat_template_kwargs": { "enable_thinking": False }}, \
)

agent = create_deep_agent(model=model, )
get_tools(agent).keys()

agent = create_deep_agent(
    model=model,
    middleware=[AddApplyPatchToolMiddleware()],
)
get_tools(agent).keys()

# %%

# graph for middleware that adds tool only:
agent.get_graph().print_ascii()

# middleware w/ hooks too
agent_hooks = create_deep_agent(
    model=model,
    middleware=[ApplyPatchHooksMiddleware()],
)
agent_hooks.get_graph().print_ascii()

# %% 

hello = [HumanMessage("hello")]
events = await stream_messages(agent_hooks, hello)
