import omni.ext
from omni.kit.widget import viewport
import omni.ui as ui
from omni.kit.widget.viewport import ViewportWidget
from pxr import Sdf, Gf
from omni.ui import Workspace
from  omni.kit.viewport.window.window import ViewportWindow
from  omni.kit.viewport.window.dragdrop.usd_file_drop_delegate import UsdFileDropDelegate
from  omni.kit.viewport.window.dragdrop.usd_prim_drop_delegate import UsdShadeDropDelegate
from  omni.kit.viewport.window.dragdrop.material_file_drop_delegate import MaterialFileDropDelegate
import carb
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

        settings = carb.settings.get_settings()
        default_name = settings.get(DEFAULT_VIEWPORT_NAME) or "Viewport Window"
        self.WINDOW_NAME = default_name
        self.MENU_PATH = f'Window/{default_name}'

        self.__window = None
        self.__registered = None

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
                    # if not visible:
                    #     self.__show_window(None, False)
                self.__window = ViewportWindow(self.WINDOW_NAME)
                self.__window.set_visibility_changed_fn(self.__set_menu)
                with self.__window._ViewportWindow__viewport_layers._ViewportLayers__ui_frame:
                    self.view_button = ui.Button("Projections", width = 0, height = 50)
                    self.view_button.set_mouse_pressed_fn(lambda x, y, a, b, widget=self.view_button: self.menu_helper(x, y, a, b, widget))

                self.viewport_api = self.__window._ViewportWindow__viewport_layers._ViewportLayers__viewport._ViewportWidget__vp_api
                self.viewport_api.camera_path = Sdf.Path('/World/Camera')
                self.viewport_api.projection.SetRotate(Gf.Rotation(Gf.Vec3d(1, 0, 1), 60))
                print(self.viewport_api.projection.ExtractRotationMatrix)

                # print(dir(self.__window.frame))
                self.cam = []
                self.stage = omni.usd.get_context().get_stage()
                prims = self.stage.GetDefaultPrim().GetChildren()
                print(type(prims[2].GetAttribute('size').Get()))
                # print(dir(self.stage.GetDefaultPrim()))
                # for p in prims:
                #     if "Camera" in str(p.GetPath()):
                #         self.cam.append(p)
                # property = self.cam[0].GetProperty('xformOp:rotateYXZ')
                # print(self.cam[0].GetAttribute('projection').Set("perspective"))


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



    
    def get_selected_prims(self):
        context = omni.usd.get_context()
        stage = context.get_stage()
        prims = [stage.GetPrimAtPath(m) for m in context.get_selection().get_selected_prim_paths()]
        return prims




    def menu_helper(self, x, y, button, modifier, widget):
        if button != 0:
            return

        # Reset the previous context popup
        self._pushed_menu.clear()
        with self._pushed_menu:
            ui.MenuItem("Perspective", height = 100)
            with ui.Menu("Orthographic"):
                self.top_orth_proj = ui.MenuItem("Top")
                self.top_orth_proj.set_mouse_pressed_fn(lambda x, y, a, b, widget=self.view_button: self.top_helper(x, y, a, b, widget))
                self.front_orth_proj=ui.MenuItem("Front")
                self.back_orth_proj=ui.MenuItem("Back")
                self.left_orth_proj=ui.MenuItem("Left")
                self.right_orth_proj=ui.MenuItem("Right")
            self.iso = ui.MenuItem("Isometric")
            self.dim = ui.MenuItem("Dimetric")

        # Show it
        self._pushed_menu.show_at(
            (int)(widget.screen_position_x), (int)(widget.screen_position_y + widget.computed_content_height)
        )

        
    def top_helper(self, x, y, button, modifier, widget):
        print('hi')
        # print(len(self.get_selected_prims()[0]))
        if len(self.get_selected_prims()) != 1 or "Camera" not in str(self.get_selected_prims()[0].GetPath()):
            return
        
        self.stage = omni.usd.get_context().get_stage()
        self.prims = self.stage.GetDefaultPrim().GetChildren()
        for p in self.prims:
            if "Camera" in str(p.GetPath()) or "Light" in str(p.GetPath()):
                self.prims.remove(p)

        if self.prims:
            print(self.prims[0])
            max_x = self.prims[0].GetAttribute('xformOp:translate').Get()[0]+self.prims[0].GetAttribute('xformOp:scale').Get()[0]*self.prims[0].GetAttribute('size').Get()
            min_x = self.prims[0].GetAttribute('xformOp:translate').Get()[0]-self.prims[0].GetAttribute('xformOp:scale').Get()[0]*self.prims[0].GetAttribute('size').Get()
            max_y = self.prims[0].GetAttribute('xformOp:translate').Get()[1]+self.prims[0].GetAttribute('xformOp:scale').Get()[1]*self.prims[0].GetAttribute('size').Get()
            min_y = self.prims[0].GetAttribute('xformOp:translate').Get()[1]-self.prims[0].GetAttribute('xformOp:scale').Get()[1]*self.prims[0].GetAttribute('size').Get()
            max_z = self.prims[0].GetAttribute('xformOp:translate').Get()[2]+self.prims[0].GetAttribute('xformOp:scale').Get()[2]*self.prims[0].GetAttribute('size').Get()
            min_z = self.prims[0].GetAttribute('xformOp:translate').Get()[2]-self.prims[0].GetAttribute('xformOp:scale').Get()[2]*self.prims[0].GetAttribute('size').Get()


        if len(self.prims) >1:
            for p in self.prims:
                if p.GetAttribute('xformOp:translate').Get()[0]+p.GetAttribute('xformOp:scale').Get()[0] > max_x:
                    max_x = p.GetAttribute('xformOp:translate').Get()[0]+p.GetAttribute('xformOp:scale').Get()[0]*self.prims[0].GetAttribute('size').Get()
                if p.GetAttribute('xformOp:translate').Get()[0]-p.GetAttribute('xformOp:scale').Get()[0] < min_x:
                    min_x = p.GetAttribute('xformOp:translate').Get()[0]-p.GetAttribute('xformOp:scale').Get()[0]*self.prims[0].GetAttribute('size').Get()
                if p.GetAttribute('xformOp:translate').Get()[2]+p.GetAttribute('xformOp:scale').Get()[2] > max_z:
                    max_z = p.GetAttribute('xformOp:translate').Get()[2]+p.GetAttribute('xformOp:scale').Get()[2]*self.prims[0].GetAttribute('size').Get()
                if p.GetAttribute('xformOp:translate').Get()[2]-p.GetAttribute('xformOp:scale').Get()[2] < min_z:
                    min_z = p.GetAttribute('xformOp:translate').Get()[2]-p.GetAttribute('xformOp:scale').Get()[2]*self.prims[0].GetAttribute('size').Get()


        
        camera = self.get_selected_prims()[0]
        camera.GetAttribute('xformOp:translate').Set(Gf.Vec3d((max_x + min_x)/2,max_y+100,(max_z + min_z)/2))
        camera.GetAttribute('xformOp:rotateYXZ').Set(Gf.Vec3d(-90,0.0,0))



