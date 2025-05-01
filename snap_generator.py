import adsk.core
import traceback
from . import config
from .apper import apper
from .lib.snaplib import configure

from .commands.SimpleCantileverCommand import SimpleCantileverCommand
from .commands.CantileverCommand import CantileverCommand
from .commands.SimplePinCommand import SimplePinCommand
from .commands.PinCommand import PinCommand
from .commands.SettingsCommand import SettingsCommand

app = adsk.core.Application.cast(adsk.core.Application.get())
ui = app.userInterface
configure.set_config(config)  # Allow access to the config fil

""" Load commands """
try:
    # Create our addin definition object
    my_addin = apper.FusionApp(config.app_name, config.company_name, False)
    my_addin.root_path = config.app_path


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
            'command_visible': True,
            'command_promoted': False,
        }
    )

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
            'command_visible': True,
            'command_promoted': False,
        }
    )

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
            'command_visible': True,
            'command_promoted': False,
        }
    )

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
            'command_visible': True,
            'command_promoted': False,
        }
    )

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

except:
    if ui:
        ui.messageBox('Initialization Failed: {}'.format(traceback.format_exc()))


def run(context):
    my_addin.run_app()


def stop(context):
    my_addin.stop_app()
