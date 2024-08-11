import json

emoji_file_path = "./configs/emoji.json"

# Load emojis from json file
with open(f"{emoji_file_path}", "r") as emoji_file:
    emoji_data = json.load(emoji_file)

# Create global variables for each emoji
for key in emoji_data.keys():
    globals()[key] = emoji_data[key]