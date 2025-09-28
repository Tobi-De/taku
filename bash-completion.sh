#!/usr/bin/env bash

_taku_completions() {
    local cur prev
    _init_completion || return

    case "$prev" in
        run|edit|install|get|rm|uninstall)
            local suggestions
            suggestions=$(tax _complete "$cur" 2>/dev/null)
            COMPREPLY=( $(printf "%s\n" $suggestions) )
            ;;
        *)
            # complete subcommands for taku
            local subcmds="get new edit rm run list install uninstall"
            COMPREPLY=( $(printf "%s\n" $subcmds) )
            ;;
    esac
}

_tax_completions() {
    local cur
    _init_completion || return

    local suggestions
    suggestions=$(tax _complete "$cur" 2>/dev/null)
    COMPREPLY=( $(printf "%s\n" $suggestions) )
}

complete -F _taku_completions taku
complete -F _tax_completions tax
