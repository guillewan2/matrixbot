import json
import os

config_file = 'config/users.json'

with open(config_file, 'r') as f:
    data = json.load(f)

users = data.get("users", {})
for user_id, config in users.items():
    if config.get("ai_enabled", False):
        # Set default to aistudio as requested
        config["ai"] = "aistudio"
        print(f"Updated {user_id}: set ai=aistudio")

with open(config_file, 'w') as f:
    json.dump(data, f, indent=4)

print("Migration complete.")
