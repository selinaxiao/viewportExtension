import omni.ext
from omni.kit.widget import viewport
import omni.ui as ui
from omni.kit.widget.viewport import ViewportWidget
from omni.usd._impl.utils import get_prim_at_path
from pxr import Sdf, Gf, Usd, UsdShade, UsdGeom, UsdLux
from omni.ui import Workspace
from  omni.kit.viewport.window.window import ViewportWindow
from  omni.kit.viewport.window.dragdrop.usd_file_drop_delegate import UsdFileDropDelegate
from  omni.kit.viewport.window.dragdrop.usd_prim_drop_delegate import UsdShadeDropDelegate
from  omni.kit.viewport.window.dragdrop.material_file_drop_delegate import MaterialFileDropDelegate
import carb
import math

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
        # print("what's up")
        if button != 0:
            return

        # Reset the previous context popup
        self._pushed_menu.clear()
        with self._pushed_menu:
            with ui.Menu("Camera Selection"):
                # ui.MenuItem("camera", triggered_fn=lambda: self.cam_sel_helper(Sdf.Path('/World/Camera')))
                # ui.MenuItem("camera_01", triggered_fn=lambda: self.cam_sel_helper(Sdf.Path('/World/Camera_01')))
                for c in range(len(self.camera_sel())):
                    # self.cam_sel_helper(c.GetPath())
                    # print(c)
                 
                    ui.MenuItem(self.camera_sel()[c].GetName(), triggered_fn=lambda argum=c: self.cam_sel_helper(argum))
                    
                    
            ui.MenuItem("Perspective", height = 100,triggered_fn=lambda: self.orth_to_persp())

            with ui.Menu("Orthographic"):
                ui.MenuItem("Top",triggered_fn=lambda: self.ortho_helper('top'))
                ui.MenuItem("Front",triggered_fn=lambda: self.ortho_helper('front'))
                ui.MenuItem("Right",triggered_fn=lambda: self.ortho_helper('right'))

            with ui.Menu("Isometric"):
                ui.MenuItem("NE", triggered_fn=lambda: self.iso_helper("NE"))
                ui.MenuItem("NW", triggered_fn=lambda: self.iso_helper("NW"))
                ui.MenuItem("SE", triggered_fn=lambda: self.iso_helper("SE"))
                ui.MenuItem("SW", triggered_fn=lambda: self.iso_helper("SW"))
            
            self.dim = ui.MenuItem("Dimetric")

            

        # Show it
        self._pushed_menu.show_at(
            (int)(widget.screen_position_x), (int)(widget.screen_position_y + widget.computed_content_height)
        )
       
    def ortho_helper(self, option:str):
        # print(self.get_selected_prims()[0])
        # if len(self.get_selected_prims()) != 1 or "Camera" not in str(omni.usd.get_prim_at_path(self.viewport_api.camera_path)):
        #     return
        
        self.stage = omni.usd.get_context().get_stage()
        self.prims = self.stage.GetDefaultPrim().GetChildren()

        prims_to_remove = []

        for p in self.prims:
            # print(self.prims, "prims begin")
            # print(str(p.GetPath()), "path")
            if p.IsA(UsdGeom.Camera):
                prims_to_remove.append(p)
                # print("camera")
            elif p.IsA(UsdLux.Light):
                # print("light")
                prims_to_remove.append(p)
            # print(self.prims, "prims")

        for p in prims_to_remove:
            self.prims.remove(p)

        # print(self.prims, "final prims")


        if self.prims:
            x_pos, y_pos, z_pos = 0 , 0, 0 
            for p in self.prims:
                x_pos = x_pos+p.GetAttribute('xformOp:translate').Get()[0]
                y_pos = y_pos+p.GetAttribute('xformOp:translate').Get()[1]
                z_pos = z_pos+p.GetAttribute('xformOp:translate').Get()[2]

        camera=omni.usd.get_prim_at_path(self.viewport_api.camera_path)

        if option == "top":
            camera.GetAttribute('xformOp:translate').Set(Gf.Vec3d(x_pos/len(self.prims),y_pos/len(self.prims)+camera.GetAttribute('focusDistance').Get(),z_pos/len(self.prims)))
            camera.GetAttribute(UsdGeom.Xformable(camera).GetOrderedXformOps()[1].GetOpName()).Set(Gf.Vec3d(-90,0.0,0))
        elif option == "front":
            camera.GetAttribute('xformOp:translate').Set(Gf.Vec3d(x_pos/len(self.prims),y_pos/len(self.prims),z_pos/len(self.prims)+camera.GetAttribute('focusDistance').Get()))
            camera.GetAttribute(UsdGeom.Xformable(camera).GetOrderedXformOps()[1].GetOpName()).Set(Gf.Vec3d(0,0.0,0))
        elif option == "right":
            camera.GetAttribute('xformOp:translate').Set(Gf.Vec3d(x_pos/len(self.prims)+camera.GetAttribute('focusDistance').Get(),y_pos/len(self.prims),z_pos/len(self.prims)))
            camera.GetAttribute(UsdGeom.Xformable(camera).GetOrderedXformOps()[1].GetOpName()).Set(Gf.Vec3d(0,90,0))

        self.persp_to_orth()

        # usd_camera = UsdGeom.Camera(self.get_selected_prims()[0])
        # frustum = Gf.Frustum(usd_camera.GetCamera().transform, Gf.Range2d(Gf.Vec2d(-2.5, 2.5), Gf.Vec2d(-2.5, 2.5)), Gf.Range1d(0, 100), Gf.Frustum.Orthographic)
        # print(self.frustum)
        # print(usd_camera.GetCamera().frustum.ComputeProjectionMatrix(), "window")
        # print(usd_camera.GetCamera().SetOrthographicFromAspectRatioAndSize(16/9, 500, Gf.Camera.FOVHorizontal))
        # print(camera.GetAttribute('xformOp:rotateYXZ').Get())
        # print(camera.GetAttribute('xformOp:translate').Get())

        # x_ang = camera.GetAttribute('xformOp:rotateYXZ').Get()[0]
        # y_ang = camera.GetAttribute('xformOp:rotateYXZ').Get()[1]
        # z_ang = camera.GetAttribute('xformOp:rotateYXZ').Get()[2]

        # print("x:", x_ang)
        # print("y:", y_ang)
        # print("z:", z_ang)

        # cam_origin = Gf.Matrix4d(
        #     (1, 0, 0, 0),
        #     (0, 1, 0, 0),
        #     (0, 0, -1, 0),
        #     (0, 0, 0, 1)
        # )

        # x_rot = Gf.Matrix4d(
        #     (1, 0, 0, 0),
        #     (0, math.cos(x_ang/180*math.pi), -math.sin(x_ang/180*math.pi), 0),
        #     (0, math.sin(x_ang/180*math.pi), math.cos(x_ang/180*math.pi), 0),
        #     (0, 0, 0, 1)
        # )

        # print("x_rot", x_rot)

        # y_rot = Gf.Matrix4d(
        #     (math.cos(y_ang/180*math.pi), 0, math.sin(y_ang/180*math.pi), 0),
        #     (0, 1, 0, 0),
        #     (-math.sin(y_ang/180*math.pi), 0, math.cos(y_ang/180*math.pi), 0),
        #     (0, 0, 0, 1)
        # )

        # print("y rot",y_rot)

        # z_rot = Gf.Matrix4d(
        #     (math.cos(z_ang/180*math.pi), math.sin(z_ang/180*math.pi), 0, 0),
        #     (-math.sin(z_ang/180*math.pi), math.cos(z_ang/180*math.pi), 0, 0),
        #     (0, 0, -1, 0),
        #     (0, 0, 0, 1)
        # )

        # print("z rot",z_rot)

        # cam_axis = z_rot*y_rot*x_rot*cam_origin



        # print(cam_axis)
        # print(usd_camera.GetCamera().transform)
        # point_x = Gf.Vec4d(1, 0, 0, 1)
        # point_y = Gf.Vec4d(0, 1, 0, 1)
        # point_z = Gf.Vec4d(0, 0, 1, 1)
        # print(usd_camera.GetCamera().transform*point_x, "camera coodrinate x")
        # print(usd_camera.GetCamera().transform*point_y, "camera coodrinate y")
        # print(usd_camera.GetCamera().transform*point_z, "camera coodrinate z")



    def iso_helper(self, angle:str):
        # forward = Gf.Vec3f(1/math.sqrt(3),1/math.sqrt(3),-1/math.sqrt(3))
        # right = Gf.Cross(Gf.Vec3f(0,1,0),forward)
        # up = Gf.Cross(forward, right)
        # Gf.Normalize(right)
        # Gf.Normalize(up)
        
        # print(forward, "forward")
        # print(up, "up")
        # print(right, "right")
        # rot_matrix = Gf.Matrix4d(
        #     (right[0],right[1],right[2],0),
        #     (up[0],up[1],up[2],0),
        #     (forward[0],forward[1],forward[2],0),
        #     (0,0,0,1)
        # )
        # print(rot_matrix, "rotational matrix")

        camera=omni.usd.get_prim_at_path(self.viewport_api.camera_path)
        # position = camera.GetAttribute('xformOp:translate').Get()
        # usd_camera = UsdGeom.Camera(camera)
        # print(type(usd_camera.GetCamera()))

        # translation_matrix = Gf.Matrix4d(
        #     (1, 0, 0, -position[0]),
        #     (0, 1, 0, -position[1]),
        #     (0, 0, 1, -position[2]),
        #     (0, 0, 0, 1)
        # )

        # transform_matrix = rot_matrix*translation_matrix
        
        # print(usd_camera.GetCamera().transform)
        # print(camera.GetAttribute('xformOp:transform').Get())
        # UsdGeom.Xformable(camera).AddTransformOp().Set(transform_matrix)
        # print(usd_camera.GetCamera().transform)
        # print(UsdGeom.Xformable(camera).GetOrderedXformOps())
        order = UsdGeom.Xformable(camera).GetOrderedXformOps()
        order_list = []
        for a in order:
            order_list.append(a.GetOpName())
        
        if 'xformOp:rotateXYZ' not in order_list:
            omni.kit.commands.execute('ChangeRotationOp',
            src_op_attr_path=Sdf.Path(str(camera.GetPath())+"."+UsdGeom.Xformable(camera).GetOrderedXformOps()[1].GetOpName()),
            op_name=UsdGeom.Xformable(camera).GetOrderedXformOps()[1].GetOpName(),
            dst_op_attr_name='xformOp:rotateXYZ',
            is_inverse_op=False)

        if angle == "NW":
            print("NW")
            camera.GetAttribute('xformOp:translate').Set(Gf.Vec3d(1000, 1000, 1000))
            camera.GetAttribute('xformOp:rotateXYZ').Set(Gf.Vec3d(-180*math.atan(1/math.sqrt(2))/math.pi,45,0))
        elif angle == "NE":
            print("NE")
            camera.GetAttribute('xformOp:translate').Set(Gf.Vec3d(-1000, 1000, 1000))
            camera.GetAttribute('xformOp:rotateXYZ').Set(Gf.Vec3d(-180*math.atan(1/math.sqrt(2))/math.pi,315,0))
        elif angle == "SE":
            print("SE")
            camera.GetAttribute('xformOp:translate').Set(Gf.Vec3d(-1000, 1000, -1000))
            camera.GetAttribute('xformOp:rotateXYZ').Set(Gf.Vec3d(-180*math.atan(1/math.sqrt(2))/math.pi,225,0))
        elif angle == "SW":
            print("SW")
            camera.GetAttribute('xformOp:translate').Set(Gf.Vec3d(1000, 1000, -1000))
            camera.GetAttribute('xformOp:rotateXYZ').Set(Gf.Vec3d(-180*math.atan(1/math.sqrt(2))/math.pi,135,0))

        self.persp_to_orth()
    
    def persp_to_orth(self):
        camera=omni.usd.get_prim_at_path(self.viewport_api.camera_path)
        camera.GetAttribute('projection').Set('orthographic')
        camera.GetAttribute('horizontalAperture').Set(5000)
        camera.GetAttribute('verticalAperture').Set(5000)

    def orth_to_persp(self):
        camera=omni.usd.get_prim_at_path(self.viewport_api.camera_path)
        camera.GetAttribute('projection').Set('perspective')
        camera.GetAttribute('horizontalAperture').Set(10)
        camera.GetAttribute('verticalAperture').Set(10)

    def camera_sel(self):
        self.stage = omni.usd.get_context().get_stage()
        self.prims = self.stage.GetDefaultPrim().GetChildren()

        cameras = []

        for p in self.prims:
            if p.IsA(UsdGeom.Camera):
                cameras.append(p)

        return cameras

    def cam_sel_helper(self, index):
        print(index)
        print(self.camera_sel()[index])
        self.viewport_api.camera_path = self.camera_sel()[index].GetPath()

