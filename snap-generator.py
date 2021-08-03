import adsk.core
import traceback


try:
    from . import config
    from .apper import apper

    # ************ My own scripts **************
    # Load commands
    from .commands.CantileverCommand import CantileverCommand
    from .commands.CantileverPinCommand import CantileverPinCommand

    # Create our addin definition object
    my_addin = apper.FusionApp(config.app_name, config.company_name, False)
    my_addin.root_path = config.app_path

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
            'command_visible': True,
            'command_promoted': False,
        }
    )

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
            'command_visible': True,
            'command_promoted': False,
        }
    )

    app = adsk.core.Application.cast(adsk.core.Application.get())
    ui = app.userInterface

except:
    app = adsk.core.Application.get()
    ui = app.userInterface
    if ui:
        ui.messageBox('Initialization Failed: {}'.format(traceback.format_exc()))

# Set to True to display various useful messages when debugging your app
debug = True


def run(context):
    my_addin.run_app()


def stop(context):
    my_addin.stop_app()