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