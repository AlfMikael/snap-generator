import adsk.core
import traceback


import os

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
        'Cantilever',
        CantileverCommand,
        {
            'cmd_description': 'Single cantilever.',
            'cmd_id': 'cantilever',
            'workspace': 'FusionSolidEnvironment',
            'toolbar_panel_id': 'Snap',
            'toolbar_tab_id': 'SolidTab',
            'cmd_resources': 'CantileverCommand',
            'command_visible': True,
            'command_promoted': True,
        }
    )


    my_addin.add_command(
        'Cantilever Pin',
        CantileverPinCommand,
        {
            'cmd_description': 'Cantilever pin.',
            'cmd_id': 'cantilever_pin',
            'workspace': 'FusionSolidEnvironment',
            'toolbar_panel_id': 'Snap',
            'toolbar_tab_id': 'SolidTab',
            'cmd_resources': 'CantileverPinCommand',
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