"""
To test whether cadquery and the import of step files work.
Or any other tests.
"""


# Create and import a basic cantilever part
import cadquery as cq
import numpy as np
import math
import adsk.core, adsk.fusion, traceback
import os.path, sys


BASE_PARAMETERS = {}
BASE_PARAMETERS["thickness"] = 4
BASE_PARAMETERS["length"] = 12
BASE_PARAMETERS["strain"] = 0.04
BASE_PARAMETERS["nose_angle"] = 85
BASE_PARAMETERS["name"] = "default_cantilever"




def create_cantilever(modified_parameters=dict()):
    p = BASE_PARAMETERS.copy()
    p.update(modified_parameters)

    # Multiplying all values by 10 to fix weirdness
    th = p["thickness"]
    l = p["length"]
    strain = p["strain"]
    nose_angle = math.radians(p["nose_angle"])
    fatness = p["extrusion_distance"]
    name = p["name"]

    arm_length = l

    nose_height = 1.09 * strain * arm_length ** 2 / th
    nose_x = nose_height / math.tan(nose_angle)

    # Point coordinates no radius business
    p_c = [(0, 0),  # Start
           (l * 1.20 + nose_x, 1 / 2 * th * 1.25),
           (l * 1.20 + nose_x, 3 / 4 * th),
           (l * 1.07 + nose_x, th + nose_height),
           (l + nose_x, th + nose_height),
           (l, th),
           (0, th)]

    sketch = (
        cq.Workplane("XY")
    )

    data = np.array(p_c)

    x = data[:, 0]
    y = data[:, 1]

    sketch = sketch.moveTo(x[0], y[0])
    for i in range(1, len(x)):
        x1, y1 = x[i], y[i]
        sketch = sketch.lineTo(x1, y1)

    sketch = sketch.close()
    sketch = sketch.extrude(fatness)

    assy = cq.Assembly()
    assy.add(sketch, name="sketch", color=cq.Color("gray"))
    cq.exporters.export(sketch, name + ".step")

    # Open stepfile to edit
    from steputils import p21
    fname = name + ".step"
    stepfile = p21.readfile(fname)

    product = stepfile.data[0].get("#7")
    product.entity.params = (name,)

    stepfile.save(fname)



def import_step_file(modified_parameters=dict()):

    p = modified_parameters
    name = p["name"]

    # Import part to Fusion 360
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        # Get import manager
        importManager = app.importManager

        # Get active design
        product = app.activeProduct
        design = adsk.fusion.Design.cast(product)

        # Get root component
        rootComp = design.rootComponent

        # Get step import options
        stpFileName = name + ".step"
        stpOptions = importManager.createSTEPImportOptions(stpFileName)
        stpOptions.isViewFit = False

        # Import step file to root component
        imported_comp = importManager.importToTarget2(stpOptions, rootComp)
        return imported_comp


    except:
        if ui:
            ui.messageBox('Import step file Failed:\n{}'.format(traceback.format_exc()))


def import_step_file2(modified_parameters=dict()):

    p = modified_parameters
    name = p["name"]

    # Import part to Fusion 360
    ui = None
    imported_object = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        # Get import manager
        importManager = app.importManager

        # Get active design
        product = app.activeProduct
        design = adsk.fusion.Design.cast(product)

        # Get root component
        rootComp = design.rootComponent

        # Get step import options
        stpFileName = name + ".step"
        stpOptions = importManager.createSTEPImportOptions(stpFileName)
        stpOptions.isViewFit = False

        # Import step file to root component
        imported_object = importManager.importToTarget2(stpOptions, rootComp)
        return imported_object
    except:
        if ui:
            ui.messageBox('Import step file Failed:\n{}'.format(traceback.format_exc()))
            #ui.messageBox("object:" + str(imported_object.asArray()))


def get_cantilever(modified_parameters=dict()):
    p = BASE_PARAMETERS.copy()
    p.update(modified_parameters)
    # First create a new cantilever with given parameters


    create_cantilever(modified_parameters)
    imported_object = import_step_file(p)
    return imported_object



