import adsk.core
import adsk.fusion
import adsk.cam
from adsk.core import SelectionCommandInput, DropDownStyles

import traceback
import json
import logging
import logging.handlers
from pathlib import Path

from ..apper import apper
from .snap.geometry import Cantilever
from .snap.control import value_input, JsonUpdater
from .snap.control import ProfileSettings, GapProfileSettings
from .snap.control import ProfileSwitcher, ProfileModifier, validate_json
from .snap.control import ProfileException
from ..lib import appdirs

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
       pass

class MyCommandExecuteHandler(adsk.core.CommandEventHandler):
    """
    Triggered when user clicks OK in command interface.
    """
    def __init__(self):
        super().__init__()
        #self.logger = logging.getLogger(type(self).__name__)

    def notify(self, args):
        #self.logger.info("Ok-button clicked.")
        #self.logger.debug("Triggered.")
        try:
            design = adsk.fusion.Design.cast(app.activeProduct)
            if design:
                build(args, preview=False)
        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


class SettingsCommand(apper.Fusion360CommandBase):

    def __init__(self, name: str, options: dict):
        super().__init__(name, options)

        # Store logs and profile config in appropriate config folder.
        # Varies depending on operating system. See appdirs module.
        appname = "Snap Generator - Fusion 360 addin"
        version = "0.2.1"

        # Loading references relative to this projects root
        self.root_dir = self.fusion_app.root_path
        self.resources_path = self.root_dir / "commands" / "resources" / \
                              "SettingsCommand"
        self.tool_clip_file_path = self.resources_path / "toolclip.png"

    def on_execute(self, command: adsk.core.Command,
                   inputs: adsk.core.CommandInputs,
                   args: adsk.core.CommandEventArgs, input_values: dict):

        try:
            myCmdDef = ui.commandDefinitions.itemById(
                'SelectionEventsSample_Python')
            if myCmdDef is None:
                myCmdDef = ui.commandDefinitions.addButtonDefinition(
                    'SelectionEventsSample_Python',
                    'Create cantilever', '', '')

            # # Connect to the command created event.
            # onCommandCreated = MyCommandCreatedHandler()
            # myCmdDef.commandCreated.add(onCommandCreated)
            # handlers.append(onCommandCreated)

            # prevent this module from being terminateD when the script returns,
            # because we are waiting for event handlers to fire
            adsk.autoTerminate(False)
            myCmdDef.execute()
        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

    def on_run(self):
        super().on_run()
        # The image that pops up when hovering over the command icon
        self.command_definition.toolClipFilename = str(self.tool_clip_file_path)

    def on_create(self, command, inputs):
        # Logging
        # Connect to the command object
        self.command = command

        # Add a tooclip image to the command
        self.command_definition.toolClipFilename = str(self.tool_clip_file_path)
        # Makes it so the command is not automatically executed when another
        # command gets activated.
        self.command.isExecutedWhenPreEmpted = False
        self.profile_data: dict


    def on_destroy(self, command: adsk.core.Command, inputs: adsk.core.CommandInputs,
                   reason: adsk.core.CommandTerminationReason, input_values: dict):

        # self.logger.debug("onDestroy triggered.")
        # self.logger.info("# Command Window closed.")
        # Removing and closing all handlers
        # root_logger = logging.getLogger()
        # for handler in root_logger.handlers:
        #     handler.close()
        #     root_logger.removeHandler(handler)

    def on_preview(self, command: adsk.core.Command,
                   inputs: adsk.core.CommandInputs,
                   args: adsk.core.CommandEventArgs, input_values: dict):
        # logging.debug("Preview triggered.")
        pass

    def createGUI(self):
        # Dividing command window into tabs
        inputs = self.command.commandInputs
        feature_tab = inputs.addTabCommandInput('tab_1', 'Feature').children


    def add_handlers(self):

        app = adsk.core.Application.get()
        ui = app.userInterface
        cmd = self.command

        # Connect to the command related events.
        onExecutePreview = MyCommandExecutePreviewHandler()
        cmd.executePreview.add(onExecutePreview)
        handlers.append(onExecutePreview)

        onExecute = MyCommandExecuteHandler()
        cmd.execute.add(onExecute)
        handlers.append(onExecute)
