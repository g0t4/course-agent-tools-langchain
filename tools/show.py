import rich
from rich.console import RenderableType
from rich.style import Style
from rich.syntax import Syntax
from rich.padding import Padding
from rich.live import Live
from rich.text import Text
from rich.tree import Tree
from rich.pretty import Pretty
from rich.markup import escape

import json
import sys
import asyncio
from dataclasses import dataclass
from typing import Any, TypedDict

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

def no_markup(text):
    """ 
    wrapper to make clear I don't want markup 
    Text alone is not specific, ableit it works too
    """
    return Text(text)

def _display_tool_message_content(message: ToolMessage, tree: Tree):
    content = message.content
    if message.name == "run_command":
        _display_tool_message_for_run_command(message, tree)
    # elif message.name == "run_python":
    #    _display_tool_run_python(message, tree)
    elif isinstance(content, str):
        lines = content.splitlines()
        if len(lines) > 5:
            tree.add(no_markup("\n".join(lines[:5]) + "\n..."))
        else:
            tree.add(no_markup(content))
    else:
        tree.add(Pretty(content))  # pretty spans multiple lines, is indented, looks very nice

def _display_tool_message_for_run_command(message: ToolMessage, tree: Tree):
    content = message.content
    if not isinstance(content, str):
        tree.add('[red]run_command message.content should be a string, but is not:[/]')  # Note: Rich parses markup in the string passed to tree.add, use Text() to block
        tree.add(Pretty(content))
        return

    try:
        obj = json.loads(content)
    except json.JSONDecodeError:
        # Show the error and raw content in the rich tree instead of the console
        tree.add("[red]failed to load JSON result:[/]") \
            .add(no_markup(content))
        return

    for key, value in obj.items():
        tree.add(f"[bold]{key}[/]:") \
            .add(no_markup(str(value)))
        # PRN dump value as json depending on value?

def show_pending_approvals(event: StreamEvent, tree: Tree):
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
    data = event.get("data")
    chunk = data.get("chunk")
    if not chunk:
        return
    if not isinstance(chunk, dict):
        return

    __interrupt__ = chunk.get("__interrupt__")
    if not __interrupt__:
        return

    for interrupt in __interrupt__:
        node = tree.add("[bold gray0 on deep_pink2]APPROVAL NEEDED[/]")
        node.add(BLANK_LINE)
        # node.add(Pretty(interrupt)) # dump interrupt object (like above)
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
            approval_node = node.add(f"{idx}. [bold]{name}[/]")
            if args:
                if name.startswith("run_python"):
                    code = args.get("code", "")
                    approval_node.add(Syntax(code, "python"))
                elif name.startswith("run_command"):
                    commandline = args.get("commandline", "")
                    approval_node.add(Syntax(commandline, "bash"))
                elif name == "apply_patch":
                    patch = args.get("patch", "")
                    approval_node.add(Syntax(patch, "diff"))
                else:
                    approval_node.add(Pretty(args))
            approval_node.add(f"[italic]{allowed}[/]")
            approval_node.add(BLANK_LINE)

@dataclass
class StreamingChunksState:
    node: Tree | None = None
    accumulated: AIMessageChunk | None = None

    def reset(self):
        """reset state for a new model response"""
        self.node = None
        self.accumulated = None

BLANK_LINE = ""

async def stream_messages(
    agent: Runnable,
    input: Any | list[BaseMessage] | Command | None,  # Any: for {"messages": list[BaseMessage] }
    *,
    dump_events = False,
    config: RunnableConfig | None = None,
    **kwargs,
):
    message_count = 0

    def increment_message_count():
        nonlocal message_count
        message_count += 1

    def show_tool_message(message: ToolMessage, tree: Tree):
        name = message.name
        id = message.tool_call_id
        show_id = ({id})
        child = tree.add(f"{message_count}. [bold gray0 on slate_blue1]ToolMessage[/]: [bold]{name}[/] ({id})")
        # FYI I could show the args pretty-ified here if I cache them and don't show on tool start
        _display_tool_message_content(message, child)
        child.add(BLANK_LINE)

    def show_system_message(message: SystemMessage, tree: Tree):
        child = tree.add(f"{message_count}. [bold gray0 on gold1]SystemMessage")
        child.add(no_markup(message.content))
        child.add(BLANK_LINE)

    def show_human_message(message: HumanMessage, tree: Tree):
        child = tree.add(f"{message_count}. [bold gray0 on slate_blue1]HumanMessage")
        child.add(no_markup(message.content))
        child.add(BLANK_LINE)

    def show_ai_message(message: AIMessage, tree: Tree):
        child = tree.add(f"{message_count}. [bold gray0 on deep_sky_blue3]AIMessage")
        reasoning = message.additional_kwargs.get("reasoning_content")
        if reasoning:
            reasoning_node = child.add("[bold]reasoning:[/]")
            reasoning_node.add(Text(reasoning, style="italic"))  # FYI Text does not parse/apply markup in the text value (1st positional arg)... use style to apply to the entire text value
            reasoning_node.add(BLANK_LINE)
        if message.content:
            content_node = child.add("[bold]content:[/]")
            content_node.add(no_markup(content))
            content_node.add(BLANK_LINE)
        if message.tool_calls:
            for call in message.tool_calls:
                # TODO? reuse? with streaming logic
                name = call.get("name", "")
                id = call.get("id", "")
                tool_tree = child.add(f"[bold]{name}[/] ({id})")
                args = call.get("args", "")
                if args:
                    tool_tree.add(Pretty(args))
                tool_tree.add(BLANK_LINE)

    def _dict_to_message(message: dict) -> BaseMessage:
        # FYI supported "role" strings: 'human', 'user', 'ai', 'assistant', 'function', 'tool', 'system', or 'developer'
        role = message.get("role")
        if role in ("human", "user"):
            return HumanMessage(**message)
        if role in ("ai", "assistant"):
            return AIMessage(**message)
        # PRN add support for role="function" ... probably can shoehorn into ToolMessage... but I also might want to show it as a separate message type
        if role == "tool":
            return ToolMessage(**message)
        if role in ("system", "developer"):
            return SystemMessage(**message)
        raise ValueError(f"Unsupported role: {role}")

    def _show_message(message, tree: Tree):
        if isinstance(message, dict):
            message = _dict_to_message(message)

        if isinstance(message, HumanMessage):
            show_human_message(message, tree)
        elif isinstance(message, SystemMessage):
            show_system_message(message, tree)
        elif isinstance(message, ToolMessage):
            show_tool_message(message, tree)
        elif isinstance(message, AIMessage):
            show_ai_message(message, tree)
        else:
            # do not raise b/c I use show_message for several scenarios beyond just initial messages... killing mid trace would not be fun
            branch = tree.add(f"[red]Unsupported message type: {type(message).__name__}[/]")
            branch.add(Pretty(message))
            branch.add(BLANK_LINE)

    def on_tool_start(event: StreamEvent, tree: Tree):
        # purpose is merely to show the arguments pretty printed (i.e. code/commandline)
        #  these are already shown from AIMessageChunks, so I don't have to redisplay these here
        #  PRN maybe I should score the need to redisplay them? and not do so unless it is a multiline known long arg
        tool_name = event["name"]
        # AFAICT there is no tool_call_id available on start event
        node = tree.add(f"[bold gray0 on deep_sky_blue3]Calling {tool_name}")

        data = event.get("data")
        args = data.get("input")
        assert isinstance(args, dict)
        if tool_name.startswith("run_python"):
            code = args.get("code", "")
            node.add(Syntax(code, "python"))
        elif tool_name.startswith("run_command"):
            commandline = args.get("commandline", "")
            node.add(Syntax(commandline, "bash"))
        elif tool_name == "apply_patch":
            patch = args.get("patch", "")
            node.add(Syntax(patch, "diff"))
        # else: FYI no reason to dump JSON again
        node.add(BLANK_LINE)

    def on_tool_end(event: StreamEvent, tree: Tree):
        increment_message_count()
        data = event.get("data")
        output = data.get("output")
        if isinstance(output, ToolMessage):
            _show_message(output, tree)
        else:
            # raise NotImplementedError("TODO how to display on_tool_end when output is not just a ToolMessage")
            # when you use the `task` tool then on_tool_end can return a Command to update multiple channels instead of just a new ToolMessage...
            # i.e. update files modified (tmp file creation by subagent)
            tree.add("[red bold] TODO SHOW ANYTHING for on_tool_end when output is not just a ToolMessage?")
            tree.add(Pretty(output))

    def on_chat_model_stream(event: StreamEvent, state: StreamingChunksState, tree: Tree):
        # streaming chunks so we can see response as it is generated
        chunk = event.get("data").get("chunk")
        assert isinstance(chunk, AIMessageChunk)

        if not state.accumulated:
            increment_message_count()
            state.accumulated = chunk
            state.node = tree.add(f"{message_count}. [bold gray0 on deep_sky_blue3]AIMessage")  # FYI header never needs updated (not currently)
        else:
            # accumulated holds cumulative chunks => effectively becomes AIMessage (handles reasoning/content/tool_calls chunking)
            state.accumulated = state.accumulated + chunk

        assert state.node is not None
        node = state.node
        node.children.clear()

        # standardized content blocks:
        #   https://docs.langchain.com/oss/python/langchain/messages#standard-content-blocks
        #   w.r.t streaming: https://docs.langchain.com/oss/python/langchain/streaming#streaming-thinking-/-reasoning-tokens
        # if not any(state.accumulated.content_blocks):
        #     return

        # node.add(Pretty(state.accumulated)) # actually looks really cool given the accumulated structure is preserved as chunks of it arrive and it fills out!

        message = state.accumulated

        # * model's reasoning
        reasoning: str = message.additional_kwargs.get("reasoning_content", "")  # w/o content_blocks, most providers set reasoning this way
        if reasoning:
            reasoning_node = node.add("[bold]reasoning:[/]")
            reasoning_node.add(Text(reasoning, style="italic"))
            reasoning_node.add(BLANK_LINE)

        # * model's content
        content: str = message.content  # w/o content_blocks
        if content:
            content_node = node.add("[bold]content:[/]")
            content_node.add(no_markup(content))
            content_node.add(BLANK_LINE)

        # * model's tool call request
        calls = message.tool_calls  # w/o content_blocks
        for call in calls:
            name = call.get("name", "")
            id = call.get("id", "")
            tool_tree = node.add(f"[bold]{name}[/] ({id})")

            args = call.get("args", "")
            if args:
                tool_tree.add(Pretty(args))
                # FYI until you receive the full json string, the value won't be valid json... so don't try to parse it
                #  for now leave tool specific argument formatters to the Calling tool in on_tool_start... otherwise you could show raw text until parses and then flip views to tool formatter but that might be jarring

            tool_tree.add(BLANK_LINE)

    def dump_all_events_except_streaming_tokens(event: StreamEvent, tree: Tree):
        event_type = event["event"]
        if event_type in {"on_chat_model_stream"}:
            return
        tree.add(Pretty(event))

    def show_input_messages(tree: Tree):
        nonlocal input
        if isinstance(input, Command) or input is None:
            # don't show command inputs, that's already obvious in the calling code
            return

        if isinstance(input, dict) and "messages" in input:
            # FYI I am not using this, just added this in case
            # someone passes { "messages": ... } like you would to astream_events
            # don't double wrap in that case
            for msg in input.get("messages", {}):
                increment_message_count()
                _show_message(msg, tree)
            return

        clear_screen()
        initial_messages = input
        # convenience to wrap in messages dict... b/c that's what astream_events/invoke/etc expects
        # I added this so you can pass initial_messages instead of always wrapping it
        input = {"messages": initial_messages}
        for tool_message in initial_messages:
            increment_message_count()
            _show_message(tool_message, tree)

    root = Tree("agent", hide_root=True)
    root.TREE_GUIDES = [("    ", "    ", "    ", "    ")]

    with Live(
            root,
            refresh_per_second=8,
            vertical_overflow="visible",  # default ellipsis (hides)
    ) as live:
        show_input_messages(root)

        tree = root
        events: list[StreamEvent] = []
        streaming_state = StreamingChunksState()
        event: StreamEvent
        async for event in agent.astream_events(input, version="v2", config=config, **kwargs):
            # https://reference.langchain.com/python/langchain-core/runnables/base/Runnable/astream_events
            # event type naming: on_[runnable_type]_(start|stream|end)
            # - runnable types: chain, chat_model, tool
            events.append(event)

            # optionally dump all non‑streaming events for debugging when requested
            if dump_events:
                dump_all_events_except_streaming_tokens(event, tree)

            event_type = event["event"]
            if event_type == "on_chain_start":
                # TODO! add nesting
                # tree = tree.add()
                pass
            elif event_type == "on_chain_end":
                # TODO! pop nesting
                # tree = tree.parent()?
                pass
            elif event_type == "on_chain_stream":
                show_pending_approvals(event, tree)
            elif event_type == "on_tool_start":
                on_tool_start(event, tree)
            elif event_type == "on_tool_end":
                on_tool_end(event, tree)
            elif event_type == "on_chat_model_start":
                streaming_state.reset()
            elif event_type == "on_chat_model_stream":
                on_chat_model_stream(event, streaming_state, tree)

    return events

def get_tools(agent: CompiledStateGraph):
    tools_node = agent.nodes["tools"]
    return tools_node.bound.tools_by_name

def show_tools(agent: CompiledStateGraph):
    tools = get_tools(agent)
    rich.inspect(tools)
