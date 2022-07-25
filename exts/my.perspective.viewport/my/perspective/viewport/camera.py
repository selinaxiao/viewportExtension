import omni.ext

from pxr import Sdf, Gf, UsdGeom, Usd
import math

def translate(x,y,z):
    """
    
    """
    return Gf.Matrix4d(
                (1, 0, 0, 0),
                (0, 1, 0, 0),
                (0, 0, 1, 0),
                (x, y, z, 1))
def x_rotation(x_angle:float):
    return  Gf.Matrix4d(
                (1, 0, 0, 0),
                (0, math.cos(x_angle), -math.sin(x_angle), 0),
                (0, math.sin(x_angle), math.cos(x_angle), 0), 
                (0, 0, 0, 1)) 
def z_rotation(z_angle:float):
    return Gf.Matrix4d(
                (math.cos(z_angle), -math.sin(z_angle), 0, 0),
                (math.sin(z_angle), math.cos(z_angle), 0, 0),
                (0, 0, 1, 0),
                (0, 0, 0, 1))
def pass_transform_matrix(camera, x_rot, z_rot, translation):
    """
    """
    camera.GetAttribute('xformOp:transform').Set(x_rot.GetTranspose()*z_rot.GetTranspose()*translation)


class CameraWrapper:
    def __init__(self,viewport_api= None):
        self.viewport_api= viewport_api
        self.cam_count = 0
        self.ortho_proj = False
        self.iso_proj = False
        self.ortho_opt = None
        self.iso_opt = None
        

    def on_shutdown(self):
        self.cam_count=0
         
    def get_selected_cam_attribute(self, attribute:str):
        camera=omni.usd.get_prim_at_path(self.viewport_api.camera_path)
        return camera.GetAttribute(attribute).Get()

    def camera_sel(self, list):
       
        cameras = []
        for p in list:
            if p.IsA(UsdGeom.Camera):
                cameras.append(p)
            if p.GetChildren():
                cameras.extend(self.camera_sel(p.GetChildren()))
     
        return cameras

    def persp_to_orth(self):
        camera=omni.usd.get_prim_at_path(self.viewport_api.camera_path)
        camera.GetAttribute('projection').Set('orthographic')
        camera.GetAttribute('horizontalAperture').Set(25000)
        camera.GetAttribute('verticalAperture').Set(25000)

    def orth_to_persp(self):
        camera=omni.usd.get_prim_at_path(self.viewport_api.camera_path)
        camera.GetAttribute('projection').Set('perspective')
        camera.GetAttribute('horizontalAperture').Set(10)
        camera.GetAttribute('verticalAperture').Set(10)
    
    def ortho_helper(self,option,current_plane = None, current_target=None):
        if current_plane is None:
            return 
        if current_target is None:
            print("target is none")
            target_pos = (0, 0, 0)
            target_rot = 0
            # target_scale = 1
        else:
            print("atrget not none")
            target_pos = current_target.GetAttribute('xformOp:translate').Get()
            target_rot = current_target.GetAttribute(UsdGeom.Xformable(current_target).GetOrderedXformOps()[1].GetOpName()).Get()[2]
            # target_scale = current_target.GetAttribute('xformOp:scale').Get()

        camera = omni.usd.get_prim_at_path(self.viewport_api.camera_path)
        plane_pos = current_plane.GetAttribute('xformOp:translate').Get()
        plane_rot = current_plane.GetAttribute('xformOp:rotateXYZ').Get()[2]
        plane_scale = current_plane.GetAttribute('xformOp:scale').Get()

        x_pos = target_pos[0]*plane_scale[0]+plane_pos[0]
        print(x_pos)
        y_pos = target_pos[1]*plane_scale[1]+plane_pos[1]
        print(y_pos)
        z_pos = target_pos[2]*plane_scale[2]+plane_pos[2]
        rot = plane_rot+target_rot

        order = UsdGeom.Xformable(camera).GetOrderedXformOps()
        order_list = []
        for a in order:
            order_list.append(a.GetOpName())

        focusdistance = max(400, self.get_selected_cam_attribute('focusDistance'))

        if 'xformOp:transform' not in order_list:
            if option == "top":
                print("ortho top")
                camera.GetAttribute('xformOp:translate').Set(Gf.Vec3d(x_pos,y_pos,z_pos+focusdistance))
                camera.GetAttribute(UsdGeom.Xformable(camera).GetOrderedXformOps()[1].GetOpName()).Set(Gf.Vec3d(0,0.0,rot))
            elif option == "front":
                print("ortho front")
                camera.GetAttribute('xformOp:translate').Set(Gf.Vec3d(x_pos+focusdistance*math.cos(rot*math.pi/180),y_pos+focusdistance*math.sin(rot*math.pi/180),z_pos))
                camera.GetAttribute(UsdGeom.Xformable(camera).GetOrderedXformOps()[1].GetOpName()).Set(Gf.Vec3d(90,0.0,90+rot))
            elif option == "right":
                print("ortho right")
                camera.GetAttribute('xformOp:translate').Set(Gf.Vec3d(x_pos-focusdistance*math.sin(rot*math.pi/180),y_pos+focusdistance*math.cos(rot*math.pi/180),z_pos))
                camera.GetAttribute(UsdGeom.Xformable(camera).GetOrderedXformOps()[1].GetOpName()).Set(Gf.Vec3d(90,0,180+rot))
            elif option == "back":
                print("ortho beck")
                camera.GetAttribute('xformOp:translate').Set(Gf.Vec3d(x_pos-focusdistance*math.cos(rot*math.pi/180),y_pos-focusdistance*math.sin(rot*math.pi/180),z_pos))
                camera.GetAttribute(UsdGeom.Xformable(camera).GetOrderedXformOps()[1].GetOpName()).Set(Gf.Vec3d(90,0,270+rot))
            elif option == "left":
                print("ortho left")
                camera.GetAttribute('xformOp:translate').Set(Gf.Vec3d(x_pos+focusdistance*math.sin(rot*math.pi/180),y_pos-focusdistance*math.cos(rot*math.pi/180),z_pos))
                camera.GetAttribute(UsdGeom.Xformable(camera).GetOrderedXformOps()[1].GetOpName()).Set(Gf.Vec3d(90,0,360+rot))

        else:
            print("pass in transform matrix")
            print("prev transform matrix", self.get_selected_cam_attribute('xformOp:transform'))

            if option == "top":
                x_rot = x_rotation(0)
                z_rot = z_rotation(rot*math.pi/180)
                translate_matrix = translate(x_pos,y_pos,z_pos+focusdistance)

                pass_transform_matrix(camera, x_rot, z_rot, translate_matrix)

                print('after top transform matrix', camera.GetAttribute('xformOp:transform').Get())

            elif option == "front":
                x_rot = x_rotation(math.pi/2)

                z_rot = z_rotation((90+rot)*math.pi/180)

                translate_matrix =  translate(x_pos+focusdistance*math.cos(rot*math.pi/180),y_pos+focusdistance*math.sin(rot*math.pi/180),z_pos)

                pass_transform_matrix(camera, x_rot, z_rot, translate_matrix)

                print('after front transform matrix', camera.GetAttribute('xformOp:transform').Get())

            elif option == "right":
                x_rot = x_rotation(math.pi/2)

                z_rot = z_rotation((180+rot)*math.pi/180)

                translate_matrix = translate(x_pos-focusdistance*math.sin(rot*math.pi/180),y_pos+focusdistance*math.cos(rot*math.pi/180),z_pos)

                pass_transform_matrix(camera, x_rot, z_rot, translate_matrix)
                
                print('\n~~~~~~~~~~~~~~~~~~~~~~~\n','After right transform matrix:\n',
                 camera.GetAttribute('xformOp:transform').Get())

        self.persp_to_orth()
        self.ortho_proj = True
        self.iso_proj = False
        self.ortho_opt = option

    def change_aperture(self, aperture_ratio):
            camera = omni.usd.get_prim_at_path(self.viewport_api.camera_path)
            old_H_ap =  camera.GetAttribute('horizontalAperture').Get()
            old_V_ap = camera.GetAttribute('verticalAperture').Get()
            camera.GetAttribute('horizontalAperture').Set(aperture_ratio*old_H_ap)
            camera.GetAttribute('verticalAperture').Set(aperture_ratio*old_V_ap)

    def iso_helper(self, angle:str, current_plane = None, current_target=None):
        if current_plane is None:
            return 
        if current_target is None:
            target_pos = (0, 0, 0)
            target_rot = 0
        else:
            target_pos = current_target.GetAttribute('xformOp:translate').Get()
            target_rot = current_target.GetAttribute(UsdGeom.Xformable(current_target).GetOrderedXformOps()[1].GetOpName()).Get()[2]


        camera = omni.usd.get_prim_at_path(self.viewport_api.camera_path)
        plane_pos = current_plane.GetAttribute('xformOp:translate').Get()
        plane_rot = current_plane.GetAttribute('xformOp:rotateXYZ').Get()[2]
        plane_scale = current_plane.GetAttribute('xformOp:scale').Get()

        x_pos = target_pos[0]*plane_scale[0]+plane_pos[0]
        y_pos = target_pos[1]*plane_scale[1]+plane_pos[1]
        z_pos = target_pos[2]*plane_scale[2]+plane_pos[2]
        rot = plane_rot+target_rot

        order = UsdGeom.Xformable(camera).GetOrderedXformOps()
        order_list = []
        for a in order:
            order_list.append(a.GetOpName())
        
        # print(order_list)
        
        if 'xformOp:rotateXYZ' not in order_list and 'xformOp:transform' not in order_list:
            omni.kit.commands.execute('ChangeRotationOp',
            src_op_attr_path=Sdf.Path(str(camera.GetPath())+"."+UsdGeom.Xformable(camera).GetOrderedXformOps()[1].GetOpName()),
            op_name=UsdGeom.Xformable(camera).GetOrderedXformOps()[1].GetOpName(),
            dst_op_attr_name='xformOp:rotateXYZ',
            is_inverse_op=False)

        proj_dist = 200
        x_trans = proj_dist*math.sqrt(2)*math.cos((45+rot)*math.pi/180)
        y_trans = proj_dist*math.sqrt(2)*math.sin((45+rot)*math.pi/180)

        if 'xformOp:transform' not in order_list:
            if angle == "NW":
                camera.GetAttribute('xformOp:translate').Set(Gf.Vec3d(x_pos-y_trans, y_pos+x_trans, z_pos+proj_dist))
                camera.GetAttribute('xformOp:rotateXYZ').Set(Gf.Vec3d(90-180*math.atan(1/math.sqrt(2))/math.pi,0,225+rot))
            elif angle == "NE":
                camera.GetAttribute('xformOp:translate').Set(Gf.Vec3d(x_pos+x_trans, y_pos+y_trans, z_pos+proj_dist))
                camera.GetAttribute('xformOp:rotateXYZ').Set(Gf.Vec3d(90-180*math.atan(1/math.sqrt(2))/math.pi,0,135+rot))
            elif angle == "SE":
                camera.GetAttribute('xformOp:translate').Set(Gf.Vec3d(x_pos+y_trans, y_pos-x_trans, z_pos+proj_dist))
                camera.GetAttribute('xformOp:rotateXYZ').Set(Gf.Vec3d(90-180*math.atan(1/math.sqrt(2))/math.pi,0,45+rot))
            elif angle == "SW":
                camera.GetAttribute('xformOp:translate').Set(Gf.Vec3d(x_pos-x_trans, y_pos-y_trans, z_pos+proj_dist))
                camera.GetAttribute('xformOp:rotateXYZ').Set(Gf.Vec3d(90-180*math.atan(1/math.sqrt(2))/math.pi,0,315+rot))
        
        else:
            print("pass in transform matrix")
            print("prev transform matrix", camera.GetAttribute('xformOp:transform').Get())
            x_rot = x_rotation(math.pi/2-math.atan(1/math.sqrt(2)))

            if angle == "NW":
                z_rot = z_rotation((225+rot)*math.pi/180)
                translate_matrix = translate(x_pos-y_trans, y_pos+x_trans, z_pos+proj_dist)

                pass_transform_matrix(camera, x_rot, z_rot, translate_matrix)
                print('after NW transform matrix', camera.GetAttribute('xformOp:transform').Get())

            elif angle == "NE":
                z_rot = z_rotation((135+rot)*math.pi/180)
                translate_matrix = translate(x_pos+x_trans, y_pos+y_trans, z_pos+proj_dist)

                pass_transform_matrix(camera, x_rot, z_rot, translate_matrix)
                print('after NE transform matrix', camera.GetAttribute('xformOp:transform').Get())

            elif angle == "SE":
                z_rot = z_rotation((45+rot)*math.pi/180)
                translate_matrix = translate(x_pos+y_trans, y_pos-x_trans, z_pos+proj_dist)

                pass_transform_matrix(camera, x_rot, z_rot, translate_matrix)
                print('after SE transform matrix', camera.GetAttribute('xformOp:transform').Get())

            elif angle == "SW":
                z_rot = z_rotation((315+rot)*math.pi/180)
                translate_matrix = translate(x_pos-x_trans, y_pos-y_trans, z_pos+proj_dist)
                
                pass_transform_matrix(camera, x_rot, z_rot, translate_matrix)
                print('after SW transform matrix', camera.GetAttribute('xformOp:transform').Get())


        self.persp_to_orth()
        self.ortho_proj = False
        self.iso_proj = True

    def create_cam_helper(self):
        omni.kit.commands.execute('CreatePrimWithDefaultXform',
            prim_type='Camera', prim_path='/World/Camera' + str(self.cam_count),
            attributes={'focusDistance': 400, 'focalLength': 24},
            select_new_prim=True)
        
        camera_pos = self.cam_position()

        omni.kit.commands.execute('ChangeProperty',
            prop_path='/World/tCamera' + str(self.cam_count)+'.xformOp:translate',
            value=Gf.Vec3f(camera_pos[0], camera_pos[1], camera_pos[2]),
            prev=None)

        self.cam_count += 1
    
    def cam_sel_helper(self, c):
        self.viewport_api.camera_path = str(c.GetPath())
        
    def forward_vec(self):
        camera = UsdGeom.Camera(omni.usd.get_prim_at_path(self.viewport_api.camera_path)) 
        print(camera.GetCamera().frustum.ComputeViewDirection()) 
        return camera.GetCamera().frustum.ComputeViewDirection()
    def cam_position(self):
        try:
            camera_pos = omni.usd.get_prim_at_path(self.viewport_api.camera_path).GetAttribute('xformOp:transform').Get()[3]
            print(camera_pos)
        except:
            camera_pos = omni.usd.get_prim_at_path(self.viewport_api.camera_path).GetAttribute('xformOp:translate').Get()
            print(camera_pos)
        return camera_pos