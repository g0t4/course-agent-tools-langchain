import pytest
import sys
from io import StringIO
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from show import show_messages

# !!! FYI run with:     pytest --no-capture
#   prints the summary and does a few verifications

def capture_output(func, *args, **kwargs):
    """Utility to capture stdout produced by a function."""
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    try:
        func(*args, **kwargs)
        return sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout

def test_show_messages_all_types(capsys):
    # Human message
    human = HumanMessage(content="Hello, assistant!")

    # AI message with plain content
    ai_plain = AIMessage(content="Sure, here's a response.")

    # AI message with a tool call (run_python)
    ai_tool_call1 = AIMessage(
        content="",
        tool_calls=[{
            "name": "run_python",
            "args": {
                "code": "print(42)"
            },
            "id": "a"
        }],
    )

    tool_result1 = ToolMessage(content="42", tool_call_id="a")

    ai_tool_call2 = AIMessage(
        content="",
        tool_calls=[{
            "name": "run_command",
            "args": {
                "commandline": "echo done"
            },
            "id": "b"
        }],
    )

    tool_result2 = ToolMessage(content="done", tool_call_id="b")

    messages = [human, ai_plain, ai_tool_call1, tool_result1, ai_tool_call2, tool_result2]

    # Capture the output of show_messages and print it for visibility
    output = capture_output(show_messages, messages)
    print(output)

    # Verify that each message type label appears in the output
    assert "Human" in output
    assert "AI" in output
    assert "Tool call" in output
    assert "Tool" in output

    # Verify that the specific contents are present
    # BTW this test largely exists to see the output and judge if it looks helpful, not to unit test output
    assert "Hello, assistant!" in output
    assert "Sure, here's a response." in output
    assert "run_python" in output
    # assert "print(42)" in output # colorful output
    assert "42" in output
    assert "run_command" in output
    # assert "echo done" in output # colorful output
