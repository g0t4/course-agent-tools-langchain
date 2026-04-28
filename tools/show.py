import rich
from rich.console import RenderableType
from rich.syntax import Syntax
from rich.padding import Padding
import json
import sys
import asyncio
from dataclasses import dataclass

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage, AIMessageChunk
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.runnables.schema import StreamEvent
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

console = rich.console.Console()

def show_messages(messages):
    for m in messages:
        if isinstance(m, HumanMessage):
            console.print(f'[bold slate_blue1]Human[/]', end="")
            print(f': {m.content}')
        elif isinstance(m, AIMessage):
            if m.content:
                console.print(f'[bold deep_sky_blue3]AI[/]', end="")
                print(f': {m.content}')
            if m.tool_calls:
                for call in m.tool_calls:
                    console.print(f'[bold deep_sky_blue3]Tool call[/]', end="")
                    name = call["name"]
                    print(": " + name, end="")
                    if name == "run_python":
                        print()
                        code = call["args"]["code"]
                        syntax = Syntax(code, "python", theme="monokai")
                        console.print(Padding(syntax, pad=(0, 0, 0, 4)))
                    elif name == "run_command":
                        print()
                        code = call["args"]["commandline"]
                        syntax = Syntax(code, "bash", theme="monokai")
                        console.print(Padding(syntax, pad=(0, 0, 0, 4)))
                    elif name == "apply_patch":
                        print()
                        patch = call["args"]["patch"]
                        syntax = Syntax(call["args"]["patch"], "diff", theme="monokai")
                        console.print(Padding(syntax, pad=(0, 0, 0, 4)))
                    else:
                        print(f'({call["args"]})')

        elif isinstance(m, ToolMessage):
            console.print(f'[bold slate_blue1]Tool[/]', end="")
            print(f': {m.content}')
        else:
            console.print(f"unexpected message type: {m}")

def clear_screen():
    from IPython import get_ipython
    # optional, clear screen first:
    get_ipython().run_line_magic("clear", "")

def _display_tool_message_content(message: ToolMessage):
    content = message.content
    if message.name == "run_command":
        _display_tool_message_for_run_command(message)
    # elif message.name == "run_python":
    #    _display_tool_run_python(message)
    elif isinstance(content, str):
        lines = content.splitlines()
        if len(lines) > 5:
            writeln_indented("\n".join(lines[:5]) + "\n...", markup=False)
        else:
            writeln_indented(content, markup=False)  # return all lines
    else:
        writeln_indented(json.dumps(content))

def _display_tool_message_for_run_command(message: ToolMessage):
    content = message.content
    if not isinstance(content, str):
        console.print('[red]run_command message.content should be a string, but is not... [/]')
        writeln_indented(json.dumps(content), markup=False)
        return

    try:
        obj = json.loads(content)
    except json.JSONDecodeError:
        console.print("[red]failed to load JSON result...[/]")
        writeln_indented(content, markup=False)
        return

    for k, v in obj.items():
        writeln_indented(f"[bold]{k}[/]:", markup=True)
        writeln_indented(str(v), markup=False)  # PRN dump value as json depending on value?

def writeln_indented(msg: RenderableType, *args, **kwargs):
    console.print(Padding(msg, (0, 0, 0, 4)), *args, **kwargs)
    sys.stdout.flush()

def writeln(msg: RenderableType = "", *args, **kwargs):
    console.print(msg or "", *args, **kwargs)
    sys.stdout.flush()

def write(msg: RenderableType, *args, **kwargs):
    console.print(msg, end="", *args, **kwargs)
    sys.stdout.flush()

def show_pending_approvals(data):
    # trigger HITL approvals
    #   use gptoss for one at a time
    #   use Qwen3.6 for parallel tool calls w/ two approvals arriving together
    # Interrupt(
    #     value={
    #         'action_requests': [
    #             {
    #                 'name': 'run_command',
    #                 'args': {'commandline': 'hostname'},
    #                 'description': "Tool execution pending approval\n\nTool: run_command\nArgs:
    # {'commandline': 'hostname'}"
    #             },
    #             {
    #                 'name': 'run_command',
    #                 'args': {'commandline': 'date'},
    #                 'description': "Tool execution pending approval\n\nTool: run_command\nArgs:
    # {'commandline': 'date'}"
    #             }
    #         ],
    #         'review_configs': [
    #             {
    #                 'action_name': 'run_command',
    #                 'allowed_decisions': ['approve', 'edit', 'reject']
    #             },
    #             {
    #                 'action_name': 'run_command',
    #                 'allowed_decisions': ['approve', 'edit', 'reject']
    #             }
    #         ]
    #     },
    #     id='8784b505500ed4b71d24ba3105d43dfc'
    # )
    chunk = data.get("chunk")
    if not chunk:
        return
    if not isinstance(chunk, dict):
        return

    __interrupt__ = chunk.get("__interrupt__")
    if not __interrupt__:
        return

    for interrupt in __interrupt__:
        writeln()
        writeln("[bold gray0 on deep_pink2]APPROVAL NEEDED[/]")
        # console.print(interrupt) # dump interrupt object (like above)
        actions = interrupt.value.get("action_requests", [])
        review_configs = interrupt.value.get("review_configs", [])
        assert len(actions) == len(review_configs)
        # actions and review configs correspond
        for idx, (request, config) in enumerate(zip(actions, review_configs), start=1):
            # description = request.get('description')  # description usually is just prefix + tool name + args, I'm going to go directly to name/args and use those
            name = request.get('name')
            args = request.get('args', {})
            #
            action_name = config.get('action_name')
            allowed = ', '.join(config.get('allowed_decisions', []))
            writeln()
            writeln_indented(f"{idx}. [bold]{name}[/]")
            if args:
                if name.startswith("run_python"):
                    code = args.get("code", "")
                    writeln_indented(Padding(Syntax(code, "python"), pad=(0, 0, 0, 4)))
                elif name.startswith("run_command"):
                    commandline = args.get("commandline", "")
                    writeln_indented(Padding(Syntax(commandline, "bash"), pad=(0, 0, 0, 4)))
                elif name == "apply_patch":
                    patch = args.get("patch", "")
                    writeln_indented(Padding(Syntax(patch, "diff"), pad=(0, 0, 0, 4)))
                else:
                    writeln_indented(Padding(str(args), pad=(0, 0, 0, 4)))
            writeln_indented(Padding(f"[italic]{allowed}[/]", pad=(0, 0, 0, 4)))

@dataclass
class StreamingChunksState:
    ai_started: bool = False
    ai_has_reasoning: bool = False
    ai_has_content: bool = False
    chunk_count: int = 0

    def reset(self):
        """reset state for a new model response"""
        self.ai_started = False
        self.ai_has_reasoning = False
        self.ai_has_content = False
        self.chunk_count = 0

async def stream_messages(agent: Runnable, input: list[BaseMessage] | Command | None, *, config: RunnableConfig | None = None, **kwargs):

    indent2_spaces = " " * 8
    message_index = 0

    def show_tool_message(message: ToolMessage):
        name = message.name
        id = message.tool_call_id
        show_id = ({id})
        writeln(f"{message_index}. [bold gray0 on slate_blue1]ToolMessage[/]: [bold]{name}[/] ({id})")
        # FYI I could show the args pretty-ified here if I cache them and don't show on tool start
        _display_tool_message_content(message)

    def show_system_message(message: SystemMessage):
        writeln(f"{message_index}. [bold gray0 on gold1]SystemMessage")
        writeln_indented(message.content, markup=False)

    def show_human_message(message: HumanMessage):
        writeln(f"{message_index}. [bold gray0 on slate_blue1]HumanMessage")
        writeln_indented(message.content, markup=False)

    def show_ai_message(message: AIMessage):
        writeln(f"{message_index}. [bold gray0 on deep_sky_blue3]AIMessage")
        reasoning = message.additional_kwargs.get("reasoning_content")
        if reasoning:
            write(f"    [bold]reasoning:[/] ")
            writeln(reasoning, markup=False)
        if message.content:
            write(f"    [bold]content:[/] ")
            writeln(message.content, markup=False)
        if message.tool_calls:
            for tool_call in message.tool_calls:
                # writeln_indented(json.dumps(tool_call, indent=2))
                id = tool_call.get("id", "")
                name = tool_call.get("name", "")
                if name:
                    write(f"\n    [bold]{name}[/]")
                    write("\n" + indent2_spaces)

                args = tool_call.get("args", "")
                if args:
                    write(json.dumps(args), markup=False)

    def _show_message(message):
        if isinstance(message, HumanMessage):
            show_human_message(message)
        elif isinstance(message, SystemMessage):
            show_system_message(message)
        elif isinstance(message, ToolMessage):
            show_tool_message(message)
        elif isinstance(message, AIMessage):
            show_ai_message(message)
        else:
            # do not raise b/c I use show_message for several scenarios beyond just initial messages... killing mid trace would not be fun
            console.print(f"[red]Unsupported message type: {type(message).__name__}[/]")
            console.print(message, markup=False)
        writeln()  # just like on_chat_model_end for non-initial messages

    def on_tool_start(event):
        # purpose is merely to show the arguments pretty printed (i.e. code/commandline)
        #  these are already shown from AIMessageChunks, so I don't have to redisplay these here
        #  PRN maybe I should score the need to redisplay them? and not do so unless it is a multiline known long arg
        tool_name = event["name"]
        # AFAICT there is no tool_call_id available on start event
        writeln_indented(f"[bold gray0 on deep_sky_blue3]Calling {tool_name}")

        data = event.get("data")
        args = data.get("input")
        assert isinstance(args, dict)
        if tool_name.startswith("run_python"):
            code = args.get("code", "")
            writeln_indented(Syntax(code, "python"))
            writeln()
        elif tool_name.startswith("run_command"):
            commandline = args.get("commandline", "")
            writeln_indented(Syntax(commandline, "bash"))
            writeln()
        elif tool_name == "apply_patch":
            patch = args.get("patch", "")
            writeln_indented(Syntax(patch, "diff"))
            writeln()
        # else: FYI no reason to dump JSON again

    def on_tool_end(event):
        nonlocal message_index
        message_index += 1
        data = event.get("data")
        output = data.get("output")
        if isinstance(output, ToolMessage):
            _show_message(output)
        else:
            # raise NotImplementedError("TODO how to display on_tool_end when output is not just a ToolMessage")
            # when you use the `task` tool then on_tool_end can return a Command to update multiple channels instead of just a new ToolMessage...
            # i.e. update files modified (tmp file creation by subagent)
            rich.print("[red bold] TODO SHOW ANYTHING for on_tool_end when output is not just a ToolMessage?")

    def dump_all_events_except_streaming_tokens():
        if event_name not in {"on_chat_model_stream"}:
            console.print(event, markup=False)

    if isinstance(input, Command) or input is None:
        # don't show command inputs, that's already obvious in the calling code
        pass
    elif isinstance(input, dict) and "messages" in input:
        # FYI I am not using this, just added this in case
        # someone passes { "messages": ... } like you would to astream_events
        # don't double wrap in that case
        for msg in input["messages"]:
            message_index += 1
            _show_message(msg)
    else:
        # convenience to wrap in messages dict
        clear_screen()  # think Ctrl+L => so chat starts at top and grows downward
        initial_messages = input
        input = {"messages": initial_messages}
        # * show initial messages
        for tool_message in initial_messages:
            message_index += 1
            _show_message(tool_message)

    events: list[StreamEvent] = []
    state = StreamingChunksState()
    event: StreamEvent
    async for event in agent.astream_events(input, version="v2", config=config, **kwargs):
        # https://reference.langchain.com/python/langchain-core/runnables/base/Runnable/astream_events
        # event type naming: on_[runnable_type]_(start|stream|end)
        # - runnable types: chain, chat_model, tool
        events.append(event)
        event_name = event["event"]
        data = event['data']

        # dump_all_events_except_streaming_tokens()
        # # continue

        if event_name == "on_chain_stream":
            show_pending_approvals(data)
        elif event_name == "on_tool_start":
            on_tool_start(event)
        elif event_name == "on_tool_end":
            on_tool_end(event)
        elif event_name == "on_chat_model_end":
            writeln()  # all messages end with blank line
        elif event_name == "on_chat_model_start":
            state.reset()

        # * streaming AIMessageChunks (Model => User)
        elif event_name == "on_chat_model_stream":
            # streaming chunks so we can see response as it is generated
            state.chunk_count += 1
            chunk = data.get("chunk")
            assert isinstance(chunk, AIMessageChunk)

            if not state.ai_started:
                message_index += 1
                state.ai_started = True
                writeln(f"{message_index}. [bold gray0 on deep_sky_blue3]AIMessage")

            # standardized content blocks:
            #   https://docs.langchain.com/oss/python/langchain/messages#standard-content-blocks
            #   w.r.t streaming: https://docs.langchain.com/oss/python/langchain/streaming#streaming-thinking-/-reasoning-tokens
            if not any(chunk.content_blocks):
                continue

            block = chunk.content_blocks[0]
            # ? what if len(chunk.content) > 1
            block_type = block.get("type", "")

            # FYI the following assumes ordered chunks per type
            #   no interleaving of reasoning/content/tool_call chunks
            #   all reasoning chunks first (if any) => then content => then tool call(s)
            # BTW not all providers return reasoning tokens

            # * model's reasoning
            # reasoning: str = chunk.additional_kwargs.get("reasoning_content", "") # w/o content_blocks, most providers set reasoning this way
            if block_type == "reasoning":
                if not state.ai_has_reasoning:
                    write(f"    [bold]reasoning:[/] ")
                    state.ai_has_reasoning = True
                write(block.get("reasoning", ""), markup=False)

            # * model's content
            # content: str = chunk.content # w/o content_blocks
            if block_type == "text":
                if not state.ai_has_content:
                    if state.ai_has_reasoning:
                        writeln()  # new line to end reasoning
                    write(f"    [bold]content:[/] ")
                    state.ai_has_content = True
                write(block.get("text", ""), markup=False)

            # * model's tool call request
            # calls = chunk.tool_call_chunks # w/o content_blocks
            if block_type == "tool_call_chunk":
                tool_call = block
                # call_index = tool_call.get("index", "")

                # * first chunk has name+id:
                name = tool_call.get("name", "")
                id = tool_call.get("id", "")
                if name:
                    write(f"\n    [bold]{name}[/] ({id})")
                    # start args on next line, indented
                    write("\n" + indent2_spaces)

                # * chunks 2+ have part of args
                args = tool_call.get("args", "")
                if args:
                    args_indented = args.replace("\n", f"\n{indent2_spaces}")  # replace with indent to match initial indent
                    write(args_indented, markup=False)

    return events

def get_tools(agent: CompiledStateGraph):
    tools_node = agent.nodes["tools"]
    return tools_node.bound.tools_by_name

def show_tools(agent: CompiledStateGraph):
    tools = get_tools(agent)
    rich.inspect(tools)
