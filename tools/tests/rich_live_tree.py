from time import sleep
from rich.live import Live
from rich.tree import Tree

tree = Tree("agent")

with Live(tree, refresh_per_second=8) as live:

    for i in range(0,100):
        plan = tree.add(f"plan {i}")

        tool = plan.add("run_command()")

        tool.add("stdout")

        plan.add("run_python()")
        sleep(0.1)
