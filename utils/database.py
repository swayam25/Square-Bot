import discord
import os
import json

config_file_path = "./configs/config.json"
temp_file_path = {}

theme_color = 0x2B2D31
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
def system_ch_id():
    with open(f"{config_file_path}", "r") as config_file:
        config_data = json.load(config_file)
        return config_data["system_ch_id"]

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

# Guild configuration utility
def guild_config(
    guild_ids: int,
    key: str = "",
    value: any = None,
    mode: str = "get",
    keys: dict = {}
):
    """
    Handles guild configuration settings

    Args:
        guild_ids (int): The guild ID
        key (str): The configuration key
        value (any, optional): The new value for the key. Defaults to None
        mode (str, optional): The operation mode ("get" or "set"). Defaults to "get"
        keys (dict, optional): The new values for the keys. Defaults to {}

    Returns:
        The current or updated value for the key
    """
    file_path = f"database/{str(guild_ids)}.json"
    os.makedirs("database", exist_ok=True)
    data = {}

    try:
        with open(file_path, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        with open(file_path, "w") as f:
            json.dump(
                {
                    "mod_log_ch": None,
                    "ticket_log_ch": None,
                    "warn_log_ch": None,
                    "antilink": "OFF",
                    "antiswear": "OFF"
                }, f, indent=4
            )

    if mode == "get":
        return data.get(key)
    elif mode == "set":
        if keys != {}:
            data[key] = value
        else:
            data = keys
        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)
        return value

# Create new db
def create(guild_ids: int):
    guild_config(guild_ids, "set", {
        "mod_log_ch": None,
        "ticket_log_ch": None,
        "warn_log_ch": None,
        "antilink": "OFF",
        "antiswear": "OFF"
    })

# Delete db
def delete(guild_ids: int):
    os.remove(f"database/{str(guild_ids)}.json")

# Mod log channel
def mod_log_ch(guild_ids: int, channel_id: int = None, mode: str = "get"):
    return guild_config(guild_ids, "mod_log_ch", channel_id, mode)

# Warn log channel
def warn_log_ch(guild_ids: int, channel_id: int = None, mode: str = "get"):
    return guild_config(guild_ids, "warn_log_ch", channel_id, mode)

# Ticket log channel
def ticket_log_ch(guild_ids: int, channel_id: int = None, mode: str = "get"):
    return guild_config(guild_ids, "ticket_log_ch", channel_id, mode)

# Antilink system
def antilink(guild_ids: int, status: str = "OFF", mode: str = "get"):
    return guild_config(guild_ids, "antilink", status, mode)

# Antiswear system
def antiswear(guild_ids: int, status: str = "OFF", mode: str = "get"):
    return guild_config(guild_ids, "antiswear", status, mode)

# -------------------- TEMP FILE --------------------

# Play channel ID
def play_ch_id(guild_ids: int, channel_id: int = None, mode: str = "get"):
    if mode == "get":
        return temp_file_path.get(f"{str(guild_ids)}-play_ch_id", None)
    elif mode == "set":
        temp_file_path.update({f"{str(guild_ids)}-play_ch_id": channel_id})

# Play msg ID
def play_msg_id(guild_ids: int, msg_id: int = None, mode: str = "get"):
    match mode:
        case "get":
            return temp_file_path.get(f"{str(guild_ids)}-play_msg_id", None)
        case "set":
            temp_file_path.update({f"{str(guild_ids)}-play_msg_id": msg_id})

# Equalizer
def equalizer(guild_ids: int, name: str = None, mode: str = "get"):
    match mode:
        case "get":
            return temp_file_path.get(f"{str(guild_ids)}-equalizer", None)
        case "set":
            temp_file_path.update({f"{str(guild_ids)}-equalizer": name})