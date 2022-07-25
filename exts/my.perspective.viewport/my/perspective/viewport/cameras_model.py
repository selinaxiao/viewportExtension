"""
This credit goes to our beloved TA John Wolford
"""

from pxr import Usd, UsdGeom

import carb
import json
import omni.ui as ui
import omni.kit.app
import omni.kit.ui
import omni.stageupdate
import omni.usd
import omni.ext
from omni.rtx.window.settings import RendererSettingsFactory
from omni.kit.capture.viewport.capture_options import CaptureOptions

class CamerasItem(ui.AbstractItem):
    def __init__(self, model):
        super().__init__()
        self.model = model

class CamerasModel(ui.AbstractItemModel):
    """ Shamelessly ripped directly from the Movie Capture Extension. """

    def __init__(self):
        super().__init__()

        # Omniverse interfaces
        self._app = omni.kit.app.get_app_interface()
        self._stage_update = omni.stageupdate.get_stage_update_interface()
        self._usd_context = omni.usd.get_context()
        self._stage_subscription = self._stage_update.create_stage_update_node(
            "CamerasModel", None, None, None, self._on_prim_created, None, self._on_prim_removed
        )
        self._update_sub = self._app.get_update_event_stream().create_subscription_to_pop(
            self._on_update, name="omni.pcg.adobeinterface cameras"
        )
        self._capture_instance = omni.kit.capture.viewport.CaptureExtension.get_instance()
        self._active_camera = ""

        # The current index of the editable_combo box
        self._current_index = ui.SimpleIntModel()
        self._camera_value_changed_fn = self._current_index.add_value_changed_fn(self._current_index_changed)
        self._refresh_cameras()

    def clear(self):
        self._capture_instance = None

    def get_item_children(self, item):
        return self._cameras

    def get_current_camera(self):
        value_model = self.get_item_value_model(self._cameras[self._current_index.as_int], 0)
        camera = value_model.as_string
        return self._strip_current_from_camera_name(camera)

    def set_current_camera(self, camera_name):
        cameras = [cam.model.as_string for cam in self._cameras]
        index = 0
        for cam in cameras:
            real_cam_name = self._strip_current_from_camera_name(cam)
            if camera_name == real_cam_name:
                break
            index += 1
        if index == len(cameras):
            carb.log_warn(f"Movie capture: {camera_name} is not available so can't set it for capture.")
        else:
            self._current_index.as_int = index

    def get_item_value_model(self, item, column_id):
        if item is None:
            return self._current_index

        return item.model

    def _strip_current_from_camera_name(self, camera_name):
        if camera_name.startswith("Current("):
            return camera_name[8 : len(camera_name) - 1]
        else:
            return camera_name

    def _refresh_cameras(self, index=0):
        self._current_index.remove_value_changed_fn(self._camera_value_changed_fn)
        self._cameras = []
        self._active_camera = omni.kit.viewport_legacy.get_viewport_interface().get_viewport_window().get_active_camera()
        self._cameras.append(CamerasItem(ui.SimpleStringModel("Current(" + self._active_camera + ")")))

        # Iterate the stage and get all the cameras
        stage = self._usd_context.get_stage()
        if stage is not None:
            for prim in Usd.PrimRange(stage.GetPseudoRoot()):
                if prim.IsA(UsdGeom.Camera) and prim.GetPath().pathString != self._active_camera:
                    self._cameras.append(CamerasItem(ui.SimpleStringModel(prim.GetPath().pathString)))

        self._current_index.as_int = 0
        self._camera_value_changed_fn = self._current_index.add_value_changed_fn(self._current_index_changed)

    def _on_update(self, event):
        if (
            self._capture_instance is not None
            and self._capture_instance.progress.capture_status == omni.kit.capture.viewport.CaptureStatus.NONE
        ):
            active_camera = omni.kit.viewport_legacy.get_viewport_interface().get_viewport_window().get_active_camera()
            if self._active_camera != active_camera:
                self._current_index_changed(None)

    def _on_prim_created(self, path):
        stage = self._usd_context.get_stage()
        prim = stage.GetPrimAtPath(path)
        if prim.IsValid() and prim.IsA(UsdGeom.Camera):
            self._cameras.append(CamerasItem(ui.SimpleStringModel(path)))
        self._item_changed(None)

    def _on_prim_removed(self, path):
        cameras = [cam.model.as_string for cam in self._cameras]
        if path in cameras:
            index = cameras.index(path)
            del self._cameras[index]
            self._current_index.as_int = 0
            self._item_changed(None)

    def _current_index_changed(self, model):
        if model is None:
            self._refresh_cameras()

        self._item_changed(None)
