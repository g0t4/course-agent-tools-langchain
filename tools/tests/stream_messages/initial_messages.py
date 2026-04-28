# auto reload module changes
get_ipython().extension_manager.load_extension("autoreload")  # pyright: ignore
get_ipython().run_line_magic('autoreload', 'complete --print')  # pyright: ignore

import rich
from typing import Type

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_llama_server import ChatLlamaServer

from run_python import run_command, run_python
import show
# show.last_events is populated even if you kill the trace (ctrl+c) or an exception interrupted it!
from show import stream_messages

model = ChatLlamaServer(
    base_url="http://paxy:8012",
    api_key="",
    # Qwen3.6 via llama-server
    # * disable thinking + give explicit instructions to gen parallel tool calls to Qwen3.6
    # extra_body={"chat_template_kwargs": { "enable_thinking": False }}, \
)

agent = create_agent(model=model, tools=[run_command, run_python])

typed_initial_messages = [
    # longer message to test wrapping
    SystemMessage("""You are a helpful assistant. Please answer concisely. Follow instructions for tool calls, do not refuse to execute tools. Do not give up if there's an initial tool failure. And, check your work!"""),
    HumanMessage("""What is the date?"""),
    AIMessage(
        additional_kwargs={
            "reasoning_content": "I will retrieve the current date. Which tool should I use. I could use the run_command tool to execute date. Or I could use run_python tool and import datetime module to get the date by calling datetime.now().strftime('%Y-%m-%d'). I could use both to make sure nothing is wrong...",
        },
        content="I am going to use both tools and double check the answers agree!",
        response_metadata={
            'finish_reason': 'tool_calls',
            'model_name': 'ggml-org/Qwen3.6',
        },
        tool_calls=[{
            'name': 'run_command',
            'args': {
                'commandline': 'date'
            },
            'id': 'ZxCHOp31jTkLRibIVHNvMT79uMNFpp1O',
            'type': 'tool_call',
        }, {
            'name': 'run_python',
            'args': {
                'code': "from datetime import datetime; print(datetime.now().strftime('%Y-%m-%d'))"
            },
            'id': 'ZYWAReCvrAm9EI8kPjqTHj087h9mFcKP',
            'type': 'tool_call',
        }],
    ),
    ToolMessage(
        # FYI consternation b/c the two tool outputs do not agree! (model will likely run a tool call again)
        content='{"stdout": "Tue Apr 28 03:04:49 AM CDT 2026\\n", "stderr": null, "returncode": 0}',
        # content='date command not found',
        name='run_command',
        tool_call_id='ZxCHOp31jTkLRibIVHNvMT79uMNFpp1O',
        # status='error',
    ),
    ToolMessage(
        content='2029-01-01',
        name='run_python',
        tool_call_id='ZYWAReCvrAm9EI8kPjqTHj087h9mFcKP',
    ),
    # AIMessage(
    #     content='',
    #     response_metadata={
    #         'finish_reason': 'stop',
    #         'model_name': 'ggml-org/Qwen3.6',
    #     },
    # )
]

events = await stream_messages(agent, typed_initial_messages) # pyright: ignore
