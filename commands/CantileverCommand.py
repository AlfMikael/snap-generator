import adsk.core
import adsk.fusion
import adsk.cam
from adsk.core import SelectionCommandInput, DropDownStyles
from adsk.core import ValueInput as valueInput
from adsk.fusion import Component

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

from .test_lib import get_cantilever

import cadquery as cq

import math

app = adsk.core.Application.get()
ui = app.userInterface
handlers = []

import time

execute_triggered = False
previous_parameters = None
previous_selections = set()
its_time_to_stop = False
first_execute_started = False
second_execute_started = False



finished_runs = []


BASE_PARAMETERS = {}
BASE_PARAMETERS["thickness"] = 4
BASE_PARAMETERS["width"] = 8
BASE_PARAMETERS["length"] = 12
BASE_PARAMETERS["strain"] = 0.04
BASE_PARAMETERS["nose_angle"] = math.radians(85)
BASE_PARAMETERS["name"] = "default_cantilever"
BASE_PARAMETERS["r_top"] = 1.5

PARAMETERS = {
    "inner_radius": (float, int),
    "strain": (float, int),
    "thickness": (float, int),
    "length": (float, int),
    "width": (float, int),
    "ledge": (float, int),
    "middle_padding": (float, int),
    "nose_angle": (float, int),
    "gap_length": (float, int),
    "gap_thickness": (float, int),
    "gap_extrusion": (float, int),
    "extra_length": (float, int),
    "x_location": (str,),
    "y_location": (str,),
    "name": (str,)
}
VALUE_PARAMETERS = [
    "inner_radius",
    "strain",
    "thickness",
    "length",
    "width",
    "ledge",
    "middle_padding",
    "nose_angle",
    "gap_length",
    "gap_thickness",
    "gap_extrusion",
    "extra_length"
]
MULTIPLY10_KEYS = [
    "inner_radius",
    "thickness",
    "length",
    "width",
    "ledge",
    "middle_padding",
    "gap_length",
    "gap_thickness",
    "gap_extrusion",
    "extra_length"
]
SHOW_BOXES = False


def generate_cantilever(params):
    # Step 1: Set variables to parameters
    p = BASE_PARAMETERS.copy()
    p.update(params)

    relevant_params = ["thickness", "length", "strain", "nose_angle",
                       "width", "r_top", "name"]

    th, l, strain, nose_angle, width, r_top, name = [p[x] for x in
                                                     relevant_params]

    nose_angle = math.radians(nose_angle)

    nose_height = 1.09 * strain * l ** 2 / th
    nose_x = nose_height / math.tan(nose_angle)

    # Step 2: Draw straight lines
    point_data = ([(0, 0),  # Starts at bottom
               (l * 1.20 + nose_x, 1 / 2 * th * 1.25),
               (l * 1.20 + nose_x, 3 / 4 * th),
               (l * 1.07 + nose_x, th + nose_height),
               (l + nose_x, th + nose_height),
               (l, th),
               (r_top, th)
               ])
    x = [point[0] for point in point_data]
    y = [point[1] for point in point_data]

    part = (
        cq.Workplane("XY")
            .moveTo(x[0], y[0])
    )
    for i in range(1, len(x)):
        part = part.lineTo(x[i], y[i])

    # Step 3: Create a radius arc
    # An arc is drawn from p0 to p2
    # To get the correct arc, an additional point (p1) must be identified
    p2 = (0, th + r_top)  # Top of radius

    deg = math.radians(10)  # An arbitrary angle on the arc
    p1_x = r_top * (1 - math.sin(deg))
    p1_y = r_top * (1 - math.cos(deg)) + th
    p1 = (p1_x, p1_y)
    part = part.threePointArc(p1, p2)

    # Step 4: close the curve and extrude
    part = part.close()
    part = part.extrude(width / 2, both=True)

    # Step 4: Position part so that origin is in the intended center of part
    part = part.translate((0, -th / 2, 0))

    # Step 5: Export file
    cq.exporters.export(part, name + ".step")

    # Open stepfile to edit
    from steputils import p21
    fname = name + ".step"
    stepfile = p21.readfile(fname)

    product = stepfile.data[0].get("#7")
    product.entity.params = (name,)

    stepfile.save(fname)





def import_part(name):
    # Import part to Fusion 360
    app = adsk.core.Application.get()
    ui = app.userInterface
    # Get import manager
    importManager = app.importManager

    # Get active design
    product = app.activeProduct
    design = adsk.fusion.Design.cast(product)

    # Get root component
    # comp = design.rootComponent

    # Get current active component
    comp = design.rootComponent

    # Get step import options
    stpFileName = name + ".step"
    stpOptions = importManager.createSTEPImportOptions(stpFileName)
    stpOptions.isViewFit = False

    # Import step file to root component
    imported_comp = importManager.importToTarget2(stpOptions, comp)
    return imported_comp


    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        # Get import manager
        importManager = app.importManager

        # Get active design
        product = app.activeProduct
        design = adsk.fusion.Design.cast(product)

        # Get root component
        # comp = design.rootComponent

        # Get current active component
        comp = design.activeComponent

        # Get step import options
        stpFileName = p["name"] + ".step"
        stpOptions = importManager.createSTEPImportOptions(stpFileName)
        stpOptions.isViewFit = False

        # Import step file to root component
        imported_comp = importManager.importToTarget2(stpOptions, comp)
        return imported_comp

    except:
        if ui:
            ui.messageBox('Import step file Failed:\n{}'.format(traceback.format_exc()))


def build_preview(args, preview=False):
    # return
    global first_execute_started
    execute = not preview

    inputs = args.command.commandInputs
    design = adsk.fusion.Design.cast(app.activeProduct)
    body_count = inputs.itemById("cut_bodies").selectionCount
    #ui.messageBox(f"FirstBox: {preview=}, {first_execute_started=} of cut bodies selected: {body_count}")


#    if not first_execute:
 #       return

    # Retrieve parameters from arguments

    timeline_start = design.timeline.markerPosition

    parameters = BASE_PARAMETERS.copy() # For external calls
    fusion_parameters = {}              # For internal calls

    try:
        logger = logging.getLogger("build-function")
        logger.debug("Build initiated.")

        inputs = args.command.commandInputs
        # Add parameters to dictionaries, making necessary adjustments
        try:
            for par_id in PARAMETERS.keys():
                item = inputs.itemById(par_id)
                if item is None:
                    continue
                if par_id in VALUE_PARAMETERS: # Value is gotten by .value
                    fusion_parameters[par_id] = item.value
                    if par_id in MULTIPLY10_KEYS:
                        parameters[par_id] = item.value * 10
                    else:
                        parameters[par_id] = item.value
                # If the parameter results from a 'selection' rather than
                # a typed value
                else:
                    value = item.selectedItem.name
                    fusion_parameters[par_id] = value
                    parameters[par_id] = value

        except:
            logger.error(f"Something went wrong with creating"
                  f" parameter {par_id}")
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

        # To prevent an additional preview version of the component being
        # generated on clicking 'OK'

        ###### Begin HACK
        # This is to prevent preview from being generated an additional
        # time when clicking OK. However it is necessary to isolate this exact
        # condition, hence the code below. Without this, the part will fail to
        # generate a preview when selecting joint_origin or cut or join body.
        # todo: include for all selected cut_bodies. Now it fails to regenerate
        # for all
        current_selections = set()
        if inputs.itemById("selected_origin").selectionCount == 1:
            org_selection = inputs.itemById("selected_origin").selection(0)
            entity = org_selection.entity
            current_selections.add(entity.name)

        if inputs.itemById("cut_bodies").selectionCount > 0:
            cut_body_selection = inputs.itemById("cut_bodies").selection(0)
            entity = cut_body_selection.entity
            current_selections.add(entity.name)

        if inputs.itemById("join_body").selectionCount == 1:
            join_body_selection = inputs.itemById("join_body").selection(0)
            entity = join_body_selection.entity
            current_selections.add(entity.name)
        #ui.messageBox(f"SECOND: {preview=} of cut bodies selected: {body_count}")

        if SHOW_BOXES:
            ui.messageBox(f"SECOND: {execute=},"
                      f" {first_execute_started=},"
                      f" {second_execute_started=}")

        global previous_parameters
        global previous_selections

        # if preview and previous_parameters == parameters:
        #     if previous_selections == current_selections:
        #         return

        # ui.messageBox(f"THIRD: {preview=} of cut bodies selected: {body_count}")

        previous_selections = current_selections
        previous_parameters = parameters.copy()
        #global first_execute

        #### END HACK

        # if its_time_to_stop:
        #     return

        it_crashed = False
        generate_cantilever(parameters)
        #ui.messageBox("Parameters for cadquery:" + str(parameters))
        try:
            cantilever = import_part(parameters["name"]).item(0).component  # Component
        except:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

        if SHOW_BOXES:
            ui.messageBox(f"THIRD: {execute=},"
                          f" {first_execute_started=},"
                          f" {second_execute_started}",
                          f" {its_time_to_stop=}",
                          )

        # cantilever_description_keys = ["length", "thickness",
        #                                "width",
        #                                "strain", "nose_angle"]
        # description_dict = {x: parameters[x] for x in
        #                     cantilever_description_keys}
        # cantilever.description = str(description_dict)

        # Join joint origins if they exist
        joint_input = inputs.itemById("selected_origin")
        if joint_input.selectionCount == 1:
            selected_joint_origin = joint_input.selection(0).entity

            jointGeometry = adsk.fusion.JointGeometry
            jointOrigins = cantilever.jointOrigins
            point = cantilever.originConstructionPoint
            geo = jointGeometry.createByPoint(point)
            joint_origin_input = jointOrigins.createInput(geo)
            joint_origin_input.xAxisEntity = cantilever.yConstructionAxis
            joint_origin_input.zAxisEntity = cantilever.xConstructionAxis

            # Joint origin on cantilever part
            joint_origin = jointOrigins.add(joint_origin_input)

            parent_comp = selected_joint_origin.parentComponent
            joints = parent_comp.joints
            joint_input = joints.createInput(joint_origin, selected_joint_origin)
            joint_input.angle = valueInput.createByString("0 deg")
            joint = joints.add(joint_input)
            joint.isLightBulbOn = True

        # Perform joining and cutting of bodies
        cut_body_input = inputs.itemById("cut_bodies")
        cut_bodies = []
        body_count = cut_body_input.selectionCount

        for i in range(body_count): # If 0 no operations
            body = cut_body_input.selection(i).entity
            cut_bodies.append(body)
            # Make cut bodies transparent in preview mode
            if not first_execute_started:
                body.opacity = 0.5


        cant_body = cantilever.bRepBodies[0]
        root_comp = design.rootComponent
        combineFeatures = root_comp.features.combineFeatures
        CutFeatureOperation = adsk.fusion.FeatureOperations.CutFeatureOperation

        subtraction_body = cant_body
        for body_to_cut in cut_bodies:
            tool_bodies = adsk.core.ObjectCollection.create()
            tool_bodies.add(subtraction_body)
            combine_input = combineFeatures.createInput(body_to_cut,
                                                        tool_bodies)
            combine_input.isKeepToolBodies = True
            combine_input.operation = CutFeatureOperation
            combineFeatures.add(combine_input)

        # Finally fix everything up in the timeline
        timeline_end = design.timeline.markerPosition

        cantilever_description_keys = ["length", "thickness",
                                       "width",
                                       "strain", "nose_angle"]
        description_dict = {x: parameters[x] for x in
                            cantilever_description_keys}
        cantilever.description = str(description_dict)

    except:
        if ui:
            logger.error(f"BUILD FAILED!, traceback" + traceback.format_exc())
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def build_execute(args, preview=False):
    design = adsk.fusion.Design.cast(app.activeProduct)
    timeline_start = design.timeline.markerPosition
    #ui.messageBox(f"FirstBox: {preview=}, {first_execute_started=} of cut bodies selected: {body_count}")

    parameters = BASE_PARAMETERS.copy()
    name = parameters["name"]

    try:
        import_part(name)
        if SHOW_BOXES:
            ui.messageBox(f"{preview}, IMPORT CRASH")
    except:
        design.timeline.item(timeline_start).deleteMe(True)

    if SHOW_BOXES:
        ui.messageBox(f"THIRD: (execute),"
                      f" {first_execute_started=},"
                      f" {second_execute_started}",
                      f" {its_time_to_stop=}",
                      )



def mating_force(parameters):
    # todo: Implement get_mating_force
    pass


class InputLimiter(adsk.core.ValidateInputsEventHandler):
    """
    Triggered when the user makes a change to any fields, and in fact it also
    triggers a bunch of additional times. Don't know why.
    If all the parameters are within acceptable intervals, it does nothing, and
    allows ExecutePreviewHandler or ExecuteHandler to be triggered. If any
    value is out of bounds, nothing happens, and any features that were
    previously generated by ExecutePreviewHandler will disappear.
    """
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("InputLimiter")

    def notify(self, args):
        try:
            all_inputs = args.inputs

            length = all_inputs.itemById("length").value
            top_radius = all_inputs.itemById("top_radius").value
            bottom_radius = all_inputs.itemById("bottom_radius").value
            strain = all_inputs.itemById("strain").value
            thickness = all_inputs.itemById("thickness").value
            width = all_inputs.itemById("width").value
            nose_angle = all_inputs.itemById("nose_angle").value
            gap_extrusion = all_inputs.itemById("gap_extrusion").value
            gap_length = all_inputs.itemById("gap_length").value
            gap_thickness = all_inputs.itemById("gap_thickness").value
            extra_length = all_inputs.itemById("extra_length").value

            # First setting to False. If everything OK, setting to True at end
            args.areInputsValid = False

            if length < 0.48:
                self.logger.info("Input invalid because length is too small .")
            elif top_radius < 0:
                self.logger.info("Input invalid because top radius is negative.")
            elif top_radius >= length:
                self.logger.info("Input invalid because top radius is too big.")
            elif bottom_radius < 0:
                self.logger.info("Input invalid because bottom radius is negative.")
            elif bottom_radius >= length:
                self.logger.info("Input invalid because bottom radius is too big.")
            elif strain < 0:
                self.logger.info("Input invalid because strain is negative.")
            elif thickness <= 0:
                self.logger.info("Input invalid because thickness is too small.")
            elif width <= 0:
                self.logger.info("Input invalid because width distance is "
                                 "too small.")
            elif nose_angle < 20:
                self.logger.info("Input invalid because nose angle is too small.")
            elif extra_length < 0:
                self.logger.info("Input invalid because extra length negative.")
            else:
                args.areInputsValid = True
                self.logger.debug("Inputs are acceptable.")
        except:
            ui.messageBox(traceback.format_exc())


class MyCommandExecutePreviewHandler(adsk.core.CommandEventHandler):
    """
    Triggered when user makes any change to a parameter that is related to
    performing the feature operations.
    """
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(type(self).__name__)

    def notify(self, args):
        self.logger.debug("Preview triggered.")
        build_preview(args, preview=True)


class MyCommandExecuteHandler(adsk.core.CommandEventHandler):
    """
    Triggered when user clicks OK in command interface.
    """
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(type(self).__name__)

    def notify(self, args):
        self.logger.info("Ok-button clicked.")
        self.logger.debug("OK button triggered.")
        try:
            design = adsk.fusion.Design.cast(app.activeProduct)
            if design:
                build_execute(args, preview=False)
        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


class CantileverCommand(apper.Fusion360CommandBase):

    GEOMETRY_PARAMETERS = [
        {"id": "top_radius", "display_text": "Top Radius", "units": "mm"},
        {"id": "nose_angle", "display_text": "Nose angle", "units": ""},
        {"id": "bottom_radius", "display_text": "Bottom Radius", "units": "mm"},
        {"id": "thickness", "display_text": "Thickness", "units": "mm"},
        {"id": "length", "display_text": "Length", "units": "mm"},
        {"id": "width", "display_text": "Width",
         "units": "mm"},
        {"id": "strain", "display_text": "Strain", "units": ""},
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
                "top_radius": 0.15,
                "bottom_radius": 0.1,
                "thickness": 0.3,
                "length": 1.2,
                "width": 0.6,
                "strain": 0.02,
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

    def __init__(self, name: str, options: dict):
        super().__init__(name, options)

        # Store logs and profile config in appropriate config folder.
        # Varies depending on operating system. See appdirs module.
        appname = "Snap Generator - Fusion 360 addin"
        version = "0.2.0"
        logs_folder = Path(
            appdirs.user_log_dir(appname=appname, version=version))
        config_folder = Path(
            appdirs.user_config_dir(appname=appname, version=version))

        if not logs_folder.exists():
            logs_folder.mkdir(parents=True)
        self.log_path = logs_folder / "CantileverCommand.log"

        self.profiles_path = config_folder / "Profile Data" / "CantileverCommand.json"
        ui.messageBox(str(self.profiles_path))
        if not self.profiles_path.parent.exists():
            self.profiles_path.parent.mkdir(parents=True)

        # Loading references relative to this projects root
        self.root_dir = self.fusion_app.root_path
        self.resources_path = self.root_dir / "commands" / "resources" / \
                              "CantileverCommand"
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
        root_logger = logging.getLogger()
        root_logger.propagate = True
        # Remove any loggers that aren't cleaned up.
        for handler in root_logger.handlers:
            handler.close()
            root_logger.removeHandler(handler)

        # Adding logging to the defined LOG_Path
        fh = logging.handlers.RotatingFileHandler(self.log_path, mode="a",
                                                  maxBytes=20000)
        self.file_handler = fh
        fh.setLevel(logging.DEBUG)

        format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s:'
                                   ' %(message)s',
                                   datefmt='%H:%M:%S')
        fh.setFormatter(format)
        fh.mode = "w"
        root_logger.addHandler(fh)

        # Creating a specific logger for this class
        self.logger = logging.getLogger(type(self).__name__)

        # Connect to the command object
        self.command = command

        # Add a tooclip image to the command
        self.command_definition.toolClipFilename = str(self.tool_clip_file_path)
        # Makes it so the command is not automatically executed when another
        # command gets activated.
        self.command.isExecutedWhenPreEmpted = False
        self.profile_data: dict

        # # Create JSON file if necessary
        # if not self.profiles_path.is_file():
        #     self.logger.info("No json file was found. Created a new,"
        #                      " default file.")
        #     with open(self.profiles_path, "w") as f:
        #         json.dump(self.FALLBACK_JSON, f, indent=2)

        # Checking and fixing profile_data json
        # Also adding parent path if it somehow is missing
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

        # Load and validate JSON data
        with open(self.profiles_path, "r") as f:
            data = json.load(f)

        try:
            validate_json(data, self.GEOMETRY_PARAMETERS, self.GAP_PARAMETERS)
        except ProfileException as e:
            self.logger.error(str(e))
            error_message = "Error in config file that stores profiles" \
                            f" and gap profiles: {str(e)}." \
                            "\nEither repair, or delete it. If you delete it," \
                            " a new one will be generated with default contents." \
                            "It's path is\n" \
                            fr"{self.profiles_path}"
            ui.messageBox(error_message)

        self.profile_data = data
        self.createGUI()
        self.logger.debug("Finished GUI.")

        self.add_handlers()
        self.logger.debug("Finished handlers.")

        self.logger.info("Opened command window.")

        # Reset previous parameters to avoid non-generation of cantilever
        # when opening commmand window
        global previous_parameters
        global previous_selections
        global first_execute_started
        global second_execute_started
        previous_parameters = None
        previous_selections = None
        first_execute_started = False
        second_execute_started = False

        first_preview = True

    def on_destroy(self, command: adsk.core.Command, inputs: adsk.core.CommandInputs,
                   reason: adsk.core.CommandTerminationReason, input_values: dict):

        self.logger.debug("onDestroy triggered.")
        self.logger.info("# Command Window closed.")
        # Removing and closing all handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            handler.close()
            root_logger.removeHandler(handler)

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

        # Geometry section
        geometry_group = feature_tab.addGroupCommandInput("geometry",
                                                          "Geometry")
        geo_list = geometry_group.children

        # Select profile:
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

        profile = self.profile_data["profiles"][default_profile_name]
        # tooltip_path = self.RESOURCE_FOLDER / "dimension illustration.png"
        # joint_choice.toolClipFilename = str(x_tooltip_path)
        for geo_par in self.GEOMETRY_PARAMETERS:
            geo_id = geo_par["id"]
            display_text = geo_par["display_text"]
            unit = geo_par["units"]
            value = value_input(profile[geo_id])
            input = geo_list.addValueInput(geo_id, display_text, unit, value)
            # input.tooltip = "hey"
            # input.toolClipFilename = str(tooltip_path)

        # Gap section
        gap_group = feature_tab.addGroupCommandInput("gaps", "Gaps")
        default_gap_profile_name = self.profile_data['default_gap_profile']
        gap_profile = self.profile_data["gap_profiles"][
            default_gap_profile_name]

        gap_list = gap_group.children
        gap_profiles = gap_list.addDropDownCommandInput("gap_profiles",
                        "Profile", DropDownStyles.LabeledIconDropDownStyle)

        gap_profiles.maxVisibleItems = 10
        items = gap_profiles.listItems
        for key in self.profile_data['gap_profiles']:
            if key == default_gap_profile_name:
                items.add(key, True, str(blank_icon_path))
            else:
                items.add(key, False, str(blank_icon_path))

        for gap_par in self.GAP_PARAMETERS:
            geo_id = gap_par["id"]
            display_text = gap_par["display_text"]
            unit = gap_par["units"]
            value = value_input(gap_profile[geo_id])
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

        try:
            join_body_input = selections.addSelectionInput("join_body",
                                                          'Body to join',
                                                          'Body to join')
            join_body_input.setSelectionLimits(0, 1)
            join_body_input.addSelectionFilter(SelectionCommandInput.Bodies)
            join_body_input.tooltip = "Select the single body you want the " \
                                     "cantilever body to join."

        except:
            ui.messageBox(traceback.format_exc())
        cut_body_input = selections.addSelectionInput("cut_bodies",
                                                      'Bodies to cut',
                                                      'Bodies to cut')
        cut_body_input.addSelectionFilter(SelectionCommandInput.Bodies)
        cut_body_input.setSelectionLimits(0)
        cut_body_input.tooltip = "Select the bodies that you want the beam to" \
                                 " connect. A mating hole will be created for" \
                                 " the pin."

        #
        # nonsense1 = selections.addSelectionInput("nonsense1",
        #                                               'Nonsense1',
        #                                               'Nonsense1')
        # nonsense1.addSelectionFilter(SelectionCommandInput.Bodies)
        # nonsense1.setSelectionLimits(0)
        # nonsense1.tooltip = "Select the bodies that you want the pin to" \
        #                          " connect. A mating hole will be created for" \
        #                          " the pin."

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

        y_items.add("top", True, str(y_top_folder_path))
        y_items.add("middle", False, str(y_middle_folder_path))
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

        profile_switcher = ProfileSwitcher(self.profile_data)
        cmd.inputChanged.add(profile_switcher)
        handlers.append(profile_switcher)

        # profile_modifier = ProfileModifier(self.profile_data, self.resources_path)
        # cmd.inputChanged.add(profile_modifier)
        # handlers.append(profile_modifier)
        #
        # j_updater = JsonUpdater(self.profile_data, self.profiles_path)
        # cmd.inputChanged.add(j_updater)
        # handlers.append(j_updater)
        #
        # input_limiter = InputLimiter()
        # cmd.validateInputs.add(input_limiter)
        # handlers.append(input_limiter)

