"""Classes for generating snap geometries."""

import adsk.core
import adsk.fusion
import adsk.cam
import math
import logging
from adsk.core import ValueInput as valueInput
from adsk.fusion import Component


app = adsk.core.Application.get()
ui = app.userInterface

class BaseSnap:
    component_name = "snap_mechanism"
    gap_in_cut_body = True

    def __init__(self, parent_comp: Component, parameters: dict,
                 target_joint_org=None, join_body=None, cut_bodies=tuple()):
        """
        A new component is created which contains a body with a bendable shape.
        Additional operations are done depending on arguments.
        :param parent_comp: The component into which this component is created.
        :param parameters: The properties that define the geometric shape, along
            with the reference position for placement.
        :param join_body: A reference to a single BRepBody that the new body is
            to be combined with.
        :param cut_bodies: A list of bodies on which a cut operation will be
            performed to create a opening for the bendable shape.
        """

        """
        Step 1: Create new component
        """

        # Test parameters to make sure they are valid
        try:
            self.test_parameters(parameters)
        except ParameterException as e:
            logging.getLogger(str(type(self)) + str(e))
        # Create a new occurrence and reference its component
        matrix = adsk.core.Matrix3D.create()
        self.occurrence = parent_comp.occurrences.addNewComponent(matrix)
        self.comp = self.occurrence.component
        self.comp.name = self.component_name
        self.cut_bodies = cut_bodies

        """
        Step 2: Create joint between selected joint origin and component. 
        """
        offsets = self._get_offsets(parameters)
        joint_origin = self._create_joint_origin(*offsets)
        if target_joint_org:
            self.place(joint_origin, target_joint_org)

        """
        Step 3: Draw sketch profiles and then extrude them into bodies. Then
        perform join and/or cut.
        """
        sketch_plane = self.comp.xZConstructionPlane
        cant_sketch = self.comp.sketches.add(sketch_plane)
        cant_sketch_data = self._sketch_join_properties(parameters)
        self._draw_sketch(cant_sketch, cant_sketch_data)
        cant_body = self._create_join_body(parameters, cant_sketch)

        if join_body:
            self._perform_join(join_body, cant_body)

        if cut_bodies:
            sub_sketch_data = self._sketch_cut_properties(parameters)
            sub_sketch = self.comp.sketches.add(sketch_plane)
            self._draw_sketch(sub_sketch, sub_sketch_data)
            subtraction_body = self._create_cut_body(parameters, sub_sketch)
            self._perform_cut(cut_bodies, subtraction_body)
            # Remove the subtraction body
            self.comp.features.removeFeatures.add(subtraction_body)

    def test_parameters(self, parameters):
        """
        This function is intended to catch errors in parameters early.
        :param parameters:
        :return:
        """
        # Defining the needed parameters and their allowed types

        PARAMETERS = self.get_parameter_dict()

        # Length has to be the same
        if len(parameters) != len(PARAMETERS):
            raise ParameterException("Number of parameters is wrong.")

        # The keys are the same
        for key in PARAMETERS:
            if key not in parameters:
                raise ParameterException(f"Parameter name {key} is missing.")

        # The types are correct
        for key, value in parameters.items():
            allowed_types = PARAMETERS[key]
            if type(value) not in allowed_types:
                raise ParameterException(
                    f"The type of {key} is not in the list of"
                    f"allowed types. type={type(value)}.")

    def _draw_sketch(self, sketch, sketch_data):
        points_coordinates = sketch_data['points_coordinates']
        point_pair_indexes = sketch_data['point_pair_indexes']
        arc_lines = sketch_data['arc_lines']

        sketch_points = []
        # Create sketch points
        for x, y in points_coordinates:
            sketch_points.append(
                sketch.sketchPoints.add(adsk.core.Point3D.create(x, y, 0)))

        # Draw straight lines
        for p0, p1 in point_pair_indexes:
            start_point = sketch_points[p0]
            end_point = sketch_points[p1]
            sketch.sketchCurves.sketchLines.addByTwoPoints(start_point,
                                                           end_point)

        # Draw arcs if any. This somehow doesn't need an "if sweep_angle > 0"
        for arc_data in arc_lines:
            origin_point = sketch_points[arc_data[0]]
            start_point = sketch_points[arc_data[1]]
            sweep_angle = arc_data[2]
            sketch.sketchCurves.sketchArcs.addByCenterStartSweep(origin_point,
                                                                 start_point,
                                                                 sweep_angle)

    def _create_cut_body(self, parameters, sketch):
        gap = parameters['gap_extrusion']
        if self.gap_in_cut_body:
            extrusion_distance = parameters['extrusion_distance'] + 2 * gap
        else:
            extrusion_distance = parameters['extrusion_distance']

        profile = sketch.profiles[0]

        extrudes = self.comp.features.extrudeFeatures
        new_body_type = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        extrudeInput = extrudes.createInput(profile, new_body_type)

        distance = adsk.core.ValueInput.createByReal(extrusion_distance)
        extrusion_extent = adsk.fusion.DistanceExtentDefinition.create(
            distance)
        extrudeInput.setOneSideExtent(extrusion_extent, 0)

        gap_value = adsk.core.ValueInput.createByReal(-1 * gap)
        start_offset = adsk.fusion.OffsetStartDefinition.create(gap_value)
        extrudeInput.startExtent = start_offset
        extrusion = extrudes.add(extrudeInput)

        # Return the newly created body.
        body = extrusion.bodies.item(0)
        return body

    def _create_join_body(self, parameters, sketch):
        extrusion_distance = parameters['extrusion_distance']
        gap = parameters['gap_extrusion']

        if self.gap_in_cut_body:
            total_distance = extrusion_distance
        else:
            total_distance = extrusion_distance - 2*gap

        profile = sketch.profiles[0]
        extrudes = self.comp.features.extrudeFeatures
        new_body_type = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        extrudeInput = extrudes.createInput(profile, new_body_type)

        distance_value = adsk.core.ValueInput.createByReal(total_distance)
        extrusion_extent = adsk.fusion.DistanceExtentDefinition.create(
            distance_value)
        extrudeInput.setOneSideExtent(extrusion_extent, 0)

        extrusion = extrudes.add(extrudeInput)

        # Return the newly created body.
        body = extrusion.bodies.item(0)

        return body

    def _create_joint_origin(self, x_offset=0, y_offset=0, z_offset=0):
        jointGeometry = adsk.fusion.JointGeometry
        jointOrigins = self.comp.jointOrigins

        # edge joint origin
        point = self.comp.originConstructionPoint
        geo = jointGeometry.createByPoint(point)
        joint_origin_input = jointOrigins.createInput(geo)
        joint_origin_input.xAxisEntity = self.comp.yConstructionAxis
        joint_origin_input.zAxisEntity = self.comp.xConstructionAxis

        joint_origin_input.offsetX = valueInput.createByReal(x_offset)
        joint_origin_input.offsetY = valueInput.createByReal(y_offset)
        joint_origin_input.offsetZ = valueInput.createByReal(z_offset)
        # joint_origin_input.angle = adsk.core.ValueInput.createByString("180 deg")
        joint_origin = jointOrigins.add(joint_origin_input)
        return joint_origin

    def _sketch_join_properties(self, geometry):
        """
        Replace in subclass.
        :param geometry:
        :return:
        """
        points_coordinates = []
        point_pair_indexes = []
        arc_lines = []
        data = {"points_coordinates": points_coordinates,
                "point_pair_indexes": point_pair_indexes,
                "arc_lines": arc_lines}
        return data

    def _sketch_cut_properties(self, geometry):
        """
        Replace in subclass.
        :param geometry:
        :return:
        """
        points_coordinates = []
        point_pair_indexes = []
        data = {"points_coordinates": points_coordinates,
                "point_pair_indexes": point_pair_indexes
                }
        return data

    # Creates a joint to given joint origin
    def place(self, joint_origin, target_joint_origin):
        parent_comp = self.occurrence.sourceComponent
        joints = parent_comp.joints
        joint_input = joints.createInput(joint_origin, target_joint_origin)
        joint_input.angle = valueInput.createByString("180 deg")
        joint = joints.add(joint_input)
        joint.isLightBulbOn = False

    def _perform_join(self, body_to_join, addition_body):
        combineFeatures = self.comp.features.combineFeatures
        tool_bodies = adsk.core.ObjectCollection.create()
        tool_bodies.add(addition_body)
        combine_input = combineFeatures.createInput(body_to_join, tool_bodies)
        result = combineFeatures.add(combine_input)
        return result

    def _perform_cut(self, bodies_to_cut, subtraction_body):
        combineFeatures = self.comp.features.combineFeatures
        CutFeatureOperation = adsk.fusion.FeatureOperations.CutFeatureOperation
        for body_to_cut in bodies_to_cut:
            tool_bodies = adsk.core.ObjectCollection.create()
            tool_bodies.add(subtraction_body)
            combine_input = combineFeatures.createInput(body_to_cut,
                                                        tool_bodies)
            combine_input.isKeepToolBodies = True
            combine_input.operation = CutFeatureOperation
            combineFeatures.add(combine_input)

    def _get_offsets(self, parameters):
        """
        Implement this function in subclasses.
        :param parameters:
        :return:
        """
        return (0, 0, 0)

    @staticmethod
    def get_parameter_dict():
        """
        Implement in subclass to define appropriate parameters.
        :return:
        """
        return dict()

    @staticmethod
    def mirror_points(pointlist, axis):
        """
        Mirrors the list of points across either the x or y axis.
        :param pointlist:
        :param axis: "x" or "y"
        :return:
        """
        newlist = []
        for pair in pointlist:
            (x, y) = pair
            if axis == "x":
                x *= -1
            elif axis == "y":
                y *= -1
            newlist.append((x, y))
        return newlist


class ExperimentalBaseSnap:
    component_name = "snap_mechanism"
    gap_in_cut_body = True

    def __init__(self, parent_comp: Component, parameters: dict,
                 target_joint_org=None, join_body=None, cut_bodies=tuple()):
        """
        A new component is created which contains a body with a bendable shape.
        Additional operations are done depending on arguments.
        :param parent_comp: The component into which this component is created.
        :param parameters: The properties that define the geometric shape, along
            with the reference position for placement.
        :param join_body: A reference to a single BRepBody that the new body is
            to be combined with.
        :param cut_bodies: A list of bodies on which a cut operation will be
            performed to create a opening for the bendable shape.
        """

        """
        Step 1: Create new component
        """
        # Test parameters to make sure they are valid
        try:
            self.test_parameters(parameters)
        except ParameterException as e:
            logging.getLogger(str(type(self)) + str(e))
        # Create a new occurrence and reference its component
        matrix = adsk.core.Matrix3D.create()
        self.occurrence = parent_comp.occurrences.addNewComponent(matrix)
        self.comp = self.occurrence.component
        self.comp.name = self.component_name
        self.cut_bodies = cut_bodies
        self.subtraction_body = None
        self.addition_body = None


        """
        Step 2: Create joint between selected joint origin and component. 
        """
        offsets = self._get_offsets(parameters)
        joint_origin = self._create_joint_origin(*offsets)
        if target_joint_org:
            self.place(joint_origin, target_joint_org)

        """
        Step 3: Draw sketch profiles and then extrude them into bodies. Then
        perform join and/or cut.
        """
        sketch_plane = self.comp.xZConstructionPlane
        cant_sketch = self.comp.sketches.add(sketch_plane)
        cant_sketch_data = self._sketch_join_properties(parameters)
        self._draw_sketch(cant_sketch, cant_sketch_data)
        cant_body = self._create_join_body(parameters, cant_sketch)

        if join_body:
            self._perform_join(join_body, cant_body)

        # Create subtraction body
        sub_sketch_data = self._sketch_cut_properties(parameters)
        sub_sketch = self.comp.sketches.add(sketch_plane)
        self._draw_sketch(sub_sketch, sub_sketch_data)
        subtraction_body = self._create_cut_body(parameters, sub_sketch)
        self.subtraction_body = subtraction_body

        if cut_bodies:
            self._perform_cut(cut_bodies, subtraction_body)
            # Remove the subtraction body
            self.comp.features.removeFeatures.add(subtraction_body)
        else:
            # If no cutting, keep subtraction body
            self.subtraction_body = subtraction_body

    def test_parameters(self, parameters):
        """
        This function is intended to catch errors in parameters early.
        :param parameters:
        :return:
        """
        # Defining the needed parameters and their allowed types

        PARAMETERS = self.get_parameter_dict()

        # Length has to be the same
        if len(parameters) != len(PARAMETERS):
            raise ParameterException("Number of parameters is wrong.")

        # The keys are the same
        for key in PARAMETERS:
            if key not in parameters:
                raise ParameterException(f"Parameter name {key} is missing.")

        # The types are correct
        for key, value in parameters.items():
            allowed_types = PARAMETERS[key]
            if type(value) not in allowed_types:
                raise ParameterException(
                    f"The type of {key} is not in the list of"
                    f"allowed types. type={type(value)}.")

    def _draw_sketch(self, sketch, sketch_data):
        points_coordinates = sketch_data['points_coordinates']
        point_pair_indexes = sketch_data['point_pair_indexes']
        arc_lines = sketch_data['arc_lines']

        sketch_points = []
        # Create sketch points
        for x, y in points_coordinates:
            sketch_points.append(
                sketch.sketchPoints.add(adsk.core.Point3D.create(x, y, 0)))

        # Draw straight lines
        for p0, p1 in point_pair_indexes:
            start_point = sketch_points[p0]
            end_point = sketch_points[p1]
            sketch.sketchCurves.sketchLines.addByTwoPoints(start_point,
                                                           end_point)

        # Draw arcs if any. This somehow doesn't need an "if sweep_angle > 0"
        for arc_data in arc_lines:
            origin_point = sketch_points[arc_data[0]]
            start_point = sketch_points[arc_data[1]]
            sweep_angle = arc_data[2]
            sketch.sketchCurves.sketchArcs.addByCenterStartSweep(origin_point,
                                                                 start_point,
                                                                 sweep_angle)

    def _create_cut_body(self, parameters, sketch):
        gap = parameters['gap_extrusion']
        if self.gap_in_cut_body:
            extrusion_distance = parameters['extrusion_distance'] + 2 * gap
        else:
            extrusion_distance = parameters['extrusion_distance']

        profile = sketch.profiles[0]

        extrudes = self.comp.features.extrudeFeatures
        new_body_type = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        extrudeInput = extrudes.createInput(profile, new_body_type)

        distance = adsk.core.ValueInput.createByReal(extrusion_distance)
        extrusion_extent = adsk.fusion.DistanceExtentDefinition.create(
            distance)
        extrudeInput.setOneSideExtent(extrusion_extent, 0)

        gap_value = adsk.core.ValueInput.createByReal(-1 * gap)
        start_offset = adsk.fusion.OffsetStartDefinition.create(gap_value)
        extrudeInput.startExtent = start_offset
        extrusion = extrudes.add(extrudeInput)

        # Return the newly created body.
        body = extrusion.bodies.item(0)

        return body

    def _create_join_body(self, parameters, sketch):
        extrusion_distance = parameters['extrusion_distance']
        gap = parameters['gap_extrusion']

        if self.gap_in_cut_body:
            total_distance = extrusion_distance
        else:
            total_distance = extrusion_distance - 2*gap

        profile = sketch.profiles[0]
        extrudes = self.comp.features.extrudeFeatures
        new_body_type = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        extrudeInput = extrudes.createInput(profile, new_body_type)

        distance_value = adsk.core.ValueInput.createByReal(total_distance)
        extrusion_extent = adsk.fusion.DistanceExtentDefinition.create(
            distance_value)
        extrudeInput.setOneSideExtent(extrusion_extent, 0)

        extrusion = extrudes.add(extrudeInput)

        # Return the newly created body.
        body = extrusion.bodies.item(0)

        return body

    def _create_joint_origin(self, x_offset=0, y_offset=0, z_offset=0):
        jointGeometry = adsk.fusion.JointGeometry
        jointOrigins = self.comp.jointOrigins

        # edge joint origin
        point = self.comp.originConstructionPoint
        geo = jointGeometry.createByPoint(point)
        joint_origin_input = jointOrigins.createInput(geo)
        joint_origin_input.xAxisEntity = self.comp.yConstructionAxis
        joint_origin_input.zAxisEntity = self.comp.xConstructionAxis

        joint_origin_input.offsetX = valueInput.createByReal(x_offset)
        joint_origin_input.offsetY = valueInput.createByReal(y_offset)
        joint_origin_input.offsetZ = valueInput.createByReal(z_offset)
        # joint_origin_input.angle = adsk.core.ValueInput.createByString("180 deg")
        joint_origin = jointOrigins.add(joint_origin_input)
        return joint_origin

    def _sketch_join_properties(self, geometry):
        """
        Replace in subclass.
        :param geometry:
        :return:
        """
        points_coordinates = []
        point_pair_indexes = []
        arc_lines = []
        data = {"points_coordinates": points_coordinates,
                "point_pair_indexes": point_pair_indexes,
                "arc_lines": arc_lines}
        return data

    def _sketch_cut_properties(self, geometry):
        """
        Replace in subclass.
        :param geometry:
        :return:
        """
        points_coordinates = []
        point_pair_indexes = []
        data = {"points_coordinates": points_coordinates,
                "point_pair_indexes": point_pair_indexes
                }
        return data

    # Creates a joint to given joint origin
    def place(self, joint_origin, target_joint_origin):
        parent_comp = self.occurrence.sourceComponent
        joints = parent_comp.joints
        joint_input = joints.createInput(joint_origin, target_joint_origin)
        joint_input.angle = valueInput.createByString("180 deg")
        joint = joints.add(joint_input)
        joint.isLightBulbOn = False

    def _perform_join(self, body_to_join, addition_body):
        combineFeatures = self.comp.features.combineFeatures
        tool_bodies = adsk.core.ObjectCollection.create()
        tool_bodies.add(addition_body)
        combine_input = combineFeatures.createInput(body_to_join, tool_bodies)
        combined_features = combineFeatures.add(combine_input)
        return combined_features

    # def _perform_join(self, bodies_to_join, addition_body):
    #     """ This is an altered version of the base function that takes multiple bodies. Probably pointless."""
    #     combineFeatures = self.comp.features.combineFeatures
    #     for body_to_join in bodies_to_join:
    #         tool_bodies = adsk.core.ObjectCollection.create()
    #         tool_bodies.add(addition_body)
    #         combine_input = combineFeatures.createInput(body_to_join, tool_bodies)
    #         combine_input.isKeepToolBodies = False
    #         combineFeatures.add(combine_input)


    def _perform_cut(self, bodies_to_cut, subtraction_body):
        combineFeatures = self.comp.features.combineFeatures
        CutFeatureOperation = adsk.fusion.FeatureOperations.CutFeatureOperation
        for body_to_cut in bodies_to_cut:
            tool_bodies = adsk.core.ObjectCollection.create()
            tool_bodies.add(subtraction_body)
            combine_input = combineFeatures.createInput(body_to_cut,
                                                        tool_bodies)
            combine_input.isKeepToolBodies = True
            combine_input.operation = CutFeatureOperation
            combineFeatures.add(combine_input)

    def _get_offsets(self, parameters):
        """
        Implement this function in subclasses.
        :param parameters:
        :return:
        """
        return (0, 0, 0)

    @staticmethod
    def get_parameter_dict():
        """
        Implement in subclass to define appropriate parameters.
        :return:
        """
        return dict()

    @staticmethod
    def mirror_points(pointlist, axis):
        """
        Mirrors the list of points across either the x or y axis.
        :param pointlist:
        :param axis: "x" or "y"
        :return:
        """
        newlist = []
        for pair in pointlist:
            (x, y) = pair
            if axis == "x":
                x *= -1
            elif axis == "y":
                y *= -1
            newlist.append((x, y))
        return newlist


class Cantilever(BaseSnap):

    component_name = "Cantilever"

    def _sketch_join_properties(self, parameters):
        # Parameters for drawing the profile
        r_top = parameters['top_radius']
        r_bot = parameters['bottom_radius']
        th = parameters['thickness']
        l = parameters['length']
        strain = parameters['strain']
        nose_angle = math.radians(parameters["nose_angle"])

        bot_radius_sweep_angle = math.atan(l / (th / 2))
        sin_th = math.sin(bot_radius_sweep_angle)
        cos_th = math.cos(bot_radius_sweep_angle)

        x_rad = (1 - cos_th) * r_bot  # The x-length of bot radius arc
        y_rad = sin_th * r_bot  # The y-length of bot radius arc
        arm_length = l - x_rad

        nose_height = 1.09 * strain * arm_length ** 2 / th
        nose_x = nose_height / math.tan(nose_angle)

        # Define points_coordinates and arcs from parameters
        p_c = [(0, 0), (r_bot, 0),
               (x_rad, y_rad),
               (l * 1.20 + nose_x, y_rad + 1 / 2 * th * 1.25),
               (l * 1.20 + nose_x, y_rad + 3 / 4 * th),
               (l * 1.07 + nose_x, y_rad + th + nose_height),
               (l + nose_x, y_rad + th + nose_height),
               (l + nose_x, y_rad + th + nose_height),
               (l, y_rad + th),
               (r_top, y_rad + th),
               (r_top, sin_th * r_bot + r_top + th),
               (0, sin_th * r_bot + r_top + th)]

        # Define which point indexes should be connected by straight lines
        point_pair_indexes = [(2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8),
                              (8, 9), (11, 0)]
        # Defines two arcs by point indexes and sweep angle
        arc_lines = [(1, 0, - bot_radius_sweep_angle), (10, 11, math.pi/2)]

        data = {"points_coordinates": p_c,
                "point_pair_indexes": point_pair_indexes,
                "arc_lines": arc_lines}
        return data

    def _sketch_cut_properties(self, parameters):
        # Parameters for drawing the profile
        r_bot = parameters['bottom_radius']
        r_top = parameters['top_radius']
        th = parameters['thickness']
        length = parameters['length']
        strain = parameters['strain']
        nose_angle = math.radians(parameters["nose_angle"])

        g_l = parameters['gap_length']
        g_h = parameters['gap_thickness']
        x_l = parameters['extra_length']

        # Determine how the profile should be drawn, depending on the value of
        theta = math.atan(length / (th / 2))
        sin_th = math.sin(theta)
        cos_th = math.cos(theta)

        x_rad_bot = (1 - cos_th) * r_bot  # The x-length of bot radius arc
        y_rad_bot = sin_th * r_bot
        x_rad_top = r_top
        y_rad_top = r_top

        arm_length = length - x_rad_bot

        nose_height = 1.09 * strain * arm_length ** 2 / th
        nose_x = nose_height / math.tan(nose_angle)

        total_length = 1.20 * length + nose_x + x_l

        p_c = [(0, -g_h),
               (x_rad_bot, y_rad_bot - g_h),
               (total_length, y_rad_bot - g_h),
               (total_length, y_rad_bot + th + nose_height + g_h),
               (length + nose_x - g_l, y_rad_bot + th + nose_height + g_h),
               (length - g_l, y_rad_bot + th + g_h),
               (x_rad_top, y_rad_bot + th + g_h),
               (0, y_rad_bot + y_rad_top + th + g_h)]

        point_pair_indexes = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6),
                              (6, 7), (7, 0)]

        # Since there are no arc lines in this profile
        arc_lines = []

        data = {"points_coordinates": p_c,
                "point_pair_indexes": point_pair_indexes,
                "arc_lines": arc_lines
                }
        return data

    @staticmethod
    def get_parameter_dict():
        PARAMETERS = {
            "top_radius": (float, int),
            "bottom_radius": (float, int),
            "strain": (float, int),
            "extrusion_distance": (float, int),
            "thickness": (float, int),
            "wall_thickness": (float, int),
            "length": (float, int),
            "nose_angle": (float, int),
            "gap_length": (float, int),
            "gap_thickness": (float, int),
            "gap_extrusion": (float, int),
            "extra_length": (float, int),
            "x_location": (str,),
            "y_location": (str,)
        }
        return PARAMETERS

    def _get_offsets(self, parameters):
        ex_dist = parameters['extrusion_distance']
        bot_rad = parameters['bottom_radius']
        thickness = parameters['thickness']
        theta = math.atan(parameters['length'] / (parameters['thickness'] / 2))
        x_offset = 0
        y_offset = 0
        z_offset = 0

        x_loc = parameters["x_location"]
        y_loc = parameters["y_location"]
        extrusion_distance = parameters["extrusion_distance"]

        if x_loc == "top":
            x_offset = extrusion_distance
        elif x_loc == "middle":
            x_offset = extrusion_distance / 2
        elif x_loc == "bottom":
            x_offset = 0

        if y_loc == "top":
            y_offset = - (bot_rad * math.sin(theta) + thickness)
        elif y_loc == "middle":
            y_offset = - (bot_rad * math.sin(theta) + thickness) / 2
        elif y_loc == "bottom":
            y_offset = 0

        return (x_offset, y_offset, z_offset)


class CantileverPin(BaseSnap):
    component_name = "Snap pin"
    gap_in_cut_body = False

    def _sketch_join_properties(self, parameters):
        i_rad = parameters['inner_radius']
        th = parameters['thickness']
        l = parameters['length']
        strain = parameters['strain']
        width = parameters['width']
        ledge = parameters["ledge"]
        e_len = parameters["extra_length"]
        m_p = parameters["middle_padding"]
        gap_length = parameters["gap_length"]
        y_gap = parameters["gap_thickness"]
        nose_angle = math.radians(parameters["nose_angle"])

        theta = math.atan(l / (th / 2))
        sin_th = math.sin(theta)
        cos_th = math.cos(theta)
        x_rad = (1 - cos_th) * i_rad  # The x-length of the radius arc
        y_rad = sin_th * i_rad  # The y-length of the radius arc.
        arm_length = l - x_rad - m_p / 2

        nose_height = 1.09 * strain * arm_length ** 2 / th
        nose_x = nose_height / math.tan(nose_angle)
        in_flat = width / 2 - th - y_rad - y_gap  # half length between inner radiuses

        first_cantilever_points = [
            (m_p / 2, in_flat),  # 0
            (m_p / 2 + i_rad, in_flat),  # 1
            (m_p / 2 + x_rad, in_flat + y_rad),  # 2
            (l * 1.20 + nose_x + gap_length, in_flat + y_rad + 1 / 2 * th * 1.25),  # 3
            (l * 1.20 + nose_x + gap_length, in_flat + y_rad + 3 / 4 * th),  # 4
            (l * 1.07 + nose_x + gap_length, in_flat + y_rad + th + nose_height),  # 5
            (l + nose_x + gap_length, in_flat + y_rad + th + nose_height),  # 6
            (l + gap_length, width / 2 - y_gap),  # 7
            (ledge, width / 2 - y_gap),  # 8
            (ledge, width / 2 - y_gap),  # 9
            (ledge, width / 2 - y_gap),  # 10
            (0, width / 2 + ledge - y_gap),  # 11
            (m_p / 2, 0)]  # 12

        # Apply a change because of the gap input
        y_mirrored_cantilever = self.mirror_points(first_cantilever_points, "y")

        # Define which point indexes should be connected by straight lines

        # Something is incredibly strange about this list, it somehow gets
        # An extra last element = 9, but it disappears when list function is
        # cast over ???
        point_pair_indexes = [(2, 3), (3, 4), (4, 5), (5, 6), (6, 7),
                              (7, 8), (9, 10), (10, 11), (12, 0)]

        all_points = first_cantilever_points + y_mirrored_cantilever
        num_lines = len(first_cantilever_points)

        app = adsk.core.Application.get()
        ui = app.userInterface

        all_points.extend(self.mirror_points(all_points, "x"))

        # WARNING: Do not remove this list casting, or Fusion will crash.
        # Why? Why, indeed.
        for pair in list(point_pair_indexes):
            for i in range(1, 4):
                # ui.messageBox(f"type is {type(pair)}, and it's value is {str(pair)}")
                x, nose_height = pair
                x += num_lines * i
                nose_height += num_lines * i
                point_pair_indexes.append((x, nose_height))

        # Defines two arcs by point indexes and sweep angle
        arc_lines = [(1, 0, - theta), (1 + num_lines, 0 + num_lines, theta),
                     (1 + 2 * num_lines, 2 * num_lines, theta),
                     (1 + 3 * num_lines, 3 * num_lines, -theta)]

        data = {"points_coordinates": all_points,
                "point_pair_indexes": point_pair_indexes,
                "arc_lines": arc_lines}
        return data

    def _sketch_cut_properties(self, parameters):
        i_rad = parameters['inner_radius']
        th = parameters['thickness']
        l = parameters['length']
        strain = parameters['strain']
        width = parameters['width']
        ledge = parameters["ledge"]
        m_p = parameters["middle_padding"]
        extra_length = parameters["extra_length"]
        nose_angle = math.radians(parameters["nose_angle"])

        theta = math.atan(l / (th / 2))
        sin_th = math.sin(theta)
        cos_th = math.cos(theta)
        x_rad = (1 - cos_th) * i_rad  # The x-length of the radius arc
        y_rad = sin_th * i_rad  # The y-length of the radius arc.
        arm_length = l - x_rad - m_p / 2

        nose_height = 1.09 * strain * arm_length ** 2 / th
        nose_x = nose_height / math.tan(nose_angle)

        total_length = l * 1.20 + nose_x + extra_length

        theta = math.atan(l / (th / 2))

        cos_th = math.cos(theta)
        x_rad = (1 - cos_th) * i_rad  # the length in x-direction of radius

        first_hole_points = [
            (total_length, 0),
            (total_length, width / 2 + nose_height),
            (l + nose_x, width / 2 + nose_height),
            (l, width / 2),
            (ledge, width / 2),
            (0, width / 2 + ledge)
        ]

        # Apply a change because of the gap input
        y_mirrored_cantilever = self.mirror_points(first_hole_points, "y")

        # Define which point indexes should be connected by straight lines

        # Something is incredibly strange about this list, it somehow gets
        # An extra last element = 9, but it disappears when list function is
        # cast over ???
        point_pair_indexes = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)]

        all_points = first_hole_points + y_mirrored_cantilever
        num_lines = len(first_hole_points)

        app = adsk.core.Application.get()
        ui = app.userInterface

        all_points.extend(self.mirror_points(all_points, "x"))

        # WARNING: Do not remove this list casting, or Fusion will crash.
        # Why? Why, indeed.
        for pair in list(point_pair_indexes):
            for i in range(1, 4):
                # ui.messageBox(f"type is {type(pair)}, and it's value is {str(pair)}")
                x, nose_height = pair
                x += num_lines * i
                nose_height += num_lines * i
                point_pair_indexes.append((x, nose_height))

        # Defines two arcs by point indexes and sweep angle
        arc_lines = []
        data = {"points_coordinates": all_points,
                "point_pair_indexes": point_pair_indexes,
                "arc_lines": arc_lines}
        return data

    @staticmethod
    def get_parameter_dict():
        PARAMETERS = {
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
        return PARAMETERS

    def _get_offsets(self, parameters):
        """
        Defines offsets that will be used when creating joint origin,
        so that one can adjust the position of the cantilever.
        :param parameters:
        :return:
        """
        x_loc = parameters["x_location"]
        y_loc = parameters["y_location"]
        extrusion_distance = parameters["extrusion_distance"]
        width = parameters["width"]
        gap_extrusion = parameters["gap_extrusion"]
        x_offset = 0
        y_offset = 0
        z_offset = 0

        if x_loc == "top":
            x_offset = extrusion_distance - gap_extrusion
        elif x_loc == "middle":
            x_offset = extrusion_distance / 2 - gap_extrusion
        elif x_loc == "bottom":
            x_offset = 0 - gap_extrusion

        if y_loc == "top":
            y_offset = -width / 2
        elif y_loc == "middle":
            y_offset = 0
        elif y_loc == "bottom":
            y_offset = width / 2

        logging.debug(f"Offsets x:{x_offset}, y:{y_offset}, z:{z_offset}")

        return x_offset, y_offset, z_offset


class ExperimentalPin(ExperimentalBaseSnap):
    component_name = "Snap pin"
    gap_in_cut_body = False


    def __init__(self, parent_comp: Component, parameters: dict,
                 target_joint_org=None, target_body1=None, target_body2=None):
        """
        A new component is created which contains a body with a bendable shape.
        Additional operations are done depending on arguments.
        :param parent_comp: The component into which this component is created.
        :param parameters: The properties that define the geometric shape, along
            with the reference position for placement.
        :param join_body: A reference to a single BRepBody that the new body is
            to be combined with.
        :param cut_bodies: A list of bodies on which a cut operation will be
            performed to create a opening for the bendable shape.
        """

        """
        Step 1: Create new component
        """
        # Test parameters to make sure they are valid
        try:
            self.test_parameters(parameters)
        except ParameterException as e:
            logging.getLogger(str(type(self)) + str(e))
        # Create a new occurrence and reference its component
        matrix = adsk.core.Matrix3D.create()
        self.occurrence = parent_comp.occurrences.addNewComponent(matrix)
        self.comp = self.occurrence.component
        self.comp.name = self.component_name
        # self.cut_bodies = cut_bodies
        self.subtraction_body = None
        self.addition_body1 = None
        self.addition_body2 = None


        """
        Step 2: Create joint between selected joint origin and component. 
        """
        offsets = self._get_offsets(parameters)
        joint_origin = self._create_joint_origin(*offsets)
        if target_joint_org:
            self.place(joint_origin, target_joint_org)

        """
        Step 3: Draw sketch profiles and then extrude them into bodies. Then
        perform join and/or cut.
        """
        sketch_plane = self.comp.xZConstructionPlane
        cant_sketch = self.comp.sketches.add(sketch_plane)
        cant_sketch_data = self._sketch_join_properties(parameters)
        self._draw_sketch(cant_sketch, cant_sketch_data)
        cant_body = self._create_join_body(parameters, cant_sketch)
        cant_body.name = "Pin body"

        # if join_body:
        #     self._perform_join(join_body, cant_body)

        # Create subtraction body
        sub_sketch_data = self._sketch_cut_properties(parameters)
        sub_sketch = self.comp.sketches.add(sketch_plane)
        self._draw_sketch(sub_sketch, sub_sketch_data)
        subtraction_body = self._create_cut_body(parameters, sub_sketch)
        subtraction_body.name = "Subtraction body"

        # Create addition bodies
        add_sketch_data = self._sketch_addition_properties(parameters)
        addition_sketch = self.comp.sketches.add(sketch_plane)
        self._draw_sketch(addition_sketch, add_sketch_data)
        self.addition_body1 = self._create_addition_body(parameters, addition_sketch)
        self.addition_body1.name = "Addition body 1"
        # Make an object_collection for the single body
        collection = adsk.core.ObjectCollection.create()
        collection.add(self.addition_body1)

        # Mirror addition_body1 over ZY plane to get number two
        mirror_input = self.comp.features.mirrorFeatures.createInput(collection,
                                                                     self.comp.yZConstructionPlane)
        mirror_feature = self.comp.features.mirrorFeatures.add(mirror_input)
        self.addition_body2 = mirror_feature.bodies[0]
        self.addition_body2.name = "Addition body 2"

        if target_body1:
            # First combine
            combined_features = self._perform_join(target_body1, self.addition_body1)

            # Then subtract
            body_to_cut = combined_features.bodies.item(0)
            self._perform_cut([body_to_cut], subtraction_body)
        else:
            self._perform_cut([self.addition_body1], subtraction_body)

        if target_body2:
            # First combine
            combined_features = self._perform_join(target_body2, self.addition_body2)

            # Then subtract
            body_to_cut = combined_features.bodies.item(0)
            self._perform_cut([body_to_cut], subtraction_body)
        else:
            self._perform_cut([self.addition_body2], subtraction_body)

        #
        # if target_body2:
        #     self._perform_join(self.addition_body2, target_body2)
        # else:
        #     self._perform_cut([self.addition_body1], subtraction_body)


        # # Cut into the addition body
        # addition_bodies = [self.addition_body1, self.addition_body2]





    def _sketch_join_properties(self, parameters):
        t = parameters['thickness']
        # wt = parameters["wall_thickness"]
        fl = parameters['length']
        lg = parameters["length_gap"]
        w = parameters['width']
        wg = parameters["width_gap"]
        gb = parameters["gap_buffer"]
        # e_len = parameters["extra_length"]
        mp = parameters["middle_padding"]
        ldg = parameters["ledge"]
        strain = parameters['strain']
        pin_prestrain = parameters['pin_prestrain']
        n_angl = math.radians(parameters["nose_angle"])

        app = adsk.core.Application.get()
        ui = app.userInterface
        # ui.messageBox(f"{t=}, {w=}, {gb=}, {wg=}\n{(w/2 - wg - t)=}, {(gb - wg)=}")

        P2x = mp
        P2y = w/2 - wg - t
        # P2y = w/2 - wg - w/2 + gb
        # P2y = gb - wg
        P3x = mp + fl + lg
        P3y = w/2 - wg - t/2

        # Midpoint of radius
        sl = (P3y - P2y)/(P3x - P2x)  # Inner slope of leg

        theta = math.atan(1/sl)  # Want the opposite angle for radius calc

        hl = 0.2*fl  # Head length
        tl = 0.05*fl  # Top length

        nh = 1.09 * (strain + pin_prestrain) * fl ** 2 / t  # nose height
        nh_hole = 1.09 * (strain) * fl ** 2 / t  # Nose hole depth

        # Offsets are adjusting for the different position of the nose
        # because it's not entering the hole all the way in
        # Only X-offset is used (y wouldn't make sense)
        nose_offset_y = nh - nh_hole
        nose_offset_x = nose_offset_y/math.tan(n_angl)

        nose_x = nh / math.tan(n_angl)    # length in x dir resulting from angled nose


        # ui.messageBox(f"{nose_offset_x=}")

        first_cantilever_points = [
            (0, 0),  # 0
            (mp, 0),  # 1
            (P2x, P2y),  # 2
            (mp + fl + lg, w/2 - wg - t/2),  # 3
            (P3x + nose_x + hl, P3y + sl*(nose_x + hl)),  # 4
            (mp + fl + lg + nose_x + hl, (w/2 - wg - t/2) + sl*(nose_x + hl) + nh/2),  # 5
            ((mp + fl + lg) + nose_x + tl, w/2 - wg + nh),  # 6
            ((mp + fl + lg) + nose_x - nose_offset_x, w/2 - wg + nh),  # 7
            (mp + fl + lg - nose_offset_x, w/2 - wg),  # 8
            (ldg, w/2 - wg),  # 9
            (0, w/2 - wg + ldg),   # 10
            # (mp + fl + lg, w/2 - wg - t/2 - 1) # Test point
        ]  #

        # Apply a change because of the gap input
        y_mirrored_cantilever = self.mirror_points(first_cantilever_points, "y")

        # Define which point indexes should be connected by straight lines

        # Something is incredibly strange about this list, it somehow gets
        # An extra last element = 9, but it disappears when list function is
        # cast over ???
        point_pair_indexes = [(1, 2), (2, 4), (4,5), (5, 6), (6, 7), (7, 8),
                              (8, 9), (9, 10)]

        all_points = first_cantilever_points + y_mirrored_cantilever
        num_lines = len(first_cantilever_points)


        all_points.extend(self.mirror_points(all_points, "x"))
        # all_points = first_cantilever_points

        # WARNING: Do not remove this list casting, or Fusion will crash.
        # Why? Why, indeed.
        for pair in list(point_pair_indexes):
            for i in range(1, 4):
                # ui.messageBox(f"type is {type(pair)}, and it's value is {str(pair)}")
                x, nose_height = pair
                x += num_lines * i
                nose_height += num_lines * i
                point_pair_indexes.append((x, nose_height))

        # Defines two arcs by point indexes and sweep angle
        # threepoint_arcs = [[1, 14, 4]]
        arcs = [(5, 2, - theta), (5 + num_lines, 2 + num_lines, theta),
                     (5 + 2 * num_lines,2 + 2 * num_lines, theta),
                     (5 + 3 * num_lines, 2+ 3 * num_lines, - theta)]

        arcs = []

        data = {"points_coordinates": all_points,
                "point_pair_indexes": point_pair_indexes,
                "arc_lines": arcs}
        return data


    def _create_addition_body(self, parameters, sketch):
        total_distance = parameters['extrusion_distance'] + 2*parameters["wall_thickness"]


        profile = sketch.profiles[0]
        extrudes = self.comp.features.extrudeFeatures
        new_body_type = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        extrudeInput = extrudes.createInput(profile, new_body_type)

        distance_value = adsk.core.ValueInput.createByReal(total_distance)
        offset_value = adsk.core.ValueInput.createByReal(-parameters["wall_thickness"])

        extrusion_extent = adsk.fusion.DistanceExtentDefinition.create(
            distance_value)
        extrudeInput.setOneSideExtent(extrusion_extent, 0)

        start_offset = adsk.fusion.OffsetStartDefinition.create(offset_value)
        extrudeInput.startExtent = start_offset

        extrusion = extrudes.add(extrudeInput)

        # Return the newly created body.
        body = extrusion.bodies.item(0)

        return body


    def _sketch_addition_properties(self, parameters):
        """ Specifies a volume around the pin cutout, so that the pin gains the necessary support.
            Defines only one half. The body must be copied and mirrored elsewhere in the code. """

        th = parameters['thickness']
        wall_thickness = parameters["wall_thickness"]
        fl = parameters['length']
        strain = parameters['strain']
        pin_prestrain = parameters['pin_prestrain']
        width = parameters['width']
        ledge = parameters["ledge"]
        mp = parameters["middle_padding"]
        extra_length = parameters["extra_length"]
        nose_angle = math.radians(parameters["nose_angle"])

        theta = math.atan(fl / (th / 2))
        sin_th = math.sin(theta)
        cos_th = math.cos(theta)

        # Note: pretension is intentionally omitted for nose height here
        hole_nh = 1.09 * strain * fl ** 2 / th
        nh = 1.09 * (strain + pin_prestrain) * fl ** 2 / th

        nose_x = nh / math.tan(nose_angle)
        hole_nose_x = hole_nh / math.tan(nose_angle)
        hl = 0.2*fl # Head length
        tl = 0.05*fl # Top length
        total_length = mp + fl + nose_x + hl + extra_length

        # The thickness of the material around the Pin

        first_hole_points = [
            (0, 0),  # 0
            # (mp + fl + extra_length + nose_x + tl, 0),  # 1
            (mp + fl + extra_length + nose_x  + tl, 0),  # 1
            (mp + fl + nose_x + tl + extra_length, width / 2 + hole_nh + wall_thickness),  # 2
            (mp + fl, width / 2 + hole_nh + wall_thickness),  # 3
            (mp + fl - nh, width / 2 + wall_thickness),  # 4
            (0, width / 2 + wall_thickness)  # 5
        ]

        # Apply a change because of the gap input
        y_mirrored_cantilever = self.mirror_points(first_hole_points, "y")

        # Define which point indexes should be connected by straight lines

        # Something is incredibly strange about this list, it somehow gets
        # An extra last element = 9, but it disappears when list function is
        # cast over ???
        point_pair_indexes = [(1, 2), (2, 3), (3, 4), (4, 5), (5, 0)]

        all_points = first_hole_points + y_mirrored_cantilever
        num_lines = len(first_hole_points)

        app = adsk.core.Application.get()
        ui = app.userInterface

        # all_points.extend(self.mirror_points(all_points, "x"))

        # WARNING: Do not remove this list casting, or Fusion will crash.
        # Why? Why, indeed.
        for pair in list(point_pair_indexes):
            for i in range(1, 2):
                # ui.messageBox(f"type is {type(pair)}, and it's value is {str(pair)}")
                x, nose_height = pair
                x += num_lines * i
                nose_height += num_lines * i
                point_pair_indexes.append((x, nose_height))

        # Defines two arcs by point indexes and sweep angle
        arc_lines = []
        data = {"points_coordinates": all_points,
                "point_pair_indexes": point_pair_indexes,
                "arc_lines": arc_lines}
        return data


    def _sketch_cut_properties(self, parameters):
        th = parameters['thickness']
        fl = parameters['length']
        strain = parameters['strain']
        pin_prestrain = parameters['pin_prestrain']
        width = parameters['width']
        ledge = parameters["ledge"]
        mp = parameters["middle_padding"]
        extra_length = parameters["extra_length"]
        nose_angle = math.radians(parameters["nose_angle"])

        theta = math.atan(fl / (th / 2))

        # Note: pretension is intentionally omitted for nose height here
        hole_nh = 1.09 * strain * fl ** 2 / th
        nh = 1.09 * (strain + pin_prestrain) * fl ** 2 / th

        nose_x = nh / math.tan(nose_angle)
        hole_nose_x = hole_nh / math.tan(nose_angle)
        hl = 0.2*fl # Head length
        tl = 0.05*fl # Top length
        total_length = mp + fl + nose_x + hl + extra_length

        # Adjustment because of pretension


        first_hole_points = [
            (0, 0),  # 0
            (mp + fl + nose_x + hl + extra_length, 0),  # 1
            (mp + fl + nose_x + hl + extra_length, width / 2 + hole_nh),  # 2
            (mp + fl + hole_nose_x, width / 2 + hole_nh),  # 3
            (mp + fl, width / 2),  # 4
            (ledge, width / 2),  # 5
            (0, width / 2 + ledge)  # 6
        ]

        # Apply a change because of the gap input
        y_mirrored_cantilever = self.mirror_points(first_hole_points, "y")

        # Define which point indexes should be connected by straight lines

        # Something is incredibly strange about this list, it somehow gets
        # An extra last element = 9, but it disappears when list function is
        # cast over ???
        point_pair_indexes = [(1, 2), (2, 3), (3, 4), (4, 5), (5, 6)]

        all_points = first_hole_points + y_mirrored_cantilever
        num_lines = len(first_hole_points)

        app = adsk.core.Application.get()
        ui = app.userInterface

        all_points.extend(self.mirror_points(all_points, "x"))

        # WARNING: Do not remove this list casting, or Fusion will crash.
        # Why? Why, indeed.
        for pair in list(point_pair_indexes):
            for i in range(1, 4):
                # ui.messageBox(f"type is {type(pair)}, and it's value is {str(pair)}")
                x, nose_height = pair
                x += num_lines * i
                nose_height += num_lines * i
                point_pair_indexes.append((x, nose_height))

        # Defines two arcs by point indexes and sweep angle
        arc_lines = []
        data = {"points_coordinates": all_points,
                "point_pair_indexes": point_pair_indexes,
                "arc_lines": arc_lines}
        return data


    def _draw_sketch(self, sketch, sketch_data):
        points_coordinates = sketch_data['points_coordinates']
        point_pair_indexes = sketch_data['point_pair_indexes']
        arc_lines = sketch_data['arc_lines']

        sketch_points_3D = []
        points_3D = []
        # Create sketch points
        for x, y in points_coordinates:
            sketch_points_3D.append(sketch.sketchPoints.add(adsk.core.Point3D.create(x, y, 0)))
            # points_3D.append((adsk.core.Point3D.create(x, y, 0)))

        # Draw straight lines
        for p0, p1 in point_pair_indexes:
            start_point = sketch_points_3D[p0]
            end_point = sketch_points_3D[p1]
            sketch.sketchCurves.sketchLines.addByTwoPoints(start_point,
                                                           end_point)

        # Draw arcs if any. This somehow doesn't need an "if sweep_angle > 0"
        for arc_data in arc_lines:
            origin_point = sketch_points_3D[arc_data[0]]
            mid_point = sketch_points_3D[arc_data[1]]
            theta = arc_data[2]
            # end_point2 = sketch_points_3D[arc_data[2]]
            app = adsk.core.Application.get()
            ui = app.userInterface
            # ui.messageBox(f"Type of last point: {end_point=}")

            # startPoint = adsk.core.Point3D.create(0, 0, 0)
            # mid_point = adsk.core.Point3D.create(5, 0, 0)
            # endPoint = adsk.core.Point3D.create(8, 7, 0)
            #
            sketch.sketchCurves.sketchArcs.addByCenterStartSweep(origin_point,
                                                                 mid_point,
                                                                 theta)
            # sketch.sketchCurves.sketchArcs.addByThreePoints(startPoint,
            #                                                      alongPoint,
            #                                                      endPoint)


    @staticmethod
    def get_parameter_dict():
        PARAMETERS = {
            "strain": (float, int),
            "pin_prestrain": (float, int),
            "extrusion_distance": (float, int),
            "thickness": (float, int),
            "wall_thickness": (float, int),
            "length": (float, int),
            "width": (float, int),
            "ledge": (float, int),
            "middle_padding": (float, int),
            "nose_angle": (float, int),
            "length_gap": (float, int),
            "width_gap": (float, int),
            "gap_extrusion": (float, int),
            "extra_length": (float, int),
            "x_location": (str,),
            "y_location": (str,),
            "gap_buffer": (float, int)
        }
        return PARAMETERS

    def _get_offsets(self, parameters):
        """
        Defines offsets that will be used when creating joint origin,
        so that one can adjust the position of the cantilever.
        :param parameters:
        :return:
        """
        x_loc = parameters["x_location"]
        y_loc = parameters["y_location"]
        extrusion_distance = parameters["extrusion_distance"]
        width = parameters["width"]
        gap_extrusion = parameters["gap_extrusion"]
        x_offset = 0
        y_offset = 0
        z_offset = 0

        if x_loc == "top":
            x_offset = extrusion_distance - gap_extrusion
        elif x_loc == "middle":
            x_offset = extrusion_distance / 2 - gap_extrusion
        elif x_loc == "bottom":
            x_offset = 0 - gap_extrusion

        if y_loc == "top":
            y_offset = -width / 2
        elif y_loc == "middle":
            y_offset = 0
        elif y_loc == "bottom":
            y_offset = width / 2

        logging.debug(f"Offsets x:{x_offset}, y:{y_offset}, z:{z_offset}")

        return x_offset, y_offset, z_offset


class ParameterException(Exception):
    pass
