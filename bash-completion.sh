#!/usr/bin/env bash

# Helper function to initialize completion variables
# (This is standard practice but often included in _init_completion)
_init_completion() {
    COMPREPLY=()
    _get_comp_words_by_ref cur prev
    return 0
}

_taku_completions() {
    local cur prev
    _init_completion || return

    # $COMP_CWORD is the index of the current word being completed (0-indexed).
    # taku is word 0. Subcommand is word 1. Script name is word 2.

    # 1. Complete subcommands (when $COMP_CWORD is 1)
    if [[ $COMP_CWORD -le 1 ]]; then
        local subcmds="get new edit rm run list install uninstall"
        COMPREPLY=( $(compgen -W "$subcmds" -- "$cur") )
        return 0
    fi

    # 2. Complete scripts (when $COMP_CWORD is 2)
    # This block requires the previous word ($prev) to be one of the specified commands.
    if [[ $COMP_CWORD -eq 2 ]]; then
        case "$prev" in
            run|edit|install|get|rm|uninstall)
                local suggestions
                # Use 'tax _complete' to get the list of scripts
                suggestions=$(tax _complete "$cur" 2>/dev/null)
                COMPREPLY=( $(compgen -W "$suggestions" -- "$cur") )
                ;;
            *)
                # If word 1 is not a script-expecting command (e.g., 'taku new'), do nothing
                COMPREPLY=()
                ;;
        esac
        return 0
    fi

    # 3. Do nothing for any word count beyond 3 ($COMP_CWORD >= 3)
    COMPREPLY=()
    return 0
}

_tax_completions() {
    local cur prev
    _init_completion || return

    # tax is word 0. Script/file is word 1.

    # 1. Complete scripts (when $COMP_CWORD is 1)
    if [[ $COMP_CWORD -le 1 ]]; then
        local suggestions

        # Get the tool's list of scripts
        suggestions=$(tax _complete "$cur" 2>/dev/null)

        # Check if the tool returned suggestions
        if [[ -n "$suggestions" ]]; then
            # If tool has matches, use them
            COMPREPLY=( $(compgen -W "$suggestions" -- "$cur") )
            return 0
        else
            # If tool has NO matches (e.g., user fully typed script name),
            # fall back to file/directory completion using -f
            COMPREPLY=( $(compgen -f -- "$cur") )
            return 0
        fi
    fi

    # 2. Complete files (when $COMP_CWORD is 2 or more)
    # If the user is typing the third word or later, switch permanently to files.
    COMPREPLY=( $(compgen -f -- "$cur") )
}

complete -F _taku_completions taku
complete -F _tax_completions tax
