#!/usr/bin/env bash

# dump end of out.ansi as changes stream into it
#  pretty easy to see out of order branch updates during parallel tool execution
#  this is flashy, yes... it is merely for making sure things are still progressing until the agent is done and the rich view (with vertical_overflow=False) can show everything past one screen...
#     only really hard to see what is going on when parallel branches update (i.e. parallel tool calls) but even thn you can see a bit of them growing!
#     so rich becomes defacto truth w/o overflow it won't be messed up...
#     file out.ansi is a backup
#     and out.ansi can be used to monitor live updates using below but THIS IS NOT A FIRST CLASS UX ... just to make sure agents don't drive off cliff
#     real "fix" is a textual like view that takes over scrollback (like a window) over the tree... and slides that window like I am doing with tmux here... 
#       and textual should be able to do it smooth w/o flashes due to interval updates
while true; do
    printf "\033[H\033[J"
    tail -n $(tput lines) out.ansi
    sleep 0.05
done
