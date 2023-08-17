#
# ~/.bashrc
#

# If not running interactively, don't do anything
[[ $- != *i* ]] && return

alias ls='exa -alh --color=auto'
alias grep='grep --color=auto'
PS1='[\u@\h \W]\$ '
shopt -s autocd
