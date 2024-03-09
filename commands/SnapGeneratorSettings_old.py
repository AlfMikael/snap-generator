from apper import AppObjects, F360App
import adsk.core, adsk.fusion, adsk.cam


app = adsk.core.Application.get()
ui = app.userInterface
handlers = []

class SnapGeneratorSettings(apper.Fusion360CommandBase):
    def __init__(self, name, options):
        super().__init__(name, options)
        self.cantileverCommandEnabled = True
        self.cantileverPinCommandEnabled = True


        # Store logs and profile config in appropriate config folder.
        # Varies depending on operating system. See appdirs module.
        appname = "Snap Generator - Fusion 360 addin"
        version = "0.2.1"
        logs_folder = Path(
            appdirs.user_log_dir(appname=appname, version=version))
        config_folder = Path(
            appdirs.user_config_dir(appname=appname, version=version))


        # Loading references relative to this projects root
        self.root_dir = self.fusion_app.root_path
        self.resources_path = self.root_dir / "commands" / "resources" / \
                              "CantileverPinCommand"
        self.tool_clip_file_path = self.resources_path / "toolclip.png"

    def on_input_changed(self, command, inputs, changed_input, input_values):
        if changed_input.id == 'cantileverCommandEnabled':
            self.cantileverCommandEnabled = changed_input.value
        elif changed_input.id == 'cantileverPinCommandEnabled':
            self.cantileverPinCommandEnabled = changed_input.value

    def on_execute(self, command, inputs, args, input_values):
        # Implement the logic to enable or disable commands here.
        # For example, you could set a global or shared variable that your other commands check
        # before executing their main logic.
        print(f"Cantilever Command Enabled: {self.cantileverCommandEnabled}")
        print(f"Cantilever Pin Command Enabled: {self.cantileverPinCommandEnabled}")

    def on_create(self, command, inputs):
        inputs.addBoolValueInput('cantileverCommandEnabled', 'Enable Cantilever Command', True, '',
                                 self.cantileverCommandEnabled)
        inputs.addBoolValueInput('cantileverPinCommandEnabled', 'Enable Cantilever Pin Command', True, '',
                                 self.cantileverPinCommandEnabled)