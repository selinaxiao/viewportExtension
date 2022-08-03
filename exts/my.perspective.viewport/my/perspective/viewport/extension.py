# from my.perspective.viewport.paint_tool import Paint_tool
import omni.ext
import omni.ui as ui
from pxr import Sdf, Gf, UsdGeom, Usd
from omni.ui import Workspace
from omni.kit.viewport.window.window import ViewportWindow
from omni.kit.viewport.window.dragdrop.usd_file_drop_delegate import UsdFileDropDelegate
from omni.kit.viewport.window.dragdrop.usd_prim_drop_delegate import UsdShadeDropDelegate
from omni.kit.viewport.window.dragdrop.material_file_drop_delegate import MaterialFileDropDelegate
import carb
import os
from carb.input import KeyboardInput as Key
from .camera import CameraWrapper
from .userinterface import ButtonSelectionWindow, IconWindow, SideIconWrapper, SliderWrapper
# from .paint_tool import PaintToolInContext
from .adobe import AdobeInterface

import os 
import subprocess




# from omni.ui._ui import CanvasFrame

# from omni.paint.system.core import extension
DEFAULT_VIEWPORT_NAME = '/exts/my.perspective.viewport/startup/windowName'
DEFAULT_VIEWPORT_NO_OPEN = '/exts/my.perspective.viewport/startup/disableWindowOnLoad'


# Any class derived from `omni.ext.IExt` in top level module (defined in `python.modules` of `extension.toml`) will be
# instantiated when extension gets enabled and `on_startup(ext_id)` will be called. Later when extension gets disabled
# on_shutdown() is called.
class MyExtension(omni.ext.IExt):
    # ext_id is current extension id. It can be used with extension manager to query additional information, like where
    # this extension is located on filesystem.

    __all__ = ['ViewportExtension']

    WINDOW_NAME = "Sketch In Context"
    MENU_PATH = f"Window/{WINDOW_NAME}"

    def on_startup(self, ext_id):
        print("[my.perspective.viewport] MyExtension startup")
        self.cam_wrapper = CameraWrapper()

        self.__window = None
        self.__registered = None

        settings = carb.settings.get_settings()
        open_window = not settings.get(DEFAULT_VIEWPORT_NO_OPEN)
        Workspace.set_show_window_fn(self.WINDOW_NAME, lambda b: self.__show_window(None, b))
        
        if open_window:
            Workspace.show_window(self.WINDOW_NAME)
            if self.__window:
                self.dock_with_window(self.WINDOW_NAME, 'Viewport', omni.ui.DockPosition.SAME)
        open_window = True if (open_window and self.__window) else False
        editor_menu = omni.kit.ui.get_editor_menu()

        if editor_menu:
            self.__menu = editor_menu.add_item(self.MENU_PATH, self.__show_window, toggle=True, value=open_window)
        
        self.__registered = self.__register_scenes()
        self.__default_drag_handlers = (
            UsdFileDropDelegate('/persistent/app/viewport/previewOnPeek'),
            UsdShadeDropDelegate(),
            MaterialFileDropDelegate()
        )

        self._pushed_menu = ui.Menu("Pushed menu")
        self.target_count = 0
        self.cam_count = 0
        self.plane_count = 0
        self.current_plane = None
        self.current_target = None   
        self.ortho_window = None
        self.iso_window = None
        self.ext_path = omni.kit.app.get_app().get_extension_manager().get_extension_path(ext_id)
        self.icon_wrapper = SideIconWrapper(self.ext_path)
        self.icon_start_helper(self.ext_path)
        self.ext_id = ext_id
        self.screenshot_window = AdobeInterface()

        

       


        # self.screenshot_window._window.visible = False
        # self.paint_tool = PaintToolInContext(ext_id)
        # self.paint_tool._create_window()

        # CanvasFrame()

        # extension.PaintCoreExtension.on_startup()
 
        # self.proj_slider_wrapper.set_up_slider()

    def on_shutdown(self):
        print("[my.perspective.viewport] MyExtension shutdown")
        self.target_count = 0
        self.plane_count = 0
        
        self.cam_wrapper.on_shutdown()
        self.icon_wrapper.shut_down_icons()
        self.screenshot_window.change_window_visibility(False)

        Workspace.set_show_window_fn(self.WINDOW_NAME, None)
        self.__show_window(None, False)
        self.__menu = None
        self.__default_drag_handlers = None
        if self.__registered:
            self.__unregister_scenes(self.__registered)
            self.__registered = None

        # from omni.kit.viewport.window.events import set_ui_delegate
        # set_ui_delegate(None)

        # self.paint_tool.paint_tool_shutdown()

        
        # extension.PaintCoreExtension.on_shutdown()
    
    def dock_with_window(self, window_name: str, dock_name: str, position: omni.ui.DockPosition, ratio: float = 1):
        async def wait_for_window():
            dockspace = Workspace.get_window(dock_name)
            window = Workspace.get_window(window_name)
            if (window is None) or (dockspace is None):
                frames = 3
                while ((window is None) or (dockspace is None)) and frames:
                    await omni.kit.app.get_app().next_update_async()
                    dockspace = Workspace.get_window(dock_name)
                    window = Workspace.get_window(window_name)
                    frames = frames - 1

            if window and dockspace:
                window.deferred_dock_in(dock_name)
                # This genrally works in a variety of cases from load, re-load, and save extesnion .py file reload
                # But it depends on a call order in omni.ui and registered selected_in_dock and dock_changed callbacks.
                await omni.kit.app.get_app().next_update_async()
                updates_enabled = window.docked and window.selected_in_dock
                window.viewport_api.updates_enabled = updates_enabled

        import asyncio
        asyncio.ensure_future(wait_for_window())
        

    def __set_menu(self, value):
        """Set the menu to create this window on and off"""
        editor_menu = omni.kit.ui.get_editor_menu()
        if editor_menu:
            editor_menu.set_value(self.MENU_PATH, value)

    def __show_window(self, menu, visible):
        self.__set_menu(visible)

        if visible:
            if not self.__window:
                def visiblity_changed(visible):
                    self.__set_menu(visible)
                    if not visible:
                        self.__show_window(None, False)
                self.__window = ViewportWindow(self.WINDOW_NAME)
                self.__window.set_visibility_changed_fn(visiblity_changed)
                
                self.viewport_api = self.__window._ViewportWindow__viewport_layers._ViewportLayers__viewport._ViewportWidget__vp_api
                self.proj_window_helper()
                
                self.cam_wrapper.viewport_api = self.viewport_api
                labels_list = [
                    ["Ortho", self.ortho_window_helper, self.ortho_remover],
                    ["Persp", self.persp_window_helper, self.persp_remover],
                    ["Iso", self.iso_window_helper, self.iso_remover], 
                    ["Dim", self.dim_window_helper, self.dim_remover]
                ]
                self.proj_slider_wrapper = SliderWrapper(labels_list)

                with self.__window._ViewportWindow__viewport_layers._ViewportLayers__ui_frame:
                    self.proj_slider_wrapper.set_up_slider()
                    # omni.kit.commands.execute('CreateMeshPrimWithDefaultXform',
                    #         prim_type='Plane')
                    # painter=Paint_tool()
                    # painter.add_layer_helper()


        elif self.__window:
            self.__window.set_visibility_changed_fn(None)
            self.__window.destroy()
            self.__window = None
        
    def __register_scenes(self):
        def _is_extension_loaded(extension_name: str) -> bool:
            import omni.kit
            def is_ext(ext_id: str) -> bool:
                ext_name = ext_id.split("-")[0]
                return ext_name == extension_name

            for ext in omni.kit.app.get_app_interface().get_extension_manager().get_extensions():
                if is_ext(ext['id']):
                    return ext['enabled']
            return False

        # Register all of the items that use omni.ui.scene to add functionality
        from omni.kit.viewport.registry import RegisterScene
        from omni.kit.viewport.window.scene.scenes import SimpleGrid, SimpleOrigin, CameraAxis
        registered = [
            RegisterScene(SimpleOrigin, 'omni.kit.viewport.window.scene.SimpleOrigin'),
            RegisterScene(CameraAxis, 'omni.kit.viewport.window.scene.CameraAxis')
        ]

        # Register items to control legacy drawing if it is loaded and available
        if _is_extension_loaded('omni.kit.viewport.legacy_gizmos'):
            from omni.kit.viewport.window.scene.legacy import LegacyGridScene, LegacyLightScene, LegacyAudioScene
            registered += [
                RegisterScene(LegacyGridScene, 'omni.kit.viewport.window.scene.LegacyGrid'),
                RegisterScene(LegacyLightScene, 'omni.kit.viewport.window.scene.LegacyLight'),
                RegisterScene(LegacyAudioScene, 'omni.kit.viewport.window.scene.LegacyAudio')
            ]
        else:
            # Otherwise use omni.scene.ui Grid
            registered += [
                RegisterScene(SimpleGrid, 'omni.kit.viewport.window.scene.SimpleGrid')
            ]

        from omni.kit.viewport.window.manipulator.context_menu import ViewportClickFactory
        registered += [
            RegisterScene(ViewportClickFactory, 'omni.kit.viewport.window.manipulator.ContextMenu')
        ]

        from omni.kit.viewport.window.manipulator.object_click import ObjectClickFactory
        registered += [
            RegisterScene(ObjectClickFactory, 'omni.kit.viewport.window.manipulator.ObjectClick')
        ]

        # Register the Selection manipulator (if available)
        from omni.kit.viewport.window.manipulator.selection import SelectionManipulatorItem
        if SelectionManipulatorItem:
            registered += [
                RegisterScene(SelectionManipulatorItem, 'omni.kit.viewport.window.manipulator.Selection')
            ]

        # Register the Camera manipulator (if available)
        from omni.kit.viewport.window.manipulator.camera import ViewportCameraManiulatorFactory
        if ViewportCameraManiulatorFactory:
            registered += [
                RegisterScene(ViewportCameraManiulatorFactory, 'omni.kit.viewport.window.manipulator.Camera')
            ]

        from omni.kit.viewport.registry import RegisterViewportLayer

        # Register the HUD stats
        # XXX Can't do this in testing as the stats will not be consistent across launches
        if not carb.settings.get_settings().get('/exts/omni.kit.test/runTestsAndQuit'):
            from omni.kit.viewport.window.stats import ViewportStatsLayer
            registered.append(RegisterViewportLayer(ViewportStatsLayer, 'omni.kit.viewport.window.ViewportStats'))

        # Finally register the ViewportSceneLayer
        from omni.kit.viewport.window.scene.layer import ViewportSceneLayer
        registered.append(RegisterViewportLayer(ViewportSceneLayer, 'omni.kit.viewport.window.SceneLayer'))
        return registered

    def __unregister_scenes(self, registered):
        for item in registered:
            try:
                item.destroy()
            except Exception:
                pass



    def icon_start_helper(self, ext_path):
        """
        Add five icons on the side: Zoning envolope, Projection, Texture, Sunstudy, Wind Simulation
        """
        icon_buttons = [
            ("Zoning Envolope", "Zoning Envolope", "envelope.png", "envelope.png", Key.Z, lambda c: carb.log_warn(f"Example button toggled {c}")), 
            ("Projection", "Projection: Ortho/ Persp/ Iso", "Camera.png", "Camera.png", Key.P, lambda c: self.proj_icon_helper(c)), 
            ("Streetview", "Streetview", "VR.png", "VR.png", Key.T, lambda c: carb.log_warn(f"Example button toggled {c}")),
            ("Sun Study", "Sun Study", "sun.png", "sun.png", Key.S, lambda c: carb.log_warn(f"Example button toggled {c}")),
            ("Acoustic Analysis", "Acoustic Analysis", "Acoustic.png", "Acoustic.png",Key.W, lambda c: carb.log_warn(f"Example button toggled {c}")),
            ("test", "test", "Acoustic.png", "Acoustic.png", Key.E, lambda c: self.quick())

        ]

        self.icon_wrapper = SideIconWrapper(ext_path, "icons", icon_buttons)
        self.icon_wrapper.set_up_icons()

    def icon_end_helper(self):
        """"
        clear up five icons on the side
        """
        self.icon_wrapper.shut_down_icons()

    def get_selected_prims(self):
        """
        Get the currently selected prims in the scene
        """
        context = omni.usd.get_context()
        stage = context.get_stage()
        prims = [stage.GetPrimAtPath(m) for m in context.get_selection().get_selected_prim_paths()]
        return prims

    def ortho_remover(self):
        self.ortho_window=None
        self.screenshot_window.change_window_visibility(False)

    def iso_remover(self):
        self.iso_window=None
        self.screenshot_window.change_window_visibility(False)

    def persp_remover(self):
        self.persp_window = None
        self.screenshot_window.change_window_visibility(False)

    def dim_remover(self):
        self.dim_window = None
        self.screenshot_window.change_window_visibility(False)
        print("remove dim center")
        try:
            omni.kit.commands.execute('DeletePrims',
                paths=['/World/Dimetric_center'])
        except:
            pass


    def ortho_window_helper(self):
        """
        get window for orthographic projection
        Contains three options for orthographic projection: top, front, right
        Updating ortho window and ortho slider
        """
        buttons = ({ 
        "Top": lambda: self.cam_wrapper.ortho_helper('top', self.current_plane, self.current_target),
        "Front":lambda: self.cam_wrapper.ortho_helper('front', self.current_plane, self.current_target),
        "Back" : lambda: self.cam_wrapper.ortho_helper('back', self.current_plane, self.current_target),
        "Right":lambda: self.cam_wrapper.ortho_helper('right', self.current_plane, self.current_target),
        "Left" : lambda: self.cam_wrapper.ortho_helper('left', self.current_plane, self.current_target)
        }, False)

        self.ortho_window = ButtonSelectionWindow("Orthographic Selection",buttons)
        paint_buttons = self.ortho_window.set_up_window(self.current_plane)[0]
        self.ortho_paint_expt = paint_buttons[0]
        self.ortho_paint_expt.set_mouse_pressed_fn(lambda x, y, a, b: self.screenshot_helper(x, y, a, b))
        # self.ortho_opt = self.ortho_window.ortho_opt
        # self.ortho_paint_end = paint_buttons[1]
    
    def screenshot_helper(self, x, y, a, b):
        print("screenshot window visible")
        print(self.screenshot_window.change_window_visibility(True))

    def iso_window_helper(self):
        """
        get window for isometric projection
        Contains three options for isometric projection: top, front, right
        Updating iso window and iso slider
        """
        buttons = ({
        "NE": lambda:self.cam_wrapper.iso_helper("NE", self.current_plane, self.current_target),
        "NW":lambda:self.cam_wrapper.iso_helper("NW", self.current_plane, self.current_target),
        "SE":lambda:self.cam_wrapper.iso_helper("SE", self.current_plane, self.current_target),
        "SW":lambda:self.cam_wrapper.iso_helper("SW", self.current_plane, self.current_target)
        }, False)

        self.iso_window = ButtonSelectionWindow("Isometric Selection",buttons)
        paint_buttons = self.iso_window.set_up_window(self.current_plane)[0]
        self.iso_paint_expt = paint_buttons[0]
        self.iso_paint_expt.set_mouse_pressed_fn(lambda x, y, a, b: self.screenshot_helper(x, y, a, b))

    def persp_window_helper(self):
        buttons = ({
            "Persp" : lambda:self.cam_wrapper.orth_to_persp(),
            "Orth" : lambda:self.cam_wrapper.persp_to_orth()
        }, False)
        self.persp_window = ButtonSelectionWindow("Perspective Selection",buttons)
        paint_buttons = self.persp_window.set_up_window(self.current_plane)[0]
        self.persp_paint_expt = paint_buttons[0]
        self.persp_paint_expt.set_mouse_pressed_fn(lambda x, y, a, b: self.screenshot_helper(x, y, a, b))
    
    def dim_window_helper(self):
        """
        get window for isometric projection
        Contains three options for isometric projection: top, front, right
        Updating dim window and dim slider
        """
        buttons = ({
        "NE": lambda:self.cam_wrapper.dim_helper("NE", self.current_plane, self.current_target),
        "NW":lambda:self.cam_wrapper.dim_helper("NW", self.current_plane, self.current_target),
        "SE":lambda:self.cam_wrapper.dim_helper("SE", self.current_plane, self.current_target),
        "SW":lambda:self.cam_wrapper.dim_helper("SW", self.current_plane, self.current_target)
        }, True)

        self.dim_window = ButtonSelectionWindow("Dimetric Selection",buttons)
        return_val = self.dim_window.set_up_window(self.current_plane)
        paint_buttons = return_val[0]
        drag = return_val[1]

        self.dim_drag = drag.model.subscribe_value_changed_fn(self.cam_wrapper.drag_helper)
        self.dim_paint_expt = paint_buttons[0]
        self.dim_paint_expt.set_mouse_pressed_fn(lambda x, y, a, b: self.screenshot_helper(x, y, a, b))

    def add_target_helper(self):
        """
        Add a target at the center of the current plane in the world
        """
        
        if self.current_plane is None:
            return 
        

        mesh_path = os.path.join(self.ext_path, "mesh")
        try:
            omni.usd.get_prim_at_path(Sdf.Path('/World/target' + str(self.target_count))).IsDefined()
            
        except:
            omni.kit.commands.execute('CreateReferenceCommand',
                usd_context=omni.usd.get_context(),
                path_to='/World/target' + str(self.target_count),
                asset_path=f"{mesh_path}/gimble.usd",
                instanceable=True)

        plane_pos = self.current_plane.GetAttribute('xformOp:translate').Get()
        print(plane_pos)
        plane_path = self.current_plane.GetPath()

        omni.kit.commands.execute('TransformPrimCommand',
            path='/World/target' + str(self.target_count),
            old_transform_matrix=Gf.Matrix4d(1.0, 0.0, 0.0, 0.0,
                    0.0, 1.0, 0.0, 0.0,
                    0.0, 0.0, 1.0, 0.0,
                    0.0, 0.0, 0.0, 1.0),
            new_transform_matrix=Gf.Matrix4d(1.0, 0.0, 0.0, 0.0,
                    0.0, 1.0, 0.0, 0.0,
                    0.0, 0.0, 1.0, 0.0,
                    plane_pos[0], plane_pos[1], plane_pos[2], 1.0),
            time_code=Usd.TimeCode.Default(),
            had_transform_at_key=False)

        omni.kit.commands.execute('ChangeProperty',
            prop_path=Sdf.Path('/World/target' + str(self.target_count)+'.xformOp:scale'),
            value=Gf.Vec3f(0.05, 0.05, 0.05),
            prev=Gf.Vec3f(1.0, 1.0, 1.0))

        omni.kit.commands.execute('MovePrim',
            path_from='/World/target' + str(self.target_count),
            path_to=f'{plane_path}/target' + str(self.target_count))


        self.current_target = omni.usd.get_prim_at_path(Sdf.Path(f'{plane_path}/target' + str(self.target_count)))
        print(self.current_target)
        
        self.target_count += 1
        self.proj_slider_wrapper.slider.enabled = True

    def add_plane_helper(self):
        """
        Add a plane in the world on camera's forward direction
        where teh camera is the current viewport api camera
        """
        forward_vec = self.cam_wrapper.forward_vec()
        cam_position = self.cam_wrapper.cam_position()
        dist = 200

        plane_count = f'0{self.plane_count}' if self.plane_count <10 else str(self.plane_count)
        plane_count = '' if plane_count == '00' else f'_{plane_count}'
        try:
            omni.usd.get_prim_at_path(Sdf.Path(f'/World/Plane{plane_count}')).IsDefined()
        except:
            omni.kit.commands.execute('CreateMeshPrimWithDefaultXform',
                prim_type='Plane', prim_path = f'/World/Plane{plane_count}')

        omni.kit.commands.execute('ChangeProperty',
            prop_path=Sdf.Path(f'/World/Plane{plane_count}.xformOp:translate'),
            value=Gf.Vec3f(cam_position[0]+forward_vec[0]*dist, cam_position[1]+forward_vec[1]*dist, cam_position[2]+forward_vec[2]*dist),
            prev=None)

        omni.kit.commands.execute('ChangeProperty',
            prop_path=Sdf.Path(f'/World/Plane{plane_count}.xformOp:scale'),
            value=Gf.Vec3f(10, 10, 10),
            prev=Gf.Vec3f(1.0, 1.0, 1.0))
        
        self.plane_count+=1
        
        self.current_plane = omni.usd.get_prim_at_path(Sdf.Path(f'/World/Plane{plane_count}'))
        for child in self.current_plane.GetChildren():
            omni.kit.commands.execute('DeletePrims',
	        paths=[child.GetPath()])
        self.proj_slider_wrapper.slider.enabled = True

    def proj_window_helper(self):
        """
        create a window for projection icon
        contains camera functions, plane functions, and target functions
        """
        buttons = {
            "Camera":[
                ("Create Camera",False, "Create", self.cam_wrapper.create_cam_helper), 
                ("Load Camera",False, "Load",self.cam_combobox_helper), 
                ("Select Camera",True, "Select", self.cam_combobox_selection_helper)
                ], 

            "Plane":[
                ("Set GroundPlane",False, "Set",self.add_plane_helper), 
                ("Load Ground Plane",False, "Load",self.plane_combobox_helper), 
                ("Select Ground Plane",True, "Select", self.plane_combobox_selection_helper)       
                ], 
            "Target":[
                ("Add Target", False, "Add", self.add_target_helper), 
                ("Load Target",False, "Load",self.target_combobox_helper), 
                ("Select Target",True, "Select", self.target_combobox_selection_helper)
            ]
        }
        self.proj_window = IconWindow('Projection Views with Cameras', buttons)
        comboboxes = self.proj_window.set_up_window()
        self.cam_combobox = comboboxes[0]
        self.plane_combobox = comboboxes[1]
        self.target_combobox = comboboxes[2]

    def cam_combobox_helper(self):
        """
        Add all the cameras under stage as child items of the combobox
        """
        self.cameras = self.cam_wrapper.camera_sel(omni.usd.get_context().get_stage().GetDefaultPrim().GetChildren())
        print(self.cameras)
        for option in self.cam_combobox.model.get_item_children():
            self.cam_combobox.model.remove_item(option)
        for c in self.cameras:
            self.cam_combobox.model.append_child_item(None, ui.SimpleStringModel(str(c.GetPath())))

    def plane_sel(self, list):
        planes = []
        for p in list:
            index = str(p.GetPath()).rfind('/')
            if "Plane" == str(p.GetPath())[index+1:index+6]:
                planes.append(p)
            if p.GetChildren():
                planes.extend(self.plane_sel(p.GetChildren()))
        return planes
    
    def plane_combobox_helper(self):
        self.planes = self.plane_sel(omni.usd.get_context().get_stage().GetDefaultPrim().GetChildren())
        for option in self.plane_combobox.model.get_item_children():
            self.plane_combobox.model.remove_item(option)
        for p in self.planes:
            self.plane_combobox.model.append_child_item(None, ui.SimpleStringModel(str(p.GetPath())))

    def cam_combobox_selection_helper(self):
        """
        Feed in camera into the viewport api to give the viewport camera view
        """
        cam_index = self.cam_combobox.model.get_item_value_model().get_value_as_int()
        print(cam_index)
        self.cam_wrapper.cam_sel_helper(self.cameras[cam_index])

    def target_sel(self, list):
        targets = []
        for t in list:
            index = str(t.GetPath()).rfind('/')
            if "target" == str(t.GetPath())[index+1:index+7]:
                targets.append(t)
            if t.GetChildren():
                targets.extend(self.target_sel(t.GetChildren()))
        return targets

    def target_combobox_helper(self):
        self.targets = self.target_sel(self.current_plane.GetChildren())
        for option in self.target_combobox.model.get_item_children():
            self.target_combobox.model.remove_item(option)
        for t in self.targets:
            self.target_combobox.model.append_child_item(None, ui.SimpleStringModel(str(t.GetPath())))

    def plane_combobox_selection_helper(self):
        plane_index = self.plane_combobox.model.get_item_value_model().get_value_as_int()
        self.current_plane = self.planes[plane_index]
        self.proj_slider_wrapper.slider.enabled = True
        print(self.current_plane.GetAttribute('primvars:displayOpacity'))
        #need to find how to create a VtArray to change the opacity
    
    def target_combobox_selection_helper(self):
        target_index = self.target_combobox.model.get_item_value_model().get_value_as_int()
        self.current_target = self.targets[target_index]
        self.proj_slider_wrapper.slider.enabled = True

    def proj_slider_helper(self, x, y, a, b, widget: ui.FloatSlider):
        """
        For the FloatSlider passed in, take its value and adjust the projection aperture
        """
        value = widget.model.get_value_as_float()
        if value>0:
            self.cam_wrapper.change_aperture(value)
        elif value < 0:
            self.cam_wrapper.change_aperture(abs(1/value))
        else:
            pass
    
    def proj_icon_helper(self, c):
        """
        helper funciton for the projection icon
        when the icon is toggled, set the projection window, slider, and labels for the slider visible. 
        """
        self.proj_window.window_object.visible = c
        self.proj_slider_wrapper.set_label_visibility(c)

    # def ortho_paint_start_helper(self, option):
    #     if option == "Top":

    def quick(self,image = "C:\\Users\\LabUser\\Pictures\\OmniBeehive\\Fun.png"):
        # os.system('cmd /k "cd C:\Program Files\Adobe\Adobe Photoshop 2022"')
        # os.system('cmd /k "Photoshop.exe --open "C:\\Users\\LabUser\\Pictures\\OmniBeehive\\Fun.png""')
        # FNULL = open(os.devnull,'w')
        # assert os.path.isfile(image)
        # args = f"C:\\Program Files\\Adobe\\Adobe Photoshop 2022\\Photoshop.exe --open {image}"
        # subprocess.call( args,stdout=FNULL,stderr=FNULL, shell=False)
        ##HOW TO SET RESOLUTION
        # self.__window.viewport_api._viewport_texture._ViewportTexture__setup_resolution((3840,2160)
        test = self.__window._ViewportWindow__viewport_layers._ViewportLayers__viewport.get_instances().gi_frame.f_trace
        
        # _ViewportWindow__viewport_layers
        print('~'*30)
        print(dir(self.__window._ViewportWindow__viewport_layers._ViewportLayers__viewport.get_instances()))
        print('~'*30)
        print(test)
        print(dir(test))
       
        # #set and get resolution
        # test._ViewportTexture__setup_resolution((1920,1080))
        # print(test.resolution)

        # # import inspect 
        # # print(inspect.getattr_static(test))

        # print(test.frame_info,type(test.frame_info))

 
        

        
