import discord
import os
import json

config_file_path = "./configs/config.json"
temp_file_path = {}

theme_color = 0x2b2d31
error_color = discord.Color.red()

# -------------------- CONFIG FILE --------------------

# Owner IDs
def owner_ids():
    with open(f"{config_file_path}", "r") as config_file:
        config_data = json.load(config_file)
        return config_data["owner_ids"]

# Add dev ID
def add_dev_ids(user_id):
    with open(f"{config_file_path}", "r") as config_file:
        config_data = json.load(config_file)
    if user_id not in list(config_data["dev_ids"]):
        config_data["dev_ids"].append(user_id)
        with open(f"{config_file_path}", "w") as config_file:
            json.dump(config_data, config_file, indent=4)
    else:
        pass

# Remove dev
def remove_dev_ids(user_id):
    with open(f"{config_file_path}", "r") as config_file:
        config_data = json.load(config_file)
    if user_id in list(config_data["dev_ids"]):
        config_data["dev_ids"].remove(user_id)
        with open(f"{config_file_path}", "w") as config_file:
            json.dump(config_data, config_file, indent=4)
    else:
        pass

# Dev IDs
def dev_ids():
    with open(f"{config_file_path}", "r") as config_file:
        config_data = json.load(config_file)
        dev_ids = []
        for ids in config_data["dev_ids"]:
            dev_ids.append(ids)
    return list(dev_ids)

# Guild IDs
def guild_ids():
    with open(f"{config_file_path}", "r") as config_file:
        config_data = json.load(config_file)
        return config_data["guild_ids"]

# Owner guild IDs
def owner_guild_ids():
    with open(f"{config_file_path}", "r") as config_file:
        config_data = json.load(config_file)
        return config_data["owner_guild_ids"]

# System channel
def system_channel_id():
    with open(f"{config_file_path}", "r") as config_file:
        config_data = json.load(config_file)
        return config_data["system_channel_id"]

# Support server
def support_server_url():
    with open(f"{config_file_path}", "r") as config_file:
        config_data = json.load(config_file)
        return config_data["support_server_url"]

# Discord API token
def discord_api_token():
    with open(f"{config_file_path}", "r") as config_file:
        config_data = json.load(config_file)
        try:
            return os.environ["discord_api_token"]
        except Exception:
            return config_data["discord_api_token"]

# OpenAI API token
def openai_api_token():
    with open(f"{config_file_path}", "r") as config_file:
        config_data = json.load(config_file)
        try:
            return os.environ["openai_api_token"]
        except Exception:
            return config_data["openai_api_token"]

# Lavalink
def lavalink(
    key: str = None,
    mode: str = "get",
    data: str = None
):
    with open(f"{config_file_path}", "r") as config_file:
        config_data = json.load(config_file)
        if mode == "get":
            return config_data["lavalink"][key]
        elif mode == "set":
            config_data["lavalink"][key] = data
            with open(f"{config_file_path}", "w") as config_file:
                json.dump(config_data, config_file, indent=4)

# Datetime format
def datetime_format():
    with open(f"{config_file_path}", "r") as config_file:
        config_data = json.load(config_file)
        return config_data["datetime_format"]

# -------------------- SETTINGS FILE --------------------

# Set on guild join
def set_on_guild_join(guild_ids):
    os.makedirs("database", exist_ok=True)
    with open(f"database/{str(guild_ids)}.json", "w") as set_file:
        set_data = {
            "mod_log_channel_id": None,
            "ticket_log_channel_id": None,
            "warn_log_channel_id": None,
            "antilink": "OFF",
            "antiswear": "OFF"
        }
        json.dump(set_data, set_file, indent=4)

# Set on guild remove
def set_on_guild_remove(guild_ids):
    os.remove(f"database/{str(guild_ids)}.json")

# Mod log channel
def mod_log_channel_id(guild_ids, channel_id: int = None, mode: str = "get"):
    os.makedirs("database", exist_ok=True)
    with open(f"database/{str(guild_ids)}.json", "r") as set_file:
        set_data = json.load(set_file)
        if mode == "get":
            return set_data["mod_log_channel_id"]
        elif mode == "set":
            set_data["mod_log_channel_id"] = channel_id
            with open(f"database/{str(guild_ids)}.json", "w") as set_file:
                json.dump(set_data, set_file, indent=4)

# Warn log channel
def warn_log_channel_id(guild_ids, channel_id: int = None, mode: str = "get"):
    os.makedirs("database", exist_ok=True)
    with open(f"database/{str(guild_ids)}.json", "r") as set_file:
        set_data = json.load(set_file)
        if mode == "get":
            return set_data["warn_log_channel_id"]
        elif mode == "set":
            set_data["warn_log_channel_id"] = channel_id
            with open(f"database/{str(guild_ids)}.json", "w") as set_file:
                json.dump(set_data, set_file, indent=4)

# Ticket log channel
def ticket_log_channel_id(guild_ids, channel_id: int = None, mode: str = "get"):
    os.makedirs("database", exist_ok=True)
    with open(f"database/{str(guild_ids)}.json", "r") as set_file:
        set_data = json.load(set_file)
        if mode == "get":
            return set_data["ticket_log_channel_id"]
        elif mode == "set":
            set_data["ticket_log_channel_id"] = channel_id
            with open(f"database/{str(guild_ids)}.json", "w") as set_file:
                json.dump(set_data, set_file, indent=4)

# Antilink system
def antilink(guild_ids, status: str = None, mode: str = "get"):
    os.makedirs("database", exist_ok=True)
    with open(f"database/{str(guild_ids)}.json", "r") as set_file:
        set_data = json.load(set_file)
        if mode == "get":
            return set_data["antilink"]
        elif mode == "set":
            set_data["antilink"] = status
            with open(f"database/{str(guild_ids)}.json", "w") as set_file:
                json.dump(set_data, set_file, indent=4)

# Antiswear system
def antiswear(guild_ids, status: str = None, mode: str = "get"):
    os.makedirs("database", exist_ok=True)
    with open(f"database/{str(guild_ids)}.json", "r") as set_file:
        set_data = json.load(set_file)
        if mode == "get":
            return set_data["antiswear"]
        elif mode == "set":
            set_data["antiswear"] = status
            with open(f"database/{str(guild_ids)}.json", "w") as set_file:
                json.dump(set_data, set_file, indent=4)

# -------------------- TEMP FILE --------------------

# Play channel ID
def play_channel_id(guild_ids, channel_id: int = None, mode: str = "get"):
    if mode == "get":
        return temp_file_path.get(f"{str(guild_ids)}-play_channel_id", None)
    elif mode == "set":
        temp_file_path.update({f"{str(guild_ids)}-play_channel_id": channel_id})

# Play msg ID
def play_msg_id(guild_ids, msg_id: int = None, mode: str = "get"):
    if mode == "get":
        return temp_file_path.get(f"{str(guild_ids)}-play_msg_id", None)
    elif mode == "set":
        temp_file_path.update({f"{str(guild_ids)}-play_msg_id": msg_id})

# Equalizer
def equalizer(guild_ids, name: str = None, mode: str = "get"):
    if mode == "get":
        return temp_file_path.get(f"{str(guild_ids)}-equalizer", None)
    elif mode == "set":
        temp_file_path.update({f"{str(guild_ids)}-equalizer": name})