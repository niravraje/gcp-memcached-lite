#!/bin/bash

# This script will only work on MacOS
# Need to tweak it further for Linux

CLIENT_COUNT=10
for ((a=1; a<=CLIENT_COUNT; a++ ))
do
    osascript -e 'tell app "Terminal"
        do script "python3 ~/memcached-lite/client.py"
    end tell'
done