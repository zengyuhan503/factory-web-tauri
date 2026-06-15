import os
import cv2 as cv
import numpy as np
# from skimage import morphology
import random
import math as math
import x10_5_1_Tool_GT_Calib_Parse as GtCalibParser
from x1_opencv.x0_base.x10_1_opencv_0_base import ScaleDrawer as ScaleDrawer
from x0_common.x2_file.x10_0_common_2_file import findSubdirWithSuffix, findSubFileWithSuffix
from x0_common.x0_base.x10_0_common_0_base_type import tupleToInt
import queue
import heapq
import time
from scipy.spatial.distance import cdist

TARGET_A = (1, "TARGET_A")
TARGET_B = (2, "TARGET_B")

BORD_ROWS = 48
BORD_COLS = 24

DIRECTION_4_INFO = ("LEFT", "RIGHT", "UP", "DOWN")


#用作距离排序
class WrapperDist:

    def __init__(self, dist, obj):
        self.dist = dist
        self.obj = obj        
    
    def __lt__(self, other):
        # 定义对象之间的比较方式
        return self.dist > other.dist    

class PointCalibrateBoard:

    def __init__(self):
        self.center_image = np.array([0, 0], dtype=float)
        self.center_image_undist = np.array([0, 0], dtype=float)
        self.center_image_reproject = np.array([0, 0], dtype=float)
        self.center_world_coordinate = np.array([0, 0, 0], dtype=float)
        self.center_camera_coordinate = np.array([0, 0, 0], dtype=float)
        self.vertices = []        
        self.perimeter = 0      #周长
        self.area = 0           #面积
        self.r = 0              #半径：按面积来计算
        self.circle_alpha = 0   #圆形alpha
        self.global_area_order = -1  #单张图全局来看自己的面积排序
        self.ratio = 0
        self.sort_d = 0
        self.contour = []       #轮廓点： N*1*2
        self.left = None
        self.right = None
        self.up = None
        self.down = None

        self.distance_at_image = []   #在单个borad内离自己最近的N个点
        self.distance_at_image_dis = []   #在单个borad内离自己最近的N个点具体距离
        # self.distance_at_image_N_MAX = 20
        # self.distance_at_image_N = -1

        self.direct_left = np.array([0, 0], dtype=float)    #特别注意：方向向量为0代表此方向还未被赋值初始化过！
        self.direct_right = np.array([0, 0], dtype=float)
        self.direct_up = np.array([0, 0], dtype=float)
        self.direct_down = np.array([0, 0], dtype=float)

        self.angle_left = 0
        self.angle_right = 0
        self.angle_up = 0
        self.angle_down = 0

        self.scale_left = 1
        self.scale_right = 1
        self.scale_up = 1
        self.scale_down = 1

        self.bBigger = False
        self.ring_alpha = 100       #是环alpha        
        self.bRing = False          #是否圆环 (在原始轮廓阶段可能是假圆环，需要进一步确认剔除)
        self.bConnected = False
        self.bComplete = False      #是否完成了BFS链接 [bComplete标识4方位补齐了]
        self.bActive = False        #是否在加入过队列 [bActive=True标识入过队]
        self.bChoosed = False
        self.bCenter = False
        self.bWorld = False
        self.times = 0              #[times标识展开过的次数]
        self.type = TARGET_A
        self.col = 0
        self.row = 0

    def isDirectHasRealValue(self, direct):
        assert(direct.size == 2)
        return direct[0] != 0 or direct[1] != 0

    def transCenterToTupleInt(self):
        return (int(self.center_image[0]), int(self.center_image[1]))

    def distanceTo(self, other):
        dist = math.sqrt((other.center_image[0] - self.center_image[0])**2 + (other.center_image[1] - self.center_image[1])**2)
        return dist
        # return [True, [dist]]

    def getInfoSnap1(self):
        return "order={:4d}, center={:.3f},{:.3f}, area={:.3f}, isRing={}, ringAlpha={:.3f}".format(self.global_area_order, self.center_image[0], self.center_image[1], self.area, self.bRing, self.ring_alpha)

    def getInfoSnap2(self):
        return "order={:4d}, center={:.3f},{:.3f}, isRing={}, bComplete={}, bActive={}".format(self.global_area_order, self.center_image[0], self.center_image[1], self.bRing, self.bComplete, self.bActive)

    def getInfoSnap3(self):
        return "order={:4d}, grid_idx={:4d},{:4d}, isRing={}, bComplete={}, bActive={}".format(self.global_area_order, self.col, self.row, self.bRing, self.bComplete, self.bActive)


'''
description: 完整标定板
return {*}
'''
class SetCalibrateBoard:

    def __init__(self):
        self.type = TARGET_A
        # self.grid = np.empty((BORD_ROWS, BORD_COLS), dtype=object)
        self.grid = None                #有序的网格
        self.unorderedCells = None      #无序的np列表

        self.bigThree = np.empty((3,), dtype=object)
        self.gravity_point = np.empty((2,), dtype=object)
        self.direct_point = np.empty((1,), dtype=object)
        self.bigThree_center = np.array([0, 0], dtype=float)

    '''
    description: 用确定的大三圆组来初始化 构建单板
    param {*} self
    param {*} type
    param {*} bigThree
    return {*}
    '''
    def initByBigThree(self, type, bigThree):
        self.type = type
        self.bigThree = bigThree

        #1）大三圆中心点
        self.bigThree_center = np.array([0, 0], dtype=float)
        for idx in range(3):
            self.bigThree_center = self.bigThree_center + bigThree[idx].center_image
        self.bigThree_center = 1.0/3 * self.bigThree_center
        
        #2）大三圆点标记
        gravityIdx = 0
        directIdx = 0
        for idx in range(3):
            if((self.type[0] == TARGET_B[0] and bigThree[idx].bRing) or (self.type[0] == TARGET_A[0] and bigThree[idx].bRing == False )):
                self.gravity_point[gravityIdx] = bigThree[idx]
                gravityIdx += 1
            else:
                self.direct_point[directIdx] = bigThree[idx]
                directIdx += 1
        if(gravityIdx != 2 or directIdx != 1):
            print("Big 3 Circle dots, marking failed!".encode('utf-8'))
            return False        

        #3）大三圆计算坐标系方向，右手坐标系：板子竖着看

        #left正方向作x正方向：从右往左？
        direct_x_2d = self.direct_point[0].center_image - (self.gravity_point[0].center_image + self.gravity_point[1].center_image) / 2
        #up正方向做y正方向：从下往上
        direct_y_2d = self.gravity_point[0].center_image - self.gravity_point[1].center_image
        direct_x_3d = np.array([direct_x_2d[0], direct_x_2d[1], 0]) / np.linalg.norm(direct_x_2d)
        direct_y_3d = np.array([direct_y_2d[0], direct_y_2d[1], 0]) / np.linalg.norm(direct_y_2d)

        #因为板子竖直时:x=(-1,0,0);y=(0,-1,0);z=x叉y=(0,0,1)
        direct_z_3d = np.array([0, 0, 1])
        direct_z_3d_cross = np.cross(direct_x_3d, direct_y_3d)

        d = np.dot(direct_z_3d, direct_z_3d_cross)
        # print("direct_x_2d =", direct_x_2d)
        # print("direct_y_2d =", direct_y_2d)
        # print("direct_z_3d_cross =", direct_z_3d_cross)
        # print("d =", d)

        if d < 0: #和标准z反向
            direct_y_2d = -direct_y_2d
        
        print("direct_x_2d =", direct_x_2d)
        print("direct_y_2d =", direct_y_2d)
        
        self.direct_point[0].direct_down = -direct_y_2d / 2
        self.direct_point[0].direct_up = direct_y_2d / 2
        self.direct_point[0].direct_left = direct_x_2d / 2
        self.direct_point[0].direct_right = -direct_x_2d / 2
        self.direct_point[0].bConnected = True
        self.direct_point[0].col = 13
        # self.direct_point[0].row = 24
        self.direct_point[0].row = 23
        self.direct_point[0].bCenter = True

        self.printInitInfo()

        return True

    '''
    description: 在完成全链接后构建网格
    param {*} self
    return {*}
    '''    
    def buildGridAfterFullConnect(self):
        self.grid = np.empty((BORD_ROWS, BORD_COLS), dtype=object)        
        self.unorderedCells = []
        # cellInQueue = np.zeros((BORD_ROWS, BORD_COLS), dtype=bool)

        oriP = self.direct_point[0]
        activeQ = queue.Queue()

        self.grid[oriP.row][oriP.col] = oriP
        self.unorderedCells.append(oriP)
        activeQ.put(oriP)

        while(not activeQ.empty()):
            curP = activeQ.get()
            # print(curP.getInfoSnap3())
            assert(self.grid[curP.row][curP.col] != None)

            if(curP.left != None and self.grid[curP.left.row][curP.left.col] == None):    #还没有遍历过
                self.grid[curP.left.row][curP.left.col] = curP.left
                self.unorderedCells.append(curP.left)
                activeQ.put(curP.left)
            if(curP.right != None and self.grid[curP.right.row][curP.right.col] == None):    #还没有遍历过
                self.grid[curP.right.row][curP.right.col] = curP.right
                self.unorderedCells.append(curP.right)
                activeQ.put(curP.right)  
            if(curP.up != None and self.grid[curP.up.row][curP.up.col] == None):    #还没有遍历过
                self.grid[curP.up.row][curP.up.col] = curP.up
                self.unorderedCells.append(curP.up)
                activeQ.put(curP.up)  
            if(curP.down != None and self.grid[curP.down.row][curP.down.col] == None):    #还没有遍历过
                self.grid[curP.down.row][curP.down.col] = curP.down
                self.unorderedCells.append(curP.down)
                activeQ.put(curP.down)
        
        self.unorderedCells = np.array(self.unorderedCells)
        print("the board grid build finished:{} , the cell nums={}".format(self.type[1], self.unorderedCells.size).encode('utf-8'))
        return True
        
    '''
    description: 基于匹配的相机模型对网格有效点去畸变
    param {*} self
    return {*}  [True, (去畸变后点列表，去畸变后点grid_id)]
    '''            
    def undistorGridByCamera(self, associatedCamera, doDebug = [False, None]):
        
        if(associatedCamera is None):
            print("undistorGridByCamera associatedCamera is None")
            return [False, None]
        
        if((self.unorderedCells is None) or (self.unorderedCells.size <= 0)):
            print("undistorGridByCamera unorderedCells is None or empty")
            return [False, None]
        
        validCellSize = self.unorderedCells.size
        ptsTmp = [None]*validCellSize
        for idx in range(validCellSize):
            assert((self.unorderedCells[idx] is None) == False)            
            ptsTmp[idx] = [self.unorderedCells[idx].center_image[0], self.unorderedCells[idx].center_image[1]]
        
        ptsTmp = np.array(ptsTmp)
        pts_undistor = associatedCamera.undistorPoints2(ptsTmp, [doDebug[0], doDebug[1], self.type[1]])
        if((pts_undistor is None)):
            print("undistorGridByCamera undistorPoints2 fail 1")
            return [False, None]
        
        if(pts_undistor.shape[0] != validCellSize):
            print("undistorGridByCamera undistorPoints2 fail 2, validCellSize={}, shape={}".format(validCellSize, pts_undistor.shape) )
            return [False, None]

        pts_grid_id = [None]*validCellSize
        for idx in range(validCellSize):
            self.unorderedCells[idx].center_image_undist = np.array([pts_undistor[idx][0][0], pts_undistor[idx][0][1]])
            pts_grid_id[idx] = [self.unorderedCells[idx].row, self.unorderedCells[idx].col]
        return [True, (pts_undistor, pts_grid_id)]




    def printInitInfo(self):
        print("Big 3 circle init Info, type=".encode('utf-8'), self.type[1])
        print("bigThree_center=",self.bigThree_center)
        print("gravity_point=\n{}:{} \n{}:{}".format(self.gravity_point[0].global_area_order, self.gravity_point[0].center_image,self.gravity_point[1].global_area_order, self.gravity_point[1].center_image))
        print("direct_point=\n{}:{}".format(self.direct_point[0].global_area_order, self.direct_point[0].center_image))

        
    def detectBordABFromBigThree(self, ringPair):
        if(len(ringPair) != 3):
            return [False, []]
        ringCount = 0
        for idx in range(3):
            if(ringPair[idx].bRing == True):
                ringCount += 1
        if(ringCount != 1 and ringCount != 2):
            return [False, []]
        
        if(ringCount == 1):
            return [True, [TARGET_A]]
        else:
            return [True, [TARGET_B]]

'''
description: 在单张图上检测圆心特征，并对应唯一位置编号
    1）图像二值化
    2）检测轮廓
    3) 提取大三圆组，同时区分a和b板
    4）在单板上从大三圆起点扩展并标记所有圆
'''
class CircleFeatureDectector:

    def __init__(self, scaleXY):
        self.mScaleXY = scaleXY
        self.mScaleDrawer = ScaleDrawer(self.mScaleXY[0], self.mScaleXY[1])
        self.mScaleDrawerDefault = ScaleDrawer(1.0, 1.0)
        

    '''
    description: 
        灰度化
        分块多阈值二值化并中值滤波
        中值滤波
    param {*} self
    param {*} imgGray
    return {*}
    '''    
    def block_threshold(self, imgIn):

        sub_height_size = 10
        sub_width_size = 10


        binary_threshold_start = 0.2
        binary_threshold_end = 2.0
        binary_threshold_level = 7
        binary_threshold_level_inv = 1.0/binary_threshold_level
        binary_threshold_step = (binary_threshold_end-binary_threshold_start) * binary_threshold_level_inv

        # imgGray = cv.cvtColor(imgIn, cv.COLOR_BGR2GRAY)
        imgGray = imgIn.copy()

        height, width = imgGray.shape[:2]
        split_height = height // sub_height_size
        split_width = width // sub_width_size

        sub_images = np.empty((sub_height_size, sub_width_size), dtype=object)

        #切块
        for hId in range(sub_height_size):  #高度方向切块

            if (hId < (sub_height_size-1)):
                height_start = hId*split_height
                height_end = height_start + split_height
            else:                           #在结束边界单独处理
                height_start = hId*split_height
                height_end = height_start + height-hId*split_height

            for wId in range(sub_width_size):#宽度方向切块

                if (wId < (sub_width_size-1)):
                    width_start = wId*split_width
                    width_end = width_start + split_width
                else:                       #在结束边界单独处理
                    width_start = wId*split_width
                    width_end = width_start + width-wId*split_width                

                #正式作切块:块坐标：块img：块灰度均值
                sub_images[hId][wId] = [[height_start,height_end], [width_start,width_end], imgGray[height_start:height_end, width_start:width_end], 0.0]
                sub_images[hId][wId][3] = np.mean(sub_images[hId][wId][2])

        #对子块图作二值化处理
        thresholded_result_tmp1 = np.zeros_like(imgGray, dtype=np.uint8)    #单阈值二值化结果
        thresholded_result_tmp2 = np.zeros_like(imgGray, dtype=np.uint8)    #多阈值二值化合成结果

        for bid in range(binary_threshold_level):
            binary_threshold_cur = binary_threshold_start + bid * binary_threshold_step
            for hId in range(sub_height_size):
                for wId in range(sub_width_size):
                    
                    binary_threshold_cur_sub = binary_threshold_cur * sub_images[hId][wId][3]
                    _, thresholded = cv.threshold(sub_images[hId][wId][2], binary_threshold_cur_sub, 255, cv.THRESH_BINARY)

                    thresholded_result_tmp1[sub_images[hId][wId][0][0]:sub_images[hId][wId][0][1], sub_images[hId][wId][1][0]:sub_images[hId][wId][1][1]] = thresholded
                    thresholded_result_tmp2[sub_images[hId][wId][0][0]:sub_images[hId][wId][0][1], sub_images[hId][wId][1][0]:sub_images[hId][wId][1][1]] = \
                        thresholded_result_tmp2[sub_images[hId][wId][0][0]:sub_images[hId][wId][0][1], sub_images[hId][wId][1][0]:sub_images[hId][wId][1][1]] + thresholded * binary_threshold_level_inv
            image_thread_comp = np.hstack((thresholded_result_tmp1, thresholded_result_tmp2))
            image_thread_comp = cv.cvtColor(image_thread_comp, cv.COLOR_GRAY2BGR)
            info1 = "binary_threshold at level: {}, binary_threshold_cur: {:.3f}".format(bid, binary_threshold_cur)
            # info2 = "binary_threshold at level: {}, binary_threshold_cur: {}"
            
            cv.putText(image_thread_comp, info1, (30, 30), cv.FONT_HERSHEY_SIMPLEX, 1, color=(0,0,255),thickness=2)
            cv.namedWindow("thresholded_result_tmp", cv.WINDOW_NORMAL)
            cv.imshow("thresholded_result_tmp", image_thread_comp)
            cv.waitKey(1)

        #对子块图作中值滤波
        for hId in range(sub_height_size):
            for wId in range(sub_width_size):
                thresholded_result_tmp2[sub_images[hId][wId][0][0]:sub_images[hId][wId][0][1], sub_images[hId][wId][1][0]:sub_images[hId][wId][1][1]] = \
                    cv.medianBlur(thresholded_result_tmp2[sub_images[hId][wId][0][0]:sub_images[hId][wId][0][1], sub_images[hId][wId][1][0]:sub_images[hId][wId][1][1]], 3)

        cv.namedWindow("thresholded_result", cv.WINDOW_NORMAL)
        cv.imshow("thresholded_result", thresholded_result_tmp2)
        cv.waitKey(0)
        
        #对全图作中值滤波
        thresholded_result_tmp2 = cv.medianBlur(thresholded_result_tmp2, 3)
        cv.namedWindow("thresholded_result", cv.WINDOW_NORMAL)
        cv.imshow("thresholded_result", thresholded_result_tmp2)
        cv.waitKey(0)        

        return thresholded_result_tmp2

    '''
    description: 检测circle轮廓
        提取canny边缘
        提取contour轮廓(外轮廓)
        计算circle圆心面积等参数，并且根据参数初步剔除异常circle

        检测出圆环
            最多采样10个轮廓点，计算轮廓点和轮廓临近内点的灰度值均值：i1
            计算圆心临近4个点的灰度均值:i2
            计算 i1和i2的比例：比例 < 1 即为圆环


        最后有个circle的Merge操作，将所有圆心相近的circle合并（圆心距小于5？）

        将circle按轮廓面积从大到小排序

        确定首个大圆（剔除异常大轮廓）
    param {*} self
    param {*} imgIn
    param {*} doDebug   是否显示普通调试信息
    param {*} doDebug2  是否显示无关紧要信息
    return {*}  按面积排好序的所有circle轮廓，第0个是最大圆
    '''    
    def detect_circle_contours(self, imgIn, doDebug = False, doDebug2 = False):

        contourResult = []

        # imgGray = cv.cvtColor(imgIn, cv.COLOR_BGR2GRAY)
        imgGray = imgIn.copy()

        # start_time = time.perf_counter()
        if(False):
            cv.namedWindow("imgGray_ori", cv.WINDOW_NORMAL)
            cv.imshow("imgGray_ori", imgGray)
            cv.waitKey(0)  
        
        # 提取canny边缘
        # gray_mean = np.mean(imgGray)
        if(False):      #在摄像头脏污，图像模糊时会漏检很多圆
            gray_mean = np.mean(imgGray)
            imgCanny1 = cv.Canny(imgGray, gray_mean, gray_mean * 2.0, 3, L2gradient=False)
            imgCanny = imgCanny1
        elif(False):    #在图像正常时，canny的阈值不稳定，会漏掉一些边缘大片圆
            imgGray = cv.equalizeHist(imgGray)     #会增加很多噪点
            cv.imshow("imgGray_ori", imgGray)
            cv.waitKey(0)
            imgGray = cv.GaussianBlur(imgGray, (3, 3), 0)
            cv.imshow("imgGray_ori", imgGray)
            cv.waitKey(0)
            imgGray = cv.medianBlur(imgGray, 3)
            cv.imshow("imgGray_ori", imgGray)
            gray_mean = np.mean(imgGray)
            imgCanny2 = cv.Canny(imgGray, gray_mean, gray_mean * 2.0, 3, L2gradient=False)

            imgCanny = imgCanny2
        else:           #合并上面两个结果：还有一个问题：有些轮廓圆有一个两个断点
            gray_mean1 = np.mean(imgGray)
            imgCanny1 = cv.Canny(imgGray, gray_mean1, gray_mean1 * 2.0, 3, L2gradient=False)

            imgGray = cv.equalizeHist(imgGray)     #会增加很多噪点
            # cv.imshow("imgGray_ori", imgGray)
            # cv.waitKey(0)
            imgGray = cv.GaussianBlur(imgGray, (3, 3), 0)
            # cv.imshow("imgGray_ori", imgGray)
            # cv.waitKey(0)
            imgGray = cv.medianBlur(imgGray, 3)
            # cv.imshow("imgGray_ori", imgGray)
            gray_mean = np.mean(imgGray)
            imgCanny2 = cv.Canny(imgGray, gray_mean, gray_mean * 2.0, 3, L2gradient=False)

            imgCanny = (0.45 * imgCanny1 + 0.5 * imgCanny2).astype(np.uint8)
            _, imgCanny = cv.threshold(imgCanny, 50, 255, cv.THRESH_BINARY)

        # print("轮廓检测,预处理 图像处理 耗时：{} ms {}".format((time.perf_counter() - start_time)*1000, "+"*10))

        # imgCanny = cv.Canny(imgGray, gray_mean, gray_mean * 2.0, 3, L2gradient=False)

        if(doDebug):
            cv.namedWindow("imgGray_canny", cv.WINDOW_NORMAL)
            cv.imshow("imgGray_canny", imgCanny)
            # cv.waitKey(0)


        #闭运算：填充小黑洞点
        if(False):
            kernel = np.ones((3, 3), np.uint8)
            imgCannyClosing = cv.morphologyEx(imgCanny, cv.MORPH_CLOSE, kernel)
            cv.namedWindow("imgCannyClosing", cv.WINDOW_NORMAL)
            cv.imshow("imgCannyClosing", imgCannyClosing)
            cv.waitKey(0)
        else:
            imgCannyClosing = imgCanny

        # start_time = time.perf_counter()
        # 提取contour轮廓(外轮廓)
        # contours, _ = cv.findContours(imgCannyClosing, cv.RETR_LIST, cv.CHAIN_APPROX_NONE)  # 只找最外层轮廓
        contours, _ = cv.findContours(imgCannyClosing, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_NONE)  # 只找最外层轮廓
        # print("轮廓检测,预处理 提取轮廓 耗时：{} ms {}".format((time.perf_counter() - start_time)*1000, "+"*10))

        if(doDebug2):
            imgDebug = cv.cvtColor(imgIn, cv.COLOR_GRAY2BGR)
            cv.namedWindow("contours_image", cv.WINDOW_NORMAL)
            cv.drawContours(imgDebug, contours, -1, (0, 255, 0), 1)
            cv.imshow("contours_image", imgDebug)
            # cv.waitKey(0)

        start_time = time.perf_counter()

        wrapCircleTime1_4 = 0
        #手动绘制轮廓图
        # if(doDebug[0]):
        if(doDebug or doDebug2):
            imgDebug2 = cv.cvtColor(imgIn, cv.COLOR_GRAY2BGR)
            imgDebug2 = cv.resize(imgDebug2, None, fx = self.mScaleXY[0], fy = self.mScaleXY[1])
            if(doDebug2):
                for cId, contour in enumerate(contours):
                    # 生成随机颜色
                    color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                    for point in contour:
                        # cv.circle(imgDebug2, (point[0][0], point[0][1]), 1, color, -1)
                        # imgDebug2[point[0][1], point[0][0]] = color
                        self.mScaleDrawer.scal_drawDot(imgDebug2, (point[0][0], point[0][1]), color)

                cv.namedWindow("contours_image_hand", cv.WINDOW_NORMAL)
                cv.imshow("contours_image_hand", imgDebug2)
                # cv.waitKey(0)        

        #将轮廓进行封装
        # 计算circle圆心面积等参数，并且根据参数初步剔除异常circle
        # 检测出圆环
        contour_delete_size = 0
        if(doDebug):
            imgDebug3 = cv.cvtColor(imgIn, cv.COLOR_GRAY2BGR)
        tx = False
        for ctId, contour in enumerate(contours):
            circleResult = self.computeCircleFromContour(contour)

            contour_info0 = '{0:.0f} {1:.2f} {2:.2f}'.format( circleResult[1][0], circleResult[1][1], circleResult[1][2])
            contour_info1 = '{0:.0f} {1:.2f}'.format( circleResult[1][0], circleResult[1][1])
            contour_info2 = '{0:.2f}'.format(circleResult[1][2])

            if(circleResult[0] == False):#计算圆的几何参数失败
                if(doDebug):
                    self.mScaleDrawer.scale_drawContours(imgDebug2, [contour], -1, (0, 255, 255), 1)#标记红色为剔除掉的轮廓(面积周长比)
                    self.mScaleDrawer.scale_putText(imgDebug2, contour_info2, (int(circleResult[1][3]), int(circleResult[1][4])), cv.FONT_HERSHEY_SIMPLEX,0.5,color=(0, 255, 255),thickness=1)
                    # cv.drawContours(imgDebug2, [contour], -1, (0, 255, 255), 3)    #标记红色为剔除掉的轮廓(面积周长比)
                    # cv.putText(imgDebug2, contour_info2, (int(circleResult[1][3]), int(circleResult[1][4])), cv.FONT_HERSHEY_SIMPLEX,0.3,color=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)),thickness=1)
                contour_delete_size = contour_delete_size + 1
                continue
            if(circleResult[1][2] < 0.55):#圆度不够
                if(doDebug):
                    self.mScaleDrawer.scale_drawContours(imgDebug2, [contour], -1, (0, 0, 255), 1)    #标记红色为剔除掉的轮廓(面积周长比)
                    self.mScaleDrawer.scale_putText(imgDebug2, contour_info2, (int(circleResult[1][3]), int(circleResult[1][4])), cv.FONT_HERSHEY_SIMPLEX,0.5,color=(0, 0, 255),thickness=1)
                    # cv.drawContours(imgDebug2, [contour], -1, (0, 0, 255), 3)    #标记红色为剔除掉的轮廓(面积周长比)
                    # cv.putText(imgDebug2, contour_info2, (int(circleResult[1][3]), int(circleResult[1][4])), cv.FONT_HERSHEY_SIMPLEX,0.3,color=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)),thickness=1)
                contour_delete_size = contour_delete_size + 1
                continue
            
            if(doDebug):
                self.mScaleDrawerDefault.scal_drawDot(imgDebug3, (int(circleResult[1][3]), int(circleResult[1][4])), (0, 255, 0))

            #准备封装
            pointCalibrateBoard = PointCalibrateBoard()

            #封装圆参数信息
            pointCalibrateBoard.center_image = np.array([circleResult[1][3], circleResult[1][4]])
            pointCalibrateBoard.perimeter = circleResult[1][0]
            pointCalibrateBoard.area = circleResult[1][1]
            pointCalibrateBoard.r = math.sqrt(pointCalibrateBoard.area/math.pi)
            pointCalibrateBoard.circle_alpha = circleResult[1][2]
            pointCalibrateBoard.contour = contour

            # start_time1_4 = time.perf_counter()
            # ringRatioResult = self.computeRingRatio(ctId, contour, circleResult[1][3], circleResult[1][4], imgGray, 6)
            # wrapCircleTime1_4 += (time.perf_counter() - start_time1_4)*1000
            # if(ringRatioResult[0] == False):
            #     pointCalibrateBoard.ring_alpha = 100
            #     pointCalibrateBoard.bRing = False
            #     if(doDebug):
            #         self.mScaleDrawer.scale_drawContours(imgDebug2, [contour], -1, (0, 0, 0), 2)    #标记黑色是
            # elif(ringRatioResult[1][0] > 1):
            #     pointCalibrateBoard.ring_alpha = ringRatioResult[1][0]
            #     pointCalibrateBoard.bRing = False
            #     if(doDebug):
            #         self.mScaleDrawer.scale_drawContours(imgDebug2, [contour], -1, (255, 0, 0), 2)    #标记蓝色不是圆环
            #         ringInfo = "{}:{:.2f} {:.2f} {:.2f}".format(ctId, ringRatioResult[1][0], ringRatioResult[1][1], ringRatioResult[1][2])
            #         self.mScaleDrawer.scale_putText(imgDebug2, ringInfo, (int(circleResult[1][3]), int(circleResult[1][4])), cv.FONT_HERSHEY_SIMPLEX,0.5,color=(0, 0, 255),thickness=1)
            # else:
            #     pointCalibrateBoard.ring_alpha = ringRatioResult[1][0]
            #     pointCalibrateBoard.bRing = True                
            #     if(doDebug):
            #         self.mScaleDrawer.scale_drawContours(imgDebug2, [contour], -1, (0, 255, 0), 5)    #标记绿色是候选圆环
            #         ringInfo = "{}:{:.2f} {:.2f} {:.2f}".format(ctId, ringRatioResult[1][0], ringRatioResult[1][1], ringRatioResult[1][2])
            #         self.mScaleDrawer.scale_putText(imgDebug2, ringInfo, (int(circleResult[1][3]), int(circleResult[1][4])), cv.FONT_HERSHEY_SIMPLEX,0.5,color=(0, 0, 255),thickness=1)                
                    

            # self.mScaleDrawer.scale_drawContours(imgDebug2, [contour], -1, (255, 0, 0), 1)    #标记红色为剔除掉的轮廓(面积周长比)
            # self.mScaleDrawer.scale_putText(imgDebug2, contour_info2, (int(circleResult[1][3]), int(circleResult[1][4])), cv.FONT_HERSHEY_SIMPLEX,0.5,color=(255, 0, 0),thickness=1)

            # if(tx == False):
            #     tx = True

            contourResult.append(pointCalibrateBoard)

        print("valid contour size = ", len(contourResult), ", contour_delete_size=", contour_delete_size)

        # if(doDebug):
        #     cv.namedWindow("contours_image_hand2", cv.WINDOW_NORMAL)
        #     cv.imshow("contours_image_hand2", imgDebug2)
        #     # cv.waitKey(0)          
        # if(doDebug2):
        #     cv.namedWindow("contours_image_hand3", cv.WINDOW_NORMAL)
        #     cv.imshow("contours_image_hand3", imgDebug3)
        #     # cv.waitKey(0)

        # print("轮廓检测,预处理 其它1 耗时：{} ms , wrapCircleTime1={}, wrapCircleTime1_2={}  {}".format((time.perf_counter() - start_time)*1000, wrapCircleTime1, wrapCircleTime1_2, "+"*10))
        print("contours detection, pretreatment other1 cost time : {} ms , wrapCircleTime1_3=, {}".format((time.perf_counter() - start_time)*1000, "+"*10).encode('utf-8'))

        # 将circle按轮廓面积从大到小排序
        sorted_contourResult = sorted(contourResult, key= lambda x: x.area, reverse=True)

        # 确定首个大圆（剔除异常大轮廓）
        if(True):
            #一张图一行至少能拍到10个圆，以此作为圆最大半径和面积阈值
            maxR = imgIn.shape[0]
            if(maxR > imgIn.shape[1]):
                maxR = imgIn.shape[1]    
            maxR = maxR / (2.0*10)
            maxArea = math.pi * maxR * maxR

            contourSize = len(sorted_contourResult)
            biggestCircleIndex = -1
            big_circle_threa1 = [1.3, 1.3, 1.5]
            for idx, curContour in enumerate(sorted_contourResult):
                if(curContour.area > maxArea):
                    print("The current contour area is too large, maxArea={}, cur_area={}".format(maxArea, curContour.area).encode('utf-8'))
                    continue
                if(idx + 15 >= contourSize):
                    print("check biggest circle, Too few remaining contours, contourSize={}, idx={}".format(contourSize, idx).encode('utf-8'))
                    break

                ratio1 = curContour.area/sorted_contourResult[idx+1].area
                ratio2 = curContour.area/sorted_contourResult[idx+2].area
                ratio3 = curContour.area/sorted_contourResult[idx+15].area

                if(doDebug and idx < 20):
                    print("check biggest circle, id={},r={:.3f},area1={},area2={},area3={},areax={},ratio1={:.3f},ratio2={:.3f},ratio3={:.3f}".format
                             (idx, curContour.r, curContour.area, sorted_contourResult[idx+1].area, sorted_contourResult[idx+2].area, sorted_contourResult[idx+15].area, ratio1, ratio2, ratio3))
                if(ratio1 > big_circle_threa1[0] or ratio2 > big_circle_threa1[1]):   #最大圆和次大圆面积比例不会相差很大！（小于1.2）
                    continue
                if(ratio3 < big_circle_threa1[2]):
                    continue
                print("find the biggest circle success: ".encode('utf-8'), idx)
                biggestCircleIndex = idx
                break
            
            if(biggestCircleIndex < 0):
                print("find the biggest circle fail".encode('utf-8'))
                contour_delete_size += len(sorted_contourResult)

                sorted_contourResult.clear()                
            else:
                contour_delete_size += (biggestCircleIndex)
                sorted_contourResult = sorted_contourResult[biggestCircleIndex : ]

        for idx in range(len(sorted_contourResult)):
            sorted_contourResult[idx].global_area_order = idx

        print("after sort,  valid contour size = ", len(sorted_contourResult), ", contour_delete_size=", contour_delete_size)

        wrapCircleTime1_4 = 0
        #把圆环检测放到后面来,放前面比较耗时
        sortedSize = len(sorted_contourResult)
        for idx, pointCalibrateBoard in enumerate(sorted_contourResult):

            if(idx > max(200, 0.1 * sortedSize)):   #按照经验来说, 圆环只出现在前几个大的circles中, 有性能问题时此处还可以加速
                continue

            start_time1_4 = time.perf_counter()
            ctId = pointCalibrateBoard.global_area_order
            contour = pointCalibrateBoard.contour
            ringRatioResult = self.computeRingRatio(ctId, contour, pointCalibrateBoard.center_image[0], pointCalibrateBoard.center_image[1], imgGray, 6)
            wrapCircleTime1_4 += (time.perf_counter() - start_time1_4)*1000
            if(ringRatioResult[0] == False):
                pointCalibrateBoard.ring_alpha = 100
                pointCalibrateBoard.bRing = False
                if(doDebug):
                    self.mScaleDrawer.scale_drawContours(imgDebug2, [contour], -1, (0, 0, 0), 2)    #标记黑色是
            elif(ringRatioResult[1][0] > 1):
                pointCalibrateBoard.ring_alpha = ringRatioResult[1][0]
                pointCalibrateBoard.bRing = False
                if(doDebug):
                    self.mScaleDrawer.scale_drawContours(imgDebug2, [contour], -1, (255, 0, 0), 2)    #标记蓝色不是圆环
                    ringInfo = "{}:{:.2f} {:.2f} {:.2f}".format(ctId, ringRatioResult[1][0], ringRatioResult[1][1], ringRatioResult[1][2])
                    self.mScaleDrawer.scale_putText(imgDebug2, ringInfo, (int(pointCalibrateBoard.center_image[0]), int(pointCalibrateBoard.center_image[1])), cv.FONT_HERSHEY_SIMPLEX,0.5,color=(0, 0, 255),thickness=1)
            else:
                pointCalibrateBoard.ring_alpha = ringRatioResult[1][0]
                pointCalibrateBoard.bRing = True                
                if(doDebug):
                    self.mScaleDrawer.scale_drawContours(imgDebug2, [contour], -1, (0, 255, 0), 5)    #标记绿色是候选圆环
                    ringInfo = "{}:{:.2f} {:.2f} {:.2f}".format(ctId, ringRatioResult[1][0], ringRatioResult[1][1], ringRatioResult[1][2])
                    self.mScaleDrawer.scale_putText(imgDebug2, ringInfo, (int(pointCalibrateBoard.center_image[0]), int(pointCalibrateBoard.center_image[1])), cv.FONT_HERSHEY_SIMPLEX,0.5,color=(0, 0, 255),thickness=1)                
                    
        print("contours detection, pretreatment other2 cost time : wrapCircleTime1_4={}  {}".format(wrapCircleTime1_4, "+"*10).encode('utf-8'))
        if(doDebug):
            cv.namedWindow("contours_image_hand2", cv.WINDOW_NORMAL)
            cv.imshow("contours_image_hand2", imgDebug2)
            # cv.waitKey(0)          
        if(doDebug2):
            cv.namedWindow("contours_image_hand3", cv.WINDOW_NORMAL)
            cv.imshow("contours_image_hand3", imgDebug3)
            # cv.waitKey(0)


        return sorted_contourResult


    # 所有
    '''
    description: 提取大三圆组，同时区分a和b板
    param {*} self
    param {*} oriCircles
    param {*} doDebug   是否debug show 图像
    param {*} doDebug2  是否debug show 日志
    return {*}
    '''    
    def detectBigThree(self, oriCircles, doDebug = [False, None], doDebug2 = False):

        #先得到所有候选圆环
        candiRings = []        
        oriSize = len(oriCircles)
        for idx in range(oriSize):
            if(oriCircles[idx].bRing):
                candiRings.append(oriCircles[idx])
                print("check ring, idx={}, oriSize={}, ratio={:.5f} {} ".format(idx, oriSize, idx/oriSize, "#"*10))
        
        print("candiRings size = ", len(candiRings))

        resultRings = []

        if(doDebug[0] == True):
            imgDebug2 = cv.cvtColor(doDebug[1], cv.COLOR_GRAY2BGR)
            imgDebug2 = cv.resize(imgDebug2, None, fx = self.mScaleXY[0], fy = self.mScaleXY[1])

            
            #把所有排好序的候选circle绘制出来：绿心，蓝圈，红序号
            for imDx in range(oriSize):
                contour_info = "s{}".format(oriCircles[imDx].global_area_order)
                self.mScaleDrawer.scal_drawDot(imgDebug2, oriCircles[imDx].transCenterToTupleInt(), (0,255, 0))
                if(oriCircles[imDx].bRing):
                    self.mScaleDrawer.scale_drawContours(imgDebug2, [oriCircles[imDx].contour], -1, (0, 255, 0), 15)
                else:
                    self.mScaleDrawer.scale_drawContours(imgDebug2, [oriCircles[imDx].contour], -1, (255, 0, 0), 15)                    
                self.mScaleDrawer.scale_putText(imgDebug2, contour_info, oriCircles[imDx].transCenterToTupleInt(), cv.FONT_HERSHEY_SIMPLEX,0.5,color=(0, 0, 255),thickness=1)

            # cv.namedWindow("oriCircles", cv.WINDOW_NORMAL)
            # cv.imshow("oriCircles", imgDebug2)
            # cv.waitKey(0)   

        #单个圆环确定：
            #按面积来看，最多取往前15个，往后15个，共30个作为搜索范围
            #进一步：和自己的面积比例 在1.3和1/1.3范围之内
            #所有候选集合找和自己距离最近的3个
        
        firsValidRMean = -1 #确定的第1个有效的三圆组半径均值：用来剔除异常的三圆组
        for candiRing in candiRings:
            startIdx = candiRing.global_area_order - 15
            endIdx = candiRing.global_area_order + 15
            if(startIdx < 0):
                startIdx = 0
            if(endIdx >= oriSize):
                endIdx = oriSize - 1
            
            ringPair = []
            ringPair.append(candiRing)

            sortedCircles = self.sortcircleByDistance(candiRing, oriCircles[startIdx:(endIdx+1)])

            if(doDebug2 == True):
                imgCandiRing = imgDebug2.copy()
                for idS in range(len(sortedCircles)):
                    if(sortedCircles[idS][1].global_area_order == candiRing.global_area_order):
                        continue
                    # lineInfo = "{}:".format(idS)
                    # print("dist=", sortedCircles[idS][0])
                    lineInfo = "{}:{:.2f}".format(idS, sortedCircles[idS][0])
                    fromP = candiRing.transCenterToTupleInt()
                    toP = sortedCircles[idS][1].transCenterToTupleInt()
                    midP = (int(0.5*(fromP[0] + toP[0])), int(0.5*(fromP[1] + toP[1])))
                    self.mScaleDrawer.scale_line(imgCandiRing, fromP, toP, (255, 255, 0), 1)
                    self.mScaleDrawer.scale_putText(imgCandiRing, lineInfo, midP, cv.FONT_HERSHEY_SIMPLEX,0.5,color=(255, 255, 0),thickness=1)
                
                cv.namedWindow("imgCandiRing", cv.WINDOW_NORMAL)
                cv.imshow("imgCandiRing", imgCandiRing)
                cv.waitKey(50)

            for idS, sortedC in enumerate(sortedCircles):

                if(doDebug2):
                    print("find big 3 circles, 目标id={},候选id={},dist={:.2f},area={:.2f},center={}, isRing={}, ringAlpha={:.3f}".format(candiRing.global_area_order, sortedC[1].global_area_order, sortedC[0], sortedC[1].area, sortedC[1].center_image, sortedC[1].bRing, sortedC[1].ring_alpha).encode('utf-8'))

                if(idS == 0):   #自己和自己
                    continue
                areaRatio = candiRing.area / sortedC[1].area
                if(areaRatio < 1/1.5 or areaRatio > 1.5):
                    continue
                ringPair.append(sortedC[1])
                if(len(ringPair) == 3):
                    break
            ringPair = sorted(ringPair, key=lambda x:x.global_area_order)
            if(len(ringPair) == 3):
                if(doDebug2):
                    print("find valid big 3 circles : ".encode('utf-8'))
                    for ringPairOne in ringPair:
                        print("global_area_order={},area={:.2f},center={}, isRing={}, ringAlpha={:.3f}".format(ringPairOne.global_area_order, ringPairOne.area, ringPairOne.center_image, ringPairOne.bRing, ringPairOne.ring_alpha))
            else:
                continue
            
            #check校验三圆组：三圆组距离小于半径10倍值
            #check校验三圆组：三圆组距离要求一样！

            rMean = 0
            for jdx in range(3):
                rMean += ringPair[jdx].r
            rMean /= 3

            dist = []
            for jdx in range(3):
                for kdx in range(jdx + 1, 3):
                    distTmp = ringPair[jdx].distanceTo(ringPair[kdx])
                    # if(distTmp[0] == False):
                    #     continue
                    # dist.append(distTmp[1][0])
                    dist.append(distTmp)
            if(len(dist) != 3):
                print("len(dist) != 3")
                continue
            distMean = 0
            for jdx in range(3):
                distMean += dist[jdx]
            distMean /= 3

            disVar = 0
            for jdx in range(3):
                disVar += (dist[jdx] - distMean)**2
            disVar /= 3

            if(doDebug2):
                print("dist_list={},distMean={:3f},disVar_norm={:3f}, rMean={:3f}, distMean/rMean={:.3f}".format(dist, distMean, disVar/(distMean**2)*1000, rMean, (distMean/rMean)))
            if(firsValidRMean <= 0):
                if(doDebug2):
                    print("firsValidRMean <= 0")
            else:
                if(doDebug2):
                    print("rMean/firsValidRMean=", rMean/firsValidRMean)

                #大三圆的半径均值和第一个比例相比不能小太多！
                if(rMean/firsValidRMean < 0.5): 
                    if(doDebug2):
                        print("rMean/firsValidRMean is Too small to meet requirements!!!!!!".encode('utf-8'))
                    continue

            #归一化后disVar值最大不超过10
            #distMean/rMean值在5左右可以放宽到5正负2
            if(disVar/(distMean**2)*1000 > 10 or (distMean/rMean) > (5+2) or (distMean/rMean) < (5-2)):      
            # if(False):
                if(doDebug2):
                    print("the candidate big 3 circles invalid, about mean dist and radius!!!!!!".encode('utf-8'))
                continue

            if(doDebug2 == True):
                for jdx in range(3):
                    self.mScaleDrawer.scale_drawContours(imgCandiRing, [ringPair[jdx].contour], -1, (0, 255, 255), 5)
                    for kdx in range(jdx + 1, 3):
                        lineInfo = "d:{:.2f}".format(ringPair[jdx].distanceTo(ringPair[kdx]))
                        fromP = ringPair[jdx].transCenterToTupleInt()
                        toP = ringPair[kdx].transCenterToTupleInt()
                        midP = (int(0.5*(fromP[0] + toP[0])), int(0.5*(fromP[1] + toP[1])))
                        self.mScaleDrawer.scale_line(imgCandiRing, fromP, toP, (0, 255, 255), 2)
                        # self.mScaleDrawer.scale_putText(imgCandiRing, lineInfo, midP, cv.FONT_HERSHEY_SIMPLEX,0.5,color=(0, 255, 255),thickness=1)
                cv.namedWindow("imgCandiRing", cv.WINDOW_NORMAL)
                cv.imshow("imgCandiRing", imgCandiRing)
                cv.waitKey(50)

            curSetCalibrateBoard = SetCalibrateBoard()
            bordType = curSetCalibrateBoard.detectBordABFromBigThree(ringPair)
            if(bordType[0] == False):
                print("Board A/B detetion failed".encode('utf-8'))
                continue
            if(curSetCalibrateBoard.initByBigThree(bordType[1][0], np.array(ringPair)) == False):
                print("big 3 circles inited Board failed".encode('utf-8'))
                continue

            #三圆组剔重

            if(len(resultRings) <= 0):
                resultRings.append(curSetCalibrateBoard)
                if(firsValidRMean <= 0):
                    firsValidRMean = rMean
            else:
                isExist = False
                for jdx in range(len(resultRings)):
                    isExist = True
                    for kdx in range(3):
                        # print("resultRings[jdx].bigThree shape=", resultRings[jdx].bigThree.shape)
                        # print(resultRings[jdx].bigThree[kdx])
                        # print(curSetCalibrateBoard.bigThree[kdx])
                        if(resultRings[jdx].bigThree[kdx].global_area_order != curSetCalibrateBoard.bigThree[kdx].global_area_order):
                            isExist = False
                    if(isExist):
                        print("big 3 circles is duplicated, skip".encode('utf-8'))
                        break
                if(isExist == False):
                    resultRings.append(curSetCalibrateBoard)
                    if(firsValidRMean <= 0):
                        firsValidRMean = rMean                    
            
        print("the final big 3 circles, size = ".encode('utf-8'), len(resultRings))
        for idx in range(len(resultRings)):
            print("the {}th, bord info : {}".format(idx, resultRings[idx].type[1]).encode('utf-8'))

            for jdx in range(3):
                print("global_area_order={},area={:.2f},center={}, isRing={}, ringAlpha={:.3f}".format(resultRings[idx].bigThree[jdx].global_area_order, resultRings[idx].bigThree[jdx].area, resultRings[idx].bigThree[jdx].center_image, resultRings[idx].bigThree[jdx].bRing, resultRings[idx].bigThree[jdx].ring_alpha))
        
        return resultRings

    '''
    description: 根据原始circle集合和大三圆构建board

        1）原始circle分配到A/B板：根据到大三圆的中心距离分配
        2）确定坐标系

        3）单板建立grid全链接：
            BFS方式遍历建立全连接关系
                队列存储活动节点
                大三圆原点初始化队列
                遍历队列，取用一个点p
                    点p在所有点中找距离最近的4个点
                    这4个点构建p的上下左右临接点
                    临接点未完成链接的加入队列
    param {*} self
    param {*} oriCircles
    param {*} resultRings
    return {*}  [True/False, [ringBoardA, ringBoardB]]
    '''    
    def buildBothBord(self, oriCircles, resultRings, doDebug = [False, None], doDebug2 = False):

        # 1）原始circle分配到A/B板：根据到大三圆的中心距离分配
        ringBoardA = None   #只取第1个
        ringBoardB = None   #只取第1个
        for idx in range(len(resultRings)):
            if(resultRings[idx].type[0] == TARGET_A[0]):
                if(ringBoardA):
                    print("skip extra ringBoardA !!!!!!!!!!")
                    resultRings[idx].printInitInfo()
                    continue
                ringBoardA = resultRings[idx]
            elif(resultRings[idx].type[0] == TARGET_B[0]):
                if(ringBoardB):
                    print("skip extra ringBoardB !!!!!!!!!!!")
                    resultRings[idx].printInitInfo()                    
                    continue
                ringBoardB = resultRings[idx]
            else:
                print("skip extra unkown type board !!!!!!!!")
                resultRings[idx].printInitInfo()                  
                continue
        
        if((not ringBoardA) and (not ringBoardB)):
            return [False, [ringBoardA, ringBoardB]]
        elif(not ringBoardA):
            self.buildSingleBord(oriCircles, ringBoardB, doDebug, doDebug2)
            return [True, [ringBoardA, ringBoardB]]
        elif(not ringBoardB):
            self.buildSingleBord(oriCircles, ringBoardA, doDebug, doDebug2)
            return [True, [ringBoardA, ringBoardB]]
        else:
            start_time = time.perf_counter()

            #先将原始circles拆分到boardA和boardB
            oriCirclesForBoardA = []
            oriCirclesForBoardB = []
            for circleOne in oriCircles:
                if(np.linalg.norm(ringBoardA.bigThree_center - circleOne.center_image) < np.linalg.norm(ringBoardB.bigThree_center - circleOne.center_image)):
                    oriCirclesForBoardA.append(circleOne)
                else:
                    oriCirclesForBoardB.append(circleOne)                

            print("one img split board A/B cost : {} ms {}".format((time.perf_counter() - start_time)*1000, "/"*15).encode('utf-8'))

            self.buildSingleBord(oriCirclesForBoardA, ringBoardA, doDebug, doDebug2)
            self.buildSingleBord(oriCirclesForBoardB, ringBoardB, doDebug, doDebug2)
            return [True, [ringBoardA, ringBoardB]]


    '''
    description: 

        3）单板建立grid全链接：
            BFS方式遍历建立全连接关系
                队列存储活动节点
                大三圆原点初始化队列
                遍历队列，取用一个点curp
                    xx-BFS展开条件：作一次逻辑链接（非展开链接），完成一次逻辑链接后， curP 4方向未补齐或者展开次数为0 就 进行BFS4方向展开 [times标识展开过的次数] [bComplete标识4方位补齐了]
                        点curp在所有点中找距离最近的4个点
                        这4个点构建curp的上下左右临接点：4个点存在错误，需要作过滤：要求和先验方向角度一致，要求和先验方向长度一致，同一个方向有多个满足要求的，取长度最接近1.0的
                        xx-临接点入队条件：还没有入过队  [bActive=True标识入过队]

    param {*} self
    param {*} oriCircles
    param {*} singleRingBoard
    param {*} doDebug   是否开启图像show debug
    param {*} doDebug2   是否开启日志打印 debug
    param {*} None
    return {*}
    '''
    def buildSingleBord(self, oriCircles, singleRingBoard, doDebug = [False, None], doDebug2 = False):

        oriSize = len(oriCircles)
        print("buildSingleBord, oriCircles For {} size = {}".format(singleRingBoard.type[1], oriSize))
        if(doDebug[0] == True):
            imgDebug2 = cv.cvtColor(doDebug[1], cv.COLOR_GRAY2BGR)
            imgDebug2 = cv.resize(imgDebug2, None, fx = self.mScaleXY[0], fy = self.mScaleXY[1])
            
            #把所有排好序的候选circle绘制出来：绿心，蓝圈，红序号
            for imDx in range(oriSize):
                contour_info = "s{}".format(oriCircles[imDx].global_area_order)
                self.mScaleDrawer.scal_drawDot(imgDebug2, oriCircles[imDx].transCenterToTupleInt(), (0,255, 0))
                if(oriCircles[imDx].bRing):
                    self.mScaleDrawer.scale_drawContours(imgDebug2, [oriCircles[imDx].contour], -1, (0, 255, 0), 15)
                else:
                    self.mScaleDrawer.scale_drawContours(imgDebug2, [oriCircles[imDx].contour], -1, (255, 0, 0), 15)                    
                self.mScaleDrawer.scale_putText(imgDebug2, contour_info, oriCircles[imDx].transCenterToTupleInt(), cv.FONT_HERSHEY_SIMPLEX,0.5,color=(0, 0, 255),thickness=1)

            cv.namedWindow("oriCircles For {}".format(singleRingBoard.type[1]), cv.WINDOW_NORMAL)
            cv.imshow("oriCircles For {}".format(singleRingBoard.type[1]), imgDebug2)
            # cv.waitKey(0)

        curZeroCircle = singleRingBoard.direct_point[0]        

        self.sortBordPointByDistance2(oriCircles)

        activeQ = queue.Queue()
        singleRingBoard.direct_point[0].bActive = True
        activeQ.put(singleRingBoard.direct_point[0])

        if(doDebug[0] == True):
            imgDebug2_copy = imgDebug2.copy()

        start_time = time.perf_counter()
        tmpCount = 0
        tmpCount2 = 0   #作耗时的展开次数
        tmpCount3 = 0   #作耗时的展开次数
        time0_connect_logic = 0.0
        time1_getNearN = 0.0
        time2_computeNearCandi = 0.0
        time2_1_computeNearCandi_Angle = 0.0
        time3_computeConnectPositive = 0.0
        time4_computeConnectNegtive = 0.0

        while( not activeQ.empty()):
            tmpCount += 1
            curP = activeQ.get()
            # curP.bActive = False
            if(doDebug2):
                print("-"*150)
                print("curPInfo:" + curP.getInfoSnap3())

            if((curP.left and curP.right and curP.up and curP.down)):
                curP.bComplete = True

            if(not curP.bComplete):
                # start_time0 = time.perf_counter()
                self._connect_logic_points(curP, [doDebug[0], imgDebug2_copy if(doDebug[0]) else None])
                # time0_connect_logic += (time.perf_counter() - start_time0)*1000
                if((curP.left and curP.right and curP.up and curP.down) or curP.times > 0):#当前P还没有完成4方链接 or 之前尝试过一次四方连接了但是没有找到完整4方链接
                    curP.bComplete = True
                if(curP.bComplete):
                    curPNear4Tmp = [curP.left, curP.right, curP.up, curP.down]
                    for curPNearTmp in curPNear4Tmp:
                        if(curPNearTmp.bActive == False):
                            curPNearTmp.bActive = True
                            activeQ.put(curPNearTmp)
                            if(doDebug[0]):
                                self.mScaleDrawer.scale_line(imgDebug2_copy, curP.center_image, curPNearTmp.center_image, (0, 0, 255), 10)
                    
                    if(doDebug[0]):
                        self.mScaleDrawer.scale_drawContours(imgDebug2_copy, [curP.contour], -1, (0, 0, 255), 20)
                        if(tmpCount % 100 == 0):
                            cv.namedWindow("Connections For {}".format(singleRingBoard.type[1]), cv.WINDOW_NORMAL)
                            cv.imshow("Connections For {}".format(singleRingBoard.type[1]), imgDebug2_copy)
                            cv.waitKey(100)

                    continue
                

                if(doDebug[0]):
                    self.mScaleDrawer.scale_drawContours(imgDebug2_copy, [curP.contour], -1, (0, 255, 255), 20)
                    if(tmpCount % 100 == 0):
                        cv.namedWindow("Connections For {}".format(singleRingBoard.type[1]), cv.WINDOW_NORMAL)
                        cv.imshow("Connections For {}".format(singleRingBoard.type[1]), imgDebug2_copy)
                        cv.waitKey(2)
                    self.mScaleDrawer.scale_drawContours(imgDebug2_copy, [curP.contour], -1, (0, 0, 255), 20)

                #是否active，是否完成了四方链接，是否尝试过链接了！
                # if((not curP.bComplete) or (curP.times <= 0)):#当前P还没有完成4方链接 or 之前尝试过一次四方连接了但是没有找到完整4方链接
                if(True):
                    curP.times += 1
                    
                    tmpCount2 += 1

                    # #尝试搜索距离最近的5个点（包括自己）
                    # start_time1 = time.perf_counter()
                    # nearN = self.getNearN(curP, oriCircles, 5)
                    # time1_getNearN += (time.perf_counter() - start_time1)*1000

                    curP4Direct_pre = [curP.direct_left, curP.direct_right, curP.direct_up, curP.direct_down]
                    curP4Direct_pre_n = [np.linalg.norm(curP1Direct_pre) for curP1Direct_pre in curP4Direct_pre]
                    curP4Scale = [curP.scale_left, curP.scale_right, curP.scale_up, curP.scale_down]

                    # start_time2 = time.perf_counter()
                    curP4Direct_candi = [None]*4  #4个方位留空，作为当前curP的候选4方位: 单个方位=[角度偏差，模长偏差, 综合偏差，候选点] [候选点, 方向向量, 角度偏差，模长偏差, 综合偏差]

                    # for ndx, curNear in enumerate(nearN):
                    for ndx, curNear in enumerate(curP.distance_at_image):
                        if(ndx == 0):   #自己
                            continue
                        if(ndx > 4):   #最多check4个
                            break
                        # curNear = curNear[0]

                        #跳过重复计算
                        if(curNear == curP.left
                            or curNear == curP.right
                            or curNear == curP.up
                            or curNear == curP.down):
                            continue

                        curNearDirect = curNear.center_image - curP.center_image
                        curNearDirect_n = np.linalg.norm(curNearDirect)
                        
                        # start_time2_1 = time.perf_counter()
                        #和先验4方位对比：左右上下
                        #确定候选点是4个方位哪一方位:minAngleIndex
                        near4Direct = [None]*4
                        near4Direct[0] = self.getAngleBy2D(curP.direct_left, curNearDirect)
                        near4Direct[1] = self.getAngleBy2D(curP.direct_right, curNearDirect)
                        near4Direct[2] = self.getAngleBy2D(curP.direct_up, curNearDirect)
                        near4Direct[3] = self.getAngleBy2D(curP.direct_down, curNearDirect)
                        # time2_1_computeNearCandi_Angle += (time.perf_counter() - start_time2_1)*1000
                        minAngleIndex = 0
                        for pdx in range(1, 4):
                            if(abs(near4Direct[pdx]) < abs(near4Direct[minAngleIndex])):
                                minAngleIndex = pdx
                        
                        #角度偏差阈值
                        if(abs(near4Direct[minAngleIndex]) > 15):
                            if(doDebug2):
                                print("nearPInfo:" + curNear.getInfoSnap2() + ",dist={:.3f}".format(curP.distanceTo(curNear)))
                                print("curNearDirect is {}, but angle is too big {}".format(DIRECTION_4_INFO[minAngleIndex], near4Direct[minAngleIndex]))
                            continue
                        
                        #模长偏差阈值
                        nearScale = curNearDirect_n / curP4Direct_pre_n[minAngleIndex]
                        if(nearScale < 0.6 or nearScale > 1.4 or abs(nearScale - curP4Scale[minAngleIndex]) > 0.2):
                            if(doDebug2):
                                print("nearPInfo:" + curNear.getInfoSnap2() + ",dist={:.3f}".format(curP.distanceTo(curNear)))
                                print("curNearDirect is {}, but scale is invalid, nearScale={}, curScale_df={}".format(DIRECTION_4_INFO[minAngleIndex], nearScale,  abs(nearScale - curP4Scale[minAngleIndex])))
                            continue

                        nearAngleScaleRatio = 0.5 * abs(near4Direct[minAngleIndex]) / 180 + 0.5*abs(nearScale - 1.0)

                        #准备添加
                        if(curP4Direct_candi[minAngleIndex]):   #已经被占空了，开始pk
                            if(nearAngleScaleRatio > curP4Direct_candi[minAngleIndex][4]):  #综合偏差没pk过
                                if(doDebug2):
                                    print("nearPInfo:" + curNear.getInfoSnap2() + ",dist={:.3f}".format(curP.distanceTo(curNear)))
                                    print("curNearDirect is {}, but nearAngleScaleRatio is big={}, exist nearAngleScaleRatio={}".format(DIRECTION_4_INFO[minAngleIndex], nearAngleScaleRatio,  curP4Direct_candi[minAngleIndex][4]))
                                continue
                        
                        if(doDebug2):
                            print("nearPInfo:" + curNear.getInfoSnap2() + ",dist={:.3f}".format(curP.distanceTo(curNear)))
                        curP4Direct_candi[minAngleIndex] = [curNear, curNearDirect, near4Direct[minAngleIndex], nearScale, nearAngleScaleRatio]
                    # time2_computeNearCandi += (time.perf_counter() - start_time2)*1000
                    
                    # start_time3 = time.perf_counter()
                    #处理展开点：完全建立链接（正向）；依次建立链接（反向）；依次加入队列
                    # 1)完全建立链接（正向）
                    if(doDebug2):
                        print("confirm curP direction candidate point : ".encode('utf-8'))
                    nearValidConnect = [False]*4    #标识是否有效地建立了链接！
                    for ndx in range(4):
                        if(not curP4Direct_candi[ndx]):
                            if(doDebug2):
                                print("direction:{}-{} has no candidate points".format(ndx, DIRECTION_4_INFO[ndx]).encode('utf-8'))
                            continue
                        if(doDebug2):
                            print("confirm candidate point, direction:{}-{} deviation{:.3f},{:.3f},{:.3f}, ".format(ndx, DIRECTION_4_INFO[ndx], curP4Direct_candi[ndx][2], curP4Direct_candi[ndx][3], curP4Direct_candi[ndx][4]).encode('utf-8') + curP4Direct_candi[ndx][0].getInfoSnap2())

                        # 开始链接展开点(正向)
                        if(0 == ndx):#左
                            if(curP.col >= (BORD_COLS - 1)):
                                if(doDebug2):
                                    print("curP reach left bound, skip near left!")
                                continue
                            if(curP.left):
                                if(curP.left != curP4Direct_candi[ndx][0]):
                                    print("WARN!!!!!!!!!curP:{} direction{} connected point already exist,  and it is different from the expansion point!!!!".format(curP.global_area_order, ndx).encode('utf-8'))
                                    print(" "*5 + "exist is " + curP.left.getInfoSnap2())
                                    print(" "*5 + "near  is " + curP4Direct_candi[ndx][0].getInfoSnap2())
                                continue
                            
                            #正式作链接
                            curP.left = curP4Direct_candi[ndx][0]
                            curP.direct_left = curP4Direct_candi[ndx][1]
                            curP.angle_left = curP4Direct_candi[ndx][2]
                            curP.scale_left = curP4Direct_candi[ndx][3]
                            # curP.direct_right = -curP.direct_left #可能会覆盖掉curP自己实际计算方向
                            nearValidConnect[ndx] = True
                 
                        elif(1 == ndx): #右

                            if(curP.col <= 0):
                                if(doDebug2):
                                    print("curP reach right bound, skip near right!")
                                continue
                            if(curP.right):
                                if(curP.right != curP4Direct_candi[ndx][0]):
                                    print("WARN!!!!!!!!!curP:{} direction{} connected point already exist,  and it is different from the expansion point!!!!".format(curP.global_area_order, ndx).encode('utf-8'))
                                    print(" "*5 + "exist is " + curP.right.getInfoSnap2())
                                    print(" "*5 + "near  is " + curP4Direct_candi[ndx][0].getInfoSnap2())
                                continue
                            
                            #正式作链接
                            curP.right = curP4Direct_candi[ndx][0]
                            curP.direct_right = curP4Direct_candi[ndx][1]
                            curP.angle_right = curP4Direct_candi[ndx][2]
                            curP.scale_right = curP4Direct_candi[ndx][3]
                            nearValidConnect[ndx] = True

                        elif(2 == ndx): #上

                            if(curP.row >= (BORD_ROWS - 1)):
                                if(doDebug2):
                                    print("curP reach up bound, skip near up!")
                                continue
                            if(curP.up):
                                if(curP.up != curP4Direct_candi[ndx][0]):
                                    print("WARN!!!!!!!!!curP:{} direction{} connected point already exist,  and it is different from the expansion point!!!!".format(curP.global_area_order, ndx).encode('utf-8'))
                                    print(" "*5 + "exist is " + curP.up.getInfoSnap2())
                                    print(" "*5 + "near  is " + curP4Direct_candi[ndx][0].getInfoSnap2())
                                continue
                            
                            #正式作链接
                            curP.up = curP4Direct_candi[ndx][0]
                            curP.direct_up = curP4Direct_candi[ndx][1]
                            curP.angle_up = curP4Direct_candi[ndx][2]
                            curP.scale_up = curP4Direct_candi[ndx][3]
                            nearValidConnect[ndx] = True

                        elif(3 == ndx): #下

                            if(curP.row <= 0):
                                if(doDebug2):
                                    print("curP reach down bound, skip near down!")
                                continue
                            if(curP.down):
                                if(curP.down != curP4Direct_candi[ndx][0]):
                                    print("WARN!!!!!!!!!curP:{} direction{} connected point already exist,  and it is different from the expansion point!!!!".format(curP.global_area_order, ndx).encode('utf-8'))
                                    print(" "*5 + "exist is " + curP.down.getInfoSnap2())
                                    print(" "*5 + "near  is " + curP4Direct_candi[ndx][0].getInfoSnap2())
                                continue
                            
                            #正式作链接
                            curP.down = curP4Direct_candi[ndx][0]
                            curP.direct_down = curP4Direct_candi[ndx][1]
                            curP.angle_down = curP4Direct_candi[ndx][2]
                            curP.scale_down = curP4Direct_candi[ndx][3]
                            nearValidConnect[ndx] = True

                        else:
                            continue
                    # time3_computeConnectPositive += (time.perf_counter() - start_time3)*1000

                    # start_time4 = time.perf_counter()
                    # 2)依次建立链接（反向）；依次加入队列
                    curPNear4 = [curP.left, curP.right, curP.up, curP.down]
                    for ndx in range(4):
                        if(nearValidConnect[ndx] == False): #标识是否有效地建立了链接！
                            continue
                        curPNear4[ndx].angle_left = curP.angle_left
                        curPNear4[ndx].angle_right = curP.angle_right
                        curPNear4[ndx].angle_up = curP.angle_up
                        curPNear4[ndx].angle_down = curP.angle_down
                        
                        curPNear4[ndx].scale_left = curP.scale_left
                        curPNear4[ndx].scale_right = curP.scale_right
                        curPNear4[ndx].scale_up = curP.scale_up
                        curPNear4[ndx].scale_down = curP.scale_down
                        if(0 == ndx):#左
                            # 反向链接
                            curP.left.col = curP.col + 1
                            curP.left.row = curP.row
                            curP.left.right = curP
                            
                            curP.left.direct_right = -curP.direct_left
                            if(not curP.left.isDirectHasRealValue(curP.left.direct_left)):
                                curP.left.direct_left = curP.direct_left
                            if(not curP.left.isDirectHasRealValue(curP.left.direct_up)):
                                curP.left.direct_up = curP.direct_up
                            if(not curP.left.isDirectHasRealValue(curP.left.direct_down)):
                                curP.left.direct_down = curP.direct_down

                            #加入队列
                            if(curP.left.bActive == False):
                                curP.left.bActive = True
                                activeQ.put(curP.left)
                                if(doDebug[0]):
                                    self.mScaleDrawer.scale_line(imgDebug2_copy, curP.center_image, curP.left.center_image, (0, 0, 255), 10)
                            if(doDebug2):
                                print("build inverse connection : direction:{}-{}".format(ndx, DIRECTION_4_INFO[ndx]).encode('utf-8') + curP4Direct_candi[ndx][0].getInfoSnap2())
                            if(doDebug[0]):
                                self.mScaleDrawer.scale_line(imgDebug2_copy, curP.center_image, curP.left.center_image, (0, 255, 0), 2)
                        elif(1 == ndx):#右
                            # 反向链接
                            curP.right.col = curP.col - 1
                            curP.right.row = curP.row
                            curP.right.left = curP
                            
                            curP.right.direct_left = -curP.direct_right
                            if(not curP.right.isDirectHasRealValue(curP.right.direct_right)):
                                curP.right.direct_right = curP.direct_right
                            if(not curP.right.isDirectHasRealValue(curP.right.direct_up)):
                                curP.right.direct_up = curP.direct_up
                            if(not curP.right.isDirectHasRealValue(curP.right.direct_down)):
                                curP.right.direct_down = curP.direct_down

                            #加入队列
                            if(curP.right.bActive == False):
                                curP.right.bActive = True
                                activeQ.put(curP.right)
                                if(doDebug[0]):
                                    self.mScaleDrawer.scale_line(imgDebug2_copy, curP.center_image, curP.right.center_image, (0, 0, 255), 10)
                            if(doDebug[0]):
                                self.mScaleDrawer.scale_line(imgDebug2_copy, curP.center_image, curP.right.center_image, (255, 255, 0), 2)
                            if(doDebug2):
                                print("build inverse connection : direction:{}-{} ".format(ndx, DIRECTION_4_INFO[ndx]).encode('utf-8') + curP4Direct_candi[ndx][0].getInfoSnap2())
                            
                                
                        elif(2 == ndx):#上

                            # 反向链接
                            curP.up.col = curP.col                            
                            curP.up.row = curP.row + 1
                            curP.up.down = curP
                            
                            curP.up.direct_down = -curP.direct_up
                            if(not curP.up.isDirectHasRealValue(curP.up.direct_up)):
                                curP.up.direct_up = curP.direct_up
                            if(not curP.up.isDirectHasRealValue(curP.up.direct_left)):
                                curP.up.direct_left = curP.direct_left
                            if(not curP.up.isDirectHasRealValue(curP.up.direct_right)):
                                curP.up.direct_right = curP.direct_right
                                
                            #加入队列
                            if(curP.up.bActive == False):
                                curP.up.bActive = True
                                activeQ.put(curP.up)
                                if(doDebug[0]):
                                    self.mScaleDrawer.scale_line(imgDebug2_copy, curP.center_image, curP.up.center_image, (0, 0, 255), 10)
                            if(doDebug[0]):
                                self.mScaleDrawer.scale_line(imgDebug2_copy, curP.center_image, curP.up.center_image, (0, 0, 0), 2)
                            if(doDebug2):
                                print("build inverse connection : direction:{}-{} ".format(ndx, DIRECTION_4_INFO[ndx]).encode('utf-8') + curP4Direct_candi[ndx][0].getInfoSnap2())
                                
                        elif(3 == ndx):#下

                            # 反向链接
                            curP.down.col = curP.col
                            curP.down.row = curP.row - 1
                            curP.down.up = curP
                            
                            curP.down.direct_up = -curP.direct_down
                            if(not curP.down.isDirectHasRealValue(curP.down.direct_down)):
                                curP.down.direct_down = curP.direct_down
                            if(not curP.down.isDirectHasRealValue(curP.down.direct_left)):
                                curP.down.direct_left = curP.direct_left
                            if(not curP.down.isDirectHasRealValue(curP.down.direct_right)):
                                curP.down.direct_right = curP.direct_right

                            #加入队列
                            if(curP.down.bActive == False):
                                curP.down.bActive = True
                                activeQ.put(curP.down)
                                if(doDebug[0]):
                                    self.mScaleDrawer.scale_line(imgDebug2_copy, curP.center_image, curP.down.center_image, (0, 0, 255), 10)
                            if(doDebug[0]):
                                self.mScaleDrawer.scale_line(imgDebug2_copy, curP.center_image, curP.down.center_image, (255, 0, 0), 2)
                            if(doDebug2):
                                print("build inverse connection : direction:{}-{} ".format(ndx, DIRECTION_4_INFO[ndx]).encode('utf-8') + curP4Direct_candi[ndx][0].getInfoSnap2())

                        else:
                            continue

                    # for ndx in range(4):
                    #     if(nearValidConnect[ndx] == False): #标识是否有效地建立了链接！
                    #         continue
                    #     self._connect_logic_points(curPNear4[ndx], [doDebug[0], imgDebug2_copy if(doDebug[0]) else None])

                    # time4_computeConnectNegtive += (time.perf_counter() - start_time4)*1000

                    if(doDebug[0] == True and tmpCount % 100 == 0):
                        cv.namedWindow("Connections For {}".format(singleRingBoard.type[1]), cv.WINDOW_NORMAL)
                        cv.imshow("Connections For {}".format(singleRingBoard.type[1]), imgDebug2_copy)
                        cv.waitKey(2)

        if(doDebug[0] == True):#最后显示完整的链接图
            cv.namedWindow("Connections For {}".format(singleRingBoard.type[1]), cv.WINDOW_NORMAL)
            cv.imshow("Connections For {}".format(singleRingBoard.type[1]), imgDebug2_copy)
            cv.waitKey(2)

        
        print("single board connections build finished :{}".format(singleRingBoard.type[1]).encode('utf-8'))
        print("cycles num tmpCount={},  tmpCount2={}".format(tmpCount, tmpCount2).encode('utf-8'))
        # print("单板链接构建耗时 : {} ms , time0_connect_logic={:.3f} ms,time1_getNearN={:.3f} ms,time2_computeNearCandi={:.3f} ms,time2_1_computeNearCandi_Angle={:.3f} ms,time3_computeConnectPositive={:.3f} ms,time4_computeConnectNegtive={:.3f} ms,{} ".format((time.perf_counter() - start_time)*1000, time0_connect_logic, time1_getNearN, time2_computeNearCandi,time2_1_computeNearCandi_Angle, time3_computeConnectPositive, time4_computeConnectNegtive, ".. .."*20))
        # print("单板链接构建耗时 : {} ms , time0_connect_logic={:.3f} ms,time1_getNearN={:.3f} ms,time2_computeNearCandi={:.3f} ms,time2_1_computeNearCandi_Angle={:.3f} ms,{} ".format((time.perf_counter() - start_time)*1000, time0_connect_logic, time1_getNearN, time2_computeNearCandi,time2_1_computeNearCandi_Angle, ".. .."*20))
        print("single board connections build cost : {} ms , time1_getNearN={:.3f} ms, time2_1_computeNearCandi_Angle={:.3f} is much big ms,{} ".format((time.perf_counter() - start_time)*1000, time1_getNearN, time2_1_computeNearCandi_Angle, ".. .."*20).encode('utf-8'))

        start_time = time.perf_counter()
        singleRingBoard.buildGridAfterFullConnect()

        if(singleRingBoard.unorderedCells is None):
            validCellSize = -1
        else:
            validCellSize = singleRingBoard.unorderedCells.size
        print("single board grid build finished:{},valid cell size={}".format(singleRingBoard.type[1], validCellSize).encode('utf-8'))
        
        # print("单板grid构建耗时 : {} ms {}".format((time.perf_counter() - start_time)*1000, ".. .."*20))

        if(doDebug[0]):

            imgDebug2_copy2 = imgDebug2.copy()
            for cId in range(BORD_COLS):
                for rId in range(BORD_ROWS):
                    curCell = singleRingBoard.grid[rId][cId]
                    if(curCell == None):
                        continue
                    cellInfo = "cr_{}_{}".format(curCell.col, curCell.row)
                    self.mScaleDrawer.scale_drawContours(imgDebug2_copy2, [curCell.contour], -1, (0, 0, 255), 15)               
                    self.mScaleDrawer.scale_putText(imgDebug2_copy2, cellInfo, (curCell.center_image[0], curCell.center_image[1] - 5), cv.FONT_HERSHEY_SIMPLEX,0.5,color=(0, 255, 0),thickness=1)

            cv.namedWindow("grid For {}".format(singleRingBoard.type[1]), cv.WINDOW_NORMAL)
            cv.imshow("grid For {}".format(singleRingBoard.type[1]), imgDebug2_copy2)
            # cv.waitKey(0)


    '''
    description: 去找最近的n个点，按距离排序返回
    param {*} self
    param {*} curCircle
    param {*} oriCircles
    return {*}
    '''    
    def getNearN(self, curCircle, oriCircles, minN = -1):
        size = len(oriCircles)
        # print("oriCircles type=",type(oriCircles))
        if(minN < 0 or minN > size):
            minN = size
        return heapq.nlargest(minN, oriCircles, key=lambda x: (curCircle.distanceTo(x)*-1.0))
        # # 创建一个空的最小堆
        # heap = []
        # for circleOne in oriCircles:
        #     if(len(heap) < minN):
        #         heapq.heappush(heap, [circleOne, curCircle.distanceTo(circleOne)], key=lambda x: x[1])
        #     else:

    '''
    description: 在oriCircles范围内, 每个点找最近的点
        对单个点,遍历求所有点与它的距离,距离在max{30, 半径*10}内的加入自己check列表
        对单个点,check列表做排序
    param {*} self
    return {*} 
    '''    
    def sortBordPointByDistance(self, oriCircles):

        distThreAbs = 60.0
        distThreRela = 10.0

        distTmp = -1

        distThreRela1 = -1
        distThreRela2 = -1
        sizeCircle = len(oriCircles)
        
        start_time = time.perf_counter()

        distTimeAll = 0
        distTimeAll2 = 0

        #把所有点放进Np 二维矩阵
        tmpPoints = np.zeros((sizeCircle,2), dtype=float)

        #把所有点半径放进 np数组
        tmpRadius = np.zeros((sizeCircle,), dtype=float)

        #遍历所有点,做些预操作
        for idx in range(sizeCircle):
            tmpPoints[idx] = oriCircles[idx].center_image
            tmpRadius[idx] = oriCircles[idx].r
            # oriCircles[idx].distance_at_image = [(None, 0)]*self.distance_at_image_N_MAX
            
        
        tmpDistances = cdist(tmpPoints, tmpPoints)
        print(f"tmpPoints shpe={tmpPoints.shape}, tmpDistances shape={tmpDistances.shape}")
        # print(f"tmpPoints top=\n", tmpPoints[0:3])
        # print(f"tmpDistances top=\n", tmpDistances[0:3][0:3])

        tmpRadius *= distThreRela
        for idx in range(sizeCircle):
            p1 = oriCircles[idx]
            # distThreRela1 = p1.r * distThreRela
            for jdx in range(idx + 1, sizeCircle):   
                p2 = oriCircles[jdx]
                # distThreRela2 = p2.r * distThreRela

                distTmp = tmpDistances[idx][jdx]

                # start_time2 = time.perf_counter()
                if(distTmp <= tmpRadius[idx] or distTmp <= distThreAbs):
                    p1.distance_at_image.append((p2, distTmp))
                if(distTmp <= tmpRadius[jdx] or distTmp <= distThreAbs):
                    p2.distance_at_image.append((p1, distTmp))
                # distTimeAll2 += (time.perf_counter() - start_time2)*1000

        print("sortBordPointByDistance filtering cost  : {} ms, distance calculation cost {}, distTimeAll2={}  {}".format((time.perf_counter() - start_time)*1000, distTimeAll, distTimeAll2, "+"*10 ).encode('utf-8'))

        start_time = time.perf_counter()
        for idx in range(sizeCircle):
            p1 = oriCircles[idx]
            # if(len(p1.distance_at_image) < 5):
            #     print(f"sortBordPointByDistance p 点 临域候选点数不够:{len(p1.distance_at_image)}")
            p1.distance_at_image = sorted(p1.distance_at_image, key=lambda x : x[1], reverse=False)
        print("sortBordPointByDistance sorting cost : {} ms {}".format((time.perf_counter() - start_time)*1000, "+"*10).encode('utf-8'))


    '''
    description: 在oriCircles范围内, 每个点找最近的点
        对单个点,遍历求所有点与它的距离,距离在max{30, 半径*10}内的加入自己check列表
        对单个点,check列表做排序
    param {*} self
    return {*} 
    '''    
    def sortBordPointByDistance2(self, oriCircles):

        distThreAbs = 60.0
        distThreRela = 10.0

        distTmp = -1

        distThreRela1 = -1
        distThreRela2 = -1
        sizeCircle = len(oriCircles)
        
        start_time = time.perf_counter()

        start_timexx = time.perf_counter()
        oriCirclesNp = np.array(oriCircles)
        print("sortBordPointByDistance oriCircles translate to Np array cost  : {} ms ".format((time.perf_counter() - start_timexx)*1000).encode('utf-8'))

        distTimeAll = 0
        distTimeAll2 = 0

        #把所有点放进Np 二维矩阵
        tmpPoints = np.zeros((sizeCircle,2), dtype=float)

        #把所有点半径放进 np数组
        tmpRadius = np.zeros((sizeCircle,), dtype=float)

        #遍历所有点,做些预操作
        for idx in range(sizeCircle):
            tmpPoints[idx] = oriCircles[idx].center_image
            tmpRadius[idx] = oriCircles[idx].r
            # oriCircles[idx].distance_at_image = [(None, 0)]*self.distance_at_image_N_MAX

        
        tmpDistances = cdist(tmpPoints, tmpPoints)
        print(f"tmpPoints shpe={tmpPoints.shape}, tmpDistances shape={tmpDistances.shape}")
        # print(f"tmpPoints top=\n", tmpPoints[0:3])
        # print(f"tmpDistances top=\n", tmpDistances[0:3][0:3])

        start_time2 = time.perf_counter()

        tmpRadius *= distThreRela
        
        for idx in range(sizeCircle):
            p1 = oriCircles[idx]
            # distThreRela1 = p1.r * distThreRela
            tmpRow = tmpDistances[idx,:]    #单行取出来整体操作

            tmpRowFilter1 = np.logical_or(tmpRow <= distThreAbs, tmpRow <= tmpRadius[idx])  #先按距离筛选范围

            p1.distance_at_image = oriCirclesNp[tmpRowFilter1]                              #范围内的点
            p1.distance_at_image_dis = tmpRow[tmpRowFilter1]                                #范围内的点对应的距离
        
        distTimeAll2 += (time.perf_counter() - start_time2)*1000

        print("sortBordPointByDistance filtering cost  : {} ms, distance calculation cost {}, distTimeAll2={}  {}".format((time.perf_counter() - start_time)*1000, distTimeAll, distTimeAll2, "+"*10 ).encode('utf-8'))

        start_time = time.perf_counter()
        for idx in range(sizeCircle):
            p1 = oriCircles[idx]
            sorted_indices = np.argsort(p1.distance_at_image_dis)                           #直接按距离排序,得到排序后的index
            p1.distance_at_image = p1.distance_at_image[sorted_indices]
            p1.distance_at_image_dis = p1.distance_at_image_dis[sorted_indices]

            #验证正确否?
            # if(idx < 10):
            #     indexTmpxx = []
            #     for kdx in p1.distance_at_image:
            #         indexTmpxx.append(kdx.global_area_order)
            #     print(f"idx={p1.global_area_order}, nearidx={indexTmpxx[0:min(len(indexTmpxx), 5)]}, neardis={p1.distance_at_image_dis[0:min(len(sorted_indices), 5)]}")
        print("sortBordPointByDistance sorting cost : {} ms {}".format((time.perf_counter() - start_time)*1000, "+"*10).encode('utf-8'))

    # def getNearN(self, curCircle, oriCircles, minN = -1):
    #     size = len(oriCircles)
    #     # print("oriCircles type=",type(oriCircles))
    #     if(minN < 0 or minN > size):
    #         minN = size

    #     nearest_objects = []
    #     for obj in oriCircles:
    #         heapq.heappush(nearest_objects, WrapperDist(curCircle.distanceTo(obj), obj))
    #         if len(nearest_objects) > minN:
    #             heapq.heappop(nearest_objects)            
    #     nearest_objects = [wrapperM.obj for wrapperM in nearest_objects]
    #     return nearest_objects

    # def getNearN(self, curCircle, oriCircles, minN = -1):
    #     size = len(oriCircles)
    #     # print("oriCircles type=",type(oriCircles))
    #     if(minN < 0 or minN > size):
    #         minN = size
        
    #     nearest_objects = sorted(oriCircles, key=lambda x: curCircle.distanceTo(x))
    #     return nearest_objects[:minN]

    def _connect_logic_points(self, p, show_connections):

        #左-上点为空，但是上-左点有链接，直接补上左-上点！
        if p and p.left and not p.left.up and p.up and p.up.left: 
            p.left.up = p.up.left
            p.left.up.down = p.left

            p.left.up.direct_left = p.left.direct_left
            p.left.up.direct_right = p.left.direct_right
            # assert cv.norm(p.left.direct_right) < 50
            p.left.up.direct_up = p.left.up.center_image - p.left.center_image
            p.left.up.direct_down = -p.left.up.direct_up

            p.left.up.angle_left = p.left.angle_left
            p.left.up.angle_right = p.left.angle_right
            p.left.up.angle_up = p.left.angle_up
            p.left.up.angle_down = p.left.angle_down

            p.left.up.scale_left = p.left.scale_left
            p.left.up.scale_right = p.left.scale_right
            p.left.up.scale_up = p.left.scale_up
            p.left.up.scale_down = p.left.scale_down

            if(show_connections[0]):
                self.mScaleDrawer.scale_line(show_connections[1], p.left.center_image, p.left.up.center_image, (0, 255, 255), 2)
                # cv.line(show_connections[1], p.left.center_image, p.left.up.center_image,
                #         (0, 0, 255), 2, cv.LINE_AA)
                # cv.namedWindow("add connect", cv.WINDOW_NORMAL)
                # cv.imshow("add connect", show_connections[1])
                # print(p.global_area_order, "addition add left up", p.left.up.global_area_order)

        if p and p.right and not p.right.up and p.up and p.up.right:
            p.right.up = p.up.right
            p.right.up.down = p.right

            p.right.up.direct_left = p.right.direct_left
            p.right.up.direct_right = p.right.direct_right
            # assert cv.norm(p.right.direct_right) < 50
            p.right.up.direct_up = p.right.up.center_image - p.right.center_image
            p.right.up.direct_down = -p.right.up.direct_up

            p.right.up.angle_left = p.right.angle_left
            p.right.up.angle_right = p.right.angle_right
            p.right.up.angle_up = p.right.angle_up
            p.right.up.angle_down = p.right.angle_down

            p.right.up.scale_left = p.right.scale_left
            p.right.up.scale_right = p.right.scale_right
            p.right.up.scale_up = p.right.scale_up
            p.right.up.scale_down = p.right.scale_down

            if(show_connections[0]):
                self.mScaleDrawer.scale_line(show_connections[1], p.right.center_image, p.right.up.center_image, (0, 255, 255), 2)
                # cv.line(show_connections[1], p.right.center_image, p.right.up.center_image,
                #         (0, 0, 255), 2, cv.LINE_AA)
                # cv.namedWindow("add connect", cv.WINDOW_NORMAL)
                # # cv.resizeWindow("add connect", 640, 480)
                # cv.imshow("add connect", show_connections[1])
                # print(p.global_area_order, "addition add right up", p.right.up.global_area_order)

        if p and p.left and not p.left.down and p.down and p.down.left:
            p.left.down = p.down.left
            p.left.down.up = p.left

            p.left.down.direct_left = p.left.direct_left
            p.left.down.direct_right = p.left.direct_right

            p.left.down.direct_down = p.left.down.center_image - p.left.center_image
            p.left.down.direct_up = -p.left.down.direct_down

            p.left.down.angle_left = p.left.angle_left
            p.left.down.angle_right = p.left.angle_right
            p.left.down.angle_up = p.left.angle_up
            p.left.down.angle_down = p.left.angle_down

            p.left.down.scale_left = p.left.scale_left
            p.left.down.scale_right = p.left.scale_right
            p.left.down.scale_up = p.left.scale_up
            p.left.down.scale_down = p.left.scale_down

            if(show_connections[0]):
                self.mScaleDrawer.scale_line(show_connections[1], p.left.center_image, p.left.down.center_image, (0, 255, 255), 2)
                # cv.line(show_connections[1], p.left.center_image, p.left.down.center_image,
                #         (0, 0, 255), 2, cv.LINE_AA)
                # cv.namedWindow("add connect", cv.WINDOW_NORMAL)
                # # cv.resizeWindow("add connect", 640, 480)
                # cv.imshow("add connect", show_connections[1])
                # print(p.global_area_order, "addition add left down", p.left.down.global_area_order)



        if p and p.right and not p.right.down and p.down and p.down.right:
            p.right.down = p.down.right
            p.right.down.up = p.right

            p.right.down.direct_left = p.right.direct_left
            p.right.down.direct_right = p.right.direct_right
            p.right.down.direct_down = p.right.down.center_image - p.right.center_image
            p.right.down.direct_up = -p.right.down.direct_down

            p.right.down.angle_left = p.right.angle_left
            p.right.down.angle_right = p.right.angle_right
            p.right.down.angle_up = p.right.angle_up
            p.right.down.angle_down = p.right.angle_down

            p.right.down.scale_left = p.right.scale_left
            p.right.down.scale_right = p.right.scale_right
            p.right.down.scale_up = p.right.scale_up
            p.right.down.scale_down = p.right.scale_down

            if(show_connections[0]):
                self.mScaleDrawer.scale_line(show_connections[1], p.right.center_image, p.right.down.center_image, (0, 255, 255), 2)
                # cv.line(show_connections[1], p.right.center_image, p.right.down.center_image,
                #         (0, 0, 255), 2, cv.LINE_AA)
                # cv.namedWindow("add connect", cv.WINDOW_NORMAL)
                # # cv.resizeWindow("add connect", 640, 480)
                # cv.imshow("add connect", show_connections[1])
                # print(p.global_area_order, "addition add right down", p.right.down.global_area_order)

        if p and p.down and not p.down.left and p.left and p.left.down:
            p.down.left = p.left.down
            p.down.left.right = p.down

            p.down.left.direct_left = p.down.left.center_image - p.down.center_image
            p.down.left.direct_right = -p.down.left.direct_left
            # assert cv.norm(p.down.left.direct_right) < 50
            p.down.left.direct_up = p.down.direct_up
            p.down.left.direct_down = p.down.direct_down

            p.down.left.angle_left = p.down.angle_left
            p.down.left.angle_right = p.down.angle_right
            p.down.left.angle_up = p.down.angle_up
            p.down.left.angle_down = p.down.angle_down

            p.down.left.scale_left = p.down.scale_left
            p.down.left.scale_right = p.down.scale_right
            p.down.left.scale_up = p.down.scale_up
            p.down.left.scale_down = p.down.scale_down

            if(show_connections[0]):
                self.mScaleDrawer.scale_line(show_connections[1], p.down.center_image, p.down.left.center_image, (0, 255, 255), 2)
                # cv.line(show_connections[1], p.down.center_image, p.down.left.center_image,
                #         (0, 0, 255), 2, cv.LINE_AA)
                # cv.namedWindow("add connect", cv.WINDOW_NORMAL)
                # # cv.resizeWindow("add connect", 640, 480)
                # cv.imshow("add connect", show_connections[1])
                # print("addition add down left", p.down.left.global_area_order)

        if p and p.down and not p.down.right and p.right and p.right.down:
            p.down.right = p.right.down
            p.down.right.left = p.down

            p.down.right.direct_right = p.down.right.center_image - p.down.center_image
            # assert cv.norm(p.down.right.direct_right) < 50
            p.down.right.direct_left = -p.down.right.direct_right
            p.down.right.direct_up = p.down.direct_up
            p.down.right.direct_down = p.down.direct_down

            p.down.right.angle_left = p.down.angle_left
            p.down.right.angle_right = p.down.angle_right
            p.down.right.angle_up = p.down.angle_up
            p.down.right.angle_down = p.down.angle_down

            p.down.right.scale_left = p.down.scale_left
            p.down.right.scale_right = p.down.scale_right
            p.down.right.scale_up = p.down.scale_up
            p.down.right.scale_down = p.down.scale_down

            if(show_connections[0]):
                self.mScaleDrawer.scale_line(show_connections[1], p.down.center_image, p.down.right.center_image, (0, 255, 255), 2)
                # cv.line(show_connections[1], p.down.center_image, p.down.right.center_image,
                #         (0, 0, 255), 2, cv.LINE_AA)
                # cv.namedWindow("add connect", cv.WINDOW_NORMAL)
                # # cv.resizeWindow("add connect", 640, 480)
                # cv.imshow("add connect", show_connections[1])
                # print(p.global_area_order, "addition add down right", p.down.right.global_area_order)



        if p and p.up and not p.up.left and p.left and p.left.up:
            p.up.left = p.left.up
            p.up.left.right = p.up
            p.up.left.angle_left = p.up.angle_left

            p.up.left.direct_left = p.up.left.center_image - p.up.center_image
            p.up.left.direct_right = -p.up.left.direct_left
            # if np.linalg.norm(p.up.left.direct_right) > 50:
            #     cv.waitKey(1)

            p.up.left.direct_up = p.up.direct_up
            p.up.left.direct_down = p.up.direct_down

            p.up.left.angle_left = p.up.angle_left
            p.up.left.angle_right = p.up.angle_right
            p.up.left.angle_up = p.up.angle_up
            p.up.left.angle_down = p.up.angle_down

            p.up.left.scale_left = p.up.scale_left
            p.up.left.scale_right = p.up.scale_right
            p.up.left.scale_up = p.up.scale_up
            p.up.left.scale_down = p.up.scale_down

            if(show_connections[0]):
                self.mScaleDrawer.scale_line(show_connections[1], p.up.center_image, p.up.left.center_image, (0, 255, 255), 2)
                # cv.line(show_connections[1], p.up.center_image, p.up.left.center_image,
                #         (0, 0, 255), 2, cv.LINE_AA)
                # cv.namedWindow("add connect", cv.WINDOW_NORMAL)
                # # cv.resizeWindow("add connect", 640, 480)
                # cv.imshow("add connect", show_connections[1])
                # print(p.global_area_order, "addition add up left", p.up.left.global_area_order)

        if p and p.up and not p.up.right and p.right and p.right.up:
            p.up.right = p.right.up
            p.up.right.left = p.up

            p.up.right.direct_right = p.up.right.center_image - p.up.center_image
            # assert np.linalg.norm(p.up.right.direct_right) < 50
            p.up.right.direct_left = -p.up.right.direct_right
            p.up.right.direct_up = p.up.direct_up
            p.up.right.direct_down = p.up.direct_down

            p.up.right.angle_left = p.up.angle_left
            p.up.right.angle_right = p.up.angle_right
            p.up.right.angle_up = p.up.angle_up
            p.up.right.angle_down = p.up.angle_down

            p.up.right.scale_left = p.up.scale_left
            p.up.right.scale_right = p.up.scale_right
            p.up.right.scale_up = p.up.scale_up
            p.up.right.scale_down = p.up.scale_down

            if(show_connections[0]):
                self.mScaleDrawer.scale_line(show_connections[1], p.up.center_image, p.up.right.center_image, (0, 255, 255), 2)                
                # cv.line(show_connections[1], p.up.center_image, p.up.right.center_image,
                #         (0, 0, 255), 2, cv.LINE_AA)
                # cv.namedWindow("add connect", cv.WINDOW_NORMAL)
                # # cv.resizeWindow("add connect", 640, 480)
                # cv.imshow("add connect", show_connections[1])
                # print(p.global_area_order, "addition add up right", p.up.global_area_order)

        if p and not p.up and p.left and p.left.up and p.left.up.right:
            p.up = p.left.up.right
            p.up.down = p

            p.up.direct_left = p.direct_left
            p.up.direct_right = p.direct_right
            p.up.direct_up = p.up.center_image - p.center_image
            p.up.direct_down = -p.up.direct_up

            p.up.angle_left = p.angle_left
            p.up.angle_right = p.angle_right
            p.up.angle_up = p.angle_up
            p.up.angle_down = p.angle_down

            p.up.scale_left = p.scale_left
            p.up.scale_right = p.scale_right
            p.up.scale_up = p.scale_up
            p.up.scale_down = p.scale_down

            if(show_connections[0]):
                self.mScaleDrawer.scale_line(show_connections[1], p.up.center_image, p.center_image, (0, 255, 255), 2)                
                # cv.line(show_connections[1], p.up.center_image, p.center_image,
                #         (0, 0, 255), 2, cv.LINE_AA)
                # cv.namedWindow("add connect", cv.WINDOW_NORMAL)
                # # cv.resizeWindow("add connect", 640, 480)
                # cv.imshow("add connect", show_connections[1])
                # print(p.global_area_order, "addition add up", p.up.global_area_order)



        if p and not p.up and p.right and p.right.up and p.right.up.left:
            p.up = p.right.up.left
            p.up.down = p

            p.up.direct_left = p.direct_left
            p.up.direct_right = p.direct_right
            p.up.direct_up = p.up.center_image - p.center_image
            p.up.direct_down = -p.up.direct_up

            p.up.angle_left = p.angle_left
            p.up.angle_right = p.angle_right
            p.up.angle_up = p.angle_up
            p.up.angle_down = p.angle_down

            p.up.scale_left = p.scale_left
            p.up.scale_right = p.scale_right
            p.up.scale_up = p.scale_up
            p.up.scale_down = p.scale_down

            if(show_connections[0]):
                self.mScaleDrawer.scale_line(show_connections[1], p.up.center_image, p.center_image, (0, 255, 255), 2)                    
                # cv.line(show_connections[1], p.up.center_image, p.center_image,
                #         (0, 0, 255), 2, cv.LINE_AA)
                # cv.namedWindow("add connect", cv.WINDOW_NORMAL)
                # # cv.resizeWindow("add connect", 640, 480)
                # cv.imshow("add connect", show_connections[1])
                # print(p.global_area_order, "addition add up ", p.up.global_area_order)

        if p and not p.down and p.right and p.right.down and p.right.down.left:
            p.down = p.right.down.left
            p.down.up = p

            p.down.direct_left = p.direct_left
            p.down.direct_right = p.direct_right
            p.down.direct_down = p.down.center_image - p.center_image
            p.down.direct_up = -p.down.direct_down

            p.down.angle_left = p.angle_left
            p.down.angle_right = p.angle_right
            p.down.angle_up = p.angle_up
            p.down.angle_down = p.angle_down

            p.down.scale_left = p.scale_left
            p.down.scale_right = p.scale_right
            p.down.scale_up = p.scale_up
            p.down.scale_down = p.scale_down

            if(show_connections[0]):
                self.mScaleDrawer.scale_line(show_connections[1], p.down.center_image, p.center_image, (0, 255, 255), 2)                    
                # cv.line(show_connections[1], p.down.center_image, p.center_image,
                #         (0, 0, 255), 2, cv.LINE_AA)
                # cv.namedWindow("add connect", cv.WINDOW_NORMAL)
                # # cv.resizeWindow("add connect", 640, 480)
                # cv.imshow("add connect", show_connections[1])
                # print(p.global_area_order, "addition add down ", p.down.global_area_order)

        if p and not p.down and p.left and p.left.down and p.left.down.right:
            p.down = p.left.down.right
            p.down.up = p

            p.down.direct_left = p.direct_left
            p.down.direct_right = p.direct_right
            p.down.direct_down = p.down.center_image - p.center_image
            p.down.direct_up = -p.down.direct_down

            p.down.angle_left = p.angle_left
            p.down.angle_right = p.angle_right
            p.down.angle_up = p.angle_up
            p.down.angle_down = p.angle_down

            p.down.scale_left = p.scale_left
            p.down.scale_right = p.scale_right
            p.down.scale_up = p.scale_up
            p.down.scale_down = p.scale_down

            if(show_connections[0]):
                self.mScaleDrawer.scale_line(show_connections[1], p.down.center_image, p.center_image, (0, 255, 255), 2)                    
                # cv.line(show_connections[1], p.down.center_image, p.center_image,
                #         (0, 0, 255), 2, cv.LINE_AA)
                # cv.namedWindow("add connect", cv.WINDOW_NORMAL)
                # # cv.resizeWindow("add connect", 640, 480)
                # cv.imshow("add connect", show_connections[1])
                # print(p.global_area_order, "addition add down ", p.down.global_area_order)

        if p and not p.left and p.up and p.up.left and p.up.left.down:
            p.left = p.up.left.down
            p.left.right = p
            p.left.angle_left = p.up.left.down.angle_left

            p.left.direct_left = p.left.center_image - p.center_image
            p.left.direct_right = -p.left.direct_left
            # assert np.linalg.norm(p.left.direct_right) < 50
            p.left.direct_up = p.direct_up
            p.left.direct_down = p.direct_down

            p.left.angle_left = p.angle_left
            p.left.angle_right = p.angle_right
            p.left.angle_up = p.angle_up
            p.left.angle_down = p.angle_down

            p.left.scale_left = p.scale_left
            p.left.scale_right = p.scale_right
            p.left.scale_up = p.scale_up
            p.left.scale_down = p.scale_down

            if(show_connections[0]):
                self.mScaleDrawer.scale_line(show_connections[1], p.left.center_image, p.center_image, (0, 255, 255), 2)                    
                # cv.line(show_connections[1], p.left.center_image, p.center_image,
                #         (0, 0, 255), 2, cv.LINE_AA)
                # cv.namedWindow("add connect", cv.WINDOW_NORMAL)
                # # cv.resizeWindow("add connect", 640, 480)
                # cv.imshow("add connect", show_connections[1])
                # print(p.global_area_order, "addition add left ", p.left.global_area_order)

        if p and not p.left and p.down and p.down.left and p.down.left.up:
            p.left = p.down.left.up
            p.left.right = p
            p.left.angle_left = p.down.left.up.angle_left

            p.left.direct_left = p.left.center_image - p.center_image
            p.left.direct_right = -p.left.direct_left
            # assert np.linalg.norm(p.left.direct_right) < 50
            p.left.direct_up = p.direct_up
            p.left.direct_down = p.direct_down

            p.left.angle_left = p.angle_left
            p.left.angle_right = p.angle_right
            p.left.angle_up = p.angle_up
            p.left.angle_down = p.angle_down

            p.left.scale_left = p.scale_left
            p.left.scale_right = p.scale_right
            p.left.scale_up = p.scale_up
            p.left.scale_down = p.scale_down

            if(show_connections[0]):
                self.mScaleDrawer.scale_line(show_connections[1], p.left.center_image, p.center_image, (0, 255, 255), 2)                    
                # cv.line(show_connections[1], p.left.center_image, p.center_image,
                #         (0, 0, 255), 2, cv.LINE_AA)
                # cv.namedWindow("add connect", cv.WINDOW_NORMAL)
                # # cv.resizeWindow("add connect", 640, 480)
                # cv.imshow("add connect", show_connections[1])
                # print(p.global_area_order, "addition add left ", p.left.global_area_order)

        if p and not p.right and p.down and p.down.right and p.down.right.up:
            p.right = p.down.right.up
            p.right.left = p

            p.right.direct_right = p.right.center_image - p.center_image
            p.right.direct_left = -p.right.direct_right
            # assert np.linalg.norm(p.right.direct_right) < 50
            p.right.direct_up = p.direct_up
            p.right.direct_down = p.direct_down

            p.right.angle_left = p.angle_left
            p.right.angle_right = p.angle_right
            p.right.angle_up = p.angle_up
            p.right.angle_down = p.angle_down

            p.right.scale_left = p.scale_left
            p.right.scale_right = p.scale_right
            p.right.scale_up = p.scale_up
            p.right.scale_down = p.scale_down

            if(show_connections[0]):
                self.mScaleDrawer.scale_line(show_connections[1], p.right.center_image, p.center_image, (0, 255, 255), 2)                    
                # cv.line(show_connections[1], p.right.center_image, p.center_image,
                #         (0, 0, 255), 2, cv.LINE_AA)
                # cv.namedWindow("add connect", cv.WINDOW_NORMAL)
                # # cv.resizeWindow("add connect", 640, 480)
                # cv.imshow("add connect", show_connections[1])
                # print(p.global_area_order, "addition add right ", p.right.global_area_order)

        if p and not p.right and p.up and p.up.right and p.up.right.down:
            p.right = p.up.right.down
            p.right.left = p

            p.right.direct_right = p.right.center_image - p.center_image
            # assert np.linalg.norm(p.right.direct_right) < 50
            p.right.direct_left = -p.right.direct_right
            p.right.direct_up = p.direct_up
            p.right.direct_down = p.direct_down

            p.right.angle_left = p.angle_left
            p.right.angle_right = p.angle_right
            p.right.angle_up = p.angle_up
            p.right.angle_down = p.angle_down

            p.right.scale_left = p.scale_left
            p.right.scale_right = p.scale_right
            p.right.scale_up = p.scale_up
            p.right.scale_down = p.scale_down

            if(show_connections[0]):
                self.mScaleDrawer.scale_line(show_connections[1], p.right.center_image, p.center_image, (0, 255, 255), 2)                    
                # cv.line(show_connections[1], p.right.center_image, p.center_image,
                #         (0, 0, 255), 2, cv.LINE_AA)
                # cv.namedWindow("add connect", cv.WINDOW_NORMAL)
                # # cv.resizeWindow("add connect", 640, 480)
                # cv.imshow("add connect", show_connections[1])
                # print(p.global_area_order, "addition add right ", p.right.global_area_order)


    def sortcircleByDistance(self, curCircle, candiCircles):
        sortedCircles = sorted(candiCircles, key= lambda x : ((x.center_image[0] - curCircle.center_image[0])**2 + (x.center_image[1] - curCircle.center_image[1])**2))
        
        return [ [curCircle.distanceTo(sCircle) , sCircle] for sCircle in sortedCircles ]

    def computeCircleFromContour(self, contour):
        perimeter = cv.arcLength(contour, False)     #计算轮廓周长，第二个参数标记是否是闭合轮廓
        if(perimeter <= 0):
            return (False, [perimeter, -1, -1, -1, -1])
        area = cv.contourArea(contour)
        alpha = 4*np.pi*area/(perimeter**2)
        # 计算轮廓对应的几何中心
        moments = cv.moments(contour)
        if(moments['m00'] <= 0 ):
            return (False, [perimeter, area, alpha, -1, -1])
        cx = moments['m10'] / moments['m00']
        cy = moments['m01'] / moments['m00']

        return (True, [perimeter, area, alpha, cx, cy])
    
    def computeRingRatio(self, ctId, contour, cx, cy, imgGray, sampleContourPointMax = 10):

        # contour是 np数组， N*1*2

        imgH, imgW = imgGray.shape

        # start_time = time.perf_counter()

        sampleIndex = []
        size = contour.shape[0]
        if(size <= sampleContourPointMax):
            sampleIndex = range(size)
        else:
            step = size / sampleContourPointMax
            sampleIndex = [ math.floor(idx*step) for idx in range(sampleContourPointMax) ]
        sizeSampleIndex = len(sampleIndex)
        # print("contour=", contour, ",contour type=", type(contour), ",sizeSampleIndex=", sizeSampleIndex)

        # 最多采样10个轮廓点，计算轮廓点和轮廓临近内点的灰度值均值：i1
        contourMeanGray = 0.0
        validContourSize = 0
        curPoint2Tmp = np.empty((1,2), dtype=int)
        for cIdx in range(sizeSampleIndex):
            if(cIdx < 0 or cIdx >= sizeSampleIndex):
                continue
            curPoint1 = contour[sampleIndex[cIdx]]

            contourMeanGray += imgGray[curPoint1[0][1]][curPoint1[0][0]]
            validContourSize += 1

            curPoint2Tmp[0][0] = curPoint1[0][0]
            curPoint2Tmp[0][1] = curPoint1[0][1]
            if(curPoint1[0][0] < cx):
                curPoint2Tmp[0][0] = curPoint1[0][0] + 1
            elif(curPoint1[0][0] > cx):
                curPoint2Tmp[0][0] = curPoint1[0][0] - 1
            
            if(curPoint1[0][1] < cy):
                curPoint2Tmp[0][1] = curPoint1[0][1] + 1
            elif(curPoint1[0][1] > cy):
                curPoint2Tmp[0][1] = curPoint1[0][1] - 1            
            
            if(curPoint2Tmp[0][0] < 0 or curPoint2Tmp[0][0] >= imgW
                or curPoint2Tmp[0][1] < 0 or curPoint2Tmp[0][1] >= imgH):
                print("curPoint2Tmp exceeded boundaries : ".encode('utf-8'), curPoint2Tmp)
                continue
            
            contourMeanGray += imgGray[curPoint2Tmp[0][1]][curPoint2Tmp[0][0]]
            validContourSize += 1

        if(validContourSize <= 0):
            print("contours gray mean calculation failed  : {}, {}".format(cx, cy).encode('utf-8'))
            return [False, []]
        
        # print("轮廓检测,computeRingRatio 耗时 : {} ms {}".format((time.perf_counter() - start_time)*1000, "+"*10))

        # 计算圆心临近4个点的灰度均值:i2
        centerX = [math.floor(cx), math.ceil(cx)]
        centerY = [math.floor(cy), math.ceil(cy)]
        centerMeanGray = 0.0
        validCenterSize = 0
        for idx in range(2):
            for idy in range(2):
                if(centerX[idx] < 0 or centerX[idx] >= imgW
                    or centerY[idy] < 0 or centerY[idy] >= imgH):
                    continue
                centerMeanGray += imgGray[centerY[idy]][centerX[idx]]
                validCenterSize += 1

        if(validCenterSize <= 0):
            print("central gray mean calculation failed  : {}, {}".format(cx, cy).encode('utf-8'))
            return [False, []]
        
        # if(300 < ctId and ctId < 600):
        if(False):
            print("ctId={}, contour:{} {},  center:{} {}".format(ctId, contourMeanGray, validContourSize, centerMeanGray, validCenterSize))

        contourMeanGray /= validContourSize
        centerMeanGray /= validCenterSize



        return [True, [contourMeanGray/centerMeanGray if(centerMeanGray > 2) else 100.0,  contourMeanGray, centerMeanGray]]

    '''
    description: 求两个2D向量的夹角
    param {*} self
    param {*} v1
    param {*} v2
    return {*}  夹角:角度；正表示从v1到v2逆时针（0,pi）；负表示从v1到v2逆时针（pi到2*pi）
    '''
    def getAngleBy2D(self, v1, v2):
        # assert(v1.size == 2 and v2.size == 2)
        v1_n = np.linalg.norm(v1)
        # assert(v1_n != 0)
        if(v1_n < 1e-6):
            return 0
        v2_n = np.linalg.norm(v2)
        # assert(v2_n != 0)
        if(v2_n < 1e-6):
            return 0
        v1_tmp = v1*(1/v1_n)
        v2_tmp = v2*(1/v2_n)
        
        # theta = math.acos(np.dot(v1_tmp, v2_tmp))*180.0/math.pi
        theta = np.dot(v1_tmp, v2_tmp)
        if(theta < -1):
            theta = -1
        elif(theta > 1):
            theta = 1
        # print("theta={}".format(theta))
        theta = math.acos(theta) * 180.0/math.pi
        # return theta
        # theta = theta * 180.0/math.pi
        # direct = np.cross(v1_tmp, v2_tmp)   #np.cross操作耗时非常高！
        direct = v1_tmp[0]*v2_tmp[1] - v1_tmp[1]*v2_tmp[0]
        if(abs(direct) < 1e-6):
            return theta
        if(direct > 0):
            return theta
        else:
            return -theta
