import cv2 as cv
import numpy as np
# from skimage import morphology
import random
import math as math


'''
description: 在图像上绘制时考虑缩放尺寸
return {*}
'''
class ScaleDrawer:

    def __init__(self, scaleX, scaleY):
        self.scaleX = scaleX
        self.scaleY = scaleY

    def scale_drawContours(self, scaledImage, contours, contourIdx, color, thickness = 1):
        # 缩放轮廓的位置和尺寸
        scaled_contours = []
        for contour in contours:
            scaled_contour = contour * [self.scaleX, self.scaleY]  # 缩放轮廓坐标
            scaled_contour = scaled_contour.astype(int)
            scaled_contours.append(scaled_contour)        
        cv.drawContours(scaledImage, scaled_contours, contourIdx, color, thickness)

    def scale_circle(self, scaledImage, center, radius, color, thickness = 1):
        # 缩放最大圆的位置和半径
        scaleCenter = (int(center[0] * self.scaleX), int(center[1] * self.scaleY))
        scaled_radius = int(radius * (self.scaleX + self.scaleY) * 0.5)
        cv.circle(scaledImage, scaleCenter, scaled_radius, color, thickness)
    
    def scale_line(self, scaledImage, pt1, pt2, color, thickness = 1):
        scalePt1 = (int(pt1[0] * self.scaleX), int(pt1[1] * self.scaleY))
        scalePt2 = (int(pt2[0] * self.scaleX), int(pt2[1] * self.scaleY))
        cv.line(scaledImage, scalePt1, scalePt2, color,thickness)

    def scale_putText(self, scaledImage, text, org, fontFace, fontScale, color, thickness = 1):
        scaleCenter = (int(org[0] * self.scaleX), int(org[1] * self.scaleY))
        cv.putText(scaledImage, text, scaleCenter, fontFace , fontScale, color ,thickness)

    def scal_drawDot(self, scaledImage, org, color):
        scaleCenter = (int(org[0] * self.scaleX), int(org[1] * self.scaleY))
        if(scaleCenter[0] < 0 or scaleCenter[0] >= scaledImage.shape[1]):
            print("org out of range, scaledImage.shape=", scaledImage.shape, ", scaleCenter=", scaleCenter)
            return
        if(scaleCenter[1] < 0 or scaleCenter[1] >= scaledImage.shape[0]):
            print("org out of range, scaledImage.shape=", scaledImage.shape, ", scaleCenter=", scaleCenter)
            return
        scaledImage[scaleCenter[1]][scaleCenter[0]] = color
