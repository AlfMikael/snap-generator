"""Classes for generating snap geometries."""

import adsk.core
import adsk.fusion
import adsk.cam
import math
import logging
from adsk.core import ValueInput as valueInput
from adsk.fusion import Component


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
        combineFeatures.add(combine_input)

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


class ParameterException(Exception):
    pass
