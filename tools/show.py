from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
import rich

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
