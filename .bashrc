#
# ~/.bashrc
#

# Starts ssh-agent and adds github identity
if [ -z "$SSH_AUTH_SOCK" ] ; then
 eval `ssh-agent -s` > /dev/null
 #ssh-add -q ~/.ssh/github
fi

# If not running interactively, don't do anything
[[ $- != *i* ]] && return

# Aliases
alias ls='exa -alh --color=auto'
alias grep='grep --color=auto'

PS1='[\u@\h \W]\$ '

shopt -s autocd

export EDITOR=/usr/bin/nvim
