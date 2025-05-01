"""
Classes and predefined object instances for streamlining GUI inputs.

There is a need for having predefined objects because these same objects are
used across different geometry classes. Input objects are typycally referred to
by string id's, and the different geometry classes expect the same names.
Because of that, it would be a good idea to define these names only once.
"""

import json
import traceback
import logging
from pathlib import Path

from adsk.core import CommandInputs
import adsk.core

PROJECT_DIRECTORY = Path(__file__).parent.parent.parent
COMMON_RESOURCES_FOLDER = PROJECT_DIRECTORY / "commands" / "resources" / "common"

app = adsk.core.Application.get()
ui = app.userInterface

class ValueCommandSynchronizer(adsk.core.InputChangedEventHandler):
    """
    This class links two interface fields so that when a value is set/changed
    in one of them, the value in the other one becomes identical. It is
    essentially trying to make two fields with different id's behave like one
    and the same.
    """
    def __init__(self, linked_input_ids=None):
        super().__init__()
        self.logger = logging.getLogger(type(self).__name__)
        if linked_input_ids is None:
            self.linked_inputs = []
        else:
            self.linked_inputs = linked_input_ids

    def notify(self, args):
        input = args.input
        all_inputs = args.inputs.command.commandInputs

        for id_1, id_2 in self.linked_inputs:
            self.logger.debug(f"Trying to match {input.id} with {id_1}")
            if input.id == id_1:
                self.logger.debug(f"Matched {id_1}, copying to {id_2}")
                all_inputs.itemById(id_2).value = input.value
                return

            self.logger.debug(f"Trying to match {input.id} with {id_2}")
            if input.id == id_2:
                self.logger.debug(f"Matched {id_2}, copying to {id_1}")
                all_inputs.itemById(id_1).value = input.value
                return

    def link(self, id_1, id_2):
        self.linked_input_ids.append((id_1, id_2))


class ProfileModifier(adsk.core.InputChangedEventHandler):
    """
    This class listens to changes made in the profile tab of the command
    interface, and performs the appropriate changes to the profile_data
    dictionary. No IO.
    """
    def __init__(self, profile_data, resource_folder):
        super().__init__()
        self.profile_data = profile_data
        self.logger = logging.getLogger(type(self).__name__)
        self.resource_folder = resource_folder

    def notify(self, args):
        """
        :param args: This is an 'InputChangedEventArgs' object.
        :return:
        """
        app = adsk.core.Application.get()
        design = adsk.fusion.Design.cast(app.activeProduct)
        ui = app.userInterface
        try:
            input = args.input
            all_inputs = args.inputs.command.commandInputs
            # If a joint origin was selected:
            if input.id == "selected_origin":
                pass

            # A a profile was selected, change to that profile.
            if input.id == "profile_list":
                try:
                    profile_id = input.selectedItem.name
                    profile = self.profile_data["profiles"][profile_id]
                except AttributeError:
                    # This happens when selected item is None
                    return
                try:
                    for key, value in profile.items():
                        value_in_float = float(value)
                        all_inputs.itemById(key).value = value_in_float
                except AttributeError as e:
                    self.logger.error(f"Error on key:{key}")

            # If save_profile was clicked
            elif input.id == "create_new_profile":
                """The user writes the new profile name in a textbox.
                If the name already exists, give an error message."""
                new_name_field = all_inputs.itemById("new_profile_name")
                new_name = new_name_field.value

                error = all_inputs.itemById("profile_exists_error")

                # TODO: String validation on new_name

                if new_name in self.profile_data["profiles"]:
                    # Display error message that profile already exists
                    error.isVisible = True
                else:
                    # Gets the first profile to extract the field_values
                    name = list(self.profile_data['profiles'])[0]
                    value_fields = (self.profile_data['profiles'][name]).keys()

                    new_profile = {}
                    try:
                        for key in value_fields:
                            current_value = all_inputs.itemById(key).value
                            new_profile[key] = round(current_value, 3)
                            self.profile_data["profiles"][
                                new_name] = new_profile
                            error.isVisible = False
                            self.reload_profile_lists(all_inputs)
                    except AttributeError as e:
                        logger = logging.getLogger(str(type(self)))
                        logger.error(f"AttributeError on key {key}")

                # Empty the new name field
                new_name_field.value = ""

                # TODO: Add a confirmation text for "new profile created"

                # TODO: Implement real-time update of list sections

            # If overwrite profile was clicked
            elif input.id == "overwrite_profile":
                """Save the current geometric data as the current profile name.
                Things to be saved:
                height, Top radius, bottom radius, height, length, strain
                extrusion distance"""

                profile_dropdown = all_inputs.itemById("profiles2")

                prof_name = profile_dropdown.selectedItem
                prof_to_overwrite = self.profile_data['profiles'][prof_name.name]
                for key in prof_to_overwrite.keys():
                    new_value = all_inputs.itemById(key).value
                    prof_to_overwrite[key] = round(new_value, 3)

            # If change default profile was clicked
            elif input.id == "make_profile_default":
                name = all_inputs.itemById("profiles2").selectedItem.name
                self.profile_data["default_profile"] = name

            # If delete profile was clicked
            elif input.id == "delete_profile":
                # Step 1: Remove it from profile_data
                name = all_inputs.itemById("profiles2").selectedItem.name
                all_inputs.itemById("profiles2").selectedItem.deleteMe()
                # It cannot be the default profile, if so, create error message.
                if self.profile_data["default_profile"] == name:
                    self.logger.info("Tried to delete default profile."
                                     " Not allowed.")
                    return
                del (self.profile_data["profiles"][name])

                self.reload_profile_lists(all_inputs)

            # If save new gap profile was clicked
            elif input.id == "create_new_gap_profile":
                """The user writes the new profile name in a textbox.
                            If the name already exists, give an error message."""
                new_name_field = all_inputs.itemById("new_gap_profile_name")
                new_name = new_name_field.value
                error = all_inputs.itemById("gap_profile_exists_error")

                # TODO: String validation on new_name

                if new_name in self.profile_data["gap_profiles"]:
                    # Display error message that profile already exists
                    error.isVisible = True
                else:
                    # Getting the value fields from the randomly first
                    # gap profile stored.
                    name = list(self.profile_data['gap_profiles'])[0]
                    value_fields = (
                    self.profile_data['gap_profiles'][name]).keys()
                    new_gap_profile = {}

                    for key in value_fields:
                        try:
                            current_value = all_inputs.itemById(key).value
                            new_gap_profile[key] = round(current_value, 3)
                        except AttributeError:
                            self.logger.error(f"Error on key {key}")
                    self.profile_data["gap_profiles"][
                        new_name] = new_gap_profile
                    error.isVisible = False
                    new_name_field.value = ""
                    self.reload_gap_profile_lists(all_inputs)

            # If overwrite gap profile was clicked
            elif input.id == "overwrite_gap_profile":
                """Save the current geometric data as the current profile name.
                Things to be saved:
                height, Top radius, bottom radius, height, length, strain
                extrusion distance"""

                self.logger.debug("Overwrite gap triggered.")

                profile_dropdown = all_inputs.itemById("gap_profiles2")
                prof_name = profile_dropdown.selectedItem.name
                prof_to_overwrite = self.profile_data['gap_profiles'][
                    prof_name]
                for key in prof_to_overwrite.keys():
                    new_value = all_inputs.itemById(key).value
                    prof_to_overwrite[key] = round(new_value, 3)
                # ui.messageBox(f"Gap profile has been changed.")

            # If change gap profile was clicked
            elif input.id == "make_gap_profile_default":
                name = all_inputs.itemById("gap_profiles2").selectedItem.name
                self.profile_data["default_gap_profile"] = name


            # If delete gap profile was clicked
            elif input.id == "delete_gap_profile":
                name = all_inputs.itemById("gap_profiles2").selectedItem.name

                if self.profile_data["default_gap_profile"] == name:
                    self.profile_data["default_gap_profile"] = None

                del (self.profile_data["gap_profiles"][name])
                self.reload_gap_profile_lists(all_inputs)

            # TODO: Make profile and gap profile list empty when custom values
            #       are entered.
        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

    def reload_profile_lists(self, all_inputs):
        # Clear lists and add the items again without making any of
        # them selected!
        profile_list1 = all_inputs.itemById("profile_list")
        item_list1 = profile_list1.listItems
        item_list1.clear()
        profile_list2 = all_inputs.itemById("profiles2")
        item_list2 = profile_list2.listItems
        item_list2.clear()

        profile_names = self.profile_data["profiles"]
        blank_icon_path = self.resource_folder / "white"
        for prof_name in profile_names.keys():
            item_list1.add(prof_name, True, str(blank_icon_path))
            item_list2.add(prof_name, True, str(blank_icon_path))

    def reload_gap_profile_lists(self, all_inputs):
        # Clear lists and add the items again without making any of
        # them selected!
        gap_profile_list1 = all_inputs.itemById("gap_profiles")
        item_list1 = gap_profile_list1.listItems
        item_list1.clear()
        gap_profile_list2 = all_inputs.itemById("gap_profiles2")
        item_list2 = gap_profile_list2.listItems
        item_list2.clear()

        gap_profile_names = self.profile_data["gap_profiles"]
        blank_icon_path = self.resource_folder / "white"
        for prof_name in gap_profile_names.keys():
            item_list1.add(prof_name, True, str(blank_icon_path))
            item_list2.add(prof_name, True, str(blank_icon_path))


class ProfileSwitcher(adsk.core.InputChangedEventHandler):
    """
    This class listens to when the user selects a new profile or gap profile
    in the Feature tab, and replaces the values currently in the relevant
    interface fields with the values from the now selected profile or gap
    profile. Note that the user can't reselect the currently active profile,
    because that doesn't trigger an InputChangedEvent.
    """
    def __init__(self, profile_data):
        super().__init__()
        self.profile_data = profile_data

    def notify(self, args):
        """
        :param args: This is an 'InputChangedEventArgs' object.
        :return:
        """
        try:
            input = args.input  # The input obj that created event
            all_inputs = args.inputs.command.commandInputs

            # If a profile or gap profile was selected, fill the values from
            # that profile into the corresponding fields.
            if input.id == "profile_list":
                try:
                    profile_id = input.selectedItem.name
                    profile = self.profile_data["profiles"][profile_id]
                    for key, value in profile.items():
                        value_in_float = float(value)
                        all_inputs.itemById(key).value = value_in_float
                except AttributeError:
                    # This happens when selected item is None,
                    # so, then there is no values to change to.
                    return
            # A gap profile was selected, change to that profile.
            elif input.id == "gap_profiles":
                try:
                    profile_id = input.selectedItem.name
                    profile = self.profile_data["gap_profiles"][profile_id]
                except AttributeError:
                    # Happens when the selected item is None
                    return
                for key, value in profile.items():
                    value_in_float = float(value)
                    all_inputs.itemById(key).value = value_in_float

        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


class JsonUpdater(adsk.core.InputChangedEventHandler):
    """
    This class overwrites the existing JSON configuration file that stores
    profiles and gap profiles when any of the defined events occur.
    """

    def __init__(self, profile_data, json_filepath):
        super().__init__()
        self.profile_data = profile_data
        self.json_filepath = json_filepath

    def notify(self, args):
        save_triggers = ["create_new_profile", "overwrite_profile",
                         "make_profile_default", "delete_profile",
                         "create_new_gap_profile", "overwrite_gap_profile",
                         "make_gap_profile_default", "delete_gap_profile"]
        input = args.input
        try:
            if input.id in save_triggers:
                with open(self.json_filepath, "w") as f:
                    json.dump(self.profile_data, f, indent=2)
        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


class ProfileSettings:
    """
    This class creates the interface elements for creating new
    profiles and modifying, overwriting, making default and deleting existing
    ones. It includes an initially invisible error message text field that can
    be made visible as a way to display errors.
    """
    def __init__(self, profile_data):
        self.profile_data = profile_data

    def add_to_inputs(self, inputs: CommandInputs):
        """Adds a standard tab for doing profile-manipulation."""
        """GEOMETRY PROFILE TAB"""
        group1 = inputs.addGroupCommandInput("create_prof_group",
                                             "Create new profile").children

        # Error message field
        error_message = """Error: A profile by that name already exists. Did 
        you mean to overwrite? """
        error = group1.addTextBoxCommandInput('profile_exists_error', '',
                                              error_message,
                                              3, True)
        error.isVisible = False

        group1.addStringValueInput("new_profile_name", "New name")

        group1.addBoolValueInput("create_new_profile", "Create new", False)

        group2 = inputs.addGroupCommandInput("overwrite_prof_group",
                                             "Edit existing profile").children
        list_style = adsk.core.DropDownStyles.LabeledIconDropDownStyle
        profile_list = group2.addDropDownCommandInput('profiles2',
                                                      "Select profile:",
                                                      list_style)
        items = profile_list.listItems
        default_profile_name = self.profile_data["default_profile"]
        blank_icon_path = COMMON_RESOURCES_FOLDER / "white"
        for key in self.profile_data['profiles']:
            if key == default_profile_name:
                items.add(key, True, str(blank_icon_path))
            else:
                items.add(key, False, str(blank_icon_path))

        group2.addBoolValueInput("overwrite_profile", "Overwrite", False)
        group2.addBoolValueInput("make_profile_default", "Make default", False)
        group2.addBoolValueInput("delete_profile", "Delete", False)


class GapProfileSettings:
    """
    This class creates the interface elements for creating new gap
    profiles and modifying, overwriting, making default and deleting existing
    ones. It includes an initially invisible error message text field that can
    be made visible as a way to display errors.
    """
    def __init__(self, profile_data):
        self.profile_data = profile_data

    def add_to_inputs(self, inputs: CommandInputs):
        """Adds a standard tab for doing gap-profile-manipulation."""
        group1 = inputs.addGroupCommandInput("create_gap_group",
                                             "Create new gap profile").children
        # Error message field
        error_message = 'Error: A gap profile by that name already exists. ' \
                        'Did you mean to overwrite? '
        error = group1.addTextBoxCommandInput('gap_profile_exists_error', '',
                                              error_message, 3, True)
        error.isVisible = False

        group1.addStringValueInput("new_gap_profile_name",
                                   "New name")

        group1.addBoolValueInput("create_new_gap_profile", "Create new", False)
        group2 = inputs.addGroupCommandInput("overwrite_gap_group",
                                             "Edit existing gap profile.").children
        list_style = adsk.core.DropDownStyles.LabeledIconDropDownStyle
        gap_profile_list = group2.addDropDownCommandInput('gap_profiles2',
                                                          "Select gap profile:",
                                                          list_style)
        gap_profile_list.maxVisibleItems = 8
        items = gap_profile_list.listItems
        default_gap_profile_name = self.profile_data["default_gap_profile"]
        blank_icon_path = COMMON_RESOURCES_FOLDER / "white"
        for key in self.profile_data['gap_profiles']:
            if key == default_gap_profile_name:
                items.add(key, True, str(blank_icon_path))
            else:
                items.add(key, False, str(blank_icon_path))

        group2.addBoolValueInput("overwrite_gap_profile", "Overwrite", False)
        group2.addBoolValueInput("make_gap_profile_default", "Make default",
                                 False)
        group2.addBoolValueInput("delete_gap_profile", "Delete", False)


class ProfileException(Exception):
    """
    This Exception is to be used when a user tries to do operations on
    profiles that don't exist in profile_data.
    """
    pass


def value_input(value):
    """
    Converts values into the format that Fusion expects for displaying values in
    interface fields and performing feature operations.
    """
    valueInput = adsk.core.ValueInput
    if isinstance(value, str):
        value_obj = valueInput.createByString(value)
    elif isinstance(value, (int, float)):
        value_obj = valueInput.createByReal(value)
    else:
        raise TypeError("Argument type should be either string or number, "
                        f"not {type(value)}.")
    return value_obj


def validate_json(profile_data: dict, geometry_parameters: list,
                  gap_parameters: list):
    """
    Looks for errors in imported json data and raises a ProfileException
    if something is wrong, and tries to provide some helpful feedback to
    pinpoint what where in the json file the error lies.
    :param gap_parameters:
    :param profile_data:
    :return:
    """
    top_keys = list(profile_data.keys())
    geometry_ids = [parameter["id"] for parameter in geometry_parameters]
    gap_ids = [parameter["id"] for parameter in gap_parameters]

    correct_keys = ["default_profile", "default_gap_profile",
                    "profiles", "gap_profiles"]

    if top_keys != correct_keys:
        raise ProfileException(f"Error in top level JSON hierarchy of profile"
                               f" data.{top_keys} not equal to {correct_keys}")

    def_prof_name = profile_data.get("default_profile")
    if def_prof_name is None:
        raise ProfileException("No 'default_profile' key defined in profile data.")

    profiles = profile_data.get("profiles")
    if profiles is None:
        raise ProfileException("No 'profiles' key defined in profile data.")

    default_profile = profiles.get(def_prof_name)
    if default_profile is None:
        raise ProfileException(
            f"Default profile '{def_prof_name}' not found in profiles."
        )

    def_gap_prof_name = profile_data.get("default_gap_profile")
    if def_gap_prof_name is None:
        raise ProfileException("No 'default_gap_profile' key defined in profile data.")

    gap_profiles = profile_data.get("gap_profiles")
    if gap_profiles is None:
        raise ProfileException("No 'gap_profiles' key defined in profile data.")

    default_profile = gap_profiles.get(def_gap_prof_name)
    if default_profile is None:
        raise ProfileException(
            f"Default gap profile '{def_gap_prof_name}' not found in 'gap_profiles'."
        )

    allowed_types = (int, float)
    for prof_name, profile in profile_data["profiles"].items():
        if len(profile) != len(geometry_ids):
            raise ProfileException(f"Profile '{prof_name}'."
                                   f" has a wrong number of parameters.")
        for key, value in profile.items():
            if type(value) not in allowed_types:
                raise ProfileException(f"In profile '{prof_name}'."
                                       f" The parameter '{key}' has a wrong"
                                       f" type. It should be among '{allowed_types}'"
                                       f" but is instead of type '{type(value)}'")

    for gap_prof_name, gap_profile in profile_data["gap_profiles"].items():
        if len(gap_profile) != len(gap_ids):
            raise ProfileException(f"Error in gap profile {gap_prof_name}."
                                   f" wrong number of parameters.")
        for key, value in gap_profile.items():
            if type(value) not in allowed_types:
                raise ProfileException(f"In profile '{gap_prof_name}'."
                                       f" The parameter '{key}' has a wrong"
                                       f" type. It should be among '{allowed_types}'"
                                       f" but is instead of type '{type(value)}'")
    return True
