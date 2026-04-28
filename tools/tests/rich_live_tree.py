from time import sleep
from rich.live import Live
from rich.markup import escape
from rich.text import Text
from rich.tree import Tree

tree = Tree("agent")

with Live(tree, refresh_per_second=8) as live:

    for i in range(0, 100):
        plan = tree.add(f"plan {i}")

        tool = plan.add("run_command()")

        tool.add("stdout")
        tree.add("[blue bold] this IS BLUE")
        tree.add(escape("[blue bold] this is not blue"))
        tree.add(Text("[blue bold] this is not blue"))

        plan.add("run_python()")
        sleep(0.1)
