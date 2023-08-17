#!/bin/bash
# Copies given folders and files to current folder

cp -r ~/.config/alacritty .
cp -r ~/.config/i3 .
cp -r ~/.config/nvim .
cp ~/setup.txt .

echo "Files copied succesfully!"
