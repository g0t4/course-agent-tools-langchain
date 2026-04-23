import rich
from rich.syntax import Syntax
from rich.padding import Padding
import json
import sys
import asyncio

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage, AIMessageChunk
from langchain_core.runnables import Runnable
from langchain_core.runnables.schema import StreamEvent

console = rich.console.Console()

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
                    if call["name"] == "run_python":
                        print()
                        code = call["args"]["code"]
                        syntax = Syntax(code, "python", theme="monokai")
                        console.print(Padding(syntax, pad=(0, 0, 0, 4)))
                    elif call["name"] == "run_command":
                        print()
                        code = call["args"]["commandline"]
                        syntax = Syntax(code, "bash", theme="monokai")
                        console.print(Padding(syntax, pad=(0, 0, 0, 4)))
                    else:
                        print(f'({call["args"]})')

        elif isinstance(m, ToolMessage):
            rich.print(f'[bold slate_blue1]Tool[/]', end="")
            print(f': {m.content}')
        else:
            rich.print(f"unexpected message type: {m}")

def clear_screen():
    from IPython import get_ipython
    # optional, clear screen first:
    get_ipython().run_line_magic("clear", "")

def display_tool_message(message: ToolMessage) -> str:
    content = message.content
    if message.name == "run_command":
        return display_tool_run_command(message)
    # if message.name == "run_python":
    #     return display_tool_run_python(message)
    if isinstance(content, str):
        lines = content.splitlines()
        if len(lines) > 5:
            return "\n".join(lines[:5]) + "\n..."
        return content  # return all lines
    return json.dumps(content)

def display_tool_run_command(message: ToolMessage) -> str:
    content = message.content
    if not isinstance(content, str):
        rich.print('[red]run_command message.content should be a string, but is not... [/]')
        return json.dumps(content)
    try:
        obj = json.loads(content)
    except json.JSONDecodeError:
        rich.print("[red]failed to load JSON result...[/]")
        return content
    lines = [f"[bold]{k}[/]:\n {v}" for k, v in obj.items()]
    return "\n".join(lines)

def writeln_indented(msg: str | Syntax):
    rich.print(Padding(msg, (0, 0, 0, 4)))
    sys.stdout.flush()

def writeln(msg: str | Padding | None = ""):
    rich.print(msg or "")
    sys.stdout.flush()

def write(msg: str):
    rich.print(msg, end="")
    sys.stdout.flush()

async def stream_messages(agent: Runnable, initial_messages: list[BaseMessage]):

    clear_screen()  # think Ctrl+L => so chat starts at top and grows downward

    SIMULATE_DELAY = False  # artificial delay so you can see chat progression when tok/sec is high (i.e. 200 tok/sec)
    indent2_spaces = " " * 8

    # initialize detectors
    ai_started = None
    ai_has_reasoning = False
    ai_has_content = False
    ai_has_tool_call = False
    chunk_count = 0

    index = 0

    def show_tool_message(message: ToolMessage):
        name = message.name
        id = message.tool_call_id
        writeln(f"{index}. [bold gray0 on slate_blue1]ToolMessage[/]: [bold]{name} ({id})[/]")
        # FYI I could show the args pretty-ified here if I cache them and don't show on tool start
        writeln_indented(display_tool_message(message))

    def show_system_message(message: SystemMessage):
        writeln(f"{index}. [bold gray0 on gold1]SystemMessage")
        writeln_indented(message.content)

    def show_human_message(message: HumanMessage):
        writeln(f"{index}. [bold gray0 on slate_blue1]HumanMessage")
        writeln_indented(message.content)

    def show_ai_message(message: AIMessage):
        writeln(f"{index}. [bold gray0 on deep_sky_blue3]AIMessage")
        reasoning = message.additional_kwargs.get("reasoning_content")
        if reasoning:
            write(f"    [bold]reasoning:[/] ")
            writeln(reasoning)
        if message.content:
            write(f"    [bold]content:[/] ")
            writeln(message.content)
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
                    write(json.dumps(args))

    def show_message(message):
        message_type = type(message).__name__
        if isinstance(message, HumanMessage):
            show_human_message(message)
        elif isinstance(message, SystemMessage):
            show_system_message(message)
        elif isinstance(message, ToolMessage):
            show_tool_message(message)
        elif isinstance(message, AIMessage):
            show_ai_message(message)
        else:
            raise NotImplementedError(f"Unsupported _INITIAL_ message type: {message_type}")
        writeln()  # just like on_chat_model_end for non-initial messages

    # * show initial messages
    for tool_message in initial_messages:
        index += 1
        show_message(tool_message)

    event: StreamEvent
    async for event in agent.astream_events({"messages": initial_messages}, ):
        # https://reference.langchain.com/python/langchain-core/runnables/base/Runnable/astream_events
        # event type naming: on_[runnable_type]_(start|stream|end)
        # - runnable types: chain, chat_model, tool

        event_name = event["event"]
        data = event['data']

        # # * dump all events except streaming tokens (too many)
        # if event_name not in {"on_chat_model_stream"}:
        #     rich.print(event)
        # continue

        # * on_tool_start
        if event_name == "on_tool_start":
            # purpose is merely to show the arguments pretty printed (i.e. code/commandline)
            #  these are already shown from AIMessageChunks, so I don't have to redisplay these here
            #  PRN maybe I should score the need to redisplay them? and not do so unless it is a multiline known long arg
            tool_name = event["name"]
            # AFAICT there is no tool_call_id available on start event
            writeln_indented(f"[bold gray0 on deep_sky_blue3]Calling {tool_name}")

            args = data.get("input")
            assert isinstance(args, dict)
            if tool_name == "run_python":
                code = args.get("code", "")
                del args["code"]  # remove so I can show rest of args if any other args encountered (s/b just "code" in this case)
                writeln_indented(Syntax(code, "python"))
            elif tool_name == "run_command":
                commandline = args.get("commandline", "")
                del args["commandline"]
                writeln_indented(Syntax(commandline, "bash"))
            # FYI no reason to dump JSON again
            writeln()

        if event_name == "on_tool_end":
            index += 1
            tool_message = data.get("output")
            assert isinstance(tool_message, ToolMessage)
            show_message(tool_message)

        elif event_name == "on_chat_model_end":
            writeln()  # all messages end with blank line

            # # dump to test show_ai_message (otherwise only used for initial messages)
            # message = data.get("output")
            # if isinstance(message, AIMessage):
            #     show_ai_message(message)
            #     writeln()

        # * HumanMessage/ToolMessage/etc (User Message => Model)
        elif event_name == "on_chat_model_start":
            # reset AIMessage (response) detectors
            ai_started = None
            ai_has_reasoning = False
            ai_has_content = False
            ai_has_tool_call = False
            chunk_count = 0

            if SIMULATE_DELAY:
                await asyncio.sleep(0.05)

        # * streaming AIMessageChunks (Model => User)
        elif event_name == "on_chat_model_stream":
            # streaming chunks so we can see response as it is generated
            chunk_count += 1
            chunk = data.get("chunk")
            assert isinstance(chunk, AIMessageChunk)

            if not ai_started:
                index += 1
                ai_started = True
                message_type = type(chunk).__name__  # * role
                writeln(f"{index}. [bold gray0 on deep_sky_blue3]AIMessage")

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
                if not ai_has_reasoning:
                    write(f"    [bold]reasoning:[/] ")
                    ai_has_reasoning = True
                write(block.get("reasoning", ""))

            # * model's content
            # content: str = chunk.content # w/o content_blocks
            if block_type == "text":
                if not ai_has_content:
                    if ai_has_reasoning:
                        writeln()  # new line to end reasoning
                    write(f"    [bold]content:[/] ")
                    ai_has_content = True
                write(block.get("text", ""))

            # * model's tool call request
            # calls = chunk.tool_call_chunks # w/o content_blocks
            if block_type == "tool_call_chunk":
                tool_call = block
                # call_index = tool_call.get("index", "")

                # if not ai_has_tool_call:
                #     if ai_has_reasoning or ai_has_content:
                #         # PRN new line after each tool call too?
                #         writeln()  # new line to end content/reasoning before this
                #     ai_has_tool_call = True

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
                    write(args_indented)

            if SIMULATE_DELAY:
                MIN_SLEEP = 0.005  # 5 ms
                INITIAL_SLEEP = 0.030  # 20 ms
                ms = MIN_SLEEP
                if chunk_count < 100:
                    # Linear decay from INITIAL_SLEEP to MIN_SLEEP over the first 100 chunks
                    decay_factor = (chunk_count - 1) / 99
                    ms = INITIAL_SLEEP - (INITIAL_SLEEP - MIN_SLEEP) * decay_factor
                await asyncio.sleep(ms)
