import bpy
import random
import bmesh
from bpy.types import Panel, Operator
from bpy.props import StringProperty, BoolProperty
from mathutils import Vector

bl_info = {
    "name": "Custom SL Utilities",
    "author": "Victor Vile",
    "version": (1, 2, 0),
    "blender": (3, 6, 22),
    "location": "View3D > N-Panel > SL Utilities",
    "description": "Various utilities for materials, UV islands, and vertex tools",
    "category": "3D View",
}

class CUSTOM_PT_main_panel(Panel):
    bl_label = "Material & UV"
    bl_idname = "CUSTOM_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'SL Utilities'

    def draw(self, context):
        layout = self.layout
        
        box = layout.box()
        box.label(text="Material and UV Utilities")
        col = box.column(align=True)
        col.operator("custom.create_seams_from_uv", text="Create Seams from UV Islands")
        col.operator("custom.assign_materials_to_uv_islands", text="Assign Materials to UV Islands")
        
        # Add blank space
        col.separator()
        
        col.operator("custom.random_material_colors", text="Random Material Colors")
        col.operator("custom.assign_materials_to_vertex_groups", text="Vertex Groups from Materials")
        
        # Add blank space
        col.separator()
        
        col.operator("custom.create_groups_and_seams_from_materials", text="Vertex Groups & Seams from Materials")

class CUSTOM_PT_vertex_tools_panel(Panel):
    bl_label = "Vertex Tools"
    bl_idname = "CUSTOM_PT_vertex_tools_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'SL Utilities'

    def draw(self, context):
        layout = self.layout
        
        box = layout.box()
        box.label(text="Vertex Selection Tools")
        col = box.column(align=True)
        
        # Add the operator with its property
        op = col.operator("mesh.select_nearest_unconnected", text="Copy Vertex Weight from Nearest Unconnected")
        # You can set default values here if needed
        # op.make_new_active = True

class MESH_OT_select_nearest_unconnected(Operator):
    bl_idname = "mesh.select_nearest_unconnected"
    bl_label = "Select Nearest Unconnected Vertex"
    bl_options = {'REGISTER', 'UNDO'}

    make_new_active: BoolProperty(
        name="Make Nearest Active",
        default=True,
        description="Make the found vertex the active one"
    )

    def execute(self, context):
        if context.object.mode != 'EDIT':
            self.report({'ERROR'}, "Must be in Edit Mode")
            return {'CANCELLED'}

        obj = context.edit_object
        bm = bmesh.from_edit_mesh(obj.data)

        selected_verts = [v for v in bm.verts if v.select]

        if not selected_verts:
            self.report({'WARNING'}, "No vertices selected")
            return {'CANCELLED'}

        connected = set()
        for v in selected_verts:
            for e in v.link_edges:
                connected.update([v_other.index for v_other in e.verts])

        avg_pos = sum((v.co for v in selected_verts), Vector()) / len(selected_verts)

        nearest_vert = None
        min_dist = float("inf")
        for v in bm.verts:
            if not v.select and v.index not in connected:
                dist = (v.co - avg_pos).length
                if dist < min_dist:
                    min_dist = dist
                    nearest_vert = v

        if nearest_vert:
            nearest_vert.select_set(True)

            if self.make_new_active:
                bm.select_history.clear()
                bm.select_history.add(nearest_vert)

            bmesh.update_edit_mesh(obj.data)
            
            # Copy vertex weights from the previously selected vertices to the new vertex
            try:
                bpy.ops.object.vertex_weight_copy()
                self.report({'INFO'}, f"Nearest vertex: {nearest_vert.index} (distance: {min_dist:.4f}) - Weights copied")
            except Exception as e:
                self.report({'WARNING'}, f"Nearest vertex: {nearest_vert.index} (distance: {min_dist:.4f}) - Weight copy failed: {str(e)}")
            
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "No unconnected vertex found")
            return {'CANCELLED'}

class CUSTOM_OT_random_material_colors(Operator):
    bl_idname = "custom.random_material_colors"
    bl_label = "Random Material Colors"
    bl_description = "Assign random colors to each material in the selected object"

    def execute(self, context):
        obj = context.active_object
        if obj and obj.type == 'MESH':
            materials = obj.data.materials
            used_colors = set()

            for mat in materials:
                while True:
                    color = (random.random(), random.random(), random.random(), 1.0)
                    if color not in used_colors:
                        used_colors.add(color)
                        break

                mat.diffuse_color = color
                if mat.use_nodes:
                    if 'Principled BSDF' in mat.node_tree.nodes:
                        principled = mat.node_tree.nodes['Principled BSDF']
                        principled.inputs['Base Color'].default_value = color

            self.report({'INFO'}, f"Assigned random colors to {len(materials)} materials")
        else:
            self.report({'WARNING'}, "No mesh object selected")
        return {'FINISHED'}

class CUSTOM_OT_create_seams_from_uv(Operator):
    bl_idname = "custom.create_seams_from_uv"
    bl_label = "Create Seams from UV Islands"
    bl_description = "Create seams from UV island boundaries"

    def execute(self, context):
        obj = context.active_object
        if obj and obj.type == 'MESH':
            bpy.ops.object.mode_set(mode='EDIT')
            bm = bmesh.from_edit_mesh(obj.data)
            bm.faces.ensure_lookup_table()

            uv_layer = bm.loops.layers.uv.verify()

            def round_uv(uv, decimals=5):
                return (round(uv.x, decimals), round(uv.y, decimals))

            # Create a dictionary of UV coordinates to faces
            uv_to_faces = {}
            for face in bm.faces:
                for loop in face.loops:
                    uv = round_uv(loop[uv_layer].uv)
                    if uv not in uv_to_faces:
                        uv_to_faces[uv] = set()
                    uv_to_faces[uv].add(face)

            # Find islands
            islands = []
            unprocessed_faces = set(bm.faces)

            while unprocessed_faces:
                start_face = unprocessed_faces.pop()
                island = set()
                to_process = {start_face}

                while to_process:
                    face = to_process.pop()
                    if face not in island:
                        island.add(face)
                        for loop in face.loops:
                            uv = round_uv(loop[uv_layer].uv)
                            connected_faces = uv_to_faces[uv]
                            to_process.update(connected_faces - island)

                islands.append(island)
                unprocessed_faces -= island

            # Mark seams
            for island in islands:
                boundary_edges = set()
                for face in island:
                    for edge in face.edges:
                        linked_faces = set(edge.link_faces)
                        if len(linked_faces.intersection(island)) == 1:
                            boundary_edges.add(edge)

                for edge in boundary_edges:
                    edge.seam = True

            bmesh.update_edit_mesh(obj.data)
            bpy.ops.object.mode_set(mode='OBJECT')

            self.report({'INFO'}, f"Created seams from {len(islands)} UV islands")
        else:
            self.report({'WARNING'}, "No mesh object selected")
        return {'FINISHED'}

class CUSTOM_OT_assign_materials_to_vertex_groups(Operator):
    bl_idname = "custom.assign_materials_to_vertex_groups"
    bl_label = "Assign Materials to Vertex Groups"
    bl_description = "Assign faces of each material to their own vertex groups"

    def execute(self, context):
        obj = context.active_object
        if obj and obj.type == 'MESH':
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_mode(type='FACE')
            bpy.ops.mesh.select_all(action='DESELECT')

            mesh = obj.data
            for mat_index, material in enumerate(obj.material_slots):
                if material.material:
                    bpy.ops.object.mode_set(mode='OBJECT')
                    for poly in mesh.polygons:
                        if poly.material_index == mat_index:
                            poly.select = True
                    
                    bpy.ops.object.mode_set(mode='EDIT')
                    vg_name = material.material.name
                    vg = obj.vertex_groups.get(vg_name) or obj.vertex_groups.new(name=vg_name)
                    bpy.ops.object.vertex_group_assign()
                    bpy.ops.mesh.select_all(action='DESELECT')

            bpy.ops.object.mode_set(mode='OBJECT')
            self.report({'INFO'}, "Assigned materials to vertex groups")
        else:
            self.report({'WARNING'}, "No mesh object selected")
        return {'FINISHED'}

class CUSTOM_OT_assign_materials_to_uv_islands(Operator):
    bl_idname = "custom.assign_materials_to_uv_islands"
    bl_label = "Assign Materials to UV Islands"
    bl_description = "Assign a new material to each UV island"

    def execute(self, context):
        obj = context.active_object
        if obj and obj.type == 'MESH':
            # First, handle material creation and cleanup in OBJECT mode
            bpy.ops.object.mode_set(mode='OBJECT')
            
            # Clean up existing UV_Island_Material_* materials if they aren't used by other objects
            for material in bpy.data.materials:
                if material.name.startswith("UV_Island_Material_"):
                    if material.users == 0:
                        bpy.data.materials.remove(material)
            
            # Clear the object's material slots first
            while len(obj.material_slots) > 0:
                bpy.ops.object.material_slot_remove()
                
            # Now go to EDIT mode for island detection
            bpy.ops.object.mode_set(mode='EDIT')
            bm = bmesh.from_edit_mesh(obj.data)
            bm.faces.ensure_lookup_table()

            uv_layer = bm.loops.layers.uv.verify()

            def round_uv(uv, decimals=5):
                return (round(uv.x, decimals), round(uv.y, decimals))

            # Create a dictionary of UV coordinates to faces
            uv_to_faces = {}
            for face in bm.faces:
                for loop in face.loops:
                    uv = round_uv(loop[uv_layer].uv)
                    if uv not in uv_to_faces:
                        uv_to_faces[uv] = set()
                    uv_to_faces[uv].add(face)

            # Find islands
            islands = []
            unprocessed_faces = set(bm.faces)

            while unprocessed_faces:
                start_face = unprocessed_faces.pop()
                island = set()
                to_process = {start_face}

                while to_process:
                    face = to_process.pop()
                    if face not in island:
                        island.add(face)
                        for loop in face.loops:
                            uv = round_uv(loop[uv_layer].uv)
                            connected_faces = uv_to_faces[uv]
                            to_process.update(connected_faces - island)

                islands.append(island)
                unprocessed_faces -= island
                
            # Store face indices instead of BMesh face references
            island_face_indices = []
            for island in islands:
                island_indices = [face.index for face in island]
                island_face_indices.append(island_indices)
            
            # Return to OBJECT mode to create and assign materials
            bpy.ops.object.mode_set(mode='OBJECT')
            
            # Create materials for each island
            for i, face_indices in enumerate(island_face_indices):
                # Create a new material
                mat_name = f"UV_Island_Material_{i+1}"
                
                # Check if material already exists
                existing_mat = bpy.data.materials.get(mat_name)
                if existing_mat:
                    mat = existing_mat
                else:
                    mat = bpy.data.materials.new(name=mat_name)
                    mat.use_nodes = True
                    
                    # Assign a random color to the material
                    nodes = mat.node_tree.nodes
                    principled = nodes.get("Principled BSDF")
                    if principled:
                        principled.inputs["Base Color"].default_value = (
                            random.random(),
                            random.random(),
                            random.random(),
                            1  # Alpha
                        )
                
                # Add the material to the object
                if mat_name not in obj.data.materials:
                    obj.data.materials.append(mat)
                
                # Get the material index
                mat_index = obj.data.materials.find(mat_name)
                
                # Make sure we have a valid material index
                if mat_index >= 0:
                    # Assign the material to faces in the island using polygon indices
                    for face_index in face_indices:
                        if face_index < len(obj.data.polygons):
                            obj.data.polygons[face_index].material_index = mat_index

            self.report({'INFO'}, f"Assigned materials to {len(islands)} UV islands")
        else:
            self.report({'WARNING'}, "No mesh object selected")
        return {'FINISHED'}

class CUSTOM_OT_create_groups_and_seams_from_materials(Operator):
    bl_idname = "custom.create_groups_and_seams_from_materials"
    bl_label = "Create Groups & Seams from Materials"
    bl_description = "Create vertex groups for each material and mark boundaries as seams"

    def execute(self, context):
        obj = context.active_object
        
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "No mesh object selected")
            return {'CANCELLED'}
            
        # Check if the object has material slots
        if not obj.data.materials:
            self.report({'WARNING'}, "Error: The object has no materials assigned")
            return {'CANCELLED'}
            
        # Check if the object is not in edit mode
        if obj.mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')

        # Switch to face select mode
        bpy.context.tool_settings.mesh_select_mode = (False, False, True)
        
        # Process each material slot
        for idx, slot in enumerate(obj.material_slots):
            # Select material slot
            obj.active_material_index = idx
            bpy.ops.object.material_slot_select()
            
            # Create a vertex group for the selected faces
            grp = obj.vertex_groups.new(name=f'Material_{idx+1}')
            
            # Go back to object mode to assign vertex group
            bpy.ops.object.mode_set(mode='OBJECT')
            
            selected_faces = [f for f in obj.data.polygons if f.select]
            for f in selected_faces:
                verts = f.vertices
                for v in verts:
                    grp.add([v], 1.0, 'ADD')

            # Go back to edit mode to mark seams
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='DESELECT')

            # Select the vertices in the group
            bpy.ops.object.vertex_group_set_active(group=grp.name)
            bpy.ops.object.vertex_group_select()

            # Mark boundary loop as seam
            bpy.ops.mesh.region_to_loop()

            bpy.ops.object.mode_set(mode='OBJECT')
            for edge in obj.data.edges:
                if edge.select:
                    edge.use_seam = True

            # Deselect the faces and go back to face select mode
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.context.tool_settings.mesh_select_mode = (False, False, True)

        # Switch back to object mode at the end
        bpy.ops.object.mode_set(mode='OBJECT')
        
        self.report({'INFO'}, f"Created vertex groups and seams for {len(obj.material_slots)} materials")
        return {'FINISHED'}

def share_uv_edge(face1, face2, uv_layer):
    edges1 = set(face1.edges)
    edges2 = set(face2.edges)
    shared_edges = edges1.intersection(edges2)
    for edge in shared_edges:
        uv1 = set(l[uv_layer].uv for l in edge.link_loops if l.face == face1)
        uv2 = set(l[uv_layer].uv for l in edge.link_loops if l.face == face2)
        if uv1 == uv2:
            return True
    return False

classes = (
    CUSTOM_PT_main_panel,
    CUSTOM_PT_vertex_tools_panel,
    MESH_OT_select_nearest_unconnected,
    CUSTOM_OT_random_material_colors,
    CUSTOM_OT_create_seams_from_uv,
    CUSTOM_OT_assign_materials_to_vertex_groups,
    CUSTOM_OT_assign_materials_to_uv_islands,
    CUSTOM_OT_create_groups_and_seams_from_materials,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()