import omni.ext

from pxr import Sdf, Gf, UsdGeom, Usd
import math

def translate(x,y,z):
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
    
    def ortho_helper(self,option,current_target=None):

        if current_target is None:
            return 

        camera = omni.usd.get_prim_at_path(self.viewport_api.camera_path)

        target_pos = current_target.GetAttribute('xformOp:translate').Get()
        x_pos = target_pos[0]
        y_pos = target_pos[1]
        z_pos = target_pos[2]
        target_rot = current_target.GetAttribute(UsdGeom.Xformable(current_target).GetOrderedXformOps()[1].GetOpName()).Get()[2]

        order = UsdGeom.Xformable(camera).GetOrderedXformOps()
        order_list = []
        for a in order:
            order_list.append(a.GetOpName())

        focusdistance = max(400, self.get_selected_cam_attribute('focusDistance'))

        if 'xformOp:transform' not in order_list:
            if option == "top":
                print("ortho top")
                camera.GetAttribute('xformOp:translate').Set(Gf.Vec3d(x_pos,y_pos,z_pos+focusdistance))
                camera.GetAttribute(UsdGeom.Xformable(camera).GetOrderedXformOps()[1].GetOpName()).Set(Gf.Vec3d(0,0.0,target_rot))
            elif option == "front":
                print("ortho front")
                camera.GetAttribute('xformOp:translate').Set(Gf.Vec3d(x_pos+focusdistance*math.cos(target_rot*math.pi/180),y_pos+focusdistance*math.sin(target_rot*math.pi/180),z_pos))
                camera.GetAttribute(UsdGeom.Xformable(camera).GetOrderedXformOps()[1].GetOpName()).Set(Gf.Vec3d(90,0.0,90+target_rot))
            elif option == "right":
                print("ortho right")
                camera.GetAttribute('xformOp:translate').Set(Gf.Vec3d(x_pos-focusdistance*math.sin(target_rot*math.pi/180),y_pos+focusdistance*math.cos(target_rot*math.pi/180),z_pos))
                camera.GetAttribute(UsdGeom.Xformable(camera).GetOrderedXformOps()[1].GetOpName()).Set(Gf.Vec3d(90,0,180+target_rot))

        else:
            print("pass in transform matrix")
            print("prev transform matrix", self.get_selected_cam_attribute('xformOp:transform'))

            if option == "top":
                x_rot = x_rotation(0)
                z_rot = z_rotation(target_rot*math.pi/180)
                translate_matrix = translate(x_pos,y_pos,z_pos+focusdistance)

                pass_transform_matrix(camera, x_rot, z_rot, translate_matrix)

                print('after top transform matrix', camera.GetAttribute('xformOp:transform').Get())

            elif option == "front":
                x_rot = x_rotation(math.pi/2)

                z_rot = z_rotation((90+target_rot)*math.pi/180)

                translate_matrix =  translate(x_pos+focusdistance*math.cos(target_rot*math.pi/180),y_pos+focusdistance*math.sin(target_rot*math.pi/180),z_pos)

                pass_transform_matrix(camera, x_rot, z_rot, translate_matrix)

                print('after front transform matrix', camera.GetAttribute('xformOp:transform').Get())

            elif option == "right":
                x_rot = x_rotation(math.pi/2)

                z_rot = z_rotation((180+target_rot)*math.pi/180)

                translate_matrix = translate(x_pos-focusdistance*math.sin(target_rot*math.pi/180),y_pos+focusdistance*math.cos(target_rot*math.pi/180),z_pos)

                pass_transform_matrix(camera, x_rot, z_rot, translate_matrix)
                
                print('\n~~~~~~~~~~~~~~~~~~~~~~~\n','After right transform matrix:\n',
                 camera.GetAttribute('xformOp:transform').Get())
    

        self.persp_to_orth()

    def iso_helper(self, angle:str, current_target=None):
        if current_target is None:
            return 

        camera=omni.usd.get_prim_at_path(self.viewport_api.camera_path)
        target_pos = current_target.GetAttribute('xformOp:translate').Get()
        x_pos = target_pos[0]
        y_pos = target_pos[1]
        z_pos = target_pos[2]
        target_rot = current_target.GetAttribute(UsdGeom.Xformable(current_target).GetOrderedXformOps()[1].GetOpName()).Get()[2]

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
        x_trans = proj_dist*math.sqrt(2)*math.cos((45+target_rot)*math.pi/180)
        y_trans = proj_dist*math.sqrt(2)*math.sin((45+target_rot)*math.pi/180)

        if 'xformOp:transform' not in order_list:
            if angle == "NW":
                camera.GetAttribute('xformOp:translate').Set(Gf.Vec3d(x_pos-y_trans, y_pos+x_trans, z_pos+proj_dist))
                camera.GetAttribute('xformOp:rotateXYZ').Set(Gf.Vec3d(90-180*math.atan(1/math.sqrt(2))/math.pi,0,225+target_rot))
            elif angle == "NE":
                camera.GetAttribute('xformOp:translate').Set(Gf.Vec3d(x_pos+x_trans, y_pos+y_trans, z_pos+proj_dist))
                camera.GetAttribute('xformOp:rotateXYZ').Set(Gf.Vec3d(90-180*math.atan(1/math.sqrt(2))/math.pi,0,135+target_rot))
            elif angle == "SE":
                camera.GetAttribute('xformOp:translate').Set(Gf.Vec3d(x_pos+y_trans, y_pos-x_trans, z_pos+proj_dist))
                camera.GetAttribute('xformOp:rotateXYZ').Set(Gf.Vec3d(90-180*math.atan(1/math.sqrt(2))/math.pi,0,45+target_rot))
            elif angle == "SW":
                camera.GetAttribute('xformOp:translate').Set(Gf.Vec3d(x_pos-x_trans, y_pos-y_trans, z_pos+proj_dist))
                camera.GetAttribute('xformOp:rotateXYZ').Set(Gf.Vec3d(90-180*math.atan(1/math.sqrt(2))/math.pi,0,315+target_rot))
        
        else:
            print("pass in transform matrix")
            print("prev transform matrix", camera.GetAttribute('xformOp:transform').Get())
            x_rot = x_rotation(math.pi/2-math.atan(1/math.sqrt(2)))

            if angle == "NW":
                z_rot = z_rotation((225+target_rot)*math.pi/180)
                translate_matrix = translate(x_pos-y_trans, y_pos+x_trans, z_pos+proj_dist)

                pass_transform_matrix(camera, x_rot, z_rot, translate_matrix)
                print('after NW transform matrix', camera.GetAttribute('xformOp:transform').Get())

            elif angle == "NE":
                z_rot = z_rotation((135+target_rot)*math.pi/180)
                translate_matrix = translate(x_pos+x_trans, y_pos+y_trans, z_pos+proj_dist)

                pass_transform_matrix(camera, x_rot, z_rot, translate_matrix)
                print('after NE transform matrix', camera.GetAttribute('xformOp:transform').Get())

            elif angle == "SE":
                z_rot = z_rotation((45+target_rot)*math.pi/180)
                translate_matrix = translate(x_pos+y_trans, y_pos-x_trans, z_pos+proj_dist)

                pass_transform_matrix(camera, x_rot, z_rot, translate_matrix)
                print('after SE transform matrix', camera.GetAttribute('xformOp:transform').Get())

            elif angle == "SW":
                z_rot = z_rotation((315+target_rot)*math.pi/180)
                translate_matrix = translate(x_pos-x_trans, y_pos-y_trans, z_pos+proj_dist)
                
                pass_transform_matrix(camera, x_rot, z_rot, translate_matrix)
                print('after SW transform matrix', camera.GetAttribute('xformOp:transform').Get())


        self.persp_to_orth()

    def create_cam_helper(self):
        omni.kit.commands.execute('CreatePrimWithDefaultXform',
            prim_type='Camera', prim_path='/World/Camera' + str(self.cam_count),
            attributes={'focusDistance': 400, 'focalLength': 24},
            select_new_prim=True)
        try:
            camera_pos = omni.usd.get_prim_at_path(self.viewport_api.camera_path).GetAttribute('xformOp:transform').Get()[3]
            print(camera_pos)
        except:
            camera_pos = omni.usd.get_prim_at_path(self.viewport_api.camera_path).GetAttribute('xformOp:translate').Get()
            print(camera_pos)

        omni.kit.commands.execute('ChangeProperty',
            prop_path='/World/tCamera' + str(self.cam_count)+'.xformOp:translate',
            value=Gf.Vec3f(camera_pos[0], camera_pos[1], camera_pos[2]),
            prev=None)

        self.cam_count += 1
        print(self.cam_count)
    
    def cam_sel_helper(self, c):
        self.viewport_api.camera_path = str(c.GetPath())
        