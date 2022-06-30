import omni.ext
import omni.ui as ui
import omni.kit.commands
from datetime import datetime as dt
# from pxr import Sdf, Gf

from omni.kit.widget.viewport import ViewportWidget

# Any class derived from `omni.ext.IExt` in top level module (defined in `python.modules` of `extension.toml`) will be
# instantiated when extension gets enabled and `on_startup(ext_id)` will be called. Later when extension gets disabled
# on_shutdown() is called.


class MyExtension(omni.ext.IExt):
    # ext_id is current extension id. It can be used with extension manager to query additional information, like where
    # this extension is located on filesystem.

    """"Current Problems:
        1. the console is giving logs every second. Causation uncelar
        2. The Cameras does not updates properly. Currently it updates every time a camera is spawned through the 
        extension, but if changes on camera is done outside the extension. The viewport can't update. ]
        (adding a update button? checking every tick??)
    """

    def on_startup(self, ext_id):
        print("[cornell.warm.ext] MyExtension startup")
        """Making the first window"""
        self._window = ui.Window("Warm Up", width=500, height=720+20)
        with self._window.frame:
            with ui.VStack():
                ui.Label("Menu", height=30, width=500, alignment=ui.Alignment.CENTER)
                with ui.CollapsableFrame("Spawns"):
                    with ui.VStack(height=0):
                        ui.Button("Spawn Cube", height=30, width=426, clicked_fn=lambda: self.on_click_cube())
                        ui.Button("Spawn Sphere", height=30, width=426, clicked_fn=lambda: self.on_click_sphere())
                        ui.Button("Spawn Cylinder", height=30, width=426, clicked_fn=lambda: self.on_click_cylinder())
                        ui.Button("Spawn Camera", height=30, width=426, clicked_fn=lambda: self.on_click_camera())
                        ui.Button("Spawn Viewport", height=30, width=426, clicked_fn=lambda: self.setup_viewPort())
                with ui.CollapsableFrame("Others"):                       
                    with ui.VStack(height=0):
                        ui.Button("Get Selected Prims in Console", height=30, width=426, 
                                  clicked_fn=lambda: self.on_click_get())
                        ui.Button("Duplicate Selected Prims", height=30, width=426, 
                                  clicked_fn=lambda: self.on_click_duplicate())
        
        self.setup_defaults() # sets up defaults

    def setup_defaults(self):
        self.context = omni.usd.get_context()
        self.stage = self.context.get_stage()
        self.viewport_widget = None
        self._window2 = None
        self.cams=[]
        self.viewport_api= None
        self.default()

    def _create_prime(self, type_of_prim :str):
        attrib = {'radius': 50, 'extent': [(-50, -50, -50), (50, 50, 50)]}
        if type_of_prim == "Cube":
            attrib = {'size': 100, 'extent': [(-50, -50, -50), (50, 50, 50)]}
        elif type_of_prim == "Cylinder":
            attrib = {'radius': 50, 'height': 100, 'extent': [(-50, -50, -50), (50, 50, 50)]}
        
        omni.kit.commands.execute('CreatePrimWithDefaultXform',
        prim_type =type_of_prim,
        attributes =attrib)
   
    def on_click_cube(self):
        self._create_prime("Cube")
        
    def on_click_sphere(self):
       self._create_prime("Sphere")

    def on_click_cylinder(self):
       
        self._create_prime('Cylinder')
       
    def on_click_camera(self):
        omni.kit.commands.execute(
            'CreatePrimWithDefaultXform',
            prim_type='Camera',
            attributes={'focusDistance': 400, 'focalLength': 24})
        """refresh the viewport everytime a new camera is created through the extension"""
        self.setup_viewPort()

    def helper_selected(self):
        """returns a list of primitives selected"""
        return [self.stage.GetPrimAtPath(m) for m in self.helper_selected_path()]

    def helper_selected_path(self):
        """returns a list of the path of the primitives selected"""
        return self.context.get_selection().get_selected_prim_paths()

    def helper_all_prims(self):
        """returns a list of all primitives on stage (Typically default is the World)"""
        self.context = omni.usd.get_context()
        self.stage = self.context.get_stage()
        return self.stage.GetDefaultPrim().GetChildren()
        
    def on_click_get(self):
        """print out the primitive in the console"""
        for p in self.helper_selected():
            strp=str(p)
            print("GET THE PRIM:" + strp)

    def on_click_duplicate(self):
        """make a duplication of the selected primitive. New primitive name is followed by the date&time"""
        duprim = self.helper_selected_path()
        for p in duprim:
            ct = dt.now()
            newpath = str(p)+str(ct.year)+str(ct.month)+str(ct.day)+str(ct.hour)+str(ct.minute)+str(ct.second)+str(ct.microsecond)
            omni.usd.duplicate_prim(self.stage, p, newpath, True)

    def helper_ret(self, itemmodel, item):
        #  self.viewport_api.camera_path = str(self.cams[cam_prim].GetPath())
        # print(str(cam_prim.GetPath()))
        #old: get the camera path and replace
        """new: get the selected combobox positional index. 
        Using the index to get the camera prim in the camera list, then get the path"""
        cam_index = self.cam_sel.model.get_item_value_model().get_value_as_int()
        self.viewport_api.camera_path = str(self.cams[cam_index].GetPath())

    def cam_loop(self):
        """Get all primitives in the stage, and sort out the camera primitives. Cam prims are in a list"""
        print("cam_loop in progress")
        
        self.cams=[]

        for p in self.helper_all_prims():
            cam = "Camera"
            if cam in str(p.GetPath()):
                self.cams.append(p)

    def default(self):
        """creates three cameras by default, called at the startup (setup_defaults)"""
        self.on_click_camera()
        self.on_click_camera()
        self.on_click_camera()
        
           
    def setup_viewPort(self):
        """generates a second separate window. The second window appears when spawn viewport is clicked"""
        self._window2 = ui.Window('Alt Viewport', width=480, height=270+20+30) # Add 20 for the title-bar
        with self._window2.frame:
            with ui.VStack():
                self.viewport_widget = ViewportWidget(resolution=(1280, 720))
                # Control of the ViewportTexture happens through the object held in the viewport_api property
                self.viewport_api = self.viewport_widget.viewport_api
                # We can reduce the resolution of the render easily
                self.viewport_api.resolution = (640, 360)
                #default view of viewport
                self.viewport_api.camera_path = '/World/Camera'
                self.cam_loop()
                print(self.cams)
                self.cam_sel = ui.ComboBox() #creates empty combobox
                
               
               

                #looping through the list of cameras and putting them into the combobox
                for c in range(len(self.cams)):
                    strc = str(self.cams[c].GetPath()).split("/")[-1] #get the camera name out of its path
                    #adds value to combobox as a string
                    self.cam_sel.model.append_child_item(None, ui.SimpleStringModel(strc)) 

                #call the helper return method everytime val of combobox changes, so it updates the cam path 
                self.cam_sel.model.add_item_changed_fn(self.helper_ret)      
                ui.Button("Update Viewport", height=30, width=426, clicked_fn=lambda: self.helper_update())

    def helper_update(self):
        self.cam_loop()
        print("help t")
        # self.cam_sel=ui.ComboBox.destroy() #creates empty combobox
        self.cam_sel=ui.ComboBox()
        print(self.cams)
        # print(dir(self.cam_sel))
        for c in range(len(self.cams)):
            strc = str(self.cams[c].GetPath()).split("/")[-1] #get the camera name out of its path
            #adds value to combobox as a string
            print(strc)
            self.cam_sel.model.append_child_item(None, ui.SimpleStringModel(strc)) 

 

    def on_shutdown(self):
        # Don't forget to destroy the objects when done with them
        self._window,self._window2 =None, None
        self.viewport_widget = None
        print("[cornell.warm.ext] MyExtension shutdown")
