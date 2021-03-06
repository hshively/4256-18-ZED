from math import acos, radians, degrees
def lowest_angle_for(depth, camera_properties, radians = False):# depth and height must be in same units
    '''Imagine that the camera lies at the center of a circle with radius depth.
    That circle intersects the ground at some point, P. This function returns the
    angle between the lower boundary of the camera's vertical_fov and point P.'''
    plumb_to_vFOVboundary = camera_properties.get_lens_to_ground_angle() - camera_properties.get_vertical_fov()/2.0
    if plumb_to_vFOVboundary < 90:
        big_angle = acos(camera_properties.height/float(depth))#TODO make sure acos is given values between -1 and 1
        lowest_angle = degrees(big_angle) - plumb_to_vFOVboundary
        return radians(lowest_angle) if radians else lowest_angle
    else:
        return 0.0


class CameraProperties(object):
    def __init__(self, height, lens_to_ground_angle = 90.0, vertical_fov = 90.0):
        self.height = float(height)
        self.lens_to_ground_angle = float(lens_to_ground_angle)
        self.vertical_fov = float(vertical_fov)
    def get_lens_to_ground_angle(self, radians = False):
        return radians(self.lens_to_ground_angle) if radians else self.lens_to_ground_angle
    def get_vertical_fov(self, radians = False):
        return radians(self.vertical_fov) if radians else self.vertical_fov

import numpy as np
from math import ceil
class DepthMap(object):
    def __init__(self, depth_map):
        self.depth_map = depth_map.copy()
        self.depth_map[self.depth_map == np.inf] = np.nan
        self.depth_map[self.depth_map == np.NINF] = np.nan
        self.height, self.width = depth_map.shape[:2]
        self.min, self.max = np.nanmin(self.depth_map), np.nanmax(self.depth_map)
        self.depth_map[np.isnan(self.depth_map)] = 0

    def enable_bird(self, resolution, camera_properties, save_config = False, load_config = False):
        if load_config:
            self.config = np.load('DepthMap.config_res{}.npy'.format(resolution)).item()

        else:
            self.config = {'resolution' : resolution, 'section_size' : (self.max - self.min)/float(resolution)}# don't use .ptp(), already have .max and .min
            height_scale = 255 - np.linspace(0, 255, num = self.height, endpoint = True)
            height_to_color = np.zeros((self.height, self.width, resolution), dtype = 'uint8')
            for i in range(resolution):
                section_depth = self.min + (i + .5)*self.config['section_size']# won't be precisely the mean depth, but close enough
                minimumY = self.height*(lowest_angle_for(section_depth, camera_properties)/camera_properties.get_vertical_fov())# basically maxY*(% of the way up)
                minimumY = self.height - ceil(minimumY)# do subtraction since y axis is inverted in images
                height_to_color[:minimumY,:,i] = height_scale[-minimumY:, None]# fill columns with counting numbers, beginning at minimumY
            self.config['height_to_color'] = height_to_color

            if save_config:
                np.save('DepthMap.config_res{}.npy'.format(resolution), self.config)

    def bird_independent(self, resolution):
        section_size = (self.max - self.min)/float(resolution)# could use .ptp() instead of .max() - .min()
        sections = np.zeros((self.height, self.width, resolution), dtype = 'uint32')
        for i in range(resolution):
            indices = np.logical_and((self.depth_map >= self.min + i*section_size), (self.depth_map < self.min + (i + 1)*section_size))
            sections[indices, i] = 1
        return sections.sum(axis = 0).transpose()

    def bird_height_aware(self):
        resolution = self.config['resolution']
        section_size = self.config['section_size']
        sections = np.zeros((self.height, self.width, resolution), dtype = 'float16')
        for i in range(resolution):
            indices = np.logical_and((self.depth_map >= self.min + i*section_size), (self.depth_map < self.min + (i + 1)*section_size))
            sections[indices, i] = 1
        sections *= self.config['height_to_color']
        sections = np.ma.masked_array(sections, sections == 0)
        result = np.mean(sections, axis = 0).transpose()
        return result.filled(0)


if __name__ == '__main__':
    '''This is meant to be used for debugging purposes; works with any depth map image.'''
    import cv2
    import time
    #{Prepare depth map from file}
    depth_map = cv2.imread("Map.jpg", 0).astype('float32')#np.load('sample depth map.npy')# get grayscale depth map
    #{Prepare for conversion}
    smart_depth_map = DepthMap(depth_map)
    smart_depth_map.enable_bird(20, CameraProperties(2.0))

    #{Do the conversion}
    start_time = time.time()
    # top_view = smart_depth_map.bird_independent(10)
    top_view = smart_depth_map.bird_height_aware()
    conversion_time = time.time() - start_time
    print('The conversion took {} seconds'.format(conversion_time))

    #{Prepare vars and resize}
    desired_height = 200
    result = cv2.resize(top_view.astype('uint8'), (depth_map.shape[1], desired_height), interpolation = cv2.INTER_LINEAR)# stretch the height

    #{Display}
    depth_map[~np.isfinite(depth_map)] = smart_depth_map.min
    depth_map -= smart_depth_map.min
    cv2.imshow('Depth Map', (depth_map*255/depth_map.max()).astype('uint8'))
    cv2.imshow('Top View', result)
    cv2.waitKey(0)
