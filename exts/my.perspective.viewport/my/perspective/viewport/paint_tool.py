from omni.kit.widgets.custom import WindowExtension
from omni.paint.system.ui.paint_tool import PaintToolWindow
import carb

EXTENSION_NAME = "Paint In Context"

g_singleton = None

class PaintToolInContext:
    def __init__(self, ext_id):
        WindowExtension.on_startup(
            self,
            menu_path=f"Window/{EXTENSION_NAME}",
            appear_after="Material Mapper",
            use_editor_menu=carb.settings.get_settings().get("/exts/omni.paint.system.ui/use_editor_menu"),
        )

        global g_singleton
        g_singleton = self
    
    def paint_tool_shutdown(self):
        WindowExtension.on_shutdown(self)
        global g_singleton
        g_singleton = None

    def _create_window(self):
        return PaintToolWindow()

    def get_paint_tool(self):
        return self._window


def get_instance():
    return g_singleton

# from omni.paint.system.core import extension
import omni.ui as ui
import omni.kit.commands
import omni.kit.commands
from pxr import Gf, Sdf
from .userinterface import  IconWindow
from .camera import CameraWrapper
# from my.perspective.viewport.extension import MyExtension


class Paint_tool(omni.ext.IExt):
    def __init__(self) -> None:
        pass
    def add_layer_helper(self):
        omni.kit.commands.execute('CreateMeshPrimWithDefaultXform',
            prim_type='Plane')

        path=str(self.get_selected_prims())
        omni.kit.commands.execute('ChangeProperty',
            prop_path=path + '.xformOp:translate',
            value=Gf.Vec3f(0,0,0),
            prev=None)

        omni.kit.commands.execute('ChangeProperty',
            prop_path=path + '.xformOp:scale',
            value=Gf.Vec3f(100,100,100),
            prev=None)

        omni.kit.commands.execute('ChangeProperty',
            prop_path=Sdf.Path(path + '.visibility'),
            value='invisible',
            prev=None)

        cam = self.layer_helper()
        print(cam)
        print(dir(cam))
#needs to set invisible plane based on the angle and distance of the camera
#add the plane on top of the z stack
# not related with z stack, z stack is more related with windows, but the plane is in the world scene
        
    def layer_helper(self):
        self.cam_wrapper = CameraWrapper()
        buttons = {
        "Camera":[
            ("Create Camera",False, "Create", self.cam_wrapper.create_cam_helper), 
            ("Load Camera",False, "Load",self.cam_combobox_helper), 
            ("Select Camera",True, "Select", self.combobox_selection_helper)
            ], 

        "Plane":[
            ("Set Plane",False, "Set",self.add_plane_helper)       
            ], 
        "Target":[
            ("Add Target", False, "Add", self.add_target_helper)
        ]
        }
        self.proj_window = IconWindow('Projection Views with Cameras', buttons)
        self.combobox = self.proj_window.set_up_window()[0]
        cam_index = self.combobox.model.get_item_value_model().get_value_as_int()
        return self.cameras[cam_index]

    def get_selected_prims(self):
            """
            Get the currently selected prims in the scene
            """
            
            context = omni.usd.get_context()
            stage = context.get_stage()
            prims = [stage.GetPrimAtPath(m) for m in context.get_selection().get_selected_prim_paths()]
            return prims
