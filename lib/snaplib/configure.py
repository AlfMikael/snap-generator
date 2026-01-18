import adsk.core
import os
import json
import traceback
import shutil
from pathlib import Path

# --- 1. Constants and Global Placeholders ---
CONFIGURABLE_COMMANDS = ["Cantilever", "Pin"]
app = adsk.core.Application.get()
ui = app.userInterface

# We define these as None initially
config = None
app_path = Path(__file__).parent.parent.parent
VERSION = None
APPNAME = None
CONFIG_PATH = None
LOGS_PATH = None
SETTINGS_PATH = None

def get_manifest():
    # Use the dynamic glob search we discussed
    manifest_files = list(app_path.glob("*.manifest"))
    if not manifest_files:
        raise FileNotFoundError(f"Could not find a .manifest file in {app_path}")
    with open(manifest_files[0], "r") as f:
        return json.load(f)

def initialize():
    global VERSION, APPNAME, CONFIG_PATH, LOGS_PATH, SETTINGS_PATH
    
    try:
        manifest = get_manifest()
        VERSION = manifest.get("version", "0.0.0")
        APPNAME = manifest.get("name", "UnknownApp")

        CONFIG_PATH = app_path / "config"
        LOGS_PATH = app_path / "logs"
        SETTINGS_PATH = CONFIG_PATH / "settings.json"
        
        # Ensure directories exist
        os.makedirs(LOGS_PATH, exist_ok=True)
        os.makedirs(CONFIG_PATH / "ProfileData", exist_ok=True)
        
    except Exception as e:
        ui.messageBox(f"Initialization Failed:\n{traceback.format_exc()}")

def set_config(c):
    global config
    config = c

def reset_single_profile_data(command_name: str):
    try:
        if command_name not in CONFIGURABLE_COMMANDS:
            raise KeyError(f"\"{command_name}\" not in list of configurable commands")
        
        source = config.app_path / "default_config" / f"{command_name}.json"
        target = CONFIG_PATH / "ProfileData" / f"{command_name}.json"
        shutil.copy(source, target)
    except:
        ui.messageBox(traceback.format_exc())

def reset_all_profile_data():
    for command_name in CONFIGURABLE_COMMANDS:
        reset_single_profile_data(command_name)

def get_settings():
    if not SETTINGS_PATH.exists():
        reset_settings()
    with open(SETTINGS_PATH, "r") as f:
        return json.load(f)

def dump_settings(settings_dict):
    with open(SETTINGS_PATH, "w") as f:
        json.dump(settings_dict, f, indent=4)

def reset_settings():
    source = config.app_path / "default_config" / "settings.json"
    os.makedirs(str(CONFIG_PATH), exist_ok=True)
    shutil.copy(source, SETTINGS_PATH)

initialize()