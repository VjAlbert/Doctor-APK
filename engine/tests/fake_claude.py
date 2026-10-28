#!/usr/bin/env python3
"""Stand-in for the `claude` program, for tests. Behaviour comes from $FAKE_CLAUDE_MODE;
every invocation is appended as JSON to $FAKE_CLAUDE_LOG."""
import json
import os
import sys
import time

args = sys.argv[1:]
mode = os.environ.get("FAKE_CLAUDE_MODE", "ok")
stdin = "" if args[:1] == ["--version"] or args[:1] == ["auth"] else sys.stdin.read()
with open(os.environ["FAKE_CLAUDE_LOG"], "a") as log:
    log.write(json.dumps({"args": args, "stdin": stdin, "cwd": os.getcwd(), "cwd_files": os.listdir(".")}) + "\n")

if args == ["--version"]:
    print("9.9.9 (Claude Code)")
elif args[:2] == ["auth", "status"]:
    print(json.dumps({"loggedIn": mode != "loggedout", "authMethod": "oauth_token" if mode != "apikey" else "api_key",
                      "apiProvider": "firstParty", "configDirectory": "/home/secret/.claude"}))
elif mode == "slow":
    time.sleep(30)
elif mode == "badjson":
    print("not json")
elif mode == "error":
    print(json.dumps({"is_error": True, "result": "Please run /login to authenticate"}))
    sys.exit(1)
elif mode == "failure":
    print(json.dumps({"is_error": True, "result": "overloaded"}))
    sys.exit(1)
else:
    print(json.dumps({"is_error": False, "result": os.environ.get("FAKE_CLAUDE_REPLY", "Spiegazione di prova."),
                      "total_cost_usd": 0.01234567, "duration_ms": 1500}))
