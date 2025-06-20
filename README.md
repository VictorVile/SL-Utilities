# SL Utilities Blender Add-on

**Author:** Victor Vile  
**Blender Version:** 3.6.22  
**Version:** 1.2.0  
**Category:** 3D View → SL Utilities

## Description

This Blender add-on provides a set of tools to improve workflow with materials, UV islands, and vertex weight copying. 
This was a personal project, with my workflow as: Marvelous Designer --> Blender --> Zbrush --> Blender. 

Use it however you like. It includes:

Materials & UV Section:
- Generate seams from UV islands
- Assign a unique material to each UV island

- Randomize material colors and match them in both Solid Shading and Material Preview 
- Assign each material to it's own unique vertex group. Useful for when you're exporting from Blender to Zbrush and need maintain 'polygroups'. 

- Create vertex groups and seams based on material slots. Sometimes your imported mesh already has materials assigned to individual parts.

Vertex Tools Section:
- Vertex tool for selecting nearest UNCONNECTED vertex and copying the vertex weight. Ideal for when you need to maintain form of objects like spikes and studs when mesh is being deformed by armature movement.
- Ensure you're in EDIT mode and Vertex Selection Mode.
- Make sure that the spike/stud/button is not connected to the mesh with weights and click on "Copy Vertex Weight from Nearest Unconnected". The script does a fairly decent job of finding the closest vertex behind but it's not entirely perfect. 
- TIP: Right click on the "Copy Vertex Weight from Nearest Unconnected" button and add it to your favourites. Now you can quickly access it without repeatedly going to the n-Panel.


## Installation

1. Download `SL_Utilities.py` or the ZIP of the repo.
2. In Blender, go to **Edit > Preferences > Add-ons > Install**
3. Select the `.py` file or `.zip`, then enable "Custom SL Utilities".

## Usage

The tools appear in the **View3D > Sidebar > SL Utilities** panel.

## License

MIT License
