import json
from utils import database as db
from rich import print
from attr import dataclass

# Load emojis from JSON file
emoji_file_path = ""
emoji_type = ""
with open(f"{db.config_file_path}", "r") as config_file:
    config_data = json.load(config_file)
    emoji_type = config_data["emoji"]
    match config_data["emoji"]:
        case "custom":
            emoji_file_path = "./configs/emoji.json"
        case "default":
            emoji_file_path = "./configs/default_emoji.json"
        case _:
            print(f"[red][bold]✗[/] Invalid emoji type in [cyan]config.json[/]: {config_data['emoji']}[/]")
            print(f"[yellow][bold]![/] Please choose either [green]custom[/] or [green]default[/].[/]")
            exit(1)

# Dataclass
@dataclass
class Emoji:
    bullet: str
    bullet2: str
    success: str
    error: str

    on: str
    off: str

    embed: str
    edit: str
    bin: str

    plus: str
    minus: str
    next: str
    previous: str
    start: str
    end: str

    kick: str
    info: str
    mod: str
    mod2: str
    mass_mod: str
    timer: str
    timer2: str
    lock: str
    unlock: str
    settings: str

    ticket: str
    ticket2: str

    music: str
    play: str
    play2: str
    pause: str
    pause2: str
    stop: str
    stop2: str
    skip: str
    skip2: str
    shuffle: str
    shuffle2: str
    seek: str
    loop: str
    loop2: str
    loop3: str
    playlist: str
    volume: str
    equalizer: str
    filled_bar: str
    empty_bar: str

    upload: str
    console: str
    restart: str
    shutdown: str

    @staticmethod
    def from_json(file_path: str) -> "Emoji":
        try:
            with open(file_path, "r", encoding="utf8") as emoji_file:
                emoji_data = json.load(emoji_file)

            # Validate keys
            missing_keys = [key for key in Emoji.__annotations__.keys() if key not in emoji_data]
            extra_keys = [key for key in emoji_data if key not in Emoji.__annotations__.keys()]

            if missing_keys:
                print(f"[red][bold]✗[/] Missing keys in emoji JSON: [cyan]{missing_keys}[/][/]")
                exit(1)
            if extra_keys:
                print(f"[yellow][bold]![/] Extra keys in emoji JSON: [cyan]{extra_keys}[/][/]")

            # Create Emoji instance
            return Emoji(**{key: emoji_data.get(key, "") for key in Emoji.__annotations__.keys()})

        except FileNotFoundError:
            if emoji_type == "custom":
                print(f"[red][bold]✗[/] Custom emoji file not found: {file_path}[/]")
                print(f"[yellow][bold]![/] Make sure to run [cyan]/emoji upload[/] command and upload emojis to the discord bot and run [cyan]/emoji sync[/] to create required config files.[/]")
                print(f"[yellow][bold]![/] If already uploaded, run [cyan]/emoji sync[/] to create required config files.[/]")
                print(f"[yellow][bold]![/] If you want to use default emojis, change the emoji type in [cyan]./configs/config.json[/] to [green]default[/].[/]")
            else:
                print(f"[red][bold]✗[/] Emoji file not found: {file_path}[/]")
                print(f"[yellow][bold]![/] Seems like default emoji file is missing. Please download the default emoji file from the repository and place it in the [green]configs[/] folder.[/]")
            exit(1)
        except json.JSONDecodeError:
            print(f"[red][bold]✗[/] Invalid JSON format in file: {file_path}[/]")


    @staticmethod
    def create_custom_emoji_config(emojis: dict) -> dict:
        with open("./configs/emoji.json", "w", encoding="utf8") as emoji_file:
            missing_keys = [key for key in Emoji.__annotations__.keys() if key not in emojis]
            extra_keys = [emojis[key] for key in emojis if key not in Emoji.__annotations__.keys()]
            if missing_keys:
                return { "status": "error", "missing_keys": missing_keys }
            else:
                emojis = { key: emojis[key] for key in Emoji.__annotations__.keys() }
                json.dump(emojis, emoji_file, ensure_ascii=False, indent=4)
                msg = { "status": "success" }
                if extra_keys:
                    msg["extra_keys"] = extra_keys
                return msg

emoji = Emoji.from_json(emoji_file_path)