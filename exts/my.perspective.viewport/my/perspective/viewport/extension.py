from asyncio.windows_events import NULL
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
from .userinterface import ButtonSelectionWindow, InitialWindow

DEFAULT_VIEWPORT_NAME = '/exts/my.perspective.viewport/startup/windowName'
DEFAULT_VIEWPORT_NO_OPEN = '/exts/my.perspective.viewport/startup/disableWindowOnLoad'


# Any class derived from `omni.ext.IExt` in top level module (defined in `python.modules` of `extension.toml`) will be
# instantiated when extension gets enabled and `on_startup(ext_id)` will be called. Later when extension gets disabled
# on_shutdown() is called.
class MyExtension(omni.ext.IExt):
    # ext_id is current extension id. It can be used with extension manager to query additional information, like where
    # this extension is located on filesystem.

    __all__ = ['ViewportExtension']

    WINDOW_NAME = "Viewport Perspective"
    MENU_PATH = f"Window/{WINDOW_NAME}"

    def on_startup(self, ext_id):
        print("[my.perspective.viewport] MyExtension startup")
        self.cam_wrapper = CameraWrapper()
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

        

        self.icon_start_helper(ext_id)
        # self.initial_window()

      
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

        self.icon_end_helper()
        self.target_count = 0
        self.cam_wrapper.on_shutdown()

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
                self.initial_window()
                self.cam_wrapper.viewport_api = self.viewport_api

                with self.__window._ViewportWindow__viewport_layers._ViewportLayers__ui_frame:
                    with ui.HStack():
                        # self.view_button = ui.Button("Projections", width = 0, height = 50)
                        # self.view_button.set_mouse_pressed_fn(lambda x, y, a, b, widget=self.view_button: self.menu_helper(x, y, a, b, widget))
                        self.slider()
                   
                

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
    
    
    def icon_start_helper(self, ext_id):
        ext_path = omni.kit.app.get_app().get_extension_manager().get_extension_path(ext_id)
        icon_path = os.path.join(ext_path, "icons")

        self._toolbar = omni.kit.window.toolbar.get_instance()

        self._zoning_envolope = SimpleToolButton(name="Zoning Envolope",
            tooltip="Zoning Envolope",
            icon_path=f"{icon_path}/envolope_icon.png",
            icon_checked_path=f"{icon_path}/envolope_icon.png",
            hotkey=Key.Z,
            toggled_fn=lambda c: carb.log_warn(f"Example button toggled {c}"))

        self._projection_icon = SimpleToolButton(name="Projection",
            tooltip="Top/ Front/ Side/ Iso",
            icon_path=f"{icon_path}/projection_icon.png",
            icon_checked_path=f"{icon_path}/projection_icon.png",
            hotkey=Key.P,
            toggled_fn=lambda c: carb.log_warn(f"Example button toggled {c}"))

        self._camera_icon = SimpleToolButton(name="Texture/ Strretview",
            tooltip="Not Decided",
            icon_path=f"{icon_path}/camera_icon.png",
            icon_checked_path=f"{icon_path}/camera_icon.png",
            hotkey=Key.T,
            toggled_fn=lambda c: carb.log_warn(f"Example button toggled {c}"))
        
        self._sun_study = SimpleToolButton(name="Sun Study",
            tooltip="Sun Study",
            icon_path=f"{icon_path}/sun_icon.png",
            icon_checked_path=f"{icon_path}/sun_icon.png",
            hotkey=Key.S,
            toggled_fn=lambda c: carb.log_warn(f"Example button toggled {c}"))
        
        self._wind_sim = SimpleToolButton(name="Wind Simulation",
            tooltip="Wind Simulation",
            icon_path=f"{icon_path}/wind_icon.png",
            icon_checked_path=f"{icon_path}/wind_icon.png",
            hotkey=Key.W,
            toggled_fn=lambda c: carb.log_warn(f"Example button toggled {c}"))


        self._toolbar.add_widget(self._zoning_envolope, 800)
        self._toolbar.add_widget(self._projection_icon, 900)
        self._toolbar.add_widget(self._camera_icon, 1000)
        self._toolbar.add_widget(self._sun_study, 1100)
        self._toolbar.add_widget(self._wind_sim, 1200)

    def icon_end_helper(self):
        self._toolbar.remove_widget(self._zoning_envolope)
        self._toolbar.remove_widget(self._projection_icon)
        self._toolbar.remove_widget(self._camera_icon)
        self._toolbar.remove_widget(self._sun_study)
        self._toolbar.remove_widget(self._wind_sim)
        self._zoning_envolope.clean()
        self._zoning_envolope = None
        self._projection_icon.clean()
        self._projection_icon = None
        self._camera_icon.clean()
        self._camera_icon = None
        self._sun_study.clean()
        self._sun_study = None
        self._wind_sim.clean()
        self._wind_sim = None
        self._toolbar = None

    def get_selected_prims(self):
        context = omni.usd.get_context()
        stage = context.get_stage()
        prims = [stage.GetPrimAtPath(m) for m in context.get_selection().get_selected_prim_paths()]
        return prims

    def ortho_window_helper(self):
        buttons = { 
        "Top": lambda: self.cam_wrapper.ortho_helper('top', self.current_target),
        "Front":lambda: self.cam_wrapper.ortho_helper('front', self.current_target),
        "Right":lambda: self.cam_wrapper.ortho_helper('right', self.current_target)
        }

        self.ortho_window = ButtonSelectionWindow("Orthographic Selection",buttons)
        self.ortho_window.set_up_window()

    def iso_window_helper(self):

        buttons = {
        "NE": lambda:self.cam_wrapper.iso_helper("NE", self.current_target),
        "NW":lambda:self.cam_wrapper.iso_helper("NW", self.current_target),
        "SE":lambda:self.cam_wrapper.iso_helper("SE", self.current_target),
        "SW":lambda:self.cam_wrapper.iso_helper("SW", self.current_target)
        }

        self.iso_window = ButtonSelectionWindow("Isometric Selection",buttons)
        self.iso_window.set_up_window()

    def add_target_helper(self):
        mesh_path = os.path.join(self.ext_path, "mesh")
        try:
            omni.usd.get_prim_at_path(Sdf.Path('/World/target' + str(self.target_count))).IsDefined()
            
        except:
            omni.kit.commands.execute('CreateReferenceCommand',
                usd_context=omni.usd.get_context(),
                path_to='/World/target' + str(self.target_count),
                asset_path=f"{mesh_path}/gimble.usd",
                instanceable=True)

        try:
            camera_pos = omni.usd.get_prim_at_path(self.viewport_api.camera_path).GetAttribute('xformOp:transform').Get()[3]
            print(camera_pos)
        except:
            camera_pos = omni.usd.get_prim_at_path(self.viewport_api.camera_path).GetAttribute('xformOp:translate').Get()
            print(camera_pos)

        # omni.kit.commands.execute('ChangeProperty',
        #     prop_path='/World/target' + str(self.target_count)+'.xformOp:translate',
        #     value=Gf.Vec3f(camera_pos[0], camera_pos[1], camera_pos[2]),
        #     prev=None)


        omni.kit.commands.execute('TransformPrimCommand',
            path='/World/target' + str(self.target_count),
            old_transform_matrix=Gf.Matrix4d(1.0, 0.0, 0.0, 0.0,
                    0.0, 1.0, 0.0, 0.0,
                    0.0, 0.0, 1.0, 0.0,
                    0.0, 0.0, 0.0, 1.0),
            new_transform_matrix=Gf.Matrix4d(1.0, 0.0, 0.0, 0.0,
                    0.0, 1.0, 0.0, 0.0,
                    0.0, 0.0, 1.0, 0.0,
                    camera_pos[0], camera_pos[1], camera_pos[2], 1.0),
            time_code=Usd.TimeCode.Default(),
            had_transform_at_key=False)


        self.current_target = omni.usd.get_prim_at_path(Sdf.Path('/World/target' + str(self.target_count)))
        print(self.current_target)
        
        self.target_count += 1
        self.proj_slider.enabled = True

    def slider(self):
        with ui.ZStack():
            self.proj_slider = ui.IntSlider(min=0, max=2, style = {"font_size": 7}, enabled = False)
            self.prev_ind = self.proj_slider.model.get_value_as_int()
            self.proj_slider.set_mouse_released_fn(lambda x, y, a, b: self.slider_helper(x, y, a, b))
            with ui.HStack():
                self.label0 = ui.Label("orth", alignment = ui.Alignment.CENTER_TOP, style = {"color":0xFF000000} )
                self.label1 =ui.Label("persp", alignment = ui.Alignment.CENTER_TOP)
                self.label2 =ui.Label("iso", alignment = ui.Alignment.CENTER_TOP)

    def slider_helper(self, x, y, a, b):
            widget=self.proj_slider
            self.index = widget.model.get_value_as_int()
            black=0xFFDDDDDD
            white=0xFF000000

            if self.index == 0:
                if self.prev_ind == 0:
                    self.label0.set_style({"color":black})
                    self.ortho_window = None
                elif self.prev_ind == 1:
                    self.label1.set_style({"color":black})
                elif self.prev_ind == 2:
                    self.label2.set_style({"color":black})
                    self.iso_window = None
                
                self.label0.set_style({"color":white})
                self.prev_ind = 0
                self.ortho_window_helper()
            
            if self.index == 1:
                if self.prev_ind == 0:
                    self.label0.set_style({"color":black})
                    self.ortho_window = None
                elif self.prev_ind == 1:
                    self.label1.set_style({"color":black})
                elif self.prev_ind == 2:
                    self.label2.set_style({"color":black})
                    self.iso_window = None
                
                self.label1.set_style({"color":white})
                self.prev_ind = 1
                self.cam_wrapper.orth_to_persp()
            
            if self.index == 2:
                if self.prev_ind == 0:
                    self.label0.set_style({"color":black})
                    self.ortho_window = None
                elif self.prev_ind == 1:
                    self.label1.set_style({"color":black})
                elif self.prev_ind == 2:
                    self.label2.set_style({"color":black})
                    self.iso_window = None
                
                self.label2.set_style({"color":white})
                self.prev_ind = 2
                self.iso_window_helper()

    def initial_window(self):
        buttons = {
            "Create Camera":(False, "Create", self.cam_wrapper.create_cam_helper), 
            "Load Camera":(False, "Load",self.combobox_helper), 
            "Select Camera":(True, "Select", self.combobox_selection_helper), 
            "Set Target": (False, "Set",self.add_target_helper)
        }
        self.init_window = InitialWindow('Projection Views with Cameras', buttons)
        self.combobox = self.init_window.set_up_window()[0]

    def combobox_helper(self):
        self.cameras = self.cam_wrapper.camera_sel(omni.usd.get_context().get_stage().GetDefaultPrim().GetChildren())
        print(self.cameras)
        for option in self.combobox.model.get_item_children():
            self.combobox.model.remove_item(option)
        for c in self.cameras:
            self.combobox.model.append_child_item(None, ui.SimpleStringModel(str(c.GetPath())))

    def combobox_selection_helper(self):
        cam_index = self.combobox.model.get_item_value_model().get_value_as_int()
        self.cam_wrapper.cam_sel_helper(self.cameras[cam_index])
        print(str(self.cameras[cam_index].GetPath()))



