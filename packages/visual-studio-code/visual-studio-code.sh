#!/bin/bash

XDG_CONFIG_HOME=${XDG_CONFIG_HOME:-~/.config}

if [[ -f $XDG_CONFIG_HOME/code-flags.conf ]]; then
   CODE_USER_FLAGS="$(sed 's/#.*//' $XDG_CONFIG_HOME/code-flags.conf | tr '\n' ' ')"
fi

exec /usr/share/code/bin/code "$@" $CODE_USER_FLAGS
