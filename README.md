Snap Generator for Fusion 360
============================

This is an addin for Autodesk Fusion which generates snap-geometries and merges them
with existing CAD bodies in a simple and convenient way.

[YouTube tutorial](https://www.youtube.com/watch?v=WntehMWM55I) (a bit out of date)


Installation
----
[Download latest release](https://github.com/AlfMikael/snap-generator/releases/download/0.3.2/snap_generator_v0.3.2.zip).
Unzip and paste the unzipped folder into the Fusion 360 add-ins folder (see below). **Do not change the name of the folder.** If you do, Fusion will not identify it as an add-in. It should be named "snap_generator_0.4.0" (or some different version).

Add-in folder for **Windows**:

__%appdata%\Autodesk\Autodesk Fusion 360\API\AddIns__

Add-in folder for **Mac**:

__~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns__

Once the folder is in place, make sure you are in the the DESIGN workspace and click on the UTILITIES. Here you will find a button for "ADD-INS". Clicking it opens up the "Scripts and Add-Ins" window. In this window, click the "Add-Ins" tab, find the name
in the list, and click _run_.

*Warning: If you already have an old version running
this needs to be stopped, as the different versions may interfere with each other.*

![Add-ins](docs/images/add-ins_menu.png)


"Snap Generator" should now appear in the SOLID tab, under _CREATE_.
![Position](docs/images/snap_generator_in_menu.png)

Usage
----
There are currently two features: *Pin* and *Cantilever*. Each has a "simple" version. The simple version is intended to be enough for most use cases. Should you need more finely-grained control over the geometry, the non-simple versions give you that.

### Workflow
Adding a snap geometry to your design will typically include these 4 steps.
1. Place a joint-origin in the location you wish to have the snap geometry.
2. Choose the type: Cantilever or Pin, and then fill in the geometric parameters.
3. Fill in your *gap*-parameters, to adjust for 3D-printer inaccuracies.
4. Select the bodies you wish to apply your snap-geometry to, and click OK.

In the case of the Cantilever, this will join the body of the cantilever to the
body of your selected part, and also creating a mating slot in a second part.
The Pin will cut a hole into two parts, while leaving the pin body intact.
Choosing bodies to join or cut is optional for both features.

### Joint origin
The built-in feature *joint_origin* is used to position and orient the snap geometry in space.
It is found in the ASSEMBLE dropdown.
![Joint origin location](docs/images/assemble_dropdown.png)

After selecting the location, the joint origin can be rotated and
moved around. Any rotation or translation you perform on the join-origin will transfer over to the snap geometry. The joint origin has a red, blue and green vector. The figure below displays how the snap gometry will be generated in relation to these colored vectors.
![Joint origin location](docs/images/joint_origin_direction_illustration.png)


### Profiles and Gap profiles
By clicking on one of the snap features, a _command window_ will pop up. If you are not using a simple version, a *profile* dropdown will be available at the top. The first time you open it, it will be set to a profile named "default". A profile contains a configuration for a specific snap geometry, as defined by the fields seen in the menu: top radius, nose angle, thickness, etc. (SIZE is special, and not included among them. More on that later.)

There are three tabs: The Feature tab is the main one
where you adjust parameters and geometry. Choosing a profile will populate the parameters with the predefined values in the selected profile. In the *Profile* tab
you can create, delete, and choose a default profile. The *Gaps* tab does the same thing for gap parameters.

![Settings page 1](docs/images/cantilever_menu_partial.png)

### Geometry

In the __Feature tab__ you can control the geometry by adjusting a handful set of parameters.
The simplified version has a **single** parameter called *SIZE*, which scales
all parameters after a (mostly linear) formula to get reasonable geometries. The
values are hidden from the command window to not overwhelm the user with too many options.
The *SIZE* parameter is also available in the standard versions, in which case
the values become visible. Setting any parameter to extremely large or small
may result in no part being generated. Parameters are explained in the sections for Pin and 
Cantilever.

### Cutting slots and Gaps
It is possible to select _Bodies to cut_, 
which will cause the selected bodies to have material removed to make a 'slot'
for the shape to 'snap into'. The gap-parameters allow you to correct for
inaccuracies in the manufacturing process. With 3D printing you may have to test your way to successful parameters. Keep in mind that that print-orientation matters for gaps. The specific parameters are explained in the sections for Pin and Cantilever. They work a little differently for each.

## The Pin
![Pin next to command window](docs/images/pin_next_to_command_window.png) 


The Pin is a standalone snap-geometry, and my preferred go-to attaching two components together. There are two main benefits to using a pin.
1. It eliminates the issue of having to reprint because of wrong gap parameters, as the gap parameters are **applied to the pin**, not the slotted part. Which means that
after you have slotted the part. If you find that the pin doesn't fit, you only have to 
generate a new pin. The main part stays functional.
2. It allows the snap-geometry to be printed in its optimal orientation. A Pin or Cantilever
that is produced by FFF (fused filament fabrication) "pointing upwards" from the build plate, will usually have a disappointing performance because layer adhesion is commonly a weakness with this process. It will be susceptible to deformation, fracture and especially fatigue failure. 

Generating a pin will result in **4 bodies**.
1. The Pin body
2. A Subtraction body
    - Cut slots into parts.
3. Addition body 1
    - Create scaffolding in one of the parts.
4. Addition body 2
    - Create scaffolding the second part.

The subtraction body is what creates the slot for the Pin to fit into. The addition bodies create scaffolding around the pin, should the part that is being slotted not have enough material to support the slot. When selecting the bodies to create slots into, the ordering matters. For that reason, there are some illustrative lines that protrude from the Pin to assist with identifying which part is which.

### Strain and Prestrain
When each cantilever leg of the Pin gets pushed (in the intended direction), a strain develops
in the material. When this reaches the region of 0.03 to 0.05 (3-5%), most thermoplastics will either
deform or break. The maximum strain that develops in the part gets determined by the nose height.
This parameter is not available. Rather, you may supply a desired strain, at which point
the corresponding nose height which would cause that level of strain is calculated and applied.
The total strain may be separated into two parts: strain + prestrain. When the part has slid 
completely into the slot, it will still be in a state of strain. This is referred to as the 
pre-strain. This is displayed in figure 1. The Pin head is displaced a distance determined by
the Prestrain from it's neutral (strain-free) position. In figure 2, you can see that for the Pin
to be in a neutral position, it would have to penetrate into the slot wall.

When starting out, it may be confusing to see the (imaginary) overlap in figure 2. This merely appears like
an overlap, because the leg of the Pin is in an unnatural position. When it is in its correct position  (figure 1),
the gap disappears.



*Fig 1: How it will actually look when pin is inserted*
![parameter_meanings](docs/images/strain_illustration2.png)



*Fig 2: The way it looks in Fusion* (with zero gaps)
![parameter_meanings](docs/images/strain_illustration.png)


### Pin gaps
As previously mentioned, the gap parameters are applied to the Pin, not the slot. The *thickness gap*
and the *extrusion gap* is easy to visualize, see figure 3. The *length gap* is harder to visualize because
of the pre-strain, but it is simply an offset from the nose and the "notch" that it hooks onto.
In practice, that means elongating the leg to achieve this effect. The *extra length* adds some material
at the end of the slot, as seen in figure 1.


### Parameter overview

*Fig 3: Pin parameters*
![parameter_meanings](docs/images/pin_parameters.png)


## The cantilever
* The gap parameters will influence the mating slot, not the pin.
* If you don't select a _Body to join_, a new component gets created.

![Settings page 1](docs/images/cantilever_isometric_illustration.png)
![Settings page 1](docs/images/cantilever_settings_1.png)  

Parameters:
![Settings page 1](docs/images/cantilever_drawing.png) 



