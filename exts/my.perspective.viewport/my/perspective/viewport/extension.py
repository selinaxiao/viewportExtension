from my.perspective.viewport.paint_tool import Paint_tool
import omni.ext
import omni.ui as ui
from pxr import Sdf, Gf, UsdGeom, Usd
from omni.ui import Workspace
from  omni.kit.viewport.window.window import ViewportWindow
from  omni.kit.viewport.window.dragdrop.usd_file_drop_delegate import UsdFileDropDelegate
from  omni.kit.viewport.window.dragdrop.usd_prim_drop_delegate import UsdShadeDropDelegate
from  omni.kit.viewport.window.dragdrop.material_file_drop_delegate import MaterialFileDropDelegate
import carb
import math
from omni.kit.window.toolbar import SimpleToolButton
import os
from carb.input import KeyboardInput as Key
from .camera import CameraWrapper
from .userinterface import ButtonSelectionWindow, IconWindow, SideIconWrapper, SliderWrapper

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


        # labels_list = [
        #     ["Ortho", self.ortho_window_helper(), self.ortho_remover()],
        #     ["Persp", self.cam_wrapper.orth_to_persp(), None],
        #     ["Iso", self.iso_window_helper(),  self.iso_remover()]
        # ]
        # self.proj_slider_wrapper = SliderWrapper(labels_list)

        settings = carb.settings.get_settings()
        default_name = settings.get(DEFAULT_VIEWPORT_NAME) or "Viewport Window"
        self.WINDOW_NAME = default_name
        self.MENU_PATH = f'Window/{default_name}'

        self.__window = None
        self.__registered = None

        self.ext_path = omni.kit.app.get_app().get_extension_manager().get_extension_path(ext_id)

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

        self.icon_wrapper = SideIconWrapper(self.ext_path)
        self.icon_start_helper(self.ext_path)

        # CanvasFrame()

        # extension.PaintCoreExtension.on_startup()
 
        # self.proj_slider_wrapper.set_up_slider()

    def on_shutdown(self):
        print("[my.perspective.viewport] MyExtension shutdown")
        Workspace.set_show_window_fn(self.WINDOW_NAME, None)
        self.__show_window(None, False)
        self.__menu = None
        self.__default_drag_handlers = None
        if self.__registered:
            self.__unregister_scenes(self.__registered)
            self.__registered = None

        from omni.kit.viewport.window.events import set_ui_delegate
        set_ui_delegate(None)


        self.target_count = 0
        self.plane_count = 0
        self.cam_wrapper.on_shutdown()
        self.icon_wrapper.shut_down_icons()
        # extension.PaintCoreExtension.on_shutdown()

    def dock_with_window(self, window_name: str, dock_name: str, position: omni.ui.DockPosition, ratio: float = 1):
        async def wait_for_window():
            dockspace = Workspace.get_window(dock_name)
            print(window_name)
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
                # def visiblity_changed(visible):
                #     self.__set_menu(visible)
                #     if not visible:
                #         self.__show_window(None, False)
                self.__window = ViewportWindow(self.WINDOW_NAME)
                self.__window.set_visibility_changed_fn(self.__set_menu)
                self.viewport_api = self.__window._ViewportWindow__viewport_layers._ViewportLayers__viewport._ViewportWidget__vp_api
                self.proj_window_helper()
                
                self.cam_wrapper.viewport_api = self.viewport_api
                labels_list = [
                    ["Ortho", self.ortho_window_helper, self.ortho_remover],
                    ["Persp", self.cam_wrapper.orth_to_persp, None],
                    ["Iso", self.iso_window_helper, self.iso_remover]
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
            ("Zoning Envolope", "Zoning Envolope", "envolope_icon.png", "envolope_icon.png", Key.Z, lambda c: carb.log_warn(f"Example button toggled {c}")), 
            ("Projection", "Top/ Front/ Side/ Iso", "projection_icon.png", "projection_icon.png", Key.P, lambda c: self.proj_icon_helper(c)), 
            ("Texture/ Streetview", "Not Decided", "camera_icon.png", "camera_icon.png", Key.T, lambda c: carb.log_warn(f"Example button toggled {c}")),
            ("Sun Study", "Sun Study", "sun_icon.png", "sun_icon.png", Key.S, lambda c: carb.log_warn(f"Example button toggled {c}")),
            ("Wind Simulation", "Wind Simulation", "wind_icon.png", "wind_icon.png",Key.W, lambda c: carb.log_warn(f"Example button toggled {c}"))

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

    def iso_remover(self):
        self.iso_window=None

    def ortho_window_helper(self):
        """
        get window for orthographic projection
        Contains three options for orthographic projection: top, front, right
        Updating ortho window and ortho slider
        """
        buttons = ({ 
        "Top": lambda: self.cam_wrapper.ortho_helper('top', self.current_plane, self.current_target),
        "Front":lambda: self.cam_wrapper.ortho_helper('front', self.current_plane, self.current_target),
        "Right":lambda: self.cam_wrapper.ortho_helper('right', self.current_plane, self.current_target)
        },
        {"Zoom in/out": (-5, 5)}
        )

        self.ortho_window = ButtonSelectionWindow("Orthographic Selection",buttons)
        self.ortho_slider = self.ortho_window.set_up_window(self.current_plane)[0]
        
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
        }, 
        {"Zoom in/out": (-5, 5)}
        )

        self.iso_window = ButtonSelectionWindow("Isometric Selection",buttons)
        self.iso_slider = self.iso_window.set_up_window(self.current_plane)[0]

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

        plane_pos = omni.usd.get_prim_at_path(Sdf.Path('/World/Plane')).GetAttribute('xformOp:translate').Get()

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
            path_to='/World/Plane/target' + str(self.target_count))

        self.current_target = omni.usd.get_prim_at_path(Sdf.Path('/World/Plane/target' + str(self.target_count)))
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

    def cam_combobox_helper(self):
        """
        Add all the cameras under stage as child items of the combobox
        """
        self.cameras = self.cam_wrapper.camera_sel(omni.usd.get_context().get_stage().GetDefaultPrim().GetChildren())
        # print(self.cameras)
        for option in self.combobox.model.get_item_children():
            self.combobox.model.remove_item(option)
        for c in self.cameras:
            self.combobox.model.append_child_item(None, ui.SimpleStringModel(str(c.GetPath())))

    def combobox_selection_helper(self):
        """
        Feed in camera into the viewport api to give the viewport camera view
        """
        cam_index = self.combobox.model.get_item_value_model().get_value_as_int()
        self.cam_wrapper.cam_sel_helper(self.cameras[cam_index])
    
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

    
        
