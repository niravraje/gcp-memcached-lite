#!/bin/bash

CLIENT_COUNT=40
for ((a=1; a<=CLIENT_COUNT; a++ ))
do
    osascript -e 'tell app "Terminal"
        do script "python3 ~/memcached-lite/client.py"
    end tell'
done