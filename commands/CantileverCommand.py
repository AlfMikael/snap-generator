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

from test_lib import get_cantilever

app = adsk.core.Application.get()
ui = app.userInterface
handlers = []

execute_triggered = False
previous_parameters = None


def build_old(args, preview=False):
    try:
        logger = logging.getLogger("build-function")
        logger.debug("Build initiated.")
        design = adsk.fusion.Design.cast(app.activeProduct)
        rootComp = design.rootComponent
        inputs = args.command.commandInputs

        # Build parameters
        parameter_ids = list(Cantilever.get_parameter_dict().keys())
        pos_parameters = ["x_location", "y_location"]
        parameters = {}

        # Extracting the value parameters from all parameters
        value_parameters = list(set(parameter_ids) - set(pos_parameters))
        try:
            for par_id in value_parameters:
                par_value = inputs.itemById(par_id).value
                parameters[par_id] = par_value
            for par_id in pos_parameters:
                position = inputs.itemById(par_id).selectedItem.name
                parameters[par_id] = position
        except:
            logger.error(f"Something went wrong with creating"
                          f" parameter {par_id}")
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

        joint_origin = None
        joint_input = inputs.itemById("selected_origin")
        if joint_input.selectionCount == 1:
            joint_origin = joint_input.selection(0).entity

        join_body = None
        join_body_input = inputs.itemById("join_body")
        if join_body_input.selectionCount == 1:
            join_body = join_body_input.selection(0).entity

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

        cant = Cantilever(rootComp, parameters,
                   target_joint_org=joint_origin,
                   join_body=join_body,
                   cut_bodies=cut_bodies)

        # Remove the component if a join-body operation was performed
        if join_body:
            rootComp.features.removeFeatures.add(cant.occurrence)

        timeline_end = design.timeline.markerPosition
        timeline_group = design.timeline.timelineGroups.add(timeline_start,
                                                            timeline_end-1)
        timeline_group.name = "Cantilever"

        logger.info(f"Build succeeded.")

    except:
        if ui:
            logger.error(f"BUILD FAILED!, traceback" + traceback.format_exc())
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def build(args, preview=False):
    try:
        logger = logging.getLogger("build-function")
        logger.debug("Build initiated.")
        
        
        design = adsk.fusion.Design.cast(app.activeProduct)
        rootComp = design.rootComponent
        inputs = args.command.commandInputs
        
        params_that_are_ok = ["strain", "nose_angle"]
        
        parameter_ids = {
            "inner_radius": (float, int),
            "strain": (float, int),
            "extrusion_distance": (float, int),
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
            "y_location": (str,)
        }
        
        pos_parameters = ["x_location", "y_location"]
        parameters = {}
        
        # Extracting the value parameters from all parameters
        value_parameters = list(set(parameter_ids) - set(pos_parameters))
        
        loop_keys = list(value_parameters)
        try:
            for par_id in loop_keys:
                #ui.messageBox("par_id: " + str(par_id))
                #output_string = f"""Number of inputs: {inputs.count} \n
                #                """ 
                
                output_string = f"""Trying to retrieve input with the id: {par_id} \n
                                """                 
                #ui.messageBox(output_string)
                                
                
                item = inputs.itemById(par_id)
                if item is None:
                    continue
                
                if par_id not in params_that_are_ok:
                    parameters[par_id] = item.value*10
                else:
                    parameters[par_id] = item.value
                
                
            #for par_id in pos_parameters:
            #    position = inputs.itemById(par_id).selectedItem.name
            #    parameters[par_id] = position
            
            #ui.messageBox("Parameters were loaded:" + str(parameters))

        except:
                    logger.error(f"Something went wrong with creating"
                          f" parameter {par_id}")
                    ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
        
        parameters["preview"] = preview
        global previous_parameters
        
        if not preview: # Delete the 'preview cantilever'
            get_cantilever(parameters)
            # pos = design.timeline.markerPosition
            # cantilever = design.timeline.item(pos-1)
            global execute_triggered
            
            execute_triggered = True
            ui.messageBox(str(parameters))
        else:
            if preview:
                if previous_parameters != parameters:
                    get_cantilever(parameters)
                    ui.messageBox("parameters were the same!\n" + str(parameters))
        
        
        previous_parameters = parameters.copy()
        
        
        
    except:
        if ui:
            logger.error(f"BUILD FAILED!, traceback" + traceback.format_exc())
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


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
            extrusion_distance = all_inputs.itemById("extrusion_distance").value
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
            elif extrusion_distance <= 0:
                self.logger.info("Input invalid because extrusion distance is "
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


class CantileverCommand(apper.Fusion360CommandBase):

    GEOMETRY_PARAMETERS = [
        {"id": "top_radius", "display_text": "Top Radius", "units": "mm"},
        {"id": "nose_angle", "display_text": "Nose angle", "units": ""},
        {"id": "bottom_radius", "display_text": "Bottom Radius", "units": "mm"},
        {"id": "thickness", "display_text": "Thickness", "units": "mm"},
        {"id": "length", "display_text": "Length", "units": "mm"},
        {"id": "extrusion_distance", "display_text": "Extrusion distance",
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
                "extrusion_distance": 0.6,
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
        
        global execute_triggered
        execute_triggered = False
        

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
            join_body_input.setSelectionLimits(0,1)
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

        profile_modifier = ProfileModifier(self.profile_data, self.resources_path)
        cmd.inputChanged.add(profile_modifier)
        handlers.append(profile_modifier)

        j_updater = JsonUpdater(self.profile_data, self.profiles_path)
        cmd.inputChanged.add(j_updater)
        handlers.append(j_updater)

        input_limiter = InputLimiter()
        cmd.validateInputs.add(input_limiter)
        handlers.append(input_limiter)

