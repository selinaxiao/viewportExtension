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