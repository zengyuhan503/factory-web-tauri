'''
Author: leven
LastEditors: leven
Description: 已知两个RGB相机的内外参，在原始标定采集图像上绘制极线，并计算极线约束误差
'''
import sys
import getopt
import os
import cv2 as cv
import numpy as np
# from skimage import morphology
import random
import math as math
import x10_5_1_Tool_GT_Calib_Parse as GtCalibParser
from x1_opencv.x0_base.x10_1_opencv_0_base import ScaleDrawer as ScaleDrawer
from x0_common.x2_file.x10_0_common_2_file import findSubdirWithSuffix, findSubFileWithSuffix
from x10_6_0_Tool_GT_Calib_detect_circle_feature import CircleFeatureDectector
from x10_6_0_Tool_GT_Calib_CxxLibHelper import CxxCircleFeatureOne, CTCalibCxxLibHelper
import time
from scipy.spatial.transform import Rotation
import threading
import ctypes
'''
    1)读取标定参数，得到RGB相机内参和外参
    2)读取，同一时刻左右相机标定图像
    3)在Rgb-L和Rgb-R上检测圆心并作匹配（暂时只作简单检测，不作匹配）
    4)对原始图像作去畸变操作，对检测的圆心特征作去畸变操作
    5-1)基于Rgb-L特征在Rgb-R上计算极线；基于Rgb-R特征在Rgb-L上计算极线
    5-2)计算极线约束误差
    5-3)绘制极线
'''

gOriImgTag = "origin_img"
gDebugImgTag = "debug_img"

mScaleXY = (1.0 , 1.0)
mScaleDrawer = ScaleDrawer(mScaleXY[0], mScaleXY[1])
mScaleDrawerDefault = ScaleDrawer(1.0, 1.0)

#相机对应畸变模型是多项式模型否？
# mCameraIsRadial = { 0:False, 1:False, 2:False, 3:False, 4:True, 5:True }

'''
description: 相机内外参数和畸变参数
return {*}
'''
class CameraModel:

    def __init__(self):        
        self.isBuild = False
        pass

    '''
    description: 根据原始标定文件数据构造相机模型对象
    '''    
    def buildByCameraInfo(self, cameraInfo, isRgb, isRadial):

        self.id = cameraInfo.id
        self.h = cameraInfo.size[1]
        self.w = cameraInfo.size[0]

        # 相机内参
        self.K = np.array([[cameraInfo.focal_length[0], 0, cameraInfo.principal_point[0]],
                            [0, cameraInfo.focal_length[1], cameraInfo.principal_point[1]],
                            [0, 0, 1]])

        # self.undisAlpha = 0.5
        # self.undisAlpha = 0.0
        self.undisAlpha = 1.0
        self.isRgb = isRgb

        # 畸变参数
        if (isRadial): #多项式畸变模型
            self.isRadial = True
            self.D = np.zeros((8), dtype=float)
            idxTmp = [0,1,4,5,6,7]
            for idx in range(6):
                self.D[idxTmp[idx]] = cameraInfo.radial_distortion[idx]
            self.newK, roi = cv.getOptimalNewCameraMatrix(self.K, self.D, (int(self.w), int(self.h)), alpha = self.undisAlpha, newImgSize = (int(self.w), int(self.h)))
            self.mapx2, self.mapy2 = cv.initUndistortRectifyMap(self.K, self.D, np.eye(3), self.newK, (int(self.w), int(self.h)), cv.CV_32F)

            if(False): #从值上对此查看畸变映射差异

                #正向畸变映射关系
                print("正向畸变映射关系")
                map_center_x = 72
                map_center_y = 1367
                map_range = 5

                from_u = np.array([ u for u in range(map_center_x, map_center_x + map_range)]).reshape(1,-1)
                from_v = np.array([ v for v in range(map_center_y, map_center_y + map_range)]).reshape(1,-1)
                print("from_uv=")
                print(" "*10, from_u)
                print(from_v.T)

                print("mapx2 shape={}, info:".format(self.mapx2.shape))                                
                # print(self.mapx2[map_center_x:(map_center_x+map_range), map_center_y:(map_center_y+map_range)])
                print(self.mapx2[map_center_y:(map_center_y+map_range), map_center_x:(map_center_x+map_range)])                
                print("mapy2 shape={}, info:".format(self.mapy2.shape))
                # print(self.mapy2[map_center_x:(map_center_x+map_range), map_center_y:(map_center_y+map_range)])
                print(self.mapy2[map_center_y:(map_center_y+map_range), map_center_x:(map_center_x+map_range)])
                print("-"*100)


                print("逆向迭代去畸变")

                iter_center_x = 107
                iter_center_y = 1339
                iter_range = 5

                from_u_dist = np.array([ u for u in range(iter_center_x, iter_center_x + iter_range)]).reshape(1,-1)
                from_v_dist = np.array([ v for v in range(iter_center_y, iter_center_y + iter_range)]).reshape(1,-1)
                print("from_uv_dist=")
                print(" "*10, from_u_dist)
                print(from_v_dist.T)


                from_uv_dist = []
                for v_dist in from_v_dist[0,:]:
                    for u_dist in from_u_dist[0,:]:
                        from_uv_dist.append([u_dist, v_dist])
                from_uv_dist = np.array(from_uv_dist).astype(float)
                from_uv_undist = cv.undistortPoints(from_uv_dist, self.K, self.D, np.eye(3), self.newK)

                #把结果按mapx和mapy形式排列表达
                mapx_inv = np.empty((iter_range,iter_range),dtype=float)
                mapy_inv = np.empty((iter_range,iter_range),dtype=float)
                for idy in range(iter_range):
                    for idx in range(iter_range):
                        mapx_inv[idy, idx] = from_uv_undist[idy*iter_range + idx][0][0]
                        mapy_inv[idy, idx] = from_uv_undist[idy*iter_range + idx][0][1]

                # print("from_uv_undist=")
                # print(from_uv_undist)

                print("mapx_inv info:")
                print(mapx_inv)
                print("mapy_inv info:")
                print(mapy_inv)                

                print("-"*100)


        else:       #鱼眼畸变模型
            self.isRadial = False
            self.D = cameraInfo.radial_distortion[0:4]
            if(self.isRgb):
                self.newK = cv.fisheye.estimateNewCameraMatrixForUndistortRectify(self.K, self.D, (int(self.w), int(self.h)), np.eye(3), balance=self.undisAlpha, new_size=(int(self.w), int(self.h)), fov_scale=(self.undisAlpha + 0.7))
            else:
                self.newK = cv.fisheye.estimateNewCameraMatrixForUndistortRectify(self.K, self.D, (int(self.w), int(self.h)), np.eye(3), balance=self.undisAlpha, new_size=(int(self.w), int(self.h)), fov_scale=1.0)

            self.mapx2, self.mapy2 = cv.fisheye.initUndistortRectifyMap(self.K, self.D, np.eye(3), self.newK, (int(self.w), int(self.h)), cv.CV_32F)

        self.R = np.array([[cameraInfo.rowMajorRotationMat[0], cameraInfo.rowMajorRotationMat[1], cameraInfo.rowMajorRotationMat[2]],
                            [cameraInfo.rowMajorRotationMat[3], cameraInfo.rowMajorRotationMat[4], cameraInfo.rowMajorRotationMat[5]],
                            [cameraInfo.rowMajorRotationMat[6], cameraInfo.rowMajorRotationMat[7], cameraInfo.rowMajorRotationMat[8]]])
        
        self.t = np.array([[cameraInfo.translation[0]],
                            [cameraInfo.translation[1]],
                            [cameraInfo.translation[2]]])
        
        self.isBuild = True
    
    def undistorImg(self, img, doDebug3 = False):
        if(self.isRadial):
            undistorted_image = cv.remap(img, self.mapx2, self.mapy2, interpolation=cv.INTER_LINEAR,
                                                    borderMode = cv.BORDER_CONSTANT)
            # undistorted_image2 = cv.undistort(img, self.K, self.D, np.eye(3), self.newK)
        else:
            undistorted_image = cv.remap(img, self.mapx2, self.mapy2, interpolation=cv.INTER_LINEAR,
                                                    borderMode = cv.BORDER_CONSTANT)            
            # undistorted_image2 = cv.fisheye.undistortImage(img, self.K, self.D, np.eye(3), self.newK, (int(self.w), int(self.h)))
        
        if(doDebug3):
            print("K=\n", self.K)
            # print("D=\n", np.array([0.0,0.0,0.0,0.0]))
            debugImg = np.hstack((img, undistorted_image))
            cv.namedWindow("dist_comp", cv.WINDOW_NORMAL)
            cv.imshow("dist_comp", debugImg)
            # cv.waitKey(0)

        return undistorted_image

    def undistorPoints(self, img, pts, seq_id1):
        global mScaleXY
        global mScaleDrawer
        if(self.isRadial):
            #对原始图去畸变，便于debug查看
            undistorted_image = cv.remap(img, self.mapx2, self.mapy2, interpolation=cv.INTER_LINEAR,
                                                    borderMode = cv.BORDER_CONSTANT)
            # undistorted_image2 = cv.undistort(img, self.K, self.D, np.eye(3), self.newK)
            undistorted_image2 = undistorted_image
            #对圆心特征点去畸变
            undistorted_pts = cv.undistortPoints(pts, self.K, self.D, np.eye(3), self.newK)
            # if(contour203_pts.size != 0):
            # # if(not contour203_pts.empty()):
            #     undistorted_contour203_pts = cv.undistortPoints(contour203_pts, self.K, self.D, np.eye(3), self.newK)

        else:
            #对原始图去畸变，便于debug查看
            undistorted_image = cv.remap(img, self.mapx2, self.mapy2, interpolation=cv.INTER_LINEAR,
                                                    borderMode = cv.BORDER_CONSTANT)
            # undistorted_image2 = cv.fisheye.undistortImage(img, self.K, self.D, np.eye(3), self.newK, (int(self.w), int(self.h)))
            undistorted_image2 = undistorted_image

            #圆心特征数据格式需要修改一下，以适用鱼眼去畸变接口
            pts_fix = np.array([[[pts[idx][0],pts[idx][1]]] for idx in range(pts.shape[0])])                                 
            #对圆心特征点去畸变
            undistorted_pts = cv.fisheye.undistortPoints(pts_fix, self.K, self.D, np.eye(3), self.newK)

            # if(contour203_pts.size != 0):
            #     contour203_pts_fix = np.array([[[contour203_pts[idx][0],contour203_pts[idx][1]]] for idx in range(contour203_pts.shape[0])])
            #     undistorted_contour203_pts = cv.fisheye.undistortPoints(contour203_pts_fix, self.K, self.D, np.eye(3), self.newK)

        # # #在原始图像上显示原始点
        # if(True):
        #     img_copy = img.copy()
        #     ori_pts_copy = pts.reshape(-1,1,2)              
        #     print("ori_pts_copy shape=", ori_pts_copy.shape, ", dtype=", ori_pts_copy.dtype)
        #     for idx in range(len(ori_pts_copy)):
        #         cv.circle(img_copy, (int(ori_pts_copy[idx][0][0]), int(ori_pts_copy[idx][0][1])), 1, (255,255,0), 1)
        #         # img_copy[int(ori_pts_copy[idx][0][1])][int(ori_pts_copy[idx][0][0])] = (255,255,0)

        #     img_ori_pts_copy = img_copy.copy()

        #     for idx in range(len(ori_pts_copy)):
        #         contour_info0 = "{}".format(seq_id1[idx])
        #         cv.putText(img_copy, contour_info0, (int(ori_pts_copy[idx][0][0]), int(ori_pts_copy[idx][0][1])), cv.FONT_HERSHEY_SIMPLEX,0.3 if self.isRadial else 0.2,color=(0,0,255),thickness=1)

        #     cv.namedWindow("pts_on_img", cv.WINDOW_NORMAL)
        #     cv.imshow("pts_on_img", img_copy)
        #     cv.waitKey(0) 

        # #在原始图像上显示原始点
        if(False):
            img_copy = cv.resize(img, None, fx = mScaleXY[0], fy = mScaleXY[1])
            ori_pts_copy = pts.reshape(-1,1,2)              
            print("ori_pts_copy shape=", ori_pts_copy.shape, ", dtype=", ori_pts_copy.dtype)
            for idx in range(len(ori_pts_copy)):
                # cv.circle(img_copy, (int(ori_pts_copy[idx][0][0]), int(ori_pts_copy[idx][0][1])), 1, (255,255,0), 1)
                mScaleDrawer.scale_circle(img_copy, (int(ori_pts_copy[idx][0][0]), int(ori_pts_copy[idx][0][1])), 1, (255,255,0), 1)
                # img_copy[int(ori_pts_copy[idx][0][1])][int(ori_pts_copy[idx][0][0])] = (255,255,0)

            # img_ori_pts_copy = img_copy.copy()

            for idx in range(len(ori_pts_copy)):
                contour_info0 = "{}_{}".format(seq_id1[idx][0], seq_id1[idx][1])
                # cv.putText(img_copy, contour_info0, (int(ori_pts_copy[idx][0][0]), int(ori_pts_copy[idx][0][1])), cv.FONT_HERSHEY_SIMPLEX,0.3 if self.isRadial else 0.2,color=(0,0,255),thickness=1)
                mScaleDrawer.scale_putText(img_copy, contour_info0, (int(ori_pts_copy[idx][0][0]), int(ori_pts_copy[idx][0][1])), cv.FONT_HERSHEY_SIMPLEX,0.38 ,color=(0,0,255),thickness=1)

            cv.namedWindow("pts_on_img", cv.WINDOW_NORMAL)
            cv.imshow("pts_on_img", img_copy)
            cv.waitKey(0) 

        #在去畸变后图像上显示原始点
        if(False):
            undistorted_image2_copy = cv.resize(undistorted_image2, None, fx = mScaleXY[0], fy = mScaleXY[1])
            ori_pts_copy = pts.reshape(-1,1,2)
            print("ori_pts_copy shape=", ori_pts_copy.shape, ", dtype=", ori_pts_copy.dtype)
            for idx in range(len(ori_pts_copy)):
                mScaleDrawer.scale_circle(undistorted_image2_copy, (int(ori_pts_copy[idx][0][0]), int(ori_pts_copy[idx][0][1])), 1, (0,255,0), 1)
                # undistorted_image2_copy[int(ori_pts_copy[idx][0][1])][int(ori_pts_copy[idx][0][0])] = (0,255,0)
                contour_info0 = "{}_{}".format(seq_id1[idx][0], seq_id1[idx][1])
                mScaleDrawer.scale_putText(undistorted_image2_copy, contour_info0, (int(ori_pts_copy[idx][0][0]), int(ori_pts_copy[idx][0][1])), cv.FONT_HERSHEY_SIMPLEX,0.38,color=(0,0,255),thickness=1)

            cv.namedWindow("pts_on_img", cv.WINDOW_NORMAL)
            cv.imshow("pts_on_img", undistorted_image2_copy)
            cv.waitKey(0)            
        
        #在去畸变后图像上显示去畸变后点
        if(False):
            undistorted_image2_copy2 = cv.resize(undistorted_image2, None, fx = mScaleXY[0], fy = mScaleXY[1])
            print("undistorted_pts shape=", undistorted_pts.shape, ", dtype=", undistorted_pts.dtype)
            for idx in range(len(undistorted_pts)):
                mScaleDrawer.scale_circle(undistorted_image2_copy2, (int(undistorted_pts[idx][0][0]), int(undistorted_pts[idx][0][1])), 1, (0,255,0), 1)
                # undistorted_image2[int(undistorted_pts[idx][0][1])][int(undistorted_pts[idx][0][0])] = (0,255,0)
                contour_info0 = "{}_{}".format(seq_id1[idx][0], seq_id1[idx][1])
                mScaleDrawer.scale_putText(undistorted_image2_copy2, contour_info0, (int(undistorted_pts[idx][0][0]), int(undistorted_pts[idx][0][1])), cv.FONT_HERSHEY_SIMPLEX,0.38,color=(0,0,255),thickness=1)

            # #显示203号轮廓
            # if(contour203_pts.size != 0):
            #     color = (0,255,255)
            #     for point in undistorted_contour203_pts:
            #         # undistorted_image2[int(point[0][1]), int(point[0][0])] = color
            #         mScaleDrawer.scal_drawDot(undistorted_image2_copy2, (int(point[0][0]), int(point[0][1])), color)

            cv.namedWindow("pts_on_img", cv.WINDOW_NORMAL)
            cv.imshow("pts_on_img", undistorted_image2_copy2)
            cv.waitKey(0)

        # #在原始图上加上圆心点后作去畸变，去畸变后图像上显示去畸变后点
        # if(True):
        #     if(self.isRadial):
        #         undistorted_img_ori_pts_copy = cv.undistort(img_ori_pts_copy, self.K, self.D, np.eye(3), self.newK)
        #     else:
        #         undistorted_img_ori_pts_copy = cv.fisheye.undistortImage(img_ori_pts_copy, self.K, self.D, np.eye(3), self.newK, (int(self.w), int(self.h)))
        #     print("undistorted_pts shape=", undistorted_pts.shape, ", dtype=", undistorted_pts.dtype)
        #     for idx in range(len(undistorted_pts)):
        #         cv.circle(undistorted_img_ori_pts_copy, (int(undistorted_pts[idx][0][0]), int(undistorted_pts[idx][0][1])), 1, (0,255,0), 1)
        #         # undistorted_img_ori_pts_copy[int(undistorted_pts[idx][0][1])][int(undistorted_pts[idx][0][0])] = (0,255,0)
        #         contour_info0 = "{}".format(seq_id1[idx])
        #         # cv.putText(undistorted_img_ori_pts_copy, contour_info0, (int(undistorted_pts[idx][0][0]), int(undistorted_pts[idx][0][1])), cv.FONT_HERSHEY_SIMPLEX,0.3,color=(0,0,255),thickness=1)

        #     cv.namedWindow("undistorted_img_ori_pts_copy", cv.WINDOW_NORMAL)
        #     cv.imshow("undistorted_img_ori_pts_copy", undistorted_img_ori_pts_copy)
        #     cv.waitKey(0)  

        #在原始图上加上圆心点后作去畸变，去畸变后图像上显示去畸变后点
        if(True):

            img_copy = img.copy()
            ori_pts_copy = pts.reshape(-1,1,2)
            for idx in range(len(ori_pts_copy)):
                # cv.circle(img_copy, (int(ori_pts_copy[idx][0][0]), int(ori_pts_copy[idx][0][1])), 1, (255,255,0), 1)
                mScaleDrawerDefault.scale_circle(img_copy, (int(ori_pts_copy[idx][0][0]), int(ori_pts_copy[idx][0][1])), 1, (255,255,0), 1)
                # img_copy[int(ori_pts_copy[idx][0][1])][int(ori_pts_copy[idx][0][0])] = (255,255,0)
            img_ori_pts_copy = img_copy


            if(self.isRadial):
                undistorted_img_ori_pts_copy = cv.undistort(img_ori_pts_copy, self.K, self.D, np.eye(3), self.newK)
            else:
                undistorted_img_ori_pts_copy = cv.fisheye.undistortImage(img_ori_pts_copy, self.K, self.D, np.eye(3), self.newK, (int(self.w), int(self.h)))
            undistorted_img_ori_pts_copy = cv.resize(undistorted_img_ori_pts_copy, None, fx = mScaleXY[0], fy = mScaleXY[1])

            print("undistorted_pts shape=", undistorted_pts.shape, ", dtype=", undistorted_pts.dtype)
            for idx in range(len(undistorted_pts)):
                mScaleDrawer.scale_circle(undistorted_img_ori_pts_copy, (int(undistorted_pts[idx][0][0]), int(undistorted_pts[idx][0][1])), 1, (0,0,255), 1)
                # undistorted_img_ori_pts_copy[int(undistorted_pts[idx][0][1])][int(undistorted_pts[idx][0][0])] = (0,255,0)
                contour_info0 = "{}_{}".format(seq_id1[idx][0], seq_id1[idx][1])
                # cv.putText(undistorted_img_ori_pts_copy, contour_info0, (int(undistorted_pts[idx][0][0]), int(undistorted_pts[idx][0][1])), cv.FONT_HERSHEY_SIMPLEX,0.3,color=(0,0,255),thickness=1)

            cv.namedWindow("undistorted_img_ori_pts_copy", cv.WINDOW_NORMAL)
            cv.imshow("undistorted_img_ori_pts_copy", undistorted_img_ori_pts_copy)
            cv.waitKey(0)  

        return undistorted_pts

    '''
    description: 对输入的点列表作整体去畸变
    param {*} self
    param {*} img
    param {*} pts
    param {*} seq_id1
    return {*}
    '''
    def undistorPoints2(self, pts, doDebug = [False, None, "tag"]):

        global mScaleXY
        global mScaleDrawer
        
        if(self.isRadial):
            #对圆心特征点去畸变
            undistorted_pts = cv.undistortPoints(pts, self.K, self.D, np.eye(3), self.newK)
        else:
            #圆心特征数据格式需要修改一下，以适用鱼眼去畸变接口
            pts_fix = np.array([[[pts[idx][0],pts[idx][1]]] for idx in range(pts.shape[0])])                                 
            #对圆心特征点去畸变
            undistorted_pts = cv.fisheye.undistortPoints(pts_fix, self.K, self.D, np.eye(3), self.newK)

        #在原始图上加上圆心点后作去畸变，去畸变后图像上显示去畸变后点
        if(doDebug[0]):

            img_copy = doDebug[1].copy()
            ori_pts_copy = pts.reshape(-1,1,2)
            for idx in range(len(ori_pts_copy)):
                # cv.circle(img_copy, (int(ori_pts_copy[idx][0][0]), int(ori_pts_copy[idx][0][1])), 1, (255,255,0), 1)
                mScaleDrawerDefault.scale_circle(img_copy, (int(ori_pts_copy[idx][0][0]), int(ori_pts_copy[idx][0][1])), 1, (255,255,0), 1)
                # img_copy[int(ori_pts_copy[idx][0][1])][int(ori_pts_copy[idx][0][0])] = (255,255,0)
            img_ori_pts_copy = img_copy


            if(self.isRadial):
                undistorted_img_ori_pts_copy = cv.undistort(img_ori_pts_copy, self.K, self.D, np.eye(3), self.newK)
            else:
                undistorted_img_ori_pts_copy = cv.fisheye.undistortImage(img_ori_pts_copy, self.K, self.D, np.eye(3), self.newK, (int(self.w), int(self.h)))
            undistorted_img_ori_pts_copy = cv.resize(undistorted_img_ori_pts_copy, None, fx = mScaleXY[0], fy = mScaleXY[1])

            # print("undistorted_pts shape=", undistorted_pts.shape, ", dtype=", undistorted_pts.dtype)
            for idx in range(len(undistorted_pts)):
                mScaleDrawer.scale_circle(undistorted_img_ori_pts_copy, (int(undistorted_pts[idx][0][0]), int(undistorted_pts[idx][0][1])), 1, (0,0,255), 1)
                # undistorted_img_ori_pts_copy[int(undistorted_pts[idx][0][1])][int(undistorted_pts[idx][0][0])] = (0,255,0)
                # contour_info0 = "{}_{}".format(seq_id1[idx][0], seq_id1[idx][1])
                # cv.putText(undistorted_img_ori_pts_copy, contour_info0, (int(undistorted_pts[idx][0][0]), int(undistorted_pts[idx][0][1])), cv.FONT_HERSHEY_SIMPLEX,0.3,color=(0,0,255),thickness=1)

            cv.namedWindow("{}:undistorted_img_ori_pts_copy".format(doDebug[2]), cv.WINDOW_NORMAL)
            cv.imshow("{}:undistorted_img_ori_pts_copy".format(doDebug[2]), undistorted_img_ori_pts_copy)
            cv.waitKey(1)

        return undistorted_pts

    '''
    description: 计算相对另外相机的几何信息：主要是相对外参，三个欧拉角和平移
    return {*}  [True/False, [相对欧拉角， 相对平移向量]]
    '''    
    def computeGeoInfoToOther(self, other):
        if(other is None):
            print("computeGeoInfoToOther, other is None")
            return [False, None]
        if(self.isBuild == False or other.isBuild == False):
            print("computeGeoInfoToOther, camera is not Build")
            return [False, None]
        radianToDegree = 180.0/math.pi

        relaR = self.R @ other.R.T
        relaT = self.t - relaR @ other.t

        R_r = Rotation.from_matrix(relaR)
        R_q = R_r.as_quat()
        R_v = R_r.as_rotvec()
        R_v_theta = np.linalg.norm(R_v)*radianToDegree

        print(f"R_v={R_v*radianToDegree}, R_v_theta={np.linalg.norm(R_v)*radianToDegree}")
        if(True): #另一种方法算夹角:直接就把正前方的Z轴当作光轴
            axisX = np.array([[0,0,1]], dtype=float)
            axisX = axisX.T
            x1 = self.R @ axisX
            x2 = other.R @ axisX
            x1_n = np.linalg.norm(x1)
            x2_n =(np.linalg.norm(x2))
            if (abs(x1_n - 1) > 0.1 or abs(x2_n - 1) > 0.1):
                print(f"computeGeoInfoToOther err 1,  x1_n={x1_n}, x2_n={x2_n}")
            else:

                x1 = x1 / x1_n
                x2 = x2 / x2_n
                print(f"axisX={axisX.T}")
                print(f"x1={x1.T}\nx2={x2.T}")
                xDot = x1[0][0]*x2[0][0] + x1[1][0]*x2[1][0] + x1[2][0]*x2[2][0]

                if(xDot < -1):
                    xDot = -1
                elif(xDot > 1):
                    xDot = 1

                xTheta = math.acos(xDot)
                xTheta = xTheta*radianToDegree
                print(f"xDot={xDot}, xTheta={xTheta}")


        #计算欧拉角
        R_eula_YXZ = np.array([-1000.0, -1000.0, -1000.0])
        

        # // roll
        cp_sr = 2*(R_q[3]*R_q[2] + R_q[0]*R_q[1])
        cp_cr = 1 - 2*(R_q[0]*R_q[0] + R_q[2]*R_q[2])
        R_eula_YXZ[2] = math.atan2(cp_sr, cp_cr)

        # // pitch 
        sp = 2*(R_q[3]*R_q[0] - R_q[1]*R_q[2])
        if (abs(sp) >= 1):
            R_eula_YXZ[1] = math.copysign(math.pi / 2, sp) # use 90 degrees if out of range
        else:
            R_eula_YXZ[1] = math.asin(sp)

        # // yaw
        cp_sy = 2*(R_q[3]*R_q[1] + R_q[0]*R_q[2])
        cp_cy = 1 - 2*(R_q[0]*R_q[0] + R_q[1]*R_q[1])
        R_eula_YXZ[0] = math.atan2(cp_sy, cp_cy)

        R_eula_YXZ = R_eula_YXZ*radianToDegree

        return [True, [R_v_theta, R_eula_YXZ, relaT]]


'''
description: 带附加圆信息的轮廓
return {*}
'''
class ContoursWithCircle:

    def __init__(self, contour, perimeter, area, alpha, cx, cy):
        self.contour = contour
        self.perimeter = perimeter
        self.area = area
        self.r = math.sqrt(area/math.pi)
        self.alpha = alpha
        self.cx = cx
        self.cy = cy


'''
description: 对图像作分块二值化
            对比度增强；    高斯滤波；  中值滤波；   以灰度均值为阈值作二值化（分块）
return {*}
'''
def block_threshold(image, binary_threshold, sub_height_size = 2, sub_width_size = 2, debug_subimg = False):

    hist_img = cv.equalizeHist(cv.cvtColor(image, cv.COLOR_BGR2GRAY))     #会增加很多噪点

    gauss_blurred_image = cv.GaussianBlur(hist_img, (3, 3), 0)
    # gauss_blurred_image = cv.bilateralFilter(hist_img, d=5, sigmaColor=30, sigmaSpace=30)   #用双边滤波，不要直接用高斯滤波
    # gauss_blurred_image_win_tag = "gauss_blurred_image_{}".format(binary_threshold)   
    gauss_blurred_image_win_tag = "block_gauss_blurred_image"      
    cv.namedWindow(gauss_blurred_image_win_tag, cv.WINDOW_NORMAL)
    cv.imshow(gauss_blurred_image_win_tag, gauss_blurred_image)

    # blurred_image = cv.medianBlur(hist_img, 3)
    blurred_image = cv.medianBlur(gauss_blurred_image, 3)
    # blurred_image_win_tag = "blurred_image_{}".format(binary_threshold)  
    blurred_image_win_tag = "block_blurred_image"
    cv.namedWindow(blurred_image_win_tag, cv.WINDOW_NORMAL)
    cv.imshow(blurred_image_win_tag, blurred_image)

    # blurred_image = image.copy()
    hist_img = blurred_image.copy()

    cv.namedWindow(gDebugImgTag, cv.WINDOW_NORMAL)
    cv.imshow(gDebugImgTag, image)            
    cv.waitKey(0)
    cv.imshow(gDebugImgTag, hist_img)            
    cv.waitKey(0)

    # Split the image into four equal parts
    height, width = hist_img.shape[:2]
    split_height = height // sub_height_size
    split_width = width // sub_width_size

    if(debug_subimg):
        print("image shape={}, split_height={}, split_width={}".format(image.shape, split_height, split_width))

    sub_images = np.empty((split_height, split_width), dtype=object)

    for hId in range(sub_height_size):  #高度方向切块

        if (hId < (sub_height_size-1)):
            height_start = hId*split_height
            height_end = height_start + split_height
            # height_range = [hId*split_height + step_h for step_h in range(split_height)]
        else:                           #在结束边界单独处理
            height_start = hId*split_height
            height_end = height_start + height-hId*split_height
            # height_range = [hId*split_height + step_h for step_h in range(height-hId*split_height)]

        for wId in range(sub_width_size):#宽度方向切块

            if (wId < (sub_width_size-1)):
                width_start = wId*split_width
                width_end = width_start + split_width
                # width_range = [wId*split_width + step_w for step_w in range(split_width)]
            else:                       #在结束边界单独处理
                width_start = wId*split_width
                width_end = width_start + width-wId*split_width                
                # width_range = [wId*split_width + step_w for step_w in range(width-wId*split_width)]

            # print("hId={}, wId={}, \nheight_range={}, \nwidth_range={}".format(hId, wId, height_range, width_range))

            #正式作切块
            sub_images[hId][wId] = hist_img[height_start:height_end, width_start:width_end]
            
            if (debug_subimg):
                print("shape1 = ", hist_img[:split_height, :split_width].shape, ", shape2 = ", sub_images[hId][wId].shape)
                cv.imshow(gDebugImgTag, sub_images[hId][wId])
                cv.waitKey(0)


    # sub_images = [
    #     hist_img[:split_height, :split_width],
    #     hist_img[:split_height, split_width:2*split_width],
    #     hist_img[:split_height, 2*split_width:],

    #     hist_img[split_height:2*split_height, :split_width],
    #     hist_img[split_height:2*split_height, split_width:2*split_width],
    #     hist_img[split_height:2*split_height, 2*split_width:],

    #     hist_img[split_height:, :split_width],
    #     hist_img[split_height:, split_width:]
    # ]

    # Calculate the average gray value for each sub-image and threshold it
    hist_images = []
    thresholded_images = np.empty((split_height, split_width), dtype=object)

    #对子块图作二值化处理
    for hId in range(sub_height_size):
        for wId in range(sub_width_size):
            sub_image = sub_images[hId][wId]

            # gray_img = cv.cvtColor(sub_image, cv.COLOR_BGR2GRAY)
            # hist_img = cv.equalizeHist(cv.cvtColor(sub_image, cv.COLOR_BGR2GRAY))
            # gray_img_mean = np.mean(gray_img)
            hist_img_mean = np.mean(sub_image)

            if(debug_subimg):
                # print("block_gray_img_mean = ", gray_img_mean)
                print("({},{}),block_hist_img_mean = {}".format(hId, wId, hist_img_mean))

            _, thresholded = cv.threshold(sub_image, hist_img_mean*binary_threshold, 255, cv.THRESH_BINARY) 
            
            # 自适应阈值二值化（可以自适应二值化出全图轮廓，效果还行，就是框图外噪点有点多）
            # thresholded = cv.adaptiveThreshold(sub_image,255,cv.ADAPTIVE_THRESH_MEAN_C, cv.THRESH_BINARY,51,2)
            # thresholded = cv.adaptiveThreshold(sub_image,255,cv.ADAPTIVE_THRESH_GAUSSIAN_C, cv.THRESH_BINARY,11,2)

            thresholded_images[hId][wId] = thresholded
            # thresholded_images.append(thresholded)
            # hist_images.append(hist_img)

    #二值化子图块重新拼接成完整二值化大图
    for hId in range(sub_height_size):
        
        for wId in range(sub_width_size):
            if wId == 0:
                concat_row = thresholded_images[hId][0]
            else:
                concat_row = np.hstack((concat_row, thresholded_images[hId][wId]))
        
        if(hId == 0):
            concat_all = concat_row
        else:
            concat_all = np.vstack((concat_all, concat_row))
            
    thresholded_result = concat_all

    # # Concatenate the thresholded images horizontally
    # top_row = np.hstack((thresholded_images[0], thresholded_images[1]))
    # bottom_row = np.hstack((thresholded_images[2], thresholded_images[3]))
    # thresholded_result = np.vstack((top_row, bottom_row))

    # # top_row = np.hstack((hist_images[0], hist_images[1]))
    # # bottom_row = np.hstack((hist_images[2], hist_images[3]))
    # # hist_result = np.vstack((top_row, bottom_row))     

    # return hist_result, thresholded_result

    if(debug_subimg):
        print("image shape=", image.shape, "thresholded_result shape=", thresholded_result.shape)

    return thresholded_result

'''
description: 对图像作分块二值化：阈值分级循环放到本函数内部了
            对比度增强；    高斯滤波；  中值滤波；   以灰度均值为阈值作二值化（分块）
return {*}
'''
def block_threshold2(image, binary_threshold, sub_height_size = 2, sub_width_size = 2, debug_subimg = False):

    binary_threshold_start = 0.2
    binary_threshold_end = 2.0
    binary_threshold_level = 7
    binary_threshold_level_inv = 1.0/binary_threshold_level
    binary_threshold_step = (binary_threshold_end-binary_threshold_start) * binary_threshold_level_inv

    hist_img = cv.equalizeHist(cv.cvtColor(image, cv.COLOR_BGR2GRAY))     #会增加很多噪点

    gauss_blurred_image = cv.GaussianBlur(hist_img, (3, 3), 0)
    # gauss_blurred_image = cv.bilateralFilter(hist_img, d=5, sigmaColor=30, sigmaSpace=30)   #用双边滤波，不要直接用高斯滤波
    # gauss_blurred_image_win_tag = "gauss_blurred_image_{}".format(binary_threshold)   
    gauss_blurred_image_win_tag = "block_gauss_blurred_image"      
    cv.namedWindow(gauss_blurred_image_win_tag, cv.WINDOW_NORMAL)
    cv.imshow(gauss_blurred_image_win_tag, gauss_blurred_image)

    # blurred_image = cv.medianBlur(hist_img, 3)
    blurred_image = cv.medianBlur(gauss_blurred_image, 3)
    # blurred_image = cv.medianBlur(cv.cvtColor(image, cv.COLOR_BGR2GRAY), 3)    
    # blurred_image_win_tag = "blurred_image_{}".format(binary_threshold)  
    blurred_image_win_tag = "block_blurred_image"
    cv.namedWindow(blurred_image_win_tag, cv.WINDOW_NORMAL)
    cv.imshow(blurred_image_win_tag, blurred_image)

    # blurred_image = image.copy()
    hist_img = blurred_image.copy()

    cv.namedWindow(gDebugImgTag, cv.WINDOW_NORMAL)
    cv.imshow(gDebugImgTag, image)            
    cv.waitKey(0)
    cv.imshow(gDebugImgTag, hist_img)            
    cv.waitKey(0)

    # Split the image into four equal parts
    height, width = hist_img.shape[:2]
    split_height = height // sub_height_size
    split_width = width // sub_width_size

    if(debug_subimg):
        print("image shape={}, split_height={}, split_width={}".format(image.shape, split_height, split_width))

    sub_images = np.empty((sub_height_size, sub_width_size), dtype=object)

    for hId in range(sub_height_size):  #高度方向切块

        if (hId < (sub_height_size-1)):
            height_start = hId*split_height
            height_end = height_start + split_height
            # height_range = [hId*split_height + step_h for step_h in range(split_height)]
        else:                           #在结束边界单独处理
            height_start = hId*split_height
            height_end = height_start + height-hId*split_height
            # height_range = [hId*split_height + step_h for step_h in range(height-hId*split_height)]

        for wId in range(sub_width_size):#宽度方向切块

            if (wId < (sub_width_size-1)):
                width_start = wId*split_width
                width_end = width_start + split_width
                # width_range = [wId*split_width + step_w for step_w in range(split_width)]
            else:                       #在结束边界单独处理
                width_start = wId*split_width
                width_end = width_start + width-wId*split_width                
                # width_range = [wId*split_width + step_w for step_w in range(width-wId*split_width)]

            # print("hId={}, wId={}, \nheight_range={}, \nwidth_range={}".format(hId, wId, height_range, width_range))

            #正式作切块
            sub_images[hId][wId] = [hist_img[height_start:height_end, width_start:width_end], [height_start,height_end], [width_start,width_end]]
            
            if (debug_subimg):
                print("shape1 = ", hist_img[:split_height, :split_width].shape, ", shape2 = ", sub_images[hId][wId][0].shape)
                cv.imshow(gDebugImgTag, sub_images[hId][wId][0])
                cv.waitKey(0)

    #对子块图作二值化处理
    thresholded_result_tmp = np.zeros_like(hist_img, dtype=np.uint8)
    for hId in range(sub_height_size):
        for wId in range(sub_width_size):
            sub_image = sub_images[hId][wId][0]

            hist_img_mean = np.mean(sub_image)

            if(debug_subimg):
                # print("block_gray_img_mean = ", gray_img_mean)
                print("({},{}),block_hist_img_mean = {}".format(hId, wId, hist_img_mean))

            sub_image_thread = np.zeros_like(sub_image, dtype=np.uint8)
            # print("sub_image_thread shape=", sub_image_thread.shape, ", date type=", sub_image_thread.dtype)

            for bid in range(binary_threshold_level):
                binary_threshold_cur = binary_threshold_start + bid * binary_threshold_step
                binary_threshold_cur *= hist_img_mean
                _, thresholded = cv.threshold(sub_image, binary_threshold_cur, 255, cv.THRESH_BINARY)
                sub_image_thread = sub_image_thread + (thresholded * binary_threshold_level_inv).astype(np.uint8)

                if(debug_subimg):

                    # print("sub_image_thread shape=", sub_image_thread.shape, ", date type=", sub_image_thread.dtype)
                    # print("thresholded shape=", thresholded.shape, ", date type=", thresholded.dtype)

                    sub_image_thread_comp = np.hstack((sub_image_thread, thresholded))
                    cv.namedWindow("sub_image_thread_comp", cv.WINDOW_NORMAL)
                    cv.imshow("sub_image_thread_comp", sub_image_thread_comp)
                    cv.waitKey(0)                    


            thresholded_result_tmp[sub_images[hId][wId][1][0]:sub_images[hId][wId][1][1], sub_images[hId][wId][2][0]:sub_images[hId][wId][2][1]] = sub_image_thread
            cv.namedWindow("thresholded_result_tmp", cv.WINDOW_NORMAL)
            cv.imshow("thresholded_result_tmp", thresholded_result_tmp)
            cv.waitKey(0)
            
            # 自适应阈值二值化（可以自适应二值化出全图轮廓，效果还行，就是框图外噪点有点多）
            # thresholded = cv.adaptiveThreshold(sub_image,255,cv.ADAPTIVE_THRESH_MEAN_C, cv.THRESH_BINARY,51,2)
            # thresholded = cv.adaptiveThreshold(sub_image,255,cv.ADAPTIVE_THRESH_GAUSSIAN_C, cv.THRESH_BINARY,11,2)

    _, thresholded_result = cv.threshold(thresholded_result_tmp, (1+2)/binary_threshold_level*(255/2), 255, cv.THRESH_BINARY)
    # thresholded_result = cv.adaptiveThreshold(thresholded_result_tmp, 255, cv.ADAPTIVE_THRESH_GAUSSIAN_C, cv.THRESH_BINARY,11,2)

    # # Concatenate the thresholded images horizontally
    # top_row = np.hstack((thresholded_images[0], thresholded_images[1]))
    # bottom_row = np.hstack((thresholded_images[2], thresholded_images[3]))
    # thresholded_result = np.vstack((top_row, bottom_row))

    # # top_row = np.hstack((hist_images[0], hist_images[1]))
    # # bottom_row = np.hstack((hist_images[2], hist_images[3]))
    # # hist_result = np.vstack((top_row, bottom_row))     

    # return hist_result, thresholded_result

    if(debug_subimg):
        print("image shape=", image.shape, "thresholded_result shape=", thresholded_result.shape)

    return thresholded_result

'''
description: 对二值化图检测轮廓
                直接提取原始二值图轮廓；
return {*}
'''
def detectContours(thresholded_img, debug_image):

    contourResult = []

    # gauss_blurred_image = cv.GaussianBlur(binary_image, (3, 3), 0)
    gauss_blurred_image = cv.GaussianBlur(thresholded_img, (3, 3), 0)
    cv.namedWindow("gauss_blurred_image", cv.WINDOW_NORMAL)
    cv.imshow("gauss_blurred_image", gauss_blurred_image)


    #在检测轮廓之前就先作canny边缘提取
    # canny_edges = cv.Canny(gauss_blurred_image, 125, 125 * 2.0)
    canny_edges = cv.Canny(thresholded_img, 125, 125 * 2.0)    
    cv.namedWindow("canny_edges", cv.WINDOW_NORMAL)
    cv.imshow("canny_edges", canny_edges)

    # Find contours in the binary image
    # contours, _ = cv.findContours(binary_image, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    # contours, _ = cv.findContours(cv.cvtColor(thresholded_img, cv.COLOR_BGR2GRAY), cv.RETR_LIST, cv.CHAIN_APPROX_SIMPLE)
    contours, _ = cv.findContours(thresholded_img, cv.RETR_LIST, cv.CHAIN_APPROX_SIMPLE)    
    # contours, _ = cv.findContours(cv.cvtColor(gauss_blurred_image, cv.COLOR_BGR2GRAY), cv.RETR_LIST, cv.CHAIN_APPROX_SIMPLE)  
    # contours, _ = cv.findContours(canny_edges, cv.RETR_LIST, cv.CHAIN_APPROX_SIMPLE)

    image_clone2 = debug_image.copy()
    cv.namedWindow("contours_image", cv.WINDOW_NORMAL)
    # Draw the contours on the original image

    cv.drawContours(image_clone2, contours, -1, (0, 255, 0), 1)
    cv.imshow("contours_image", image_clone2)

    print("contours info\n", "size=", len(contours))
    # print(contours)
    #手动绘制轮廓图
    image_clone3 = debug_image.copy()
    for cId, contour in enumerate(contours):
        # 生成随机颜色
        color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        for point in contour:
            # cv.circle(image_clone3, (point[0][0], point[0][1]), 1, color, -1)
            image_clone3[point[0][1], point[0][0]] = color

    cv.namedWindow("contours_image_by_hand", cv.WINDOW_NORMAL)
    cv.imshow("contours_image_by_hand", image_clone3)

    #计算所有轮廓的面积周长, 并筛选出圆
    contour_delete_size = 0
    for ind, contour in enumerate(contours):
        perimeter = cv.arcLength(contour, True)     #计算轮廓周长，第二个参数标记是否是闭合轮廓
        if(perimeter <= 0):
            continue

        area = cv.contourArea(contour)
        alpha = 4*np.pi*area/(perimeter**2)
        # contour_info = '{0:>6} {1:>9,.0f} {2:>9,.2f} {3:>9,.3f}'.format(ind, area, perimeter, alpha)
        # contour_info = '{0:>9,.0f} {1:>9,.2f}'.format( area, perimeter)
        contour_info0 = '{0:.0f} {1:.2f} {2:.2f}'.format( area, perimeter, alpha)        
        contour_info1 = '{0:.0f} {1:.2f}'.format( area, perimeter)
        contour_info2 = '{0:.2f}'.format(alpha)
        
        # Compute moments in order to find the centroid of objects
        # 计算轮廓对应的几何中心
        moments = cv.moments(contour)
        if(moments['m00'] <= 0 ):
            continue
        cx = moments['m10'] / moments['m00']
        cy = moments['m01'] / moments['m00']
        if(alpha < 0.65):
            cv.drawContours(image_clone2, [contour], -1, (0, 0, 255), 1)    #标记红色为剔除掉的轮廓(面积周长比)
            # cv.putText(image_clone2, contour_info0, (cx,cy), cv.FONT_HERSHEY_SIMPLEX,0.3,color=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)),thickness=1)

            contour_delete_size = contour_delete_size + 1
            continue

        # if(area < 20 or perimeter < 15):
        #     cv.drawContours(image_clone2, [contour], -1, (0, 0, 255), 1)    #标记红色为剔除掉的轮廓(面积,周长)
        #     # cv.putText(image_clone2, contour_info0, (cx,cy), cv.FONT_HERSHEY_SIMPLEX,0.3,color=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)),thickness=1)

        #     contour_delete_size = contour_delete_size + 1
        #     continue
        # if(area > 1000 or perimeter > 250):
        #     cv.drawContours(image_clone2, [contour], -1, (0, 0, 255), 1)    #标记红色为剔除掉的轮廓(面积,周长)
        #     # cv.putText(image_clone2, contour_info0, (cx,cy), cv.FONT_HERSHEY_SIMPLEX,0.3,color=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)),thickness=1)

        #     contour_delete_size = contour_delete_size + 1
        #     continue

        # cv.putText(image_clone2, contour_info1, (cx,cy), cv.FONT_HERSHEY_SIMPLEX,0.3,color=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)),thickness=1)
        # cv.putText(image_clone2, "{0:.0f}".format(ind), (cx,cy), cv.FONT_HERSHEY_SIMPLEX,0.5,color=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)),thickness=1)

        contoursWithCircle = ContoursWithCircle(contour, perimeter, area, alpha, cx, cy)
        contourResult.append(contoursWithCircle)

    print("contour_delete_size=", contour_delete_size)
    cv.imshow("contours_image", image_clone2)

    return contourResult

'''
description: 检测大三圆
    先检测到最大圆，再检测次大圆
return {*}
'''
def detectBigCircle(contourResult, debug_image, isRGB):
    global mScaleXY
    global mScaleDrawer

    #确定提取circle的最大数目
    #确定提取圆时3个ratio的阈值
    if(isRGB):   #RGB摄像头可以
        # tmp_circle_size_max = 10  #最多检测到200个圆结束
        tmp_circle_size_max = 1000  #最多检测到200个圆结束

        big_circle_threa1 = [1.2, 1.3, 1.8]
        big_circle_threa2 = [1.3, 1.3, 1.3]

    else:
        # tmp_circle_size_max = 10  #最多检测到200个圆结束
        tmp_circle_size_max = 600  #最多检测到200个圆结束

        big_circle_threa1 = [1.3, 1.3, 1.5]
        big_circle_threa2 = [1.3, 1.3, 1.3]

    bigCircles = []

    sortedContour = sorted(contourResult, key = lambda contour: contour.area, reverse=True)
    contourSize = len(sortedContour)

    oriShape = debug_image.shape

    #一张图一行至少能拍到10个圆，以此作为圆最大半径和面积阈值
    maxR = oriShape[0]
    if(maxR > oriShape[1]):
        maxR = oriShape[1]    
    maxR = maxR / (2.0*10)    
    maxArea = math.pi * maxR * maxR

    
    big_circle_list1 = []       #最大圆
    big_circle_list2 = []       #大圆
    common_circle_list = []     #普通圆

    isBigCircleBreak = False    #先确定最大圆， 之后才开始连续确定大圆，连续确定大圆时步骤断开了就开始确定普通圆

    for idx, curContour in enumerate(sortedContour):
        if(curContour.area > maxArea):
            print("cur contour area is too big, maxArea={}, cur_area={}".format(maxArea, curContour.area).encode('utf-8'))
            continue
        if(idx + 15 >= contourSize):
            print("check biggest circle, remaining contour num too small, contourSize={}, idx={}".format(contourSize, idx).encode('utf-8'))
            break
        ratio1 = curContour.area/sortedContour[idx+1].area
        ratio2 = curContour.area/sortedContour[idx+2].area
        ratio3 = curContour.area/sortedContour[idx+15].area
        if(idx < 20):
            print("check biggest circle, id={},r={:.3f},area1={},area2={},area3={},areax={},ratio1={:.3f},ratio2={:.3f},ratio3={:.3f}".format
                                            (idx, curContour.r, curContour.area,sortedContour[idx+1].area, sortedContour[idx+2].area, sortedContour[idx+15].area, ratio1, ratio2, ratio3))


        if((len(big_circle_list1) + len(big_circle_list2) + len(common_circle_list)) > tmp_circle_size_max):
            print(" circles num is enouph: {},{},{}".format(len(big_circle_list1) , len(big_circle_list2) , len(common_circle_list)).encode('utf-8'))
            break
        # if(idx > 50):
        #     break

        if(len(big_circle_list1) <= 0):
            if(ratio1 > big_circle_threa1[0] or ratio2 > big_circle_threa1[1]):   #最大圆和次大圆面积比例不会相差很大！（小于1.2）
                continue
            if(ratio3 < big_circle_threa1[2]):
                continue
            print("got the biggest circle".encode('utf-8'))
            big_circle_list1.append([curContour, [ratio1, ratio2, ratio3]])
            continue
        
        if(isBigCircleBreak == False):
            # if(ratio1 > big_circle_threa2[0]):   #最大圆和次大圆面积比例不会相差很大！（小于1.2）
            #     isBigCircleBreak = True
            #     continue
            # if(ratio3 < big_circle_threa2[2]):
            #     isBigCircleBreak = True
            #     continue
            if(ratio3 < big_circle_threa2[2]):
                isBigCircleBreak = True
                continue

            print("got the ohter big circles".encode('utf-8'))
            big_circle_list2.append([curContour, [ratio1, ratio2, ratio3]])
            continue

        common_circle_list.append([curContour, [ratio1, ratio2, ratio3]])
    
    #绘制检测到的圆结果
    # debug_image2 = debug_image.copy()
    debug_image2 = cv.resize(debug_image, None, fx=mScaleXY[0], fy=mScaleXY[1])
    circle_result = []
    for otherIdx in range(len(big_circle_list1)):   #最大圆
        cx = big_circle_list1[otherIdx][0].cx
        cy = big_circle_list1[otherIdx][0].cy
        r = big_circle_list1[otherIdx][0].r
        cx = int(cx)
        cy = int(cy)
        r = int(r)

        color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

        mScaleDrawer.scale_circle(debug_image2, (cx,cy), max(int(r),2), color, -1)

        # cv.drawContours(debug_image2, [big_circle_list1[otherIdx][0].contour], -1, (0, 255, 255), 1) 
        mScaleDrawer.scale_drawContours(debug_image2, [big_circle_list1[otherIdx][0].contour], -1, (0, 255, 255), 1) 

        seq_id = otherIdx
        contour_info0 = "{}".format(seq_id)
        
        mScaleDrawer.scale_putText(debug_image2, contour_info0, (cx,cy), cv.FONT_HERSHEY_SIMPLEX,0.5 if isRGB else 0.25,color=(0,0,255),thickness=1)

        circle_result.append([big_circle_list1[otherIdx][0], big_circle_list1[otherIdx][1], color, seq_id])

    for otherIdx in range(len(big_circle_list2)):   #大圆
        cx = big_circle_list2[otherIdx][0].cx
        cy = big_circle_list2[otherIdx][0].cy
        r = big_circle_list2[otherIdx][0].r   
        cx = int(cx)
        cy = int(cy)
        r = int(r)
        color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        mScaleDrawer.scale_circle(debug_image2, (cx,cy), max(int(r),2), color, -1)
        mScaleDrawer.scale_drawContours(debug_image2, [big_circle_list2[otherIdx][0].contour], -1, (255, 255, 0), 1) 

        seq_id = len(big_circle_list1) + otherIdx
        contour_info0 = "{}".format(seq_id)
        mScaleDrawer.scale_putText(debug_image2, contour_info0, (cx,cy), cv.FONT_HERSHEY_SIMPLEX,0.5 if isRGB else 0.25,color=(0,0,255),thickness=1)

        circle_result.append([big_circle_list2[otherIdx][0], big_circle_list2[otherIdx][1], color, seq_id])

    for otherIdx in range(len(common_circle_list)): #普通圆
        cx = common_circle_list[otherIdx][0].cx
        cy = common_circle_list[otherIdx][0].cy
        r = common_circle_list[otherIdx][0].r
        cx = int(cx)
        cy = int(cy)
        r = int(r)
        color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        mScaleDrawer.scale_circle(debug_image2, (cx,cy), max(int(r),2), color, -1)
        mScaleDrawer.scale_drawContours(debug_image2, [common_circle_list[otherIdx][0].contour], -1, (0, 0, 0), 1)

        seq_id = len(big_circle_list1) + len(big_circle_list2) + otherIdx
        contour_info0 = "{}".format(seq_id)

        mScaleDrawer.scale_putText(debug_image2, contour_info0, (cx,cy), cv.FONT_HERSHEY_SIMPLEX,0.5 if isRGB else 0.25,color=(0,0,255),thickness=1)
        circle_result.append([common_circle_list[otherIdx][0], common_circle_list[otherIdx][1], color, seq_id])


    cv.namedWindow("contours_biggest_circle", cv.WINDOW_NORMAL)
    cv.imshow("contours_biggest_circle", debug_image2)
    cv.waitKey(0)

    return circle_result

'''
description: 基于二值化轮廓检测圆:对比度增强；图像二值化；二值图去噪()；高斯滤波；轮廓检测
param {*} image
    https://zhuanlan.zhihu.com/p/425936810?utm_id=0 
return {*}
'''     
def detect_circl2_2(image):
    image_clone = image.copy()
    gray_img = cv.cvtColor(image, cv.COLOR_BGR2GRAY)     
    hist_img = cv.equalizeHist(cv.cvtColor(image, cv.COLOR_BGR2GRAY))

    gray_img_mean = np.mean(gray_img)
    hist_img_mean = np.mean(hist_img)

    print("gray_img_mean = ", gray_img_mean)
    print("hist_img_mean = ", hist_img_mean)

    cv.namedWindow("hist_img", cv.WINDOW_NORMAL)
    cv.imshow("hist_img", hist_img)

    _, thresholded_img = cv.threshold(hist_img, hist_img_mean*0.6, 255, cv.THRESH_BINARY)
    # ret, thresholded_img = cv.threshold(hist_img, 0, 255, cv.THRESH_BINARY | cv.THRESH_OTSU)
    cv.namedWindow("thresholded_img", cv.WINDOW_NORMAL)
    cv.imshow("thresholded_img", thresholded_img)

    # for idx, binary_threshold in enumerate([1.4, 1.2, 1.0, 0.8, 0.6, 0.4, 0.2]):
    # 按照不同阈值作二值化处理
    for idx, binary_threshold in enumerate([1.2]):
        win_tag = "block_thresholded_img_{}".format(binary_threshold)
        # 对图像作分块二值化
        # block_thresholded_img_tmp = block_threshold(image, binary_threshold, 2, 2, (idx == 0))
        block_thresholded_img_tmp = block_threshold(image, binary_threshold, 1,1, (idx == 0))
        if(idx == 0):
            block_thresholded_img = block_thresholded_img_tmp

        cv.namedWindow(win_tag, cv.WINDOW_NORMAL)
        cv.imshow(win_tag, block_thresholded_img_tmp)

        if(False):   #https://blog.csdn.net/qq_43163978/article/details/105645623    #分水岭算法检测圆
            block_thresholded_img_tmp_inv = cv.bitwise_not(block_thresholded_img_tmp)       #黑白颜色互换

            cv.namedWindow(win_tag + "_distImg_inv", cv.WINDOW_NORMAL)        
            cv.imshow(win_tag + "_distImg_inv", block_thresholded_img_tmp_inv)
            cv.waitKey(0)

            # distImg = cv.distanceTransform(block_thresholded_img_tmp_inv, cv.DIST_L1, 3, 5) # 转换成距离图像
            distImg = cv.distanceTransform(block_thresholded_img_tmp, cv.DIST_L2, 3) # 转换成距离图像
            cv.namedWindow(win_tag + "_distImg", cv.WINDOW_NORMAL)
            cv.imshow(win_tag + "_distImg", distImg)
            cv.waitKey(0)

            # 对距离变换结果进行归一化到[0~1]之间
            distImg = cv.normalize(distImg, None, 0, 1, cv.NORM_MINMAX)
            cv.imshow(win_tag + "_distImg", distImg)
            cv.waitKey(0)

            # 使用阈值，再次二值化，得到标记(binary again)
            _, distImg = cv.threshold(distImg, 0.05, 1, cv.THRESH_BINARY)
            cv.imshow(win_tag + "_distImg", distImg)
            cv.waitKey(0)

            # 腐蚀得到每个Peak - erode
            # kernel1 = np.ones((13, 13), np.uint8)
            kernel1 = cv.getStructuringElement(cv.MORPH_RECT, (3, 3))
            distImg = cv.erode(distImg, kernel1, iterations=1)
            cv.namedWindow(win_tag + "_distImg_erode", cv.WINDOW_NORMAL)
            cv.imshow(win_tag + "_distImg_erode", distImg)
            cv.waitKey(0)

        elif (False):    #https://blog.csdn.net/qq_47618845/article/details/109271220 #分水岭算法图像分割
            # morphology operation
            block_thresholded_img_tmp_inv = cv.bitwise_not(block_thresholded_img_tmp)       #黑白颜色互换

            cv.namedWindow(win_tag + "_distImg", cv.WINDOW_NORMAL)        
            cv.imshow(win_tag + "_distImg", block_thresholded_img_tmp_inv)
            cv.waitKey(0)

            # morphology_kernel = cv.getStructuringElement(cv.MORPH_RECT, (3, 3))
            morphology_kernel = cv.getStructuringElement(cv.MORPH_RECT, (3, 3))
            opening = cv.morphologyEx(block_thresholded_img_tmp_inv, cv.MORPH_OPEN, kernel=morphology_kernel, iterations=2)   #开运算：先腐蚀再膨胀
            cv.namedWindow(win_tag + "_distImg", cv.WINDOW_NORMAL)        
            cv.imshow(win_tag + "_distImg", opening)
            cv.waitKey(0)

            sure_bg = cv.dilate(opening, morphology_kernel, iterations=3)      #进一步膨胀
            cv.namedWindow(win_tag + "_distImg", cv.WINDOW_NORMAL)        
            cv.imshow(win_tag + "_distImg", sure_bg)
            cv.waitKey(0)

            # Finding sure foreground area
            dist_transform = cv.distanceTransform(opening, 1,5)
            ret, sure_fg = cv.threshold(dist_transform, 0.7*dist_transform.max(), 255, 0)
            sure_fg = np.uint8(sure_fg)

            cv.namedWindow(win_tag + "_distImg_fg", cv.WINDOW_NORMAL)        
            cv.imshow(win_tag + "_distImg_fg", sure_fg)
            cv.waitKey(0)

            unknown = cv.subtract(sure_bg,sure_fg)            

            cv.namedWindow(win_tag + "_distImg_unknown", cv.WINDOW_NORMAL)        
            cv.imshow(win_tag + "_distImg_unknown", unknown)
            cv.waitKey(0)

            ret, markers1 =cv.connectedComponents(sure_fg)
            # watershed transform
            markers = markers1 + 1
            markers[unknown==255] = 0
            block_thresholded_img_tmp_inv_color = cv.cvtColor(block_thresholded_img_tmp_inv, cv.COLOR_GRAY2BGR)   
            markers3 = cv.watershed(block_thresholded_img_tmp_inv_color, markers=markers)
            image_clone[markers3 == -1] =[0, 0, 255]
            cv.namedWindow('result', cv.WINDOW_NORMAL)
            cv.imshow("result", image_clone)

    myCoutours = detectContours(block_thresholded_img, image)
    print("myCoutours size = ", len(myCoutours))

    detectBigCircle(myCoutours, image)

    return

    # gauss_blurred_image = cv.GaussianBlur(binary_image, (3, 3), 0)
    gauss_blurred_image = cv.GaussianBlur(block_thresholded_img, (3, 3), 0)
    cv.namedWindow("gauss_blurred_image", cv.WINDOW_NORMAL)
    cv.imshow("gauss_blurred_image", gauss_blurred_image)


    #在检测轮廓之前就先作canny边缘提取
    # canny_edges = cv.Canny(gauss_blurred_image, 125, 125 * 2.0)
    canny_edges = cv.Canny(block_thresholded_img, 125, 125 * 2.0)    
    cv.namedWindow("canny_edges", cv.WINDOW_NORMAL)
    cv.imshow("canny_edges", canny_edges)

    # Find contours in the binary image
    # contours, _ = cv.findContours(binary_image, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    # contours, _ = cv.findContours(cv.cvtColor(block_thresholded_img, cv.COLOR_BGR2GRAY), cv.RETR_LIST, cv.CHAIN_APPROX_SIMPLE)
    contours, _ = cv.findContours(block_thresholded_img, cv.RETR_LIST, cv.CHAIN_APPROX_SIMPLE)    
    # contours, _ = cv.findContours(cv.cvtColor(gauss_blurred_image, cv.COLOR_BGR2GRAY), cv.RETR_LIST, cv.CHAIN_APPROX_SIMPLE)  
    # contours, _ = cv.findContours(canny_edges, cv.RETR_LIST, cv.CHAIN_APPROX_SIMPLE)
    image_clone2 = image.copy()
    cv.namedWindow("contours_image", cv.WINDOW_NORMAL)
    # Draw the contours on the original image

    cv.drawContours(image_clone2, contours, -1, (0, 255, 0), 1)
    cv.imshow("contours_image", image_clone2)

    print("contours info\n", "size=", len(contours))
    # print(contours)
    #手动绘制轮廓图
    image_clone3 = image.copy()
    for cId, contour in enumerate(contours):
        # 生成随机颜色
        color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        for point in contour:
            # cv.circle(image_clone3, (point[0][0], point[0][1]), 1, color, -1)
            image_clone3[point[0][1], point[0][0]] = color

    cv.namedWindow("contours_image_by_hand", cv.WINDOW_NORMAL)
    cv.imshow("contours_image_by_hand", image_clone3)

    #计算所有轮廓的面积周长, 并筛选出圆
    contour_delete_size = 0
    for ind, contour in enumerate(contours):
        perimeter = cv.arcLength(contour, True)
        if(perimeter <= 0):
            continue

        area = cv.contourArea(contour)
        alpha = 4*np.pi*area/(perimeter**2)
        # contour_info = '{0:>6} {1:>9,.0f} {2:>9,.2f} {3:>9,.3f}'.format(ind, area, perimeter, alpha)
        # contour_info = '{0:>9,.0f} {1:>9,.2f}'.format( area, perimeter)
        contour_info0 = '{0:.0f} {1:.2f} {2:.2f}'.format( area, perimeter, alpha)        
        contour_info1 = '{0:.0f} {1:.2f}'.format( area, perimeter)
        contour_info2 = '{0:.2f}'.format(alpha)
        
        # Compute moments in order to find the centroid of objects
        # 计算轮廓对应的几何中心
        moments = cv.moments(contour)
        if(moments['m00'] <= 0 ):
            continue
        cx = int(moments['m10'] / moments['m00'])
        cy = int(moments['m01'] / moments['m00'])
        if(alpha < 0.65):
            cv.drawContours(image_clone2, [contour], -1, (0, 0, 255), 1)    #标记红色为剔除掉的轮廓(面积周长比)
            # cv.putText(image_clone2, contour_info0, (cx,cy), cv.FONT_HERSHEY_SIMPLEX,0.3,color=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)),thickness=1)

            contour_delete_size = contour_delete_size + 1
            continue

        if(area < 20 or perimeter < 15):
            cv.drawContours(image_clone2, [contour], -1, (0, 0, 255), 1)    #标记红色为剔除掉的轮廓(面积,周长)
            # cv.putText(image_clone2, contour_info0, (cx,cy), cv.FONT_HERSHEY_SIMPLEX,0.3,color=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)),thickness=1)

            contour_delete_size = contour_delete_size + 1
            continue
        if(area > 1000 or perimeter > 250):
            cv.drawContours(image_clone2, [contour], -1, (0, 0, 255), 1)    #标记红色为剔除掉的轮廓(面积,周长)
            # cv.putText(image_clone2, contour_info0, (cx,cy), cv.FONT_HERSHEY_SIMPLEX,0.3,color=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)),thickness=1)

            contour_delete_size = contour_delete_size + 1
            continue

        # cv.putText(image_clone2, contour_info1, (cx,cy), cv.FONT_HERSHEY_SIMPLEX,0.3,color=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)),thickness=1)

        # cv.putText(image_clone2, "{0:.0f}".format(ind), (cx,cy), cv.FONT_HERSHEY_SIMPLEX,0.5,color=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)),thickness=1)


    print("contour_delete_size=", contour_delete_size)
    cv.imshow("contours_image", image_clone2)

    return


    # 霍夫圈变换
    # 参数分别为：image, method, dp, minDist, param1, param2, minRadius, maxRadius
    # 其中：image为灰度图像，method使用的方法为霍夫梯度法，minDist两个圆中心的最小距离
    # circles = cv.HoughCircles(gray_img, cv.HOUGH_GRADIENT, 1, 30, param1=50, param2=30, minRadius=0, maxRadius=50)
    # circles = cv.HoughCircles(gray_img, cv.HOUGH_GRADIENT, 1, 10, param1=20, param2=15, minRadius=3, maxRadius=20)
    circles = cv.HoughCircles(binary_image, cv.HOUGH_GRADIENT, 1, 10, param1=40, param2=20, minRadius=3, maxRadius=20)

    # circles = cv.HoughCircles(gray_img, cv.HOUGH_GRADIENT, 1, 3, param1=50, param2=0.1, minRadius=0, maxRadius=20)

    # # 对数据进行取整
    # # print("取整前信息：" + str(circles))
    # circles = np.uint16(np.around(circles))
    # # print("取整后信息：" + str(circles))
     
    # return circles

'''
description: 分水岭算法作图像轮廓提取?(感觉太粗粒度了)
param {*} image
return {*}
'''
def detect_circl3(image):

    print(image.shape)
    blurred = cv.pyrMeanShiftFiltering(image, 10, 100)
    gray = cv.cvtColor(blurred, cv.COLOR_BGR2GRAY)
    ret, binary = cv.threshold(gray, 0, 255, cv.THRESH_BINARY | cv.THRESH_OTSU)
    cv.namedWindow("binary", cv.WINDOW_NORMAL)
    cv.imshow("binary", binary)

    # morphology operation
    kernel = cv.getStructuringElement(cv.MORPH_RECT, (3, 3))
    opening = cv.morphologyEx(binary, cv.MORPH_OPEN, kernel=kernel, iterations=2)
    sure_bg = cv.dilate(opening, kernel, iterations=3)
    cv.namedWindow("morphology operation", cv.WINDOW_NORMAL)
    cv.imshow("morphology operation", sure_bg)
    # Finding sure foreground area
    dist_transform = cv.distanceTransform(opening, 1,5)
    ret, sure_fg = cv.threshold(dist_transform, 0.7*dist_transform.max(), 255, 0)

    # Finding unknown region
    sure_fg = np.uint8(sure_fg)
    unknown = cv.subtract(sure_bg,sure_fg)

    ret, markers1 =cv.connectedComponents(sure_fg)
    print(ret)

    # watershed transform
    markers = markers1 + 1
    markers[unknown==255] = 0
    markers3 = cv.watershed(image, markers=markers)
    image[markers3 == -1] =[0, 0, 255]
    # cv.namedWindow('result', 0)
    cv.namedWindow("result", cv.WINDOW_NORMAL)
    cv.imshow("result", image)

def draw_circle(img, circles):
    '''
     作用：根据圆形信息在图片中绘制圆
     参数1：原始图片信息
     参数2：圆形坐标信息
     返回：无
    '''
    for i in circles[0, :]:
        # 绘制圆外圈
        # 参数分别为：圆心、半径、颜色、线框宽度
        cv.circle(img, (i[0], i[1]), i[2], (0, 255, 0), 2)
        # 绘制圆心 
        cv.circle(img, (i[0], i[1]), 1, (255, 255, 0), 2)
    cv.namedWindow("draw_circle_img", cv.WINDOW_NORMAL)
    cv.imshow("draw_circle_img", img)


'''
description: 用极线check标定外参
'''
class CalibEpilineChecker:

    def __init__(self, gTCalibCxxLibHelper):

        self.debugx = True #必要的debug信息
        self.debug = False #次要的debug信息
        self.debug2 = False #次要的详细debug信息

        self.mCTCalibCxxLibHelper = gTCalibCxxLibHelper

        pass

    # 读取标定参数，得到RGB相机内参和外参
    def _readCameraParams(self, calibInfo, cameraModelOut, camPairId, mCameraIsRadial):
        # calibInfo = GtCalibParser.GTCalibInfo()
        # if(GtCalibParser.parse_calib_xml(calibPath, calibInfo) == False):
        #     print("calib parse fail, path={}".format(calibPath))
        #     return False

        for idx in range(2):
            if(camPairId[idx] == 0):
                cameraModelOut[idx].buildByCameraInfo(calibInfo.trackingA, False, mCameraIsRadial[camPairId[idx]])
            elif (camPairId[idx] == 1):
                cameraModelOut[idx].buildByCameraInfo(calibInfo.trackingB, False, mCameraIsRadial[camPairId[idx]])
            elif (camPairId[idx] == 2):
                cameraModelOut[idx].buildByCameraInfo(calibInfo.ctrl_trackingA, False, mCameraIsRadial[camPairId[idx]])
            elif (camPairId[idx] == 3):
                cameraModelOut[idx].buildByCameraInfo(calibInfo.ctrl_trackingB, False, mCameraIsRadial[camPairId[idx]])
            elif (camPairId[idx] == 4):
                cameraModelOut[idx].buildByCameraInfo(calibInfo.rgb_left, True, mCameraIsRadial[camPairId[idx]])
            elif (camPairId[idx] == 5):
                cameraModelOut[idx].buildByCameraInfo(calibInfo.rgb_right, True, mCameraIsRadial[camPairId[idx]])
            else:
                print("camera id err:{},{}".format(idx, camPairId[idx]))
                continue

            # print("{}\nidx={}\nh={},w={}\nK=\n{}\nD=\n{}\nR=\n{}\nt=\n{}\n{}".format( "+"*50 ,idx, cameraModelOut[idx].h,cameraModelOut[idx].w, cameraModelOut[idx].K,cameraModelOut[idx].D,cameraModelOut[idx].R,cameraModelOut[idx].t, "="*50))

        # cameraModelOut[0].buildByRGBCamera(calibInfo.rgb_left)
        # cameraModelOut[1].buildByRGBCamera(calibInfo.rgb_right)
        
        for idx, cameraModel in enumerate(cameraModelOut):
            print("{}\npair_id={}\ncid={}\nh={},w={}\nK=\n{}\nD=\n{}\nR=\n{}\nt=\n{}\nnewK=\n{}\n{}".format( "+"*50 ,idx, cameraModel.id, cameraModel.h,cameraModel.w, cameraModel.K,cameraModel.D,cameraModel.R,cameraModel.t,cameraModel.newK, "="*50))

        return True

    def _readCalibImg(self):
        pass

    '''
    description: 在单张图上检测圆心特征，并对应唯一位置编号
    param {*} img
    return {*} [ContoursWithCircle,[ratio1, ratio2, ratio3],color,seqid]
    '''
    def _detectFeatures(self, image, isRGB):
        # image_clone = image.copy()

        # 按照不同阈值作二值化处理
        # for idx, binary_threshold in enumerate([0.6, 0.8, 1.0, 1.2]):
        # for idx, binary_threshold in enumerate([0.6]):    #RGB图可以
        #确定二值化的阈值
        if(isRGB):
            bt = [0.6]  #二值化阈值
            # bt = [1.2]  #二值化阈值
        else:
            bt = [1.2]  #二值化阈值
        for idx, binary_threshold in enumerate(bt):
            win_tag = "block_thresholded_img_{}".format(binary_threshold)
            # 对图像作分块二值化
            if(isRGB):
                block_thresholded_img_tmp = block_threshold(image, binary_threshold, 1,1, (idx == 0))
            else:
                block_thresholded_img_tmp = block_threshold(image, binary_threshold, 4,1, (idx == 0))
            print("block_thresholded_img_tmp shape=", block_thresholded_img_tmp.shape, ", date type=", block_thresholded_img_tmp.dtype)
            if(idx == 0):
                block_thresholded_img = block_thresholded_img_tmp

            cv.namedWindow(win_tag, cv.WINDOW_NORMAL)
            cv.imshow(win_tag, block_thresholded_img_tmp)

        myCoutours = detectContours(block_thresholded_img, image)
        print("myCoutours size = ", len(myCoutours))

        return detectBigCircle(myCoutours, image, isRGB)

    '''
    description: 在单张图上检测圆心特征，并对应唯一位置编号
    param {*} img
        1）图像二值化(取消不再做)
        2）检测轮廓
        3) 提取大三圆组，同时区分a和b板
        4）剔除异常circle
        5）在单板上从大三圆起点扩展并标记所有圆
    return {*} [ContoursWithCircle,[ratio1, ratio2, ratio3],color,seqid]
    return [True/False, [ringBoardA, ringBoardB]]
    '''
    def _detectFeatures2(self, image, isRGB):
        global mScaleXY
        imgGray = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
        # imgGray = cv.cvtColor(image, cv.COLOR_RGB2GRAY)
        mCircleFeatureDectector = CircleFeatureDectector(mScaleXY)
        # 1）图像二值化(取消)
        if(False):
            thresholded_result = mCircleFeatureDectector.block_threshold(imgGray)
        # 2）检测轮廓
        start_time = time.perf_counter()
        oriCircles = mCircleFeatureDectector.detect_circle_contours(imgGray, self.debug)
        print("2)contours detecion cost: {} ms {}".format((time.perf_counter() - start_time)*1000, "/"*20).encode('utf-8'))

        # 3) 提取大三圆组，同时区分a和b板
        start_time = time.perf_counter()
        resultRings = mCircleFeatureDectector.detectBigThree(oriCircles, doDebug = [self.debug, imgGray], doDebug2 = self.debug2)
        print(" big 3 circles detection cost:{} ms {}".format((time.perf_counter() - start_time)*1000, "/"*20).encode('utf-8'))

        #4）剔除异常circle

        # 5）在单板上根据原始circle集合和大三圆构建board
        start_time = time.perf_counter()
        ret = mCircleFeatureDectector.buildBothBord(oriCircles, resultRings, doDebug = [self.debug, imgGray], doDebug2 = self.debug2)
        print("2 boards build cost : {} ms {}".format((time.perf_counter() - start_time)*1000, "/"*20).encode('utf-8'))

        return ret




    '''
    description: 
    param {*} pts1: from特征列表
    param {*} pts2：to特征列表（暂时为空）（暂未作匹配关联）
    param {*} Fmat  F矩阵
    '''
    def _computeEpilineAndShow(self, pts1, pts2, Fmat):
        pass

    def check(self, cameraModelOut, rgbLeft, rgbRight, mainImg, targetId, imgPathCur):

        global mScaleXY
        global mScaleDrawer

        start_time = time.perf_counter()
        # #1)读取标定参数
        # cameraModelOut = [CameraModel(), CameraModel()]
        # if(self._readCameraParams(calibInfo, cameraModelOut, camPairId) == False):
        #     return
        # # print("_readCameraParams success:{}".format(calibPath))

        #2)读取原始图片
        rgbImgs = [rgbLeft.copy(), rgbRight.copy()]
        #原始图片去畸变
        rbgImgsUndist = [cameraModelOut[0].undistorImg(rgbImgs[0], self.debug2), cameraModelOut[1].undistorImg(rgbImgs[1], self.debug2)]                
        
        #3)检测圆心特征
        #在此选提取特征的主图像
        imgId = mainImg
        if(imgId == 0):
            imgId2 = 1
        else:
            imgId2 = 0
        
        if(self.debug):
            rgbFull = np.hstack((rgbImgs[imgId], rgbImgs[imgId2]))
            # cv.namedWindow(gOriImgTag, cv.WINDOW_NORMAL)
            # cv.imshow(gOriImgTag, rgbFull)

            rgbFullUndist = np.hstack((rbgImgsUndist[imgId], rbgImgsUndist[imgId2]))
            # cv.namedWindow(gOriImgTag + "_undist", cv.WINDOW_NORMAL)
            # cv.imshow(gOriImgTag + "_undist", rgbFullUndist)

            rgbFullComp = np.vstack((rgbFull, rgbFullUndist))

            cv.namedWindow(gOriImgTag + "_dist_undist", cv.WINDOW_NORMAL)
            cv.imshow(gOriImgTag + "_dist_undist", rgbFullComp)

            cv.waitKey(1)

        print(" img distortion cost: {} ms {} ".format((time.perf_counter() - start_time)*1000, "<"*20).encode('utf-8'))

        start_time = time.perf_counter()
        # [ContoursWithCircle, [ratio1, ratio2, ratio3], color, seqid]
        # cv.destroyAllWindows()
        feature1 = self._detectFeatures2(rgbImgs[imgId], cameraModelOut[imgId].isRgb)
        print(" img 1 features extraction cost :{} ms {}".format((time.perf_counter() - start_time)*1000, "<"*20).encode('utf-8'))

        if(self.debug):
            cv.waitKey(3000)
            # cv.destroyAllWindows()
        
        start_time = time.perf_counter()
        feature2 = self._detectFeatures2(rgbImgs[imgId2], cameraModelOut[imgId2].isRgb)
        print(" img 2 features extraction cost :{} ms {}".format((time.perf_counter() - start_time)*1000, "<"*20).encode('utf-8'))

        if(self.mCTCalibCxxLibHelper):
            print("Prepare to use mCTCalibCxxLibHelper to extract features!!!!!!!!!!!!!!".encode('utf-8'))
            if(targetId == 0 or targetId == 1):
                leftImgPath = imgPathCur
                rightImgPath = imgPathCur
            else:
                leftImgPath = imgPathCur[0]
                rightImgPath = imgPathCur[1]
            
            start_time = time.perf_counter()
            bRet, dRet = self.mCTCalibCxxLibHelper.detectFeatures(leftImgPath, targetId, True)
            if(bRet and dRet != None):
                print(f"BoardA feature size={len(dRet[0])}, BoardB feature size={len(dRet[1])}")            
            print("img 1 features extraction cost: {} ms {}".format((time.perf_counter() - start_time)*1000, "<"*50).encode('utf-8'))

            start_time = time.perf_counter()
            bRet, dRet = self.mCTCalibCxxLibHelper.detectFeatures(rightImgPath, targetId, False)
            if(bRet and dRet != None):
                print(f"BoardA feature size={len(dRet[0])}, BoardB feature size={len(dRet[1])}")            
            print("img 2 features extraction cost: {} ms {}".format((time.perf_counter() - start_time)*1000, "<"*50).encode('utf-8'))

        if(self.debug):
            cv.waitKey(3000)
            # cv.destroyAllWindows()
        # return

        start_time = time.perf_counter()
        #4）把圆心特征的特征中心作为特征点，构建一个点数组，准备作去畸变操作
        pts1 = []
        pts_color1 = []
        # seq_id1 = []
        
        pts2 = []
        seq_id2 = []

        board_pairs = []    #图1和图2的有效匹配对:[[图1板,图2板], [图1板,图2板]]
        #优先取A板特征
        #其次取B板特征
        if(feature1[0] == False or feature2[0] == False):
            print("two imgs features extraction fail 1".encode('utf-8'))
            return [False, None]
        if(feature1[1][0] != None and feature1[1][0].unorderedCells.size > 50 
            and feature2[1][0] != None and feature2[1][0].unorderedCells.size > 50):
            board1 = feature1[1][0]
            board2 = feature2[1][0]
            feature1Tmp = feature1[1][0].unorderedCells
            feature2Tmp = feature2[1][0].unorderedCells
            board_pairs.append([board1, board2])

        if(feature1[1][1] != None and feature1[1][1].unorderedCells.size > 50 
            and feature2[1][1] != None and feature2[1][1].unorderedCells.size > 50):
            board1 = feature1[1][1]
            board2 = feature2[1][1]            
            feature1Tmp = feature1[1][1].unorderedCells
            feature2Tmp = feature2[1][1].unorderedCells
            board_pairs.append([board1, board2])
        
        if(len(board_pairs) <= 0):
            print("two imgs features extraction fail 2".encode('utf-8'))
            return [False, None]

        # for idxx in range(feature1Tmp.size):
        #     pts1.append([feature1Tmp[idxx].center_image[0], feature1Tmp[idxx].center_image[1]])
        #     # pts_color1.append(feature1[idxx][2])
        #     # seq_id1.append([feature1Tmp[idxx].col, feature1Tmp[idxx].row])
        #     seq_id1.append([feature1Tmp[idxx].row, feature1Tmp[idxx].col])

        # pts1 = np.array(pts1)
        # print("pts1 shape=", pts1.shape, ", dtype=", pts1.dtype)

        # for idxx in range(feature2Tmp.size):
        #     pts2.append([feature2Tmp[idxx].center_image[0], feature2Tmp[idxx].center_image[1]])
        #     # pts_color1.append(feature1[idxx][2])
        #     # seq_id2.append([feature2Tmp[idxx].col, feature2Tmp[idxx].row])
        #     seq_id2.append([feature2Tmp[idxx].row, feature2Tmp[idxx].col])

        # pts2 = np.array(pts2)
        # print("pts2 shape=", pts2.shape, ", dtype=", pts2.dtype)

        # return

        # #把203号的轮廓点提取出来
        # contour203_pts = []
        # for fid in range(len(feature1)):
        #     if(feature1[fid][3] == 203):
        #         for point in feature1[fid][0].contour:
        #             contour203_pts.append([point[0][0], point[0][1]])
        #         break
        # contour203_pts = np.array(contour203_pts).astype(float)

        #正式去畸变
        # pts1_undistor = cameraModelOut[imgId].undistorPoints2(pts1, doDebug = [True, rgbImgs[imgId], board1.type[1]])
        # pts2_undistor = cameraModelOut[imgId2].undistorPoints2(pts2, doDebug = [True, rgbImgs[imgId2], board2.type[1]])

        #去畸变后图1和图2的特征点pairs:  [ [[图1板A去畸点,图1板A去畸点grid_id,图1板A],[图2板A去畸点,图2板A去畸点grid_id,图2板A]],  
        #                               [[图1板B去畸点,图1板B去畸点grid_id,图1板B],[图2板B去畸点,图2板B去畸点grid_id,图2板B]]
        #                             ]
        pts_undistor_pairs = []
        for board_pair_one in board_pairs:
            pts1_undistor = board_pair_one[0].undistorGridByCamera(cameraModelOut[imgId], doDebug = [self.debug, rgbImgs[imgId]])
            pts2_undistor = board_pair_one[1].undistorGridByCamera(cameraModelOut[imgId2], doDebug = [self.debug, rgbImgs[imgId2]])
            if(pts1_undistor[0] == False):
                print("{} features distortion fail :".format(board_pair_one[0].type[1]).encode('utf-8'))
                continue
            if(pts2_undistor[0] == False):
                print("{} features distortion fail :".format(board_pair_one[1].type[1]).encode('utf-8'))
                continue

            # seq_id1 = pts1_undistor[1][1]
            # pts1_undistor = pts1_undistor[1][0]
            # seq_id2 = pts2_undistor[1][1]
            # pts2_undistor = pts2_undistor[1][0]

            pts_undistor_pairs.append([ [pts1_undistor[1][0], pts1_undistor[1][1], board_pair_one[0]], [pts2_undistor[1][0], pts2_undistor[1][1], board_pair_one[1]] ])

        if(len(pts_undistor_pairs) <= 0):
            print("Failed to construct effective point pairs after distortion".encode('utf-8'))
            return [False, None]

        print("two imgs features distortion cost :{} ms {} ".format((time.perf_counter() - start_time)*1000, "<"*20).encode('utf-8'))

        # for idx1 in range(pts1_undistor.shape[0]):
        #     # print("pts1_undistor=",pts1_undistor[idx1][0])
        #     # print("seq_id1=",seq_id1[idx1])
        #     # print("board1.grid[seq_id1[0]][seq_id1[1]]=",board1.grid[seq_id1[idx1][0]][seq_id1[idx1][1]])
        #     board1.grid[seq_id1[idx1][0]][seq_id1[idx1][1]].center_image_undist = np.array([pts1_undistor[idx1][0][0], pts1_undistor[idx1][0][1]])

        # for idx2 in range(pts2_undistor.shape[0]):
        #     board2.grid[seq_id2[idx2][0]][seq_id2[idx2][1]].center_image_undist = np.array([pts2_undistor[idx2][0][0], pts2_undistor[idx2][0][1]])

        start_time = time.perf_counter()
        # 5-1)基于Rgb-L特征在Rgb-R上计算极线；基于Rgb-R特征在Rgb-L上计算极线

        if(self.debug2):
            print("<"*150)
            print("print camera calib info, K,D,Rt".encode('utf-8'))
            
            for cid in [imgId, imgId2]:
                print("imgId={}, caliId={}".format(cid, cameraModelOut[cid].id))
                print("newK=\n", cameraModelOut[cid].newK)
                print("D=\n", cameraModelOut[cid].D)
                print("R=\n", cameraModelOut[cid].R)
                print("t=\n", cameraModelOut[cid].t)
                print("-"*50)

        #计算F矩阵
        # K1_inv = np.linalg.inv(cameraModelOut[imgId].K)
        # K2_inv = np.linalg.inv(cameraModelOut[imgId2].K)

        K1_inv = np.linalg.inv(cameraModelOut[imgId].newK)
        K2_inv = np.linalg.inv(cameraModelOut[imgId2].newK)

        if(False):
            # (右乘pose描述)（标准计算）
            R_ex = cameraModelOut[imgId].R.T @ cameraModelOut[imgId2].R
            t_ex = cameraModelOut[imgId].R.T @ (cameraModelOut[imgId2].t - cameraModelOut[imgId].t)
            t_ex_skew = np.array([[0, -t_ex[2][0], t_ex[1][0]],
                        [t_ex[2][0], 0, -t_ex[0][0]],
                        [-t_ex[1][0], t_ex[0][0], 0]])

            print("R_ex=\n", R_ex)
            print("t_ex=\n", t_ex)
            print("t_ex_skew=\n", t_ex_skew)

            # E = (np.cross(t_ex, np.eye(3))) @ R_ex
            E = t_ex_skew @ R_ex
            F = K1_inv.T @ E @ K2_inv

            print("E=\n", E)
            print("F=\n", F)
            
            Ft = F.T
            targetF = Ft
        else:
            # (左乘pose描述)（标准计算）
            R_ex = cameraModelOut[imgId2].R @ cameraModelOut[imgId].R.T
            t_ex = cameraModelOut[imgId2].t - R_ex @ cameraModelOut[imgId].t
        
            t_ex_skew = np.array([[0, -t_ex[2][0], t_ex[1][0]],
                        [t_ex[2][0], 0, -t_ex[0][0]],
                        [-t_ex[1][0], t_ex[0][0], 0]])

            if(self.debug2):
                print("R_ex=\n", R_ex)
                print("t_ex=\n", t_ex)
                print("t_ex_skew=\n", t_ex_skew)

            # E = (np.cross(t_ex, np.eye(3))) @ R_ex
            E = t_ex_skew @ R_ex
            F = K2_inv.T @ E @ K1_inv

            if(self.debug2):
                print("E=\n", E)
                print("F=\n", F)
            
            Ft = F.T

            targetF = F


        # print("pts1_undistor info, shape=", pts1_undistor.shape, ", dtype=", pts1_undistor.dtype)

        #对比自己计算的极线和opencv计算的极线差别：以下能对应上，证明物理意义相反？
        if(False):
            pts1_size = pts1_undistor.shape[0]
            pts1_tmp = np.empty((3, pts1_size), dtype=float) #将所有特征点归一化坐标够成3*n的矩阵，便于统一计算
            for pid in range(pts1_size):
                pts1_tmp[0,pid] = pts1_undistor[pid][0][0]
                pts1_tmp[1,pid] = pts1_undistor[pid][0][1]
                pts1_tmp[2,pid] = 1.0
            lines_tmp = targetF @ pts1_tmp
            lines1_ori = lines_tmp.T
            #齐次化方便对比
            for idx in range(lines1_ori.shape[0]):
                lines1_ori[idx][0] = lines1_ori[idx][0] / lines1_ori[idx][2]
                lines1_ori[idx][1] = lines1_ori[idx][1] / lines1_ori[idx][2]
                lines1_ori[idx][2] = 1

            print("lines1_ori=\n",lines1_ori)
            print("x "*50)

            #直接调用opencv接口
            #在左乘pose下计算到的F，取 1 表示将图1的特征点映射到图2上形成一条极线
            lines1_1 = cv.computeCorrespondEpilines(pts1_undistor, 1, F)        
            lines1_1 = lines1_1.reshape(-1,3)
            #齐次化方便对比
            for idx in range(lines1_1.shape[0]):
                lines1_1[idx][0] = lines1_1[idx][0] / lines1_1[idx][2]
                lines1_1[idx][1] = lines1_1[idx][1] / lines1_1[idx][2]
                lines1_1[idx][2] = 1

            print("lines1_1=\n",lines1_1)
            print("x "*50)
            
            print("lines1_ori - lines1_1=\n",(lines1_ori - lines1_1))
            print("x "*50)
        
        # 极线 opencv的计算方式，有点搅得头疼， 干脆自己来计算
        # 采用targetF作为F矩阵计算极线

        validP2Count = 0
        validEpilineErr = 0

        preMeanErr = 0
        preMeanErr2 = 0

        for pts_undistor_pair_one in pts_undistor_pairs:
            
            pts1_undistor = pts_undistor_pair_one[0][0]
            seq_id1 = pts_undistor_pair_one[0][1]
            
            board2 = pts_undistor_pair_one[1][2]

            pts1_size = pts1_undistor.shape[0]
            pts1_tmp = np.empty((3, pts1_size), dtype=float)
            for pid in range(pts1_size):
                pts1_tmp[0,pid] = pts1_undistor[pid][0][0]
                pts1_tmp[1,pid] = pts1_undistor[pid][0][1]
                pts1_tmp[2,pid] = 1.0
            lines_tmp = targetF @ pts1_tmp
            lines1 = lines_tmp.T


            for idl, line in enumerate(lines1):#计算极线误差（像素级别）
                gridId = seq_id1[idl]
                p2 = board2.grid[gridId[0]][gridId[1]]
                if(p2):  #在图2上有对应有效点
                    
                    ErrTmp = line[0] * p2.center_image_undist[0] + line[1] * p2.center_image_undist[1] + line[2]
                    ErrTmp /= math.sqrt(line[0]**2 + line[1]**2)
                    ErrTmp = abs(ErrTmp)

                    validP2Count += 1
                    validEpilineErr += ErrTmp

                    preMeanErr = ((validP2Count - 1)*preMeanErr + ErrTmp)/validP2Count
                    preMeanErr2 = ((validP2Count - 1)*preMeanErr2 + ErrTmp*ErrTmp)/validP2Count
                    
            if(validP2Count <= 0):
                print("img1 and img2 features lose matching, epilines Err calculation unreachable".encode('utf-8'))
            else:
                print("img1 and img2 features  epilines Err Info, validP2Count={}, validEpilineErr={},meanErr={}".format(validP2Count, validEpilineErr, validEpilineErr/validP2Count).encode('utf-8'))
                print("Iterative calculation,Err Mean={}, Err Var={}".format(preMeanErr, (preMeanErr2 - preMeanErr*preMeanErr)).encode('utf-8'))
        
        if(validP2Count < 20):
            return [False, None]
        print("epilines Err calculation  cost : {} ms {}".format((time.perf_counter() - start_time)*1000, "<"*20).encode('utf-8'))

        return [True, [validP2Count, preMeanErr, (preMeanErr2 - preMeanErr*preMeanErr)]]

        # #在image2上绘制极线
        # image2 = rbgImgsUndist[imgId2]
        # scaleImage2 = cv.resize(image2, None, fx=mScaleXY[0], fy=mScaleXY[1])
        # img2Width = image2.shape[1]
        # img2Height = image2.shape[0]
        # for idl, line in enumerate(lines1):
        #     x0,y0 = map(int, [0, -line[2]/line[1] ])
        #     x1,y1 = map(int, [img2Width, -(line[2]+line[0]*img2Width)/line[1]])
        #     # x0,y0 = map(int, [-line[2]/line[0], 0])
        #     # x1,y1 = map(int, [-(line[2]+line[1]*img2Height)/line[0], img2Height])

        #     color = pts_color1[idl]

        #     cv.line(image2, (x0,y0), (x1,y1), color,1)
        #     cv.putText(image2, "{}".format(seq_id1[idl]), (int((x0+x1)*0.5),int((y0+y1)*0.5)), cv.FONT_HERSHEY_SIMPLEX,0.38 ,color=(0,0,255),thickness=1)

        #     mScaleDrawer.scale_line(scaleImage2, (x0,y0), (x1,y1), color,1)
        #     mScaleDrawer.scale_putText(scaleImage2, "{}".format(seq_id1[idl]), (int((x0+x1)*0.5),int((y0+y1)*0.5)), cv.FONT_HERSHEY_SIMPLEX,0.38 ,color,thickness=1)
        
        # cv.namedWindow("epilines_on_image2", cv.WINDOW_NORMAL)
        # cv.imshow("epilines_on_image2", image2)
        # cv.waitKey(0)
        # cv.imshow("epilines_on_image2", scaleImage2)
        # cv.waitKey(0)        


'''
description: 输入两个rgb的图像名列表，按时间戳对齐，且以第1个列表为主
return {*}
'''
def _timeAlignRgbImgs(rgbImgsLeft, rgbImgsRight, diffTimeMax = 20*1e6, doPreSorted = False):
    
    size1 = len(rgbImgsLeft)
    size2 = len(rgbImgsRight)
    print("_timeAlignRgbImgs size1={}, size2={}".format(size1, size2))
    if(size1 <= 0 or size2 <= 0):
        return [False, None]
    
    if(doPreSorted):
        rgbImgsLeftSorted = sorted(rgbImgsLeft)
        rgbImgsRightSorted = sorted(rgbImgsRight)
    else:
        rgbImgsLeftSorted = rgbImgsLeft
        rgbImgsRightSorted = rgbImgsRight

    alignedResult = []
    li = 0
    ri = 0
    
    while( li < size1 and ri < size2 ):
        diffT = int(rgbImgsLeftSorted[li].split(".")[0]) - int(rgbImgsRightSorted[ri].split(".")[0])
        if(abs(diffT) < diffTimeMax):
            alignedResult.append((rgbImgsLeftSorted[li], rgbImgsRightSorted[ri]))
            li += 1
            ri += 1
        elif(diffT < 0):
            li += 1
        else:
            ri += 1
    
    validSize = len(alignedResult)

    # if(False):#统计配对时间差，基本都在10ms以上，最大会达到16ms
    diffMax = 0
    diffMin = diffTimeMax*10
    diffMean = 0        
    for alignPair in alignedResult:
        diffT = int(alignPair[0].split(".")[0]) - int(alignPair[1].split(".")[0])
        diffT = abs(diffT)
        if(diffT > diffMax):
            diffMax = diffT
        if(diffT < diffMin):
            diffMin = diffT
        diffMean += diffT
    
    if(validSize <= 0):
        print("_timeAlignRgbImgs fail, validSize=",validSize)
        return [False, None]
    else:
        print("_timeAlignRgbImgs success, validSize={}, diffMax={}, diffMin={}, diffMean={}".format(validSize, diffMax, diffMin, diffMean/validSize))
        return [True, alignedResult]

#标定文件和采集图对应关系：
# trackA : cam8左图
# trackB : cam8右图
# ctrl-trackA : cam9左图
# ctrl-trackB : cam9右图
# RGB-left:  cam5
# RGB-right: cam4


class GTCalibChecker:

    def __init__(self, useCxxLib = [False, ""]):

        self.calibPath = None
        self.mCameraIsRadial = { 0:False, 1:False, 2:False, 3:False, 4:True, 5:True }

        self.calibRawDataDirSuffix = ".log"
        self.calibRawDataDir = ""
        self.trackingDir = "Camera8"
        self.ctrlTrackingDir = "Camera9"
        self.rgbLeftDir = "Camera5"
        self.rgbRightDir = "Camera4"    
        self.calibImgSuffix = ".pgm"

        self.calibId = [ [(0,1), (3,3), (self.trackingDir,), "tracking"], [(2,3), (3,3), (self.ctrlTrackingDir,), "ctrl-tracking"], [(4,5), (3,3), (self.rgbLeftDir,self.rgbRightDir), "RGB"]]   
        # calibId = [ [(0,1), (3,3), (trackingDir,), "tracking"], [(2,3), (3,3), (ctrlTrackingDir,), "ctrl-tracking"], [(4,5), (31,31), (rgbLeftDir,rgbRightDir), "RGB"]]
        # calibId = [ [(0,1), (332,332), (trackingDir,), "tracking"], [(2,3), (332,332), (ctrlTrackingDir,), "ctrl-tracking"], [(4,5), (32,32), (rgbLeftDir,rgbRightDir), "RGB"]]        
        # self.targetId = 2    #处理目标: 0-tracking相机；1-ctrl_tracking相机；2-rgb相机
        self.mainImg = 0     #两个图以左右哪个为主：0-左图为主；1-右图为主

        # self.startImgIdx = 3 #-1：表示从第0张图开始处理
        # self.endImgIdx = 100 #-1：表示处理所有图
        # self.stepImgIdx = 1
        # self.pauseShowIdx = [3, 4, 5]

        self.trackingImgs = []
        self.ctrlTrackingImgs = []
        self.rgbLeftImgs = []
        self.rgbRightImgs = []
        self.rgbAlignImgs = []

        self.UseMultiThread = False

        if(useCxxLib[0] and useCxxLib[1] and os.path.exists(useCxxLib[1])):
            print(f"load cxxLib:{useCxxLib[1]}")
            mCTCalibCxxLibHelper = CTCalibCxxLibHelper(useCxxLib[1])
            ret = mCTCalibCxxLibHelper.init()
            print(f"mCTCalibCxxLibHelper init = {ret}")
            
            self.mCalibEpilineChecker = CalibEpilineChecker(mCTCalibCxxLibHelper if (ret) else None)
        else:
            print(f"cxxLib is not exist :{useCxxLib[1]}")
            self.mCalibEpilineChecker = CalibEpilineChecker(None)
        # self.mCalibEpilineChecker = CalibEpilineChecker()

        pass

    '''
    description: 输入标定数据集路径，预先读取所有图片路径，预先读取标定文件数据
    param {*} self
    param {*} calibPath:"xxx/qvrdataset"
    return {*}
    '''
    def feedCalibRawData(self, calibPath, mCameraIsRadial):

        if(not os.path.exists(calibPath)):
            print(f"posePath is invalid:{calibPath}")
            return False

        self.calibPath = calibPath
        self.mCameraIsRadial = mCameraIsRadial

        res1 , rawDataDir = findSubdirWithSuffix(self.calibPath, self.calibRawDataDirSuffix)
        if(res1 == False):
            print("findSubdirWithSuffix fail:", self.calibPath)
            return False
        self.calibRawDataDir = os.path.join(self.calibPath, rawDataDir[0])
        print("calibRawDataDir=", self.calibRawDataDir)

        #读取所有相机图片路径
        res1 , self.trackingImgs = findSubFileWithSuffix(os.path.join(self.calibRawDataDir, self.trackingDir), self.calibImgSuffix)
        if(res1 == False):
            print("find trackingImgs fail:", self.trackingDir)
            return False
        res1 , self.ctrlTrackingImgs = findSubFileWithSuffix(os.path.join(self.calibRawDataDir, self.ctrlTrackingDir), self.calibImgSuffix)
        if(res1 == False):
            print("find ctrlTrackingImgs fail:", self.ctrlTrackingDir)
            return False
        res1 , self.rgbLeftImgs = findSubFileWithSuffix(os.path.join(self.calibRawDataDir, self.rgbLeftDir), self.calibImgSuffix)
        if(res1 == False):
            print("find rgbLeftImgs fail:", self.rgbLeftDir)
            return False
        res1 , self.rgbRightImgs = findSubFileWithSuffix(os.path.join(self.calibRawDataDir, self.rgbRightDir), self.calibImgSuffix)
        if(res1 == False):
            print("find rgbRightImgs fail:", self.rgbRightDir)
            return False
        
        bResult, self.rgbAlignImgs = _timeAlignRgbImgs(self.rgbLeftImgs, self.rgbRightImgs)
        # return False

        print("read raw img success, trackingImgs.size={}, ctrlTrackingImgs.size={}, rgbLeftImgs.size={}, rgbRightImgs.size={},".format(len(self.trackingImgs), len(self.ctrlTrackingImgs),len(self.rgbLeftImgs),len(self.rgbRightImgs)))
        
        # print("process target:{}".format(calibId[targetId]))
    
        #读取标定参数
        self.calibInfo = GtCalibParser.GTCalibInfo()
        if(GtCalibParser.parse_calib_xml(self.calibPath, self.calibInfo) == False):
            print("calib parse fail, path={}".format(self.calibPath))
            self.calibInfo = None
            return False

        print("read calib success, path={}".format(self.calibPath))

        return True

    '''
    description: 得到两个相机的相对几何信息：主要是相对外参，三个欧拉角和平移
    param {*} self
    param {*} cameraId1
    param {*} cameraId2
    return {*}
    '''
    def getGeoInfoBetweenTwo(self, cameraId1, cameraId2):
        if(self.calibInfo is None):
            return [False, None]
        
        cameraModelOut = [CameraModel(), CameraModel()]
        if(self.mCalibEpilineChecker._readCameraParams(self.calibInfo, cameraModelOut, [cameraId1, cameraId2], self.mCameraIsRadial) == False):
            print("read Camera Model Fail")
            return [False, None]
        
        bGeoRet, dGeoRet = cameraModelOut[0].computeGeoInfoToOther(cameraModelOut[1])
        if(bGeoRet == False or dGeoRet == None):
            print("Camera Model computeGeoInfoToOther Fail")
            return [False, None]
        print("two cameras relative Geo Info:".encode('utf-8'))
        print("R_v_theta={}, Euler={},\nrelaT={}, relaT_n={}".format(dGeoRet[0], dGeoRet[1], dGeoRet[2].T, np.linalg.norm(dGeoRet[2])))

        return [bGeoRet, dGeoRet]

    '''
    description: 计算相机对之间的极线距离Err
    param {*} self
    param {*} cameraType:0-tracking; 1-ctrl-tracking; 2-RGB
    return {*}
    '''
    def getEpilinesErrBetweenTwo(self, cameraType, startImgIdx = 3, endImgIdx = 15, stepImgIdx = 1, pauseShowIdx = []):
        
        global mScaleXY
        global mScaleDrawer

        if(not cameraType in [0,1,2]):
            print(f"cameraType invalid:{cameraType}")
        targetId = cameraType

        #处理参数转换
        if(targetId == 0 or targetId == 1):#灰度图        
            if(targetId == 0):
                imgParentDir = os.path.join(self.calibRawDataDir, self.trackingDir)
                imgFileList = self.trackingImgs
            else:

                imgParentDir = os.path.join(self.calibRawDataDir, self.ctrlTrackingDir)
                imgFileList = self.ctrlTrackingImgs

            mScaleXY = (16.0 , 16.0)
            mScaleDrawer = ScaleDrawer(mScaleXY[0], mScaleXY[1])
            
        elif(targetId == 2): #RGB图

            imgParentDir = os.path.join(self.calibRawDataDir)
            imgFileList = self.rgbAlignImgs

            mScaleXY = (3.0 , 3.0)
            mScaleDrawer = ScaleDrawer(mScaleXY[0], mScaleXY[1])

        else:
            print("unkown targetId:{}".format(targetId))
            return [False, None]

        if(startImgIdx < 0):
            startImgIdx = 0
        if(startImgIdx >= len(imgFileList)):
            print("startImgIdx invalid, startImgIdx={}, len(imgFileList)={}".format(startImgIdx, len(imgFileList)))
            return [False, None]               
        if(endImgIdx >= len(imgFileList) or endImgIdx < 0):
            endImgIdx = len(imgFileList) - 1
        if(endImgIdx < startImgIdx):
            print("endImgIdx invalid, endImgIdx={}, startImgIdx={}".format(endImgIdx, startImgIdx))
            return [False, None]
        if(stepImgIdx <= 0):
            stepImgIdx = 1
        
        if(self.calibInfo is None):
            print("calibInfo is None")
            return [False, None]

        cameraModelOut = [CameraModel(), CameraModel()]
        if(self.mCalibEpilineChecker._readCameraParams(self.calibInfo, cameraModelOut, self.calibId[targetId][0], self.mCameraIsRadial) == False):
            print("read Camera Model Fail")
            return [False, None]

        summaryRet = []
        summaryErr = []
        #正式开始处理图片
        if(not self.UseMultiThread):        
            for idx in range(startImgIdx, endImgIdx+1, stepImgIdx):

                start_time = time.perf_counter()

                if(targetId == 0 or targetId == 1):#灰度图
                    imgPathCur = os.path.join(imgParentDir, imgFileList[idx])
                    imgGray = cv.imread(os.path.join(imgParentDir, imgFileList[idx]))
                        
                    split_width = imgGray.shape[1] // 2
                    imgGray2 = [imgGray[: , :split_width], imgGray[: , split_width:]]
                    imgPair = imgGray2
                    
                elif(targetId == 2): #RGB图
                    
                    imgPathCur = [os.path.join(self.calibRawDataDir, self.rgbLeftDir, imgFileList[idx][0]),
                                    os.path.join(self.calibRawDataDir, self.rgbRightDir, imgFileList[idx][1])]

                    imgRgb = [cv.imread(os.path.join(self.calibRawDataDir, self.rgbLeftDir, imgFileList[idx][0])),
                                cv.imread(os.path.join(self.calibRawDataDir, self.rgbRightDir, imgFileList[idx][1]))]
                    imgPair = imgRgb

                else:
                    print("unkown targetId:{}".format(targetId))
                    return [False, None]
                
                print("read img pair cost: {} ms {}".format((time.perf_counter() - start_time)*1000, "<>"*20).encode('utf-8'))

                start_time = time.perf_counter()
                bRet, dRet =  self.mCalibEpilineChecker.check(cameraModelOut, imgPair[0], imgPair[1], self.mainImg, targetId, imgPathCur)
                print("check img pair cost: {} ms {}".format((time.perf_counter() - start_time)*1000, "<>"*20).encode('utf-8'))
                            
                if(idx in pauseShowIdx):
                    cv.waitKey(0)
                    # cv.destroyAllWindows()
                
                if(bRet == False or (dRet is None)):
                    continue
                summaryRet.append(dRet)

                print("*"*150)
                #计算总的平均Err
                print("summaryRet:valid Err num={}".format(len(summaryRet)).encode('utf-8'))
                validSizeAll = 0
                validErrAll = 0
                validVarAll = 0
                for errRetOne in summaryRet:
                    validSizeAll += errRetOne[0]
                    validErrAll += errRetOne[1]*errRetOne[0]
                    validVarAll += errRetOne[2]*errRetOne[0]
                if(validSizeAll <= 0):
                    print("summaryRet: validSizeAll=0")
                else:
                    print("summaryRet: validSizeAll={}, validErrMean={}, validVarMean={}".format(validSizeAll, validErrAll/validSizeAll,validVarAll/validSizeAll))
                
                print("*"*150)
                cv.waitKey(50)

        else:
            
            #多线程处理

            SizeThread = 5
            handleImgIdxs = range(startImgIdx, endImgIdx+1, stepImgIdx)

            
            for idFrom in range(0, len(handleImgIdxs), SizeThread):
                
                start_time = time.perf_counter()

                threadAll = [None]*SizeThread
                retAll = [None]*SizeThread

                def threadFun(idToTrue, imgPathCurTrue, calibEpilineCheckerTrue, mainImgTrue):
                    nonlocal retAll #返回结果

                    start_time = time.perf_counter()
                    if(targetId == 0 or targetId == 1):#灰度图
                        imgGray = cv.imread(imgPathCurTrue)
                            
                        split_width = imgGray.shape[1] // 2
                        imgGray2 = [imgGray[: , :split_width], imgGray[: , split_width:]]
                        imgPair = imgGray2
                        
                    elif(targetId == 2): #RGB图
                        imgRgb = [cv.imread(imgPathCurTrue[0]),
                                    cv.imread(imgPathCurTrue[1])]
                        imgPair = imgRgb

                    else:
                        print("unkown targetId:{}".format(targetId))
                        return 
                    
                    bRet, dRet =  calibEpilineCheckerTrue.check(cameraModelOut, imgPair[0], imgPair[1], mainImgTrue, targetId, imgPathCurTrue)
                    
                    print("check img pair cost: {} ms {}".format((time.perf_counter() - start_time)*1000, "<>"*20).encode('utf-8'))

                    retAll[idToTrue] = [bRet, dRet]
                    return 

                for idTo in range(SizeThread):
                    if((idFrom + idTo) >= len(handleImgIdxs)):
                        continue
                    idx = handleImgIdxs[idFrom + idTo]
                    
                    if(targetId == 0 or targetId == 1):#灰度图
                        imgPathCur = os.path.join(imgParentDir, imgFileList[idx])
                    elif(targetId == 2): #RGB图                    
                        imgPathCur = [os.path.join(self.calibRawDataDir, self.rgbLeftDir, imgFileList[idx][0]),
                                        os.path.join(self.calibRawDataDir, self.rgbRightDir, imgFileList[idx][1])]
                    else:
                        print("unkown targetId:{}".format(targetId))
                        return [False, None]
                    
                    threadAll[idTo] = threading.Thread(target=threadFun, args=(idTo, imgPathCur, self.mCalibEpilineChecker, self.mainImg))
                    
                for idTo in range(SizeThread):
                    if(threadAll[idTo] is None):
                        continue
                    threadAll[idTo].start()

                for idTo in range(SizeThread):
                    if(threadAll[idTo] is None):
                        continue
                    threadAll[idTo].join()


                for idTo in range(SizeThread):
                    if(threadAll[idTo] is None):
                        continue
                    if(retAll[idTo] is None):
                        print(f"thread processed err1, idFrom={idFrom}, idTo={idTo}")
                        continue

                    if(retAll[idTo][0] == False or (retAll[idTo][1] is None)):
                        print(f"thread processed empty, idFrom={idFrom}, idTo={idTo}, bRet={retAll[idTo][0]}, dRet={retAll[idTo][1]}")
                        continue

                    summaryRet.append(retAll[idTo][1])
                
                    print("*"*150)
                    #计算总的平均Err
                    print("summaryRet: valid Err num={}".format(len(summaryRet)).encode('utf-8'))
                    validSizeAll = 0
                    validErrAll = 0
                    validVarAll = 0
                    for errRetOne in summaryRet:
                        validSizeAll += errRetOne[0]
                        validErrAll += errRetOne[1]*errRetOne[0]
                        validVarAll += errRetOne[2]*errRetOne[0]
                    if(validSizeAll <= 0):
                        print("summaryRet: validSizeAll=0")
                    else:
                        print("summaryRet: validSizeAll={}, validErrMean={}, validVarMean={}".format(validSizeAll, validErrAll/validSizeAll,validVarAll/validSizeAll))            
                    print("*"*150)
                
                print("check total{} img pairs, cost: {} ms {}".format(SizeThread, (time.perf_counter() - start_time)*1000, "<>"*50).encode('utf-8'))

                cv.waitKey(50)
        
        cv.waitKey(0)
        cv.destroyAllWindows()

        return [True, summaryRet]