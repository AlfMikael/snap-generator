import adsk.core
import adsk.fusion
import traceback
import logging

from ..lib.snaplib.control import value_input
from ..apper import apper
from ..lib.snaplib import configure

app = adsk.core.Application.get()
ui = app.userInterface
handlers = []

class MyCommandExecutePreviewHandler(adsk.core.CommandEventHandler):
    """
    Triggered when user makes any change to a parameter that is related to
    performing the feature operations.
    """
    def __init__(self):
        super().__init__()
        # self.logger = logging.getLogger(type(self).__name__)

    def notify(self, args):
        # ui.messageBox("Input triggered")
        pass


class InputHandler(adsk.core.InputChangedEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        input_command = args.input

        if input_command.id == "open_config_folder":
            try:
                import os, sys, platform, subprocess
                if platform.system() == "Windows":
                    os.startfile(str(configure.CONFIG_PATH))
                # todo: should probably use platform.system() for both checks
                elif sys.platform == "darwin":
                    subprocess.call(["open", str(configure.CONFIG_PATH)])
                else:
                    logging.exception(f"Unable to open config folder. Unsupported operating system. {platform.system()} (this should not happen).")
            except:
                ui.messageBox(f"Error: {traceback.format_exc()}")
        elif input_command.id == "reset_all_profile_data":
            try:
                configure.reset_all_profile_data()
            except:
                logging.exception("Unable to reset all profile data.")
                ui.messageBox(f"Error: {traceback.format_exc()}")



class InputLimiter(adsk.core.ValidateInputsEventHandler):
    def notify(self, args):
        pass


class MyCommandExecuteHandler(adsk.core.CommandEventHandler):
    """
    Triggered when user clicks OK in command interface.
    """
    def __init__(self):
        super().__init__()

    def notify(self, args):
        pass


class SettingsCommand(apper.Fusion360CommandBase):
    def __init__(self, name: str, options: dict):
        super().__init__(name, options)

    def on_execute(self, command: adsk.core.Command,
                   inputs: adsk.core.CommandInputs,
                   args: adsk.core.CommandEventArgs):

        try:
            myCmdDef = ui.commandDefinitions.itemById(
                'SelectionEventsSample_Python')
            if myCmdDef is None:
                myCmdDef = ui.commandDefinitions.addButtonDefinition(
                    'SelectionEventsSample_Python',
                    'Settings', '', '')

            # prevent this module from being terminateD when the script returns,
            # because we are waiting for event handlers to fire
            adsk.autoTerminate(False)
            myCmdDef.execute()
        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

    def on_run(self):
        super().on_run()

    def on_create(self, command, inputs):
        self.command = command

        # Makes it so the command is not automatically executed when another
        # command gets activated.
        self.command.isExecutedWhenPreEmpted = False
        self.add_handlers()
        self.createGUI()


    def on_destroy(self, command: adsk.core.Command, inputs: adsk.core.CommandInputs,
                   reason: adsk.core.CommandTerminationReason, input_values: dict):
        pass

    def on_preview(self, command: adsk.core.Command,
                   inputs: adsk.core.CommandInputs,
                   args: adsk.core.CommandEventArgs, input_values: dict):
        pass


    def createGUI(self):
        # Dividing command window into tabs
        inputs = self.command.commandInputs
        feature_tab = inputs.addTabCommandInput('tab_1', 'Feature').children

        feature_tab.addBoolValueInput("open_config_folder", "Open config folder", False, "", False)
        feature_tab.addBoolValueInput("reset_all_profile_data", "Reset All Profile Data", False, "", False)

    def add_handlers(self):
        cmd = self.command

        # Connect to the command related events.
        onExecutePreview = MyCommandExecutePreviewHandler()
        cmd.executePreview.add(onExecutePreview)
        handlers.append(onExecutePreview)

        onExecute = MyCommandExecuteHandler()
        cmd.execute.add(onExecute)
        handlers.append(onExecute)

        input_handler = InputHandler()
        cmd.inputChanged.add(input_handler)
        handlers.append(input_handler)

        input_limiter = InputLimiter()
        cmd.validateInputs.add(input_limiter)
        handlers.append(input_limiter)