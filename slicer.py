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

GLOBAL_EDIT_OBJECT = None


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
		self.layout.prop(context.scene, "slicer_only_contour")
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
		only_contours = context.scene.slicer_only_contour
		slcr = Slicer(step, only_contours)
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

		bpy.types.Scene.slicer_only_contour = bpy.props.BoolProperty(
			name = "only_contours",
			description = "only horizontal contours",
			default = False
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

	@staticmethod
	def activate_object(obj, deselect_all = True):
		if (deselect_all):
			bpy.ops.object.select_all(action="DESELECT")

		obj.select = True
		bpy.context.scene.objects.active = obj


	
	def __init__(self, step = 0.5, only_contours = False):
		self.x, self.y, self.z = None, None, None
		self.step = step
		self.only_contours = only_contours
		self.slicers = []
		self.objects = []
		
		self.main_object = bpy.context.active_object
		self.prev_name = self.main_object.name
		new_name = 'object_{}_slice'.format(random.randint(1000, 50000))
		self.main_object.name = new_name

	def slice(self):
		self._compute_min_max()
		self._generate_slicers()
		self._generate_objects_to_slice()
		
		self.main_object.hide = True
		
		Slicer.to_object();
		for obj in self.objects:
			Slicer.activate_object(obj)
			
			self._apply_mod1(obj)
			self._apply_mod2(obj)
			
			self._raise_slicers()

		if self.only_contours:
			self.create_contours()

		self._clean()
	 
	
	def _compute_min_max(self):
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
	
	def _generate_slicers(self):
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
	
	
	def _generate_objects_to_slice(self):
		total_height = (self.z["max"] - self.z["min"]) + 0.0
		step_count = total_height / self.step
		
		Slicer.activate_object(self.main_object)
		
		count = 0
		while count <= step_count:
			new_obj = self._make_object(count+1)
			self.objects.append(new_obj)
			count += 1

	def _make_object(self, new_object_number):
		Slicer.activate_object(self.main_object)
		bpy.ops.object.duplicate()
		
		object_name = '{}.{:03d}'.format(self.main_object.name, new_object_number)
		return bpy.data.objects[object_name]
	

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
	
	def _raise_slicers(self):
		for sl in self.slicers:
			Slicer.activate_object(sl)
			sl.location += Vector((0.0, 0.0, self.step))

	def _clean(self):
		self._remove_slicers()
				
		self.main_object.name = self.prev_name
		Slicer.activate_object(self.main_object)
		
		key = 1
		for slc in self.objects:
			slc.name = '{}.slice_{}'.format(self.main_object.name, key)
			key += 1

	def _remove_slicers(self):
		for slicer in self.slicers:
			Slicer.activate_object(slicer)
			bpy.ops.object.delete()

	def create_contours(self):
		Slicer.to_object()
		obj_count = 0
		for obj in self.objects:
			Slicer.activate_object(obj)
			Slicer.to_edit()

			bm = bmesh.from_edit_mesh(obj.data)

			matrix_to_global = obj.matrix_world
			points = [v.co * matrix_to_global for v in obj.data.vertices]
			lines = []

			# line = []
			# for i in range(int(len(points) / 2)):
			# 	line = [i, i+1]
			# 	lines.append(line)

			# line = [int(len(points) / 2), 0]
			# lines.append(line)

			meshName = 'mesh' + str(obj_count)
			obName = 'ob' + str(obj_count)
			me = bpy.data.meshes.new(meshName)
			ob = bpy.data.objects.new(obName, me)
			scn = bpy.context.scene
			scn.objects.link(ob)

			me.from_pydata(points, lines, [])
			me.update()

			print("\n" * 2)
			print(points)
			print(lines)

			Slicer.to_object()
			bpy.ops.object.delete()
			obj_count += 1

	# issue 1
	# def create_contours(self):
	# 	Slicer.to_object()
	# 	obj_count = 0;
	# 	new_contours = []
	# 	for obj in self.objects:
	# 		Slicer.activate_object(obj)
	# 		Slicer.to_edit()

	# 		edges = []

	# 		bm = bmesh.from_edit_mesh(obj.data)
	# 		matrix_to_global = obj.matrix_world
	# 		for e in bm.edges:
	# 			line = []
	# 			for v in e.verts:
	# 				line.append(v.co)
	# 			edges.append(line)
	# 		#



	# 		edges[0][0] = edges[0][0] * matrix_to_global
	# 		edges[0][1] = edges[0][1] * matrix_to_global
	# 		min_z = min(edges[0][0].z, edges[0][1].z)

	# 		for e in edges:
	# 			e[0] = e[0] * matrix_to_global
	# 			e[1] = e[1] * matrix_to_global
	# 			min_z = min(min_z, e[0].z, e[1].z)

	# 		contour_lines = []

	# 		for e in edges:
	# 			add_to_contour = True

	# 			if (e[0].z > min_z) or (e[1].z > min_z):
	# 				add_to_contour = False

	# 			if add_to_contour:
	# 				contour_lines.append(e)

	# 		points_data = []
	# 		edges_data = []

	# 		for contour in contour_lines:
	# 			for point in contour:
	# 				points_data.append(point)
	# 				# points_data.append(true_coord)
	# 				# print('coords', true_coord, point)

	# 			if points_data:
	# 				edges_data.append([len(points_data) -2, len(points_data) -1])


	# 		points_data = [v.co for v in obj.data.vertices]
	# 		edges_data = []


	# 		# print([v.co for v in obj.data.vertices])



	# 		# https://wiki.blender.org/index.php/Dev:Py/Scripts/Cookbook/Code_snippets/Three_ways_to_create_objects
	# 		meshName = 'mesh' + str(obj_count)
	# 		obName = 'ob' + str(obj_count)
	# 		me = bpy.data.meshes.new(meshName)
	# 		ob = bpy.data.objects.new(obName, me)
	# 		scn = bpy.context.scene
	# 		scn.objects.link(ob)

	# 		me.from_pydata(points_data, edges_data, [])
	# 		me.update()
	# 		print('new contour')

	# 		new_contours.append(ob)

	# 		print("\n" * 5)

	# 		obj_count += 1

	# 		Slicer.to_object()
	# 		bpy.ops.object.delete()
		
	# 	for c in new_contours:
	# 		self.objects.append(c)

if __name__ == "__main__":
	register()