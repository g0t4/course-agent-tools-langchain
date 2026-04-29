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
    try:
        from IPython import get_ipython
        ip = get_ipython()
        if ip:
            ip.run_line_magic("clear", "")
    except Exception:
        # Silently ignore if IPython is not available or any error occurs.
        pass

def _display_tool_message_content(message: ToolMessage, tree: "TreeWrapper"):
    content = message.content
    if message.name == "run_command":
        _display_tool_message_for_run_command(message, tree)
    # elif message.name == "run_python":
    #    _display_tool_run_python(message, tree)
    elif isinstance(content, str):
        lines = content.splitlines()
        if len(lines) > 5:
            tree.add_no_markup("\n".join(lines[:5]) + "\n...")
        else:
            tree.add_no_markup(content)
    else:
        tree.add_pretty(content)  # pretty spans multiple lines, is indented, looks very nice

def _display_tool_message_for_run_command(message: ToolMessage, tree: "TreeWrapper"):
    if not isinstance(message.content, str):
        tree.add_markup('[red]run_command message.content should be a string, but is not:[/]')
        tree.add_pretty(message.content)
        return
    tree.add_sections_from_json_keys(message.content)

def show_approval_interrupts(event: StreamEvent, tree: "TreeWrapper"):
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
        node = tree.add_markup("[bold gray0 on deep_pink2]APPROVAL NEEDED[/]")
        node.blank_line()
        # node.add_pretty(interrupt) # dump interrupt object (like above)
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
            approval_node = node.add_markup(f"{idx}. [bold]{name}[/]")
            if args:
                if name.startswith("run_python"):
                    code = args.get("code", "")
                    approval_node.add_syntax(code, "python")
                elif name.startswith("run_command"):
                    commandline = args.get("commandline", "")
                    approval_node.add_syntax(commandline, "bash")
                elif name == "apply_patch":
                    patch = args.get("patch", "")
                    approval_node.add_syntax(patch, "diff")
                else:
                    approval_node.add_pretty(args)
            approval_node.add_markup(f"[italic]{allowed}[/]")
            approval_node.blank_line()

class TreeWrapper(Tree):
    """ Thin wrapper around :class:`rich.tree.Tree` with additional helpers. """

    parent: "TreeWrapper | None" = None

    def blank_line(self) -> None:
        BLANK_LINE = ""

        if not self.children:
            self.add(BLANK_LINE)
            return

        last = self.children[-1]
        label = last.label
        if isinstance(label, Text):
            ends_newline = label.plain.endswith("\n")
        else:
            ends_newline = isinstance(label, str) and label.endswith("\n")
        if not ends_newline:
            self.add(BLANK_LINE)

    def add(self, *renderables, **kwargs) -> "TreeWrapper":
        """ make sure child trees are all TreeWrapper type too """
        node = super().add(*renderables, **kwargs)
        if not isinstance(node, TreeWrapper):
            node.__class__ = TreeWrapper
        node.parent = self
        return node

    def add_no_markup(self, text: str, **kwargs) -> "TreeWrapper":
        """ make explicit this content should not have markup rendered """
        # btw Text == plain unless you pass a style arg
        return self.add(Text(text), **kwargs)

    def add_markup(self, text: str, **kwargs) -> "TreeWrapper":
        """ this is purely for readability, to make it clear that the content should have markup rendered """
        return self.add(text, **kwargs)

    def add_pretty(self, obj: Any, **kwargs) -> "TreeWrapper":
        return self.add(Pretty(obj), **kwargs)

    def add_syntax(
        self,
        code: str,
        lexer: str,
        *,
        theme: str = "monokai",
        **kwargs,
    ) -> "TreeWrapper":
        return self.add(Syntax(code, lexer, theme=theme), **kwargs)

    def add_sections_from_json_keys(self, json_str: str, **kwargs) -> "TreeWrapper":
        try:
            obj = json.loads(json_str)
        except json.JSONDecodeError:
            # Show the error and raw content in the tree
            self.add_markup("[red]failed to load JSON result:[/]")\
                .add_no_markup(json_str)
            return self

        for key, value in obj.items():
            # Create a node for the key and attach the value as a child
            self.add_section(key, value)
        return self

    def add_section(self, title: str, value: Any) -> "TreeWrapper":
        self.add_markup(f"[bold]{title}[/]:")\
            .add_no_markup(str(value))
        return self

    def remove_self(self):
        if self.parent:
            try:
                self.parent.children.remove(self)
            except ValueError:
                pass
            self.parent = None
        return self

@dataclass
class StreamingChunksState:
    node: TreeWrapper | None = None
    accumulated: AIMessageChunk | None = None

    def reset(self):
        """reset state for a new model response"""
        self.node = None
        self.accumulated = None

async def stream_messages(
    agent: Runnable,
    input: Any | list[BaseMessage] | Command | None,  # Any: for {"messages": list[BaseMessage] }
    *,
    dump_events=False,
    config: RunnableConfig | None = None,
    **kwargs,
):
    message_count = 0

    def increment_message_count():
        nonlocal message_count
        message_count += 1

    def show_system_message(message: SystemMessage, tree: "TreeWrapper"):
        child = tree.add_markup(f"{message_count}. [bold gray0 on gold1]SystemMessage")
        child.add_no_markup(message.content)
        child.blank_line()

    def show_human_message(message: HumanMessage, tree: "TreeWrapper"):
        child = tree.add_markup(f"{message_count}. [bold gray0 on slate_blue1]HumanMessage")
        child.add_no_markup(message.content)
        child.blank_line()

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

    def _show_message(message, tree: "TreeWrapper"):
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
            branch = tree.add_markup(f"[red]Unsupported message type: {type(message).__name__}[/]")
            branch.add_pretty(message)
            branch.blank_line()

    def on_tool_start(event: StreamEvent, tree: "TreeWrapper"):
        tool_name = event["name"]
        node = tree.add_markup(f"[bold gray0 on deep_sky_blue3]Calling {tool_name}")
        # AFAICT no tool_call_id available in on_tool_start

        # * show select arguments pretty printed
        data = event.get("data")
        args = data.get("input")
        assert isinstance(args, dict)
        if tool_name.startswith("run_python"):
            code = args.get("code", "")
            node.add_syntax(code, "python")
        elif tool_name.startswith("run_command"):
            commandline = args.get("commandline", "")
            node.add_syntax(commandline, "bash")
        elif tool_name == "apply_patch":
            patch = args.get("patch", "")
            node.add_syntax(patch, "diff")
        # do not show other tools/args that I don't have custom formatter for b/c they already show from AIMessage
        node.blank_line()

    def show_tool_message(message: ToolMessage, tree: "TreeWrapper"):
        name = message.name
        id = message.tool_call_id
        child = tree.add_markup(f"{message_count}. [bold gray0 on slate_blue1]ToolMessage[/]: [bold]{name}[/] ({id})")
        # FYI I could show the args pretty-ified here if I cache them and don't show on tool start
        _display_tool_message_content(message, child)
        child.blank_line()

    def on_tool_end(event: StreamEvent, tree: "TreeWrapper"):
        increment_message_count()
        data = event.get("data")
        output = data.get("output")
        if isinstance(output, ToolMessage):
            show_tool_message(output, tree)
        else:
            # raise NotImplementedError("TODO how to display on_tool_end when output is not just a ToolMessage")
            # when you use the `task` tool then on_tool_end can return a Command to update multiple channels instead of just a new ToolMessage...
            # i.e. update files modified (tmp file creation by subagent)
            tree.add_markup("[red bold] TODO SHOW ANYTHING for on_tool_end when output is not just a ToolMessage?")
            tree.add_pretty(output)

    def show_ai_message(message: AIMessage, tree: "TreeWrapper"):
        child = tree.add_markup(f"{message_count}. [bold gray0 on deep_sky_blue3]AIMessage")
        reasoning = message.additional_kwargs.get("reasoning_content")
        if reasoning:
            reasoning_node = child.add_markup("[bold]reasoning:[/]")
            reasoning_node.add(Text(reasoning, style="italic"))  # FYI Text does not parse/apply markup in the text value (1st positional arg)... use style to apply to the entire text value
            reasoning_node.blank_line()
        if message.content:
            content_node = child.add_markup("[bold]content:[/]")
            content_node.add_no_markup(message.content)
            content_node.blank_line()
        if message.tool_calls:
            for call in message.tool_calls:
                name = call.get("name", "")
                id = call.get("id", "")
                tool_tree = child.add_markup(f"[bold]{name}[/] ({id})")
                args = call.get("args", "")
                if args:
                    tool_tree.add_pretty(args)
                tool_tree.blank_line()
        return child

    def on_chat_model_stream(event: StreamEvent, state: StreamingChunksState, tree: "TreeWrapper"):
        # streaming chunks so we can see response as it is generated
        chunk = event.get("data").get("chunk")
        assert isinstance(chunk, AIMessageChunk)

        # * accumulate chunks
        if not state.accumulated:
            increment_message_count()
            state.accumulated = chunk
        else:
            # accumulated holds cumulative chunks => effectively becomes AIMessage (handles reasoning/content/tool_calls chunking)
            state.accumulated = state.accumulated + chunk

        # * replace node
        if state.node:
            state.node.remove_self()
        state.node = show_ai_message(state.accumulated, tree)
        # state.node.add_pretty(state.accumulated) # DEBUGGING: fixed structure fills out as each chunk arrives (looks cool)

    def dump_all_events_except_streaming_tokens_for_debugging(event: StreamEvent, tree: "TreeWrapper"):
        event_type = event["event"]
        if event_type in {"on_chat_model_stream"}:
            return
            tree.add_pretty(event)

    def show_initial_messages(tree: "TreeWrapper"):
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

    root = TreeWrapper("agent", hide_root=True)
    root.TREE_GUIDES = [("    ", "    ", "    ", "    ")]

    with Live(
            root,
            refresh_per_second=8,
            vertical_overflow="visible",  # default ellipsis (hides)
    ) as live:
        show_initial_messages(root)

        tree = root
        events: list[StreamEvent] = []
        streaming_state = StreamingChunksState()
        event: StreamEvent
        async for event in agent.astream_events(input, version="v2", config=config, **kwargs):
            # https://reference.langchain.com/python/langchain-core/runnables/base/Runnable/astream_events
            # event type naming: on_[runnable_type]_(start|stream|end)
            # - runnable types: chain, chat_model, tool
            events.append(event)

            if dump_events:
                dump_all_events_except_streaming_tokens_for_debugging(event, tree)

            event_type = event["event"]
            if event_type == "on_chain_start":
                tree = tree.add_no_markup("[chain start]")  # this label makes it very easy to see in my hierarchy where the chain starts/ends!
            elif event_type == "on_chain_end":
                tree.add_no_markup("[chain end]")
                tree = tree.parent
            elif event_type == "on_chain_stream":
                show_approval_interrupts(event, tree)
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
