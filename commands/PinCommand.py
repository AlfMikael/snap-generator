"""
The difference between the "Addition" version of the Pin and the "non-addition" is the inclusion of a
positive body when generating the slot. This insured that there is enough material around the pin
to support it.
"""

import adsk.core
import adsk.fusion
from adsk.core import SelectionCommandInput, DropDownStyles

import traceback
import json
from pathlib import Path
# import logging
# import logging.handlers

from ..apper import apper
from ..lib.snaplib.geometry import Pin
from ..lib.snaplib.control import value_input, JsonUpdater
from ..lib.snaplib.control import ProfileSettings, GapProfileSettings
from ..lib.snaplib.control import ProfileSwitcher, ProfileModifier
from ..lib.snaplib.configure import CONFIG_PATH
from ..lib.snaplib import configure

app = adsk.core.Application.get()
ui = app.userInterface
handlers = []
first_timeline_object_index = [0]

DEFAULT_SIZE = 0

target_body1 = None
target_body2 = None

def build(args, preview=False):
    """
    There is an important difference between this build function and the one that doesn't perform
    addition. The boolean joins and subtract is performed within this function, as opposed to within the
    Pin object.
    """
    try:
        app = adsk.core.Application.get()
        design = adsk.fusion.Design.cast(app.activeProduct)
        rootComp = design.rootComponent

        inputs = args.command.commandInputs
        # Build parameters
        parameter_ids = list(Pin.get_parameter_dict().keys())
        pos_parameters = ["x_location", "y_location"]  # Origin point of the component
        parameters = {}  # Assembly of parameters for constructing the geometry
        value_parameters = list(set(parameter_ids) - set(pos_parameters))  # Subset of parameters that are int or float

        # Retrieve the values from inputs and add them to the parameters
        # Two loops because one gets 'value', and the other 'name'.
        try:
            for par_id in value_parameters:
                par_value = inputs.itemById(par_id).value
                parameters[par_id] = par_value
            for par_id in pos_parameters:
                position = inputs.itemById(par_id).selectedItem.name
                parameters[par_id] = position
        except:
            # logging.error(f"Something went wrong with creating"
            #               f" parameter {par_id}")
            ui.messageBox(f"Id that failed: {par_id}")
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

        joint_origin = None
        joint_input = inputs.itemById("selected_origin")
        if joint_input.selectionCount == 1:
            joint_origin = joint_input.selection(0).entity

        """ At this point there should be one main body, one subtraction body, and two
        addition bodies. The following steps are for the boolean operations.
        """

        # Join the first addition body to the first selected mating body
        target1 = inputs.itemById("target1")
        target2 = inputs.itemById("target2")

        global target_body1
        global target_body2

        # Dealing with the bug in Fusion, where it deselects your choice
        if preview:
            if target1.selectionCount > 0:
                target_body1 = target1.selection(0).entity
            else:
                target_body1 = None
            if target2.selectionCount > 0:
                target_body2 = target2.selection(0).entity
            else:
                target_body2 = None

        # Perform the operations
        timeline_start = design.timeline.markerPosition
        pin = Pin(rootComp, parameters,
                              target_joint_org=joint_origin,
                              target_body1=target_body1,
                              target_body2=target_body2)

        # Draw lines if preview
        if preview:
            # Yellow line
            try:
                # Get the root component of the active design
                comp = pin.comp
                graphicsGroup = comp.customGraphicsGroups.add()

                # Define points along the X-axis
                start_point = adsk.core.Point3D.create(0, parameters["width"]/2, 0)  # Origin point
                end_point = adsk.core.Point3D.create(-parameters["length"]*4.5, parameters["width"]/2, 0)  # 100 units along the X-axis

                # Create custom graphics coordinates
                points = [
                    start_point.x, start_point.y, start_point.z,
                    end_point.x, end_point.y, end_point.z
                ]

                # Create the coordinates object
                coordinates = adsk.fusion.CustomGraphicsCoordinates.create(points)

                # Create the lines using the coordinates and indices
                lines = graphicsGroup.addLines(coordinates, [0, 1], False)

                # Optionally set the color of the line (red in this example)
                color = adsk.core.Color.create(255, 255, 0, 255)  # RGBA format
                colorEffect = adsk.fusion.CustomGraphicsSolidColorEffect.create(color)
                lines.color = colorEffect
                lines.weight = 5
                lines.depthPriority = 1000
                # Refresh the viewport to see the change
                app.activeViewport.refresh()
            except:
                ui.messageBox(traceback.format_exc())

            # Blue line
            try:
                # Get the root component of the active design
                comp = pin.comp
                graphicsGroup = comp.customGraphicsGroups.add()

                # Define points along the X-axis
                start_point = adsk.core.Point3D.create(0, parameters["width"]/2, 0)  # Origin point
                end_point = adsk.core.Point3D.create(parameters["length"]*4.5, parameters["width"]/2, 0)  # 100 units along the X-axis

                # Create custom graphics coordinates
                points = [
                    start_point.x, start_point.y, start_point.z,
                    end_point.x, end_point.y, end_point.z
                ]

                # Create the coordinates object
                coordinates = adsk.fusion.CustomGraphicsCoordinates.create(points)

                # Create the lines using the coordinates and indices
                lines = graphicsGroup.addLines(coordinates, [0, 1], False)

                # Optionally set the color of the line (red in this example)
                color = adsk.core.Color.create(0, 0, 255, 255)  # RGBA format
                colorEffect = adsk.fusion.CustomGraphicsSolidColorEffect.create(color)
                lines.color = colorEffect
                lines.weight = 5
                lines.depthPriority = 1000
                # Refresh the viewport to see the change
                app.activeViewport.refresh()
            except:
                ui.messageBox(traceback.format_exc())

        subtraction_body = pin.comp.bRepBodies.itemByName("Subtraction body")

        # Make som bodies less opaque
        if target_body1 and preview:
            target_body1.opacity = 0.40
            # Don't want to display subtraction body during preview
            subtraction_body.isVisible = False
        if target_body2 and preview:
            target_body2.opacity = 0.40
            # Don't want to display subtraction body during preview
            subtraction_body.isVisible = False

        # Remove subtraction body in the case of both additions being applied
        if target_body1 and target_body1:
            pin.comp.features.removeFeatures.add(subtraction_body)

        # If there is still a subtraction body, make it opaque
        if subtraction_body:
            subtraction_body.opacity = 0.3

        if pin.addition_body1:
            pin.addition_body1.opacity = 0.5

        if pin.addition_body2:
            pin.addition_body2.opacity = 0.5

        # Folding all operations neatly into a timeline block
        timeline_end = design.timeline.markerPosition
        timeline_group = design.timeline.timelineGroups.add(timeline_start,
                                                            timeline_end - 1)
        timeline_group.name = "Cantilever pin"

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def size_parameters(size, length_width_ratio=1.6):
    """
    This function generates a set of parameter values as a function -of the
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

    # logger = logging.getLogger("size-parameters")
    width = size
    extrusion_distance = size
    length = size * length_width_ratio
    gap_buffer = 0
    max_gap_buffer = 0.08
    if 0 < size <= 0.3:
        gap_buffer = size / 10
    elif 0.3 < size <= 1:
        gap_buffer = 0.030 + (size - 0.3) / 25
    elif 1 < size <= 1.5:
        gap_buffer = 0.050 + (max_gap_buffer-0.05)*(size - 1)/(1.5 - 1)
    elif 1.5 <= size:
        gap_buffer = max_gap_buffer

    thickness = width/2 - gap_buffer
    middle_padding = thickness
    ledge = width / 12
    gap_buffer = round(gap_buffer, 4)
    thickness = round(thickness, 4)
    ledge = round(ledge, 4)
    wall_thickness = round(size / 4, 4)

    advanced_params = {"width": width,
                       "length": length,
                       "extrusion_distance": extrusion_distance,
                       "thickness": thickness,
                       "middle_padding": middle_padding,
                       "ledge": ledge,
                       "gap_buffer": gap_buffer,
                       "wall_thickness": wall_thickness
                       }

    return advanced_params

class SizeInputHandler(adsk.core.InputChangedEventHandler):
    """
    Reacts when the 'size' field is changed, and changes a set of parameters
    by the "size_parameters" function. See its docstring for details.
    """
    def __init__(self, profile_data):
        self.profile_data = profile_data
        # self.logger = logging.getLogger(type(self).__name__)
        super().__init__()

    def notify(self, args):
        # ui.messageBox("Triggered size input")
        input_command = args.input
        all_inputs = args.inputs.command.commandInputs
        # self.logger.debug(f"Input = {input_command.id}")

        if input_command.id == "size":
            try:
                # self.logger.debug(f"Size triggered")
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
        # self.logger = logging.getLogger(type(self).__name__)

    def notify(self, args):
        # self.logger.debug("Triggered.")
        # ui.messageBox("Reached Preview")
        build(args, preview=True)


class MyCommandExecuteHandler(adsk.core.CommandEventHandler):
    """
    Triggered when user clicks OK in command interface.
    """
    def __init__(self):
        super().__init__()
        # self.logger = logging.getLogger(type(self).__name__)

    def notify(self, args):
        # self.logger.info("Ok-button clicked.")
        # self.logger.debug("Triggered.")
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
class PinCommand(apper.Fusion360CommandBase):
    GEOMETRY_PARAMETERS = [
        {
            "id": "nose_angle",
            "display_text": "Nose angle",
            "units": ""
        },
        {
            "id": "thickness",
            "display_text": "Thickness",
            "units": "mm"
        },
        {
            "id": "width",
            "display_text": "Width",
            "units": "mm"
        },
        {
            "id": "length",
            "display_text": "Length",
            "units": "mm"
        },
        {
            "id": "extrusion_distance",
            "display_text": "Extrusion distance",
            "units": "mm"
        },
        {
            "id": "strain",
            "display_text": "Strain",
            "units": ""
        },
        {
            "id": "pin_prestrain",
            "display_text": "Pin Prestrain",
            "units": ""
        },
        {
            "id": "ledge",
            "display_text": "Ledge",
            "units": "mm"
        },
        {
            "id": "middle_padding",
            "display_text": "Middle_padding",
            "units": "mm"
        },
        {
            "id": "gap_buffer",
            "display_text": "Gap buffer",
            "units": "mm"
        },
        {
            "id": "wall_thickness",
            "display_text": "Wall thickness",
            "units": "mm"
        },
    ]

    SIMPLE_GEOMETRY_PARAMETERS = [
        {
            "id": "simple_size",
            "display_text": "Size",
            "units": "mm"
        },
        {
            "id": "simple_strain",
            "display_text": "Size",
            "units": ""
        },
    ]

    GAP_PARAMETERS = [
        {
            "id": "width_gap",
            "display_text": "Thickness gap",
            "units": "mm"
        },
        {
            "id": "extrusion_gap",
            "display_text": "Extrusion gap",
            "units": "mm"
        },
        {
            "id": "length_gap",
            "display_text": "Length gap",
            "units": "mm"
        },
        {
            "id": "extra_length",
            "display_text": "Extra length",
            "units": "mm"
        },
    ]

    def __init__(self, name: str, options: dict):
        super().__init__(name, options)
        self.profiles_path = CONFIG_PATH / "ProfileData" / "Pin.json"
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
            self.command = command

            # Makes it so the command is not automatically executed when another
            # command gets activated.
            self.command.isExecutedWhenPreEmpted = False
            self.profile_data: dict

            # IO stuff
            try:
                # Checking and fixing profile_data json
                # If parent folder somehow is missing, add it
                profile_path = Path(self.profiles_path)
                if not self.profiles_path.parent.exists():
                    self.profiles_path.parent.mkdir(parents=True)

                if not profile_path.is_file():
                    # Profile does not exist, recreate it from default
                    configure.reset_single_profile_data("Pin")

                # Load profile data
                with open(profile_path, "r") as f:
                    self.profile_data = json.load(f)
            except:
                ui.messageBox(traceback.format_exc())

            self.add_handlers()
            self.createGUI()
        except:
            ui.messageBox(traceback.format_exc())

    def on_preview(self, command: adsk.core.Command,
                   inputs: adsk.core.CommandInputs,
                   args: adsk.core.CommandEventArgs, input_values: dict):
        pass

    def createGUI(self):
        # Dividing command window into tabs
        inputs = self.command.commandInputs
        feature_tab = inputs.addTabCommandInput('tab_1', 'Feature').children
        prof_tab = inputs.addTabCommandInput('tab_2', 'Profiles').children
        gap_tab = inputs.addTabCommandInput('tab_3', 'Gaps').children

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

        size_value = value_input(DEFAULT_SIZE)
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

        target1_input = selections.addSelectionInput("target2",
                                                        'Yellow body for slot',
                                                        'Select body in direction of yellow line')

        target1_input.addSelectionFilter(SelectionCommandInput.Bodies)
        target1_input.setSelectionLimits(0, 1)
        target1_input.tooltip = "First body to insert slot."

        target2_input = selections.addSelectionInput("target1",
                                                      'Blue body for slot',
                                                      'Select body in direction of blue line')

        target2_input.addSelectionFilter(SelectionCommandInput.Bodies)
        target2_input.setSelectionLimits(0, 1)
        target2_input.tooltip = "Inward body to insert slot."

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

        simple_handler = SizeInputHandler(self.profile_data)
        cmd.inputChanged.add(simple_handler)
        handlers.append(simple_handler)
