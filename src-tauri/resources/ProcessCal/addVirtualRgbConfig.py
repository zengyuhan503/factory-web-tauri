#!/usr/bin/python
# -*- coding: utf-8 -*-
# python 3.x

import os
import xml.etree.ElementTree as Et

string_rgb_config = r'''    <Camera cam_name="rgb-left" name="rgb-left" id="4">
        <Calibration size="1748 1748 " principal_point="876.99361 876.98486 " focal_length="866.91461 866.91461 " model="RADIAL_6_PARAMETERS" radial_distortion="2.394892 -0.13978131 -0.018713967 2.8828346 0.36778809 -0.085692131 " distortion_limit="2.760000" undistortion_limit="1.228837" />
        <Rig translation="-0.012030806 0.023472049 -0.010676192 " rowMajorRotationMat="0.011755585 -0.98986917 -0.14149501 0.80934271 -0.073680834 0.58269676 -0.58721903 -0.12136789 0.80027723 " />
        <RollingShutter isRollingShutter="true" linetime="5.50478e-06" />
        <TimeAlignment delta="0.001869" />
        <CaptureDetails nativeSensorWidth="4656" nativeSensorHeight="3496" cropL="580" cropR="580" cropT="0" cropB="0" binningH="2" binningV="2" />
        <VignettingCorrection model="RADIAL_POLYNOMIAL" center="877.74609 876.92684 " normalizer="1236.022654" coeffs="-1.3038254 1.2382247 -0.75058539 " />
    </Camera>
    <Camera cam_name="rgb-right" name="rgb-right" id="5">
        <Calibration size="1748 1748 " principal_point="868.08853 861.12314 " focal_length="868.82772 868.82772 " model="RADIAL_6_PARAMETERS" radial_distortion="2.7595785 0.099710442 -0.0090457885 3.2475327 0.73641594 -0.033600983 " distortion_limit="2.780000" undistortion_limit="1.228045" />
        <Rig translation="-0.07842864 0.02561925 -0.010788971 " rowMajorRotationMat="0.018268411 -0.98807867 -0.15286207 0.81150467 -0.074657417 0.57955711 -0.58406031 -0.13463587 0.80046658 " />
        <RollingShutter isRollingShutter="true" linetime="5.50478e-06" />
        <TimeAlignment delta="0.001813" />
        <CaptureDetails nativeSensorWidth="4656" nativeSensorHeight="3496" cropL="580" cropR="580" cropT="0" cropB="0" binningH="2" binningV="2" />
        <VignettingCorrection model="RADIAL_POLYNOMIAL" center="868.88531 861.06346 " normalizer="1236.022654" coeffs="-0.93424259 0.13003032 0.22973808 " />
    </Camera>'''

def getElementByCamNmae(xml_path, cam_name):
    xmltree = Et.parse(xml_path)
    root = xmltree.getroot()
    for elem in root.findall("Camera"):
        xml_cam_name = elem.attrib["cam_name"]
        if(xml_cam_name == cam_name):
            break;
    return elem

def getLineNumByString(xml_path, search_string):
    with open(xml_path, mode="r", newline="") as f:
        for i, line in enumerate(f, start=1):
            if search_string in line:
                return i

def insertStringToLine(xml_path, lineNum, search_string):
    fp = open(xml_path, mode="r", newline="")           #指定文件
    s = fp.read()                   #将指定文件读入内存
    fp.close()                      #关闭该文件
    a = s.split('\n')
    a.insert(lineNum, search_string)    #在第 LINE+1 行插入
    s = '\n'.join(a)                #用'\n'连接各个元素
    fp = open(xml_path, mode="w", newline="")
    fp.write(s)
    fp.close()

def insertRgbConfig(xml_path):
    line_num = getLineNumByString(xml_path ,'''Image format="interleaved"''')
    if line_num:
        insertStringToLine(xml_path, line_num - 1, string_rgb_config)
        print("插入RGB camera 配置：",line_num)
        return True
    else:
        print('''没有找到关键字Image format="interleaved"''')
        return False

if __name__ == '__main__':
    line_num = getLineNumByString("device_calibration.xml" ,'''Image format="interleaved"''')
    if line_num:
        insertStringToLine("device_calibration.xml", line_num - 1, string_rgb_config)
    print(line_num)
    #if rgb_left and rgb_right :
    #for child in rgb_left:
    #    print(child.tag, child.attrib)