
import json
import ast
import sys

with open("games.json") as f:
    data = ast.literal_eval(f.read())

json.dump(data, sys.stdout, indent=2)
