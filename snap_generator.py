import adsk.core
import traceback
import json
import shutil
from pathlib import Path
from .lib import appdirs
import shutil



# app = adsk.core.Application.cast(adsk.core.Application.get())
# ui = app.userInterface

import importlib
from . import config
from .lib.snaplib import configure

configure.set_config(config)  # Allow access to the config fil



""" Load commands """
try:
    from . import config
    from .apper import apper

    # ************ My own scripts **************
    # Load commands

    # todo: Implement RotatableCantileverCommand
    # todo: Implement RotatableCantileverPinCommand
    # todo: Implement AnnularCommand
    # todo: Implement AnnularPinCommand

    # Create our addin definition object
    my_addin = apper.FusionApp(config.app_name, config.company_name, False)
    my_addin.root_path = config.app_path

    # Settings to determine which commands to load
    app_settings = configure.get_settings()["apps_enable"]

    cantilever_visible = app_settings["cantilever_advanced_enabled"]
    from .commands.CantileverCommand import CantileverCommand
    my_addin.add_command(
        'Cantilever Snap',
        CantileverCommand,
        {
            'cmd_description': 'Create a cantilever snap shape, join it to a'
                               ' body, and create a mating slot in one or more other bodies.'
                               ' Note that gap parameters will change the dimensions of the'
                               ' mating hole, not the cantilever shape itself.',
            'cmd_id': 'cantilever snap',
            'workspace': 'FusionSolidEnvironment',
            'toolbar_panel_id': 'SolidCreatePanel',
            "drop_down_cmd_id": "snap_drop_down",
            "drop_down_name": "Snap Generator",
            'toolbar_tab_id': 'SolidTab',
            'cmd_resources': 'CantileverCommand',
            'drop_down_resources': 'CantileverCommand',
            'add_to_drop_down': True,
            'command_visible': cantilever_visible,
            'command_promoted': False,
        }
    )

    pin_visible = app_settings["pin_advanced_enabled"]
    from .commands.CantileverPinCommand import CantileverPinCommand
    my_addin.add_command(
        'Snap Pin',
        CantileverPinCommand,
        {
            'cmd_description': 'Create a cantilever snap pin. Use the SIZE'
                               ' parameter to get a "standardized" shape that is appropriate for '
                               'the given SIZE. Note that gap parameters change the dimensions'
                               ' of the pin.'
                               ' For that reason, the gap thickness is limited by the difference '
                               'between "width" and "thickness."',
            'cmd_id': 'cantilever_pin',
            'workspace': 'FusionSolidEnvironment',
            'toolbar_panel_id': 'SolidCreatePanel',
            "drop_down_cmd_id": "snap_drop_down",
            "drop_down_name": "Snap Generator",
            'toolbar_tab_id': 'SolidTab',
            'cmd_resources': 'CantileverPinCommand',
            'add_to_drop_down': True,
            'command_visible': pin_visible,
            'command_promoted': False,
        }
    )



    from .commands.SettingsCommand import SettingsCommand
    my_addin.add_command(
        'Settings',
        SettingsCommand,
        {
            'cmd_description': 'Settings',
            'cmd_id': 'settings',
            'workspace': 'FusionSolidEnvironment',
            'toolbar_panel_id': 'SolidCreatePanel',
            "drop_down_cmd_id": "snap_drop_down",
            "drop_down_name": "Snap Generator",
            'toolbar_tab_id': 'SolidTab',
            'cmd_resources': 'SettingsCommand',
            'cmd_resources': 'CantileverPinCommand',
            'add_to_drop_down': True,
            'command_visible': True,
            'command_promoted': False,
        }
        # {
        #     'cmd_description': 'Control Panel for activating or deactivating features.',
        #     'cmd_id': 'control_panel',
        #     'workspace': 'FusionSolidEnvironment',
        #     'toolbar_panel_id': 'SolidScriptsAddinsPanel',  # Adjust as necessary
        #     "drop_down_cmd_id": "snap_drop_down",
        #     "drop_down_name": "Snap Generator",
        #     'toolbar_tab_id': 'SolidTab',
        #     'cmd_resources': 'CantileverPinCommand',
        #     'add_to_drop_down': True,
        #     'command_visible': True,
        #     'command_promoted': False,
        # }
    )

    app = adsk.core.Application.cast(adsk.core.Application.get())
    ui = app.userInterface

    # ui.messageBox("So far so good.")
except:
    app = adsk.core.Application.get()
    ui = app.userInterface

    if ui:
        ui.messageBox('Initialization Failed: {}'.format(traceback.format_exc()))

""" Sets up config files for initial install."""
try:

    pass
    # from .lib.snaplib import config
    # # Get app info from manifest
    # with open(Path(__file__).parent / "snap-generator.manifest", "r") as f:
    #     manifest = json.load(f)
    #
    # appname = "snap-generator"
    # version = manifest["version"]
    #
    # default_config_folder = Path(__file__) / "default_config"
    # config_folder = Path(
    #     appdirs.user_config_dir(appname=appname, version=version))

    # ui.messageBox(f"default config folder: {str(default_config_folder)}"
    #               f"\n config directiory: {str(config_folder)}")

except:
    ui.messageBox('Initialization Failed: {}'.format(traceback.format_exc()))

def run(context):
    my_addin.run_app()


def stop(context):
    my_addin.stop_app()



