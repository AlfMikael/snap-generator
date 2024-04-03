import json
import os
import traceback

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

# For debugging
import adsk.core
app = adsk.core.Application.get()
ui = app.userInterface
# ui.messageBox("Opened configure.py")


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
    destination_dir = os.path.dirname(CONFIG_PATH)

    import adsk.core
    app = adsk.core.Application.get()
    ui = app.userInterface

    os.makedirs(str(CONFIG_PATH), exist_ok=True)
    # ui.messageBox(f"{str(CONFIG_PATH)}")

    shutil.copy(source_settings_file_path, target_settings_file_path)

def reset_profile_config(command_name):
    """ Replace a profile config file for the given command, with the default."""
    if (command_name == "CantileverCommand"):
        shutil.copy()

    elif (command_name == "CantileverPinCommand"):
        pass



def reset_all_config():
    for command_name in CONFIGURABLE_COMMANDS:
        reset_profile_config(command_name)

    source_config_folder = config.app_path / "default_config"
    destination_config_folder = CONFIG_PATH

    if destination_config_folder.exists:
        shutil.rmtree(destination_config_folder)

    os.makedirs(CONFIG_PATH, exist_ok=True)
    shutil.copytree(source_config_folder, destination_config_folder)



