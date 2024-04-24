import adsk.core
import traceback
import json
import shutil
from pathlib import Path
from .lib import appdirs
import shutil



# app = adsk.core.Application.cast(adsk.core.Application.get())
# ui = app.userInterface
app = adsk.core.Application.cast(adsk.core.Application.get())
ui = app.userInterface
# ui.messageBox("Started app")

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



    simple_cantilever_visible = app_settings["cantilever_simple_enabled"]
    from .commands.SimpleCantileverCommand import SimpleCantileverCommand
    my_addin.add_command(
        'Simple Cantilever',
        SimpleCantileverCommand,
        {
            'cmd_description': 'Create a cantilever snap with few options.',

            'cmd_id': 'simple_cantilever',
            'workspace': 'FusionSolidEnvironment',
            'toolbar_panel_id': 'SolidCreatePanel',
            "drop_down_cmd_id": "snap_drop_down",
            "drop_down_name": "Snap Generator",
            'drop_down_resources': 'CantileverCommand',
            'toolbar_tab_id': 'SolidTab',
            'cmd_resources': 'CantileverCommand',
            'add_to_drop_down': True,
            'command_visible': simple_cantilever_visible,
            'command_promoted': False,
        }
    )

    cantilever_visible = app_settings["cantilever_advanced_enabled"]
    from .commands.CantileverCommand import CantileverCommand
    my_addin.add_command(
        'Cantilever',
        CantileverCommand,
        {
            'cmd_description': 'Create a cantilever snap shape.'
                               'It may join to a selected body and perform a cut to create a slot in another.'
                               'Note that gap parameters will change the dimensions of the'
                               'mating hole, not the cantilever shape itself. (opposite for pin).',
            'cmd_id': 'advanced_cantilever',
            'workspace': 'FusionSolidEnvironment',
            'toolbar_panel_id': 'SolidCreatePanel',
            "drop_down_cmd_id": "snap_drop_down",
            "drop_down_name": "Snap Generator",
            # 'drop_down_resources': 'CantileverCommand',
            'toolbar_tab_id': 'SolidTab',
            'cmd_resources': 'CantileverCommand',
            'add_to_drop_down': True,
            'command_visible': cantilever_visible,
            'command_promoted': False,
        }
    )
    # ui.messageBox("loaded cantilever")




    simple_pin_visible = app_settings["pin_simple_enabled"]
    from .commands.SimplePinCommand import SimplePinCommand
    my_addin.add_command(
        'Simple Pin',
        SimplePinCommand,
        {
            'cmd_description': 'Create a snap pin using a single parameter.',
            'cmd_id': 'simple_pin',
            'workspace': 'FusionSolidEnvironment',
            'toolbar_panel_id': 'SolidCreatePanel',
            "drop_down_cmd_id": "snap_drop_down",
            "drop_down_name": "Snap Generator",
            'toolbar_tab_id': 'SolidTab',
            'cmd_resources': 'CantileverPinCommand',
            # 'drop_down_resources': 'CantileverCommand',
            'add_to_drop_down': True,
            'command_visible': simple_pin_visible,
            'command_promoted': False,
        }
    )

    simple_pin_visible = app_settings["pin_simple_enabled"]
    from .commands.ExperimentalSimplePinCommand import ExperimentalSimplePinCommand
    my_addin.add_command(
        'Experimental Simple Pin',
        ExperimentalSimplePinCommand,
        {
            'cmd_description': 'Create a snap pin using a single parameter.',
            'cmd_id': 'simple_pin_experimental',
            'workspace': 'FusionSolidEnvironment',
            'toolbar_panel_id': 'SolidCreatePanel',
            "drop_down_cmd_id": "snap_drop_down",
            "drop_down_name": "Snap Generator",
            'toolbar_tab_id': 'SolidTab',
            'cmd_resources': 'CantileverPinCommand',
            # 'drop_down_resources': 'CantileverCommand',
            'add_to_drop_down': True,
            'command_visible': simple_pin_visible,
            'command_promoted': False,
        }
    )



    pin_visible = app_settings["pin_advanced_enabled"]
    from .commands.PinCommand import PinCommand
    my_addin.add_command(
        'Pin',
        PinCommand,
        {
            'cmd_description': 'Create a cantilever snap pin.'
                               ' parameter to get a "standardized" shape that is appropriate for '
                               'the given SIZE. Note that gap parameters change the dimensions'
                               ' of the pin.'
                               ' For that reason, the gap thickness is limited by the difference '
                               'between "width" and "thickness."',
            'cmd_id': 'advanced_pin',
            'workspace': 'FusionSolidEnvironment',
            'toolbar_panel_id': 'SolidCreatePanel',
            "drop_down_cmd_id": "snap_drop_down",
            "drop_down_name": "Snap Generator",
            'toolbar_tab_id': 'SolidTab',
            'cmd_resources': 'CantileverPinCommand',
            # 'drop_down_resources': 'CantileverPinCommand40',
            'add_to_drop_down': True,
            'command_visible': pin_visible,
            'command_promoted': False,
        }
    )

    # pin_visible = app_settings["pin_advanced_enabled"]
    # from .commands.ExperimentalPinCommand import ExperimentalPinCommand
    # my_addin.add_command(
    #     'Pin',
    #     ExperimentalPinCommand,
    #     {
    #         'cmd_description': 'Snap Pin',
    #         'cmd_id': 'pin',
    #         'workspace': 'FusionSolidEnvironment',
    #         'toolbar_panel_id': 'SolidCreatePanel',
    #         "drop_down_cmd_id": "snap_drop_down",
    #         "drop_down_name": "Snap Generator",
    #         'toolbar_tab_id': 'SolidTab',
    #         'cmd_resources': 'CantileverPinCommand',
    #         # 'drop_down_resources': 'CantileverPinCommand40',
    #         'add_to_drop_down': True,
    #         'command_visible': pin_visible,
    #         'command_promoted': False,
    #     }
    # )

    # pin_visible = app_settings["pin_advanced_enabled"]
    # from .commands.CantileverPinCommand import ExperimentalPinCommandAddition
    # my_addin.add_command(
    #     'Addition Pin',
    #     ExperimentalPinCommandAddition,
    #     {
    #         'cmd_description': 'Snap Pin',
    #         'cmd_id': 'pin_addition',
    #         'workspace': 'FusionSolidEnvironment',
    #         'toolbar_panel_id': 'SolidCreatePanel',
    #         "drop_down_cmd_id": "snap_drop_down",
    #         "drop_down_name": "Snap Generator",
    #         'toolbar_tab_id': 'SolidTab',
    #         'cmd_resources': 'CantileverPinCommand',
    #         # 'drop_down_resources': 'CantileverPinCommand40',
    #         'add_to_drop_down': True,
    #         'command_visible': pin_visible,
    #         'command_promoted': False,
    #     }
    # )






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
            'cmd_resources': 'Settings',
            # 'drop_down_resources': 'CantileverCommand',
            'add_to_drop_down': True,
            'command_visible': True,
            'command_promoted': False,
        }
    )





    # ui.messageBox("Finished initialization script.")


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



