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
from .snap.geometry import BaseSnap, CantileverPin
from .snap.control import value_input, JsonUpdater
from .snap.control import ProfileSection, ProfileSettings, GapProfileSettings
from .snap.control import ProfileSwitcher, ProfileModifier
from ..lib import appdirs


app = adsk.core.Application.get()
ui = app.userInterface
handlers = []
first_timeline_object_index = [0]


def build(args, preview=False):
    try:
        logger = logging.getLogger("build")
        logger.debug("Build function initiated.")
        app = adsk.core.Application.get()
        design = adsk.fusion.Design.cast(app.activeProduct)
        rootComp = design.rootComponent

        inputs = args.command.commandInputs
        # Build parameters
        parameter_ids = list(CantileverPin.get_parameter_dict().keys())
        pos_parameters = ["x_location", "y_location"]
        parameters = {}
        value_parameters = list(set(parameter_ids) - set(pos_parameters))
        try:
            for par_id in value_parameters:
                par_value = inputs.itemById(par_id).value
                parameters[par_id] = par_value
            for par_id in pos_parameters:
                position = inputs.itemById(par_id).selectedItem.name
                parameters[par_id] = position
        except:
            logging.error(f"Something went wrong with creating"
                          f" parameter {par_id}")
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

        joint_origin = None
        joint_input = inputs.itemById("selected_origin")
        if joint_input.selectionCount == 1:
            joint_origin = joint_input.selection(0).entity

        cut_body_input = inputs.itemById("cut_bodies")
        cut_bodies = []
        body_count = cut_body_input.selectionCount
        for i in range(body_count):
            body = cut_body_input.selection(i).entity
            cut_bodies.append(body)
            # Make cut bodies transparent in preview mode
            if preview:
                body.opacity = 0.5

        # Performing the actual operations
        timeline_start = design.timeline.markerPosition

        CantileverPin(rootComp, parameters,
                      target_joint_org=joint_origin,
                      cut_bodies=cut_bodies)
        logging.info(f"Build succeeded with {len(cut_bodies)} cut_bodies.")
        timeline_end = design.timeline.markerPosition
        timeline_group = design.timeline.timelineGroups.add(timeline_start,
                                                            timeline_end - 1)
        timeline_group.name = "Cantilever pin"

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def get_mating_force(parameters):
    # todo: Implement get_mating_force
    pass


def size_parameters(size, length_width_ratio=1.6):
    """
    This function generates a set of parameter values as a function of the
    value of size. This is intended to make a sort of "standardized"
    geometry, so that the different parameters scale well with the overall
    size. For example, the size of the ledge should not be linear with the
    overall with of the pin. That would make it uselessly small for small
    pins, and pointlessly large for large pins. Radius on the other hand,
    has an optimal value unrelated to the size of the pin: 1.5mm (to combat
    fatigue). This can't achieved on small pins because then they wouldn't
    have any thickness, so a compromise has to be made.

    Parameters unaffected by size: strain, nose_angle and all gaps.
    """

    logger = logging.getLogger("size-parameters")
    # Don't allow size to go below 3
    # Kind of a dirty hack, but avoids trouble.
    if size <= 0.3:
        size = 0.3
    width = size
    extrusion_distance = size
    length = size * length_width_ratio
    inner_radius = 0
    gap_buffer = 0
    if 0 < size <= 0.3:
        inner_radius = 0.03
        gap_buffer = 0.030
    elif 0.3 < size <= 1:
        inner_radius = 0.03 + (size - 0.3) / 12
        gap_buffer = 0.030 + (size - 0.3) / 25
    elif 1 < size <= 1.5:
        inner_radius = 0.05 + (size - 0.3) / 12
        gap_buffer = 0.050
    elif 1.5 <= size:
        inner_radius = 0.15
        gap_buffer = 0.050

    thickness = width / 2 - inner_radius - gap_buffer
    middle_padding = thickness
    ledge = 0.05 + width / 20

    gap_buffer = round(gap_buffer, 4)
    thickness = round(thickness, 4)
    ledge = round(ledge, 4)
    inner_radius = round(inner_radius, 4)
    size = round(size, 4)

    advanced_params = {"width": width,
                       "length": length,
                       "extrusion_distance": extrusion_distance,
                       "inner_radius": inner_radius,
                       "thickness": thickness,
                       "middle_padding": middle_padding,
                       "ledge": ledge,
                       }

    logger.debug(f"Size={round(size*10, 5)}mm.\tRadius={round(inner_radius*10, 5)}mm\t"
                 f"Gap buffer={round(gap_buffer*10, 5)}mm")
    return advanced_params


class InputLimiter(adsk.core.ValidateInputsEventHandler):
    """
    Triggered when the user makes a change to any fields, and in fact it also
    triggers a bunch of additional times. Don't know why.
    If all the parameters are within acceptable intervals, it does nothing, and
    allows ExecutePreviewHandler or ExecuteHandler to be triggered. If any
    value is out of bounds, nothing happens, and any features that were
    previously generated by ExecutePreviewHandler will disappear.
    """
    logger = logging.getLogger("InputLimiter")
    def notify(self, args):
        try:
            all_inputs = args.inputs

            # size is evaluated because it isn't an actual parameter, and it
            # can be the case that the value of size is not related the actual
            # parameters, because there is only a one way relationship
            # size affects parameters, but parameters don't affect size.
            length = all_inputs.itemById("length").value
            width = all_inputs.itemById("width").value
            inner_radius = all_inputs.itemById("inner_radius").value
            middle_padding = all_inputs.itemById("middle_padding").value
            ledge = all_inputs.itemById("ledge").value
            strain = all_inputs.itemById("strain").value
            thickness = all_inputs.itemById("thickness").value
            extrusion_distance = all_inputs.itemById("extrusion_distance").value
            nose_angle = all_inputs.itemById("nose_angle").value
            gap_extrusion = all_inputs.itemById("gap_extrusion").value
            gap_length = all_inputs.itemById("gap_length").value
            gap_thickness = all_inputs.itemById("gap_thickness").value
            extra_length = all_inputs.itemById("extra_length").value

            middle_flat = width/2 - thickness - inner_radius - gap_thickness

            if length < 0.48:
                args.areInputsValid = False
                self.logger.info("Input invalid because length is too small .")
            elif width <= 0.3:
                args.areInputsValid = False
                self.logger.info("Input invalid because width is too small.")
            elif inner_radius < 0:
                args.areInputsValid = False
                self.logger.info("Input invalid because inner radius is negative.")
            elif middle_flat < 0:
                args.areInputsValid = False
                self.logger.info("Input invalid because middle flat is too small.")
            elif middle_padding <= 0:
                args.areInputsValid = False
                self.logger.info("Input invalid gap thickness is too big "
                                 "compared to the difference between width "
                                 "and thickness. Either reduce thickness, or "
                                 "increase width.")
            elif ledge < 0:
                args.areInputsValid = False
                self.logger.info("Input invalid because ledge is negative.")
            elif strain < 0:
                args.areInputsValid = False
                self.logger.info("Input invalid because strain is negative.")
            elif extrusion_distance <= 0:
                args.areInputsValid = False
                self.logger.info("Input invalid because extrusion distance is too small.")
            elif nose_angle < 20 or nose_angle > 140:
                args.areInputsValid = False
                self.logger.info("Input invalid because nose angle is too big or too small.")
            elif extra_length < 0:
                args.areInputsValid = False
                self.logger.info("Input invalid because extra length is negative.")
            else:
                args.areInputsValid = True

        except:
            ui.messageBox(traceback.format_exc())


class SizeInputHandler(adsk.core.InputChangedEventHandler):
    """
    Reacts when the 'size' field is changed, and changes a set of parameters
    by the "size_parameters" function. See its docstring for details.
    """
    def __init__(self, profile_data):
        self.profile_data = profile_data
        self.logger = logging.getLogger(type(self).__name__)
        super().__init__()

    def notify(self, args):
        input_command = args.input
        all_inputs = args.inputs.command.commandInputs
        self.logger.debug(f"Input = {input_command.id}")
        if input_command.id == "size":
            try:
                self.logger.debug(f"Size triggered")
                size = input_command.value
                parameters = size_parameters(size)
                for key, value in parameters.items():
                    all_inputs.itemById(key).value = value
            except:
                ui.messageBox(f"Error: {traceback.format_exc()}")


class MyCommandExecutePreviewHandler(adsk.core.CommandEventHandler):
    """
    Triggered when user makes any change to a parameter that is related to
    performing the feature operations.
    """
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(type(self).__name__)

    def notify(self, args):
        self.logger.debug("Triggered.")
        build(args, preview=True)


class MyCommandExecuteHandler(adsk.core.CommandEventHandler):
    """
    Triggered when user clicks OK in command interface.
    """
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(type(self).__name__)

    def notify(self, args):
        self.logger.info("Ok-button clicked.")
        self.logger.debug("Triggered.")
        try:
            design = adsk.fusion.Design.cast(app.activeProduct)
            if design:
                build(args, preview=False)
        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


# Class for a Fusion 360 Command
# Place your program logic here
# Delete the line that says "pass" for any method you want to use
class CantileverPinCommand(apper.Fusion360CommandBase):

    GEOMETRY_PARAMETERS = [
        {"id": "nose_angle", "display_text": "Nose angle", "units": ""},
        {"id": "thickness", "display_text": "Thickness", "units": "mm"},
        {"id": "width", "display_text": "Width", "units": "mm"},
        {"id": "length", "display_text": "Length", "units": "mm"},
        {"id": "extrusion_distance", "display_text": "Extrusion distance",
         "units": "mm"},
        {"id": "strain", "display_text": "Strain", "units": ""},
        {"id": "ledge", "display_text": "Ledge", "units": "mm"},
        {"id": "middle_padding", "display_text": "Middle_padding",
         "units": "mm"},
        {"id": "inner_radius", "display_text": "Inner Radius", "units": "mm"}
    ]
    SIMPLE_GEOMETRY_PARAMETERS = [
        {"id": "simple_size", "display_text": "Size", "units": "mm"},
        {"id": "simple_strain", "display_text": "Size", "units": ""}
    ]
    GAP_PARAMETERS = [
        {"id": "gap_thickness", "display_text": "Gap thickness", "units": "mm"},
        {"id": "gap_extrusion", "display_text": "Gap extrusion", "units": "mm"},
        {"id": "gap_length", "display_text": "Gap length", "units": "mm"},
        {"id": "extra_length", "display_text": "Extra length", "units": "mm"}
    ]

    # Default data for JSON file if it doesn't exist
    FALLBACK_JSON = {
        "default_profile": "default",
        "default_gap_profile": "default",
        "profiles": {
            "default": {
                "thickness": 0.3,
                "length": 1.2,
                "width": 0.9,
                "extrusion_distance": 0.9,
                "strain": 0.02,
                "inner_radius": 0.1,
                "ledge": 0.1,
                "middle_padding": 0.3,
                "nose_angle": 70
            }
        },
        "gap_profiles": {
            "default": {
                "gap_thickness": 0.015,
                "gap_length": 0.015,
                "gap_extrusion": 0.015,
                "extra_length": 0.06
            }
        }
    }

    # Default value for the size (fake) parameter.
    DEFAULT_SIZE = 0  # cm

    def __init__(self, name: str, options: dict):
        super().__init__(name, options)

        # Store logs and profile config in appropriate config folder.
        # Varies depending on operating system. See appdirs module.
        appname = "Snap Generator - Fusion 360 addin"
        version = "0.2.1"
        logs_folder = Path(
            appdirs.user_log_dir(appname=appname, version=version))
        config_folder = Path(
            appdirs.user_config_dir(appname=appname, version=version))

        if not logs_folder.exists():
            logs_folder.mkdir(parents=True)
        self.log_path = logs_folder / "CantileverPinCommand.log"

        self.profiles_path = config_folder / "Profile Data" / "CantileverPinCommand.json"
        if not self.profiles_path.parent.exists():
            self.profiles_path.parent.mkdir(parents=True)

        # Loading references relative to this projects root
        self.root_dir = self.fusion_app.root_path
        self.resources_path = self.root_dir / "commands" / "resources" / \
                              "CantileverPinCommand"
        self.tool_clip_file_path = self.resources_path / "toolclip.png"

    def on_execute(self, command: adsk.core.Command,
                   inputs: adsk.core.CommandInputs,
                   args: adsk.core.CommandEventArgs, input_values: dict):
        pass

    def on_run(self):
        super().on_run()
        # The image that pops up when hovering over the command icon
        self.command_definition.toolClipFilename = str(self.tool_clip_file_path)

    def on_create(self, command, inputs):
        try:
            """Setting up logging"""
            fh = logging.FileHandler(self.log_path, mode="w")
            fh.setLevel(logging.DEBUG)

            logging_format = logging.Formatter('%(asctime)s - %(name)s - %('
                                               'levelname)s: '
                                               ' %(message)s',
                                               datefmt='%H:%M:%S')
            fh.setFormatter(logging_format)
            fh.mode = "w"

            root_logger = logging.getLogger()
            root_logger.propagate = True
            for handler in root_logger.handlers:
                root_logger.removeHandler(handler)

            root_logger.setLevel(logging.DEBUG)
            root_logger.addHandler(fh)

            self.logger = logging.getLogger(type(self).__name__)
            logging.debug("####### NEW RUN.")

            self.command = command

            # Makes it so the command is not automatically executed when another
            # command gets activated.
            self.command.isExecutedWhenPreEmpted = False
            self.profile_data: dict

            # Checking and fixing profile_data json
            # If parent folder somehow is missing, add it
            profile_path = Path(self.profiles_path)
            if not self.profiles_path.parent.exists():
                self.profiles_path.parent.mkdir(parents=True)

            if profile_path.is_file():
                with open(profile_path, "r") as f:
                    self.profile_data = json.load(f)
            else:
                with open(profile_path, "w") as f:
                    json.dump(self.FALLBACK_JSON, f, indent=2)
                self.profile_data = self.FALLBACK_JSON

            self.createGUI()
            self.logger.debug("Finished GUI")
            self.add_handlers()
            self.logger.debug("Finished handlers.")
        except:
            ui.messageBox(traceback.format_exc())

    def on_preview(self, command: adsk.core.Command,
                   inputs: adsk.core.CommandInputs,
                   args: adsk.core.CommandEventArgs, input_values: dict):
        # logging.debug("Preview triggered.")
        pass

    def createGUI(self):
        # Dividing command window into tabs
        inputs = self.command.commandInputs
        feature_tab = inputs.addTabCommandInput('tab_1', 'Feature').children
        prof_tab = inputs.addTabCommandInput('tab_2', 'Profiles').children
        gap_tab = inputs.addTabCommandInput('tab_3', 'Gaps').children

        default_profile_name = self.profile_data["default_profile"]
        # size = self.profile_data["profiles"][default_profile_name]["width"]
        # strain = self.profile_data["profiles"][default_profile_name]["strain"]

        """
            FEATURE TAB
            The user selects the properties of the snap mechanism. Either from 
            a stored profile or custom defined.
        """

        # todo: add an error message at the top for when input fails

        # Geometry section
        geometry_group = feature_tab.addGroupCommandInput("geometry",
                                                          "Geometry")
        geo_list = geometry_group.children

        profile_list = geo_list.addDropDownCommandInput(
            "profile_list", "Profile",
            DropDownStyles.LabeledIconDropDownStyle)
        profile_list.maxVisibleItems = 10
        # profile_list.isFullWidth = True
        blank_icon_path = self.resources_path / "white"

        default_profile_name = self.profile_data["default_profile"]
        items = profile_list.listItems
        for key in self.profile_data["profiles"]:
            if key == default_profile_name:
                items.add(key, True, str(blank_icon_path))
            else:
                items.add(key, False, str(blank_icon_path))

        default_profile_name = self.profile_data['default_profile']
        profile = self.profile_data["profiles"][default_profile_name]

        # SIZE is not in the list of parameters, because it is not a real
        # parameter. It is just a way to change all of them in a fell swoop
        size_value = value_input(self.DEFAULT_SIZE)

        geo_list.addValueInput("size", "SIZE", "mm", size_value)


        for geo_par in self.GEOMETRY_PARAMETERS:
            geo_id = geo_par["id"]
            display_text = geo_par["display_text"]
            unit = geo_par["units"]
            value = value_input(profile[geo_id])
            geo_list.addValueInput(geo_id, display_text, unit, value)

        # Gap section
        gap_group = feature_tab.addGroupCommandInput("gaps", "Gaps")
        gap_list = gap_group.children

        default_gap_profile_name = self.profile_data['default_gap_profile']

        gap_profile_list = gap_list.addDropDownCommandInput(
            "gap_profiles", "Gap profile",
            DropDownStyles.LabeledIconDropDownStyle)

        items = gap_profile_list.listItems
        for key in self.profile_data["gap_profiles"]:
            if key == default_gap_profile_name:
                items.add(key, True, str(blank_icon_path))
            else:
                items.add(key, False, str(blank_icon_path))

        default_gap_profile = self.profile_data["gap_profiles"][
            default_gap_profile_name]

        for gap_par in self.GAP_PARAMETERS:
            geo_id = gap_par["id"]
            display_text = gap_par["display_text"]
            unit = gap_par["units"]
            value = value_input(default_gap_profile[geo_id])
            gap_list.addValueInput(geo_id, display_text, unit, value)

        # Selection section
        selections_group = feature_tab.addGroupCommandInput("selections",
                                                            "Selections")
        selections = selections_group.children
        joint_org_input = selections.addSelectionInput('selected_origin',
                                                       'Joint origin',
                                                       'Joint origin')
        jointOrigins = SelectionCommandInput.JointOrigins
        joint_org_input.addSelectionFilter(jointOrigins)
        joint_org_input.setSelectionLimits(0, 1)
        joint_org_input.tooltip = "First create a joint origin feature at " \
                                  "a certain position and orientation. Then" \
                                  " select it here to position the pin."

        cut_body_input = selections.addSelectionInput("cut_bodies",
                                                      'Bodies to cut',
                                                      'Bodies to cut')
        cut_body_input.addSelectionFilter(SelectionCommandInput.Bodies)
        cut_body_input.setSelectionLimits(0)
        cut_body_input.tooltip = "Select the bodies that you want the pin to" \
                                 " connect. A mating hole will be created for" \
                                 " the pin."

        """
            Position section
            Each button is an image. Fusion accepts a folder path and assumes
            the image has the name '16x16-normal.png' within that folder.
            It also uses the '16-16-disabled.png' for the other button state.
            Note that it is in fact possible to use an image that has different 
            dimensions than 16x16. Probably a bug.
            """

        # For choosing x_location
        joint_choice = selections.addButtonRowCommandInput("x_location",
                                                            "x location",
                                                            False)
        joint_choice.tooltip = "Choose the x-location of the origin."
        x_items = joint_choice.listItems

        x_top_folder_path = self.resources_path / "joint_pos_thickness" / "top"
        x_middle_folder_path = self.resources_path / "joint_pos_thickness" / "middle"
        x_bottom_folder_path = self.resources_path / "joint_pos_thickness" / "bottom"

        x_items.add("top", False, str(x_top_folder_path))
        x_items.add("middle", True, str(x_middle_folder_path))
        x_items.add("bottom", False, str(x_bottom_folder_path))

        # x_tooltip_path = self.RESOURCE_FOLDER / "joint_pos_height" / "tooltipclip.png"
        # joint_choice.toolClipFilename = str(x_tooltip_path)

        # y_location
        joint_choice = selections.addButtonRowCommandInput("y_location",
                                                            "y location",
                                                            False)
        y_items = joint_choice.listItems
        y_top_folder_path = self.resources_path / "joint_pos_length" / "top"
        y_middle_folder_path = self.resources_path / "joint_pos_length" / "middle"
        y_bottom_folder_path = self.resources_path / "joint_pos_length" / "bottom"

        y_items.add("top", False, str(y_top_folder_path))
        y_items.add("middle", True, str(y_middle_folder_path))
        y_items.add("bottom", False, str(y_bottom_folder_path))

        # y_tooltip_path = self.RESOURCE_FOLDER / "joint_pos_length" / "tooltipclip.png"
        # joint_choice.toolClipFilename = str(y_tooltip_path)
        joint_choice.tooltip = "Choose the y location of the origin."

        """
            Profile Tab
            The gui elements make changes on the profile_data dictionary, but
            does not perform IO.       
            """
        prof_settings = ProfileSettings(self.profile_data)
        prof_settings.add_to_inputs(prof_tab)

        """
            Gap profile tab
            The gui elements make changes on the profile_data dictionary, but
            does not perform IO.
            """
        prof_settings = GapProfileSettings(self.profile_data)
        prof_settings.add_to_inputs(gap_tab)

    def add_handlers(self):

        cmd = self.command

        # Connect to the command related events.
        onExecutePreview = MyCommandExecutePreviewHandler()
        cmd.executePreview.add(onExecutePreview)
        handlers.append(onExecutePreview)

        onExecute = MyCommandExecuteHandler()
        cmd.execute.add(onExecute)
        handlers.append(onExecute)

        profile_switcher = ProfileSwitcher(self.profile_data)
        cmd.inputChanged.add(profile_switcher)
        handlers.append(profile_switcher)

        profile_modifier = ProfileModifier(self.profile_data,
                                           self.resources_path)
        cmd.inputChanged.add(profile_modifier)
        handlers.append(profile_modifier)

        j_updater = JsonUpdater(self.profile_data, self.profiles_path)
        cmd.inputChanged.add(j_updater)
        handlers.append(j_updater)

        # input_synchronizer = ValueCommandSynchronizer(self.LINKED_INPUT_IDS)
        # cmd.inputChanged.add(input_synchronizer)
        # handlers.append(input_synchronizer)

        simple_handler = SizeInputHandler(self.profile_data)
        cmd.inputChanged.add(simple_handler)
        handlers.append(simple_handler)

        input_limiter = InputLimiter()
        cmd.validateInputs.add(input_limiter)
        handlers.append(input_limiter)