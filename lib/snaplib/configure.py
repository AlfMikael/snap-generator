import adsk.core

import os
import json
import traceback
from pathlib import Path
import shutil

CONFIGURABLE_COMMANDS = ["Cantilever", "Pin"]

# Get config info from manifest file
app_path = Path(__file__).parent.parent.parent
manifest_path = app_path / "snap-generator.manifest"
with open(manifest_path, "r") as f:
    manifest = json.load(f)
VERSION = manifest["version"]
APPNAME = manifest["name"]

CONFIG_PATH = app_path / "config"
LOGS_PATH = app_path / "logs"
SETTINGS_PATH = CONFIG_PATH / "settings.json"

app = adsk.core.Application.get()
ui = app.userInterface
config = None
def set_config(c):
    global config
    config = c

def reset_single_profile_data(command_name: str):
    try:
        if command_name not in CONFIGURABLE_COMMANDS:
            raise KeyError(f"\"{command_name}\" not in list of configurable commands" )

        else:
            source_config_file_path = config.app_path / "default_config" / f"{command_name}.json"
            target_config_file_path = CONFIG_PATH / "ProfileData" / f"{command_name}.json"
            os.makedirs(CONFIG_PATH / "ProfileData", exist_ok=True)
            shutil.copy(source_config_file_path, target_config_file_path)
    except:
        ui.messageBox(traceback.format_exc())

def reset_all_profile_data():
    os.makedirs(CONFIG_PATH / "ProfileData", exist_ok=True)
    for command_name in CONFIGURABLE_COMMANDS:
        source_config_file_path = config.app_path / "default_config" / f"{command_name}.json"
        target_config_file_path = CONFIG_PATH / "ProfileData" / f"{command_name}.json"
        shutil.copy(source_config_file_path, target_config_file_path)

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
    os.makedirs(str(CONFIG_PATH), exist_ok=True)
    shutil.copy(source_settings_file_path, target_settings_file_path)

