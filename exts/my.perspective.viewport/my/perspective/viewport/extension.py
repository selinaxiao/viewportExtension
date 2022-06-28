import omni.ext
import omni.ui as ui
from omni.kit.widget.viewport import ViewportWidget

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
        # super().on_startup()

        # self.viewport_window = omni.ui.Window('Perspective Viewport', width=1280, height=720+20) # Add 20 for the title-bar
        # with self.viewport_window.frame:
        #     with ui.VStack():
        #         self.viewport_widget = ViewportWidget(resolution = (1280, 720))
        #         ui.ComboBox(0,"Perspective","Orthographic", width=100, height=100)

        #     # Control of the ViewportTexture happens through the object held in the viewport_api property
        #     self.viewport_api = self.viewport_widget.viewport_api

        #     # We can reduce the resolution of the render easily
        #     self.viewport_api.resolution = (640, 480)

        #     # We can also switch to a different camera if we know the path to one that exists
        #     self.viewport_api.camera_path = '/World/Camera'

        #     # And inspect 
        #     # print(self.viewport_api.projection)
        #     # print(self.viewport_api.transform)
        
        self.mainmenu = None

        settings = carb.settings.get_settings()
        default_name = settings.get(DEFAULT_VIEWPORT_NAME) or MyExtension.WINDOW_NAME
        MyExtension.WINDOW_NAME = default_name
        MyExtension.MENU_PATH = f'Window/{default_name}'

        self.__window = None
        self.__registered = None

        open_window = not settings.get(DEFAULT_VIEWPORT_NO_OPEN)
        Workspace.set_show_window_fn(MyExtension.WINDOW_NAME, lambda b: self.__show_window(None, b))
        if open_window:
            Workspace.show_window(MyExtension.WINDOW_NAME)
            if self.__window:
                MyExtension.dock_with_window(MyExtension.WINDOW_NAME, 'Viewport', omni.ui.DockPosition.SAME)
        open_window = True if (open_window and self.__window) else False

        editor_menu = omni.kit.ui.get_editor_menu()
        if editor_menu:
            self.__menu = editor_menu.add_item(MyExtension.MENU_PATH, self.__show_window, toggle=True, value=open_window)
        
        self.__registered = self.__register_scenes()
        self.__default_drag_handlers = (
            UsdFileDropDelegate('/persistent/app/viewport/previewOnPeek'),
            UsdShadeDropDelegate(),
            MaterialFileDropDelegate()
        )


    def on_shutdown(self):
        print("[my.perspective.viewport] MyExtension shutdown")
        Workspace.set_show_window_fn(MyExtension.WINDOW_NAME, None)
        self.__show_window(None, False)
        self.__menu = None
        self.__default_drag_handlers = None
        if self.__registered:
            self.__unregister_scenes(self.__registered)
            self.__registered = None

        from omni.kit.viewport.window.events import set_ui_delegate
        set_ui_delegate(None)

    def dock_with_window(window_name: str, dock_name: str, position: omni.ui.DockPosition, ratio: float = 1):
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
            editor_menu.set_value(MyExtension.MENU_PATH, value)

    
    def __show_window(self, menu, visible):
        self.__set_menu(visible)

        if visible:
            if not self.__window:
                def visiblity_changed(visible):
                    self.__set_menu(visible)
                    if not visible:
                        self.__show_window(None, False)
                self.__window = ViewportWindow(MyExtension.WINDOW_NAME)
                self.__window.set_visibility_changed_fn(visiblity_changed)
                with self.__window._ViewportWindow__viewport_layers._ViewportLayers__ui_frame:
                    self.mainmenu  = ui.Menu("Direction of View")
                    with self.mainmenu:
                        ui.MenuItem("Perspective")
                        with ui.Menu("Orthographic"):
                            ui.MenuItem("Top")
                            ui.MenuItem("Front")
                            ui.MenuItem("Back")
                            ui.MenuItem("Left")
                            ui.MenuItem("Right")
                        ui.MenuItem("Isometric")
                        ui.MenuItem("Dimetric")

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



    # ['_ViewportWindow__name', '_ViewportWindow__external_drop_support', '_ViewportWindow__added_frames',
    #  '_ViewportWindow__z_stack', '_ViewportWindow__viewport_layers', '__module__', '__doc__', '__init__', 'name', 
    #  'viewport_api', 'set_style', 'add_external_drag_drop_support', 'remove_external_drag_drop_support', 
    #  'get_frame', '__del__', 'destroy', '_ViewportWindow__external_drop', '_ViewportWindow__frame_built', 
    #  '_ViewportWindow__selected_in_dock_changed', '_ViewportWindow__dock_changed', 'set_default_style', 'get_instances',
    #   '_ViewportWindow__clean_instances', '_ViewportWindow__g_instances', '_ViewportWindow__g_default_style', '__dict__',
    #    'notify_app_window_change', 'get_window_callback', 'move_to_app_window', 'set_top_modal', 'visible', 'title', 
    #    'flags', 'padding_x', 'padding_y', 'width', 'height', 'position_x', 'position_y', 'setPosition', 'auto_resize', 
    #    'noTabBar', 'exclusive_keyboard', 'detachable', 'docked', 'selected_in_dock', 'frame', 'menu_bar', 'focused', 
    #    'set_visibility_changed_fn', 'set_width_changed_fn', 'set_height_changed_fn', 'set_position_x_changed_fn', 
    #    'set_position_y_changed_fn', 'set_docked_changed_fn', 'set_selected_in_dock_changed_fn', 'set_key_pressed_fn', 
    #    'has_key_pressed_fn', 'call_key_pressed_fn', 'dock_in_window', 'deferred_dock_in', 'set_focused_changed_fn', 
    #    'dock_tab_bar_visible', 'dock_tab_bar_enabled', 'dock_order', 'dock_id', 'undock', 'dock_in', 'focus', 
    #    'is_selected_in_dock', '__repr__', '__new__', '__hash__', '__str__', '__getattribute__', '__setattr__', 
    #    '__delattr__', '__lt__', '__le__', '__eq__', '__ne__', '__gt__', '__ge__', '__reduce_ex__', '__reduce__', 
    #    '__subclasshook__', '__init_subclass__', '__format__', '__sizeof__', '__dir__', '__class__']


#    ['__init__', '__doc__', '__module__', 'shown', 'get_current', 'show', 'show_at', 'hide', 'invalidate', 
#    'set_shown_changed_fn', 'tearable', 'teared', 'set_teared_changed_fn', 'set_on_build_fn', 'has_on_build_fn', 
#    'call_on_build_fn', 'direction', 'content_clipping', 'spacing', 'add_child', 'clear', '__enter__', '__exit__', 
#    'FLAG_WANT_CAPTURE_KEYBOARD', 'destroy', 'set_style', 'width', 'height', 'name', 'style_type_name_override', 
#    'identifier', 'style', 'visible', 'visible_min', 'visible_max', 'tooltip', 'set_tooltip', 'scroll_here_x', 
#    'scroll_here_y', 'scroll_here', 'tooltip_offset_x', 'tooltip_offset_y', 'enabled', 'selected', 'checked', 
#    'dragging', 'opaque_for_mouse_events', 'skip_draw_when_clipped', 'computed_width', 'computed_height', 
#    'computed_content_width', 'computed_content_height', 'screen_position_x', 'screen_position_y', 'set_checked_changed_fn', 
#    'set_tooltip_fn', 'has_tooltip_fn', 'call_tooltip_fn', 'set_mouse_moved_fn', 'has_mouse_moved_fn', 'call_mouse_moved_fn',
#     'set_mouse_pressed_fn', 'has_mouse_pressed_fn', 'call_mouse_pressed_fn', 'set_mouse_released_fn', 'has_mouse_released_fn', 
#     'call_mouse_released_fn', 'set_mouse_double_clicked_fn', 'has_mouse_double_clicked_fn', 'call_mouse_double_clicked_fn', 
#     'set_mouse_wheel_fn', 'has_mouse_wheel_fn', 'call_mouse_wheel_fn', 'set_mouse_hovered_fn', 'has_mouse_hovered_fn',
#      'call_mouse_hovered_fn', 'set_key_pressed_fn', 'has_key_pressed_fn', 'call_key_pressed_fn', 'set_drag_fn', 'has_drag_fn', 
#      'call_drag_fn', 'set_accept_drop_fn', 'has_accept_drop_fn', 'call_accept_drop_fn', 'set_drop_fn', 'has_drop_fn', 
#      'call_drop_fn', 'set_computed_content_size_changed_fn', 'has_computed_content_size_changed_fn', 
#      'call_computed_content_size_changed_fn', '__new__', '__repr__', '__hash__', '__str__', '__getattribute__', 
#      '__setattr__', '__delattr__', '__lt__', '__le__', '__eq__', '__ne__', '__gt__', '__ge__', '__reduce_ex__', 
#      '__reduce__', '__subclasshook__', '__init_subclass__', '__format__', '__sizeof__', '__dir__', '__class__', 
#      'text', 'delegate', 'hotkey_text', 'checkable', 'hide_on_click', 'menu_compatibility', 'set_triggered_fn', 
#      'has_triggered_fn', 'call_triggered_fn']

#  ['_ViewportLayers__viewport_layers', '_ViewportLayers__added_frames', '_ViewportLayers__ui_frame', 
#  '_ViewportLayers__viewport', '_ViewportLayers__zstack', '_ViewportLayers__timeline', '__module__', '__doc__', 
#  'viewport_api', 'layers', 'get_frame', '__init__', '_ViewportLayers__viewport_updated', 
#  '_ViewportLayers__viewport_layer_event', '__del__', 'destroy', '__dict__', '__weakref__', '__repr__', '__hash__', 
#  '__str__', '__getattribute__', '__setattr__', '__delattr__', '__lt__', '__le__', '__eq__', '__ne__', '__gt__', '__ge__', 
#  '__new__', '__reduce_ex__', '__reduce__', '__subclasshook__', '__init_subclass__', '__format__', '__sizeof__', '__dir__', 
#  '__class__']

# ['__repr__', '__hash__', '__getattribute__', '__lt__', '__le__', '__eq__', '__ne__', '__gt__', '__ge__', '__iter__', 
# '__init__', '__len__', '__getitem__', '__setitem__', '__delitem__', '__contains__', '__new__', '__sizeof__', 'get', 
# 'setdefault', 'pop', 'popitem', 'keys', 'items', 'values', 'update', 'fromkeys', 'clear', 'copy', '__doc__', '__str__', 
# '__setattr__', '__delattr__', '__reduce_ex__', '__reduce__', '__subclasshook__', '__init_subclass__', '__format__', 
# '__dir__', '__class__']

# ['_ViewportWidget__ui_frame', '_ViewportWidget__stage_listener', '_ViewportWidget__rsettings_changed', '_ViewportWidget__viewport_texture', 
# '_ViewportWidget__viewport_image', '_ViewportWidget__viewport_provider', '_ViewportWidget__vp_api', '_ViewportWidget__proxy_api', 
# '_ViewportWidget__update_api_texture', '_ViewportWidget__stage_subscription', '__module__', '__doc__', '_ViewportWidget__g_instances', 
# 'get_instances', '_ViewportWidget__clean_instances', 'viewport_api', 'name', 'visible', '__init__', 'destroy', 'usd_context_name', 
# '_viewport_changed', '_ViewportWidget__ensure_usd_context', '_ViewportWidget__ensure_usd_stage', '_ViewportWidget__remove_notifications', 
# '_ViewportWidget__setup_notifications', '_ViewportWidget__build_ui', '_ViewportWidget__destroy_ui', '_ViewportWidget__set_image_data', 
# '_ViewportWidget__on_stage_opened', '__dict__', '__weakref__', '__repr__', '__hash__', '__str__', '__getattribute__', '__setattr__', 
# '__delattr__', '__lt__', '__le__', '__eq__', '__ne__', '__gt__', '__ge__', '__new__', '__reduce_ex__', '__reduce__', '__subclasshook__', 
# '__init_subclass__', '__format__', '__sizeof__', '__dir__', '__class__']

['_MyExtension__window', '_MyExtension__registered', '__module__', '__all__', 'WINDOW_NAME', 'MENU_PATH', 'on_startup', 
'on_shutdown', 'dock_with_window', '_MyExtension__set_menu', '_MyExtension__show_window', '_MyExtension__register_scenes', 
'_MyExtension__unregister_scenes', '__dict__', '__doc__', '__init__', 'startup', 'shutdown', '__new__', '__repr__', '__hash__', 
'__str__', '__getattribute__', '__setattr__', '__delattr__', '__lt__', '__le__', '__eq__', '__ne__', '__gt__', '__ge__', 
'__reduce_ex__', '__reduce__', '__subclasshook__', '__init_subclass__', '__format__', '__sizeof__', '__dir__', '__class__']