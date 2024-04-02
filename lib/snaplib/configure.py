import json
import os

from .. import appdirs

from pathlib import Path
# from config import app_path

import shutil
config = None

CONFIGURABLE_COMMANDS = ["CantileverCommand", "CantileverPinCommand"]

# Get config info from manifest file
manifest_path = Path(__file__).parent.parent.parent / "snap-generator.manifest"
with open(manifest_path, "r") as f:
    manifest = json.load(f)
VERSION = manifest["version"]
APPNAME = manifest["name"]

CONFIG_PATH = Path(appdirs.user_config_dir(appname=APPNAME, version=VERSION))
LOGS_PATH = Path(appdirs.user_log_dir(appname=APPNAME, version=VERSION))
SETTINGS_PATH = CONFIG_PATH / "settings.json"

config = None
def set_config(c):
    global config
    config = c

def reset_config_file(commandName: str):
    source_config_file_path = config.app_path / "default_config" / f"{commandName}.json"
    target_config_file_path = CONFIG_PATH / f"{commandName}.json"

    os.makedirs(CONFIG_PATH, exist_ok=True)

def get_settings():
    # First check that the settings file exists
    if not Path(SETTINGS_PATH).exists():
        reset_settings()
    with open(SETTINGS_PATH, "r") as f:
        return json.load(f)

def dump_settings(settings_dict):
    with open(SETTINGS_PATH, "w") as f:
        return json.dump(settings_dict, f, indent=4)


def reset_settings():
    source_settings_file_path = config.app_path / "default_config" / f"settings.json"
    target_settings_file_path = SETTINGS_PATH
    destination_dir = os.path.dirname(CONFIG_PATH)

    import adsk.core
    app = adsk.core.Application.get()
    ui = app.userInterface

    os.makedirs(str(CONFIG_PATH), exist_ok=True)
    ui.messageBox(f"{str(CONFIG_PATH)}")

    shutil.copy(source_settings_file_path, target_settings_file_path)

def reset_all_config():
    source_config_folder = config.app_path / "default_config"
    destination_config_folder = CONFIG_PATH

    if destination_config_folder.exists:
        shutil.rmtree(destination_config_folder)

    os.makedirs(CONFIG_PATH, exist_ok=True)
    shutil.copytree(source_config_folder, destination_config_folder)



