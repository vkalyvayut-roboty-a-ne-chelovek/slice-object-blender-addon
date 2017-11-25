bl_info = {
	"name": "Object Slicer Addon",
	"author": "6d7367",
	"location": "View3D > Tools > Slicer Addon",
	"version": (0, 1, 0),
	"blender": (2, 7, 6),
	"description": "Slices active object for number of pieces",
	"wiki": "",
	"category": "Object"
}


def register():
	bpy.utils.register_class(SlicerOperator)
	bpy.utils.register_class(SlicerPanel)
	


def unregister():
	bpy.utils.unregister_class(SlicerPanel)
	bpy.utils.unregister_class(SlicerOperator)
	pass


import random
from mathutils import Vector
import bpy
import bmesh


class SlicerPanel(bpy.types.Panel):
	bl_space_type = "VIEW_3D"
	bl_region_type = "TOOLS"
	bl_category = "Slicer Addon"
	bl_label = "Slicer Addon"
	bl_context = "objectmode"

	def draw(self, context):
		self.layout.prop(context.scene, "slicer_step")
		self.layout.operator("object.slicer_operator")

	@classmethod
	def register(cls):
		pass

	@classmethod
	def unregister(cls):
		pass

class SlicerOperator(bpy.types.Operator):
	bl_idname = "object.slicer_operator"
	bl_label = "Slice object"

	def execute(self, context):
		step = round(context.scene.slicer_step, 2)
		slcr = Slicer(step)
		slcr.slice()

		del slcr
		
		return {'FINISHED'}

	@classmethod
	def register(cls):
		bpy.types.Scene.slicer_step = bpy.props.FloatProperty(
			name = "step",
			description = "object slicer step",
			default = 0.25
		)

	@classmethod
	def unregister(cls):
		pass


class Slicer():
    @staticmethod    
    def to_object():
        bpy.ops.object.mode_set(mode='OBJECT')
    
    @staticmethod
    def to_edit():
        bpy.ops.object.mode_set(mode='EDIT')
    
    def __init__(self, step = 0.5):
        self.x, self.y, self.z = None, None, None
        self.step = step
        self.slicers = []
        self.objects = []
        
        self.main_object = bpy.context.active_object
        self.prev_name = self.main_object.name
        new_name = 'object_{}_slice'.format(random.randint(1000, 50000))
        self.main_object.name = new_name
     
    
    def compute_min_max(self):
        Slicer.to_edit()
        
        bm = bmesh.from_edit_mesh(bpy.context.object.data)

        matrix_to_global = bpy.context.active_object.matrix_world

        for v in bm.verts:
            curr_co = matrix_to_global * v.co
            if self.x is None:
                self.x = { "min": curr_co[0], "max": curr_co[0] }
                self.y = { "min": curr_co[1], "max": curr_co[1] }
                self.z = { "min": curr_co[2], "max": curr_co[2] }
            #
            self.x["min"] = min(self.x["min"], curr_co[0])
            self.x["max"] = max(self.x["max"], curr_co[0])
            #
            self.y["min"] = min(self.y["min"], curr_co[1])
            self.y["max"] = max(self.y["max"], curr_co[1])
            #
            self.z["min"] = min(self.z["min"], curr_co[2])
            self.z["max"] = max(self.z["max"], curr_co[2])
        
        Slicer.to_object()
    
    def generate_slicers(self):
        width_x = (self.x["max"] - self.x["min"])
        width_y = (self.y["max"] - self.y["min"])
        
        middle_x = self.x["min"] + (width_x / 2)
        middle_y = self.y["min"] + (width_y / 2)
        
        current_z = self.z["min"]
        
        size = max(width_x, width_y)
        for i in range(0, 2):
            current_z += (self.step * i) - 0.001
            self.slicers.append(
                self._make_slicer(
                    size, middle_x, middle_y, current_z
                )
            )
    
    def _make_slicer(self, size, x, y, z):
        bpy.ops.mesh.primitive_plane_add(
            radius= size, 
            location=(x, y, z), 
            layers=(True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False)
        )
        
        return bpy.context.active_object
    
    def _make_object(self, new_object_number):
        bpy.ops.object.select_all(action="DESELECT")    
        self.main_object.select = True
        bpy.ops.object.duplicate()
        
        object_name = '{}.{:03d}'.format(self.main_object.name, new_object_number)
        return bpy.data.objects[object_name]
    
    def generate_objects_to_slice(self):
        total_height = (self.z["max"] - self.z["min"]) + 0.0
        step_count = total_height / self.step
        
    
        bpy.ops.object.select_all(action="DESELECT")    
        self.main_object.select = True
        
        count = 0
        while count <= step_count:
            self.objects.append(
                self._make_object(count+1)
            )
            count += 1
        pass
    
    def _remove_slicers(self):
        bpy.ops.object.select_all(action="DESELECT")
        for slicer in self.slicers:
            slicer.select = True
            bpy.ops.object.delete()
    
    def _remove_objects(self):
        bpy.ops.object.select_all(action="DESELECT")
        for obj in self.objects:
            obj.select = True
            bpy.ops.object.delete()
    
    def clean(self):
        self._remove_slicers()
        #self._remove_objects()
                
        self.main_object.select = True
        self.main_object.name = self.prev_name
        
        key = 1
        for slice in self.objects:
            slice.name = '{}.slice_{}'.format(self.main_object.name, key)
            key += 1
    
    def slice(self):
        self.compute_min_max()
        self.generate_slicers()
        self.generate_objects_to_slice()
        
        self.main_object.hide = True
        
        bpy.ops.object.select_all(action="DESELECT")
        
        
        Slicer.to_object();
        for obj in self.objects:
            obj.select = True
            bpy.context.scene.objects.active = obj
            
            self._apply_mod1(obj)
            self._apply_mod2(obj)
            
            self._raise_slicers()    
            obj.select = False
            
        
        self.clean()
    def _apply_mod1(self, obj):
        bpy.ops.object.modifier_add(type='BOOLEAN')
        curr_obj_name = obj.name
        curr_mods = bpy.data.objects[curr_obj_name].modifiers
        
        for modK, mod in curr_mods.items():
            mod.operation = 'DIFFERENCE'
            mod.object = self.slicers[0]
            bpy.ops.object.modifier_apply(modifier=modK)
        pass
    
    def _apply_mod2(self, obj):
        if (self.slicers[1].location[2] >= self.z["max"]):
            return
        
        bpy.ops.object.modifier_add(type='BOOLEAN')
        curr_obj_name = obj.name
        curr_mods = bpy.data.objects[curr_obj_name].modifiers
        
        for modK, mod in curr_mods.items():
            mod.operation = 'INTERSECT'
            mod.object = self.slicers[1]
            bpy.ops.object.modifier_apply(modifier=modK)
        pass
    
    def _raise_slicers(self):
        bpy.ops.object.select_all(action="DESELECT")
        for sl in self.slicers:
            sl.select = True
            bpy.context.scene.objects.active = sl
            
            sl.location += Vector((0.0, 0.0, self.step))
            
            sl.select = False
        pass