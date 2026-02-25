#!/bin/bash
# Start cron daemon in background
service cron start 2>/dev/null

# Drop to ctfplayer user
exec su - ctfplayer
