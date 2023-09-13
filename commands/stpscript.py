# export_path =  r"C:\Users\Alf\Programmering\CAD_Generator\stepfile.step"
export_path = r"stepfile.step"
import math
import cadquery.cadquery as cq

import numpy as np



def snap_thingy():
    r_top = 0
    r_bot = 0
    th = 4
    l = 12
    strain = 0.04
    nose_angle = math.radians(85)
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
    sketch = sketch.extrude(1)

    assy = cq.Assembly()
    assy.add(sketch, name="sketch", color=cq.Color("gray"))
    cq.exporters.export(sketch, export_path)
    return assy

snap_thingy()
