
import sys
import getopt
import os
from GT_Calib_Checker import GTCalibChecker

def createFile(filePath, info, consoleOut = True):
    if(consoleOut):
        print(info)
    with open(filePath, 'w') as file:
        file.write(info + "\n")

def log2File(filePath, info, consoleOut = True):
    if(consoleOut):
        print(info)
    with open(filePath, 'a') as file:
        file.write(info + "\n")


if __name__ == '__main__':

    #程序的输入参数
    functionId = 1              #-f 执行功能:     携带值:[1:只check两个RGB相机光轴夹角][2:只check两个RGB相机图像的极线距离Err][3:同时check1和check2]
    calibPath = ""              #-d 数据集路径:   携带值:["/xxx/qvrdataset"]
    badGeoThr = 1.5             #-a check光轴夹角阈值:  携带值:[单位:角度]
    badEpilineErrThr = 1.0      #-e check图像的极线距离Err阈值:  携带值:[单位:像素]
    leftFishEye = False         #-l RGB左相机是否鱼眼模型   携带值:空
    rightFishEye = False        #-r RGB右相机是否鱼眼模型   携带值:空

    #程序返回code:               # 0:通过check
                                # 1:输入参数有误
                                # 2:check光轴夹角，执行有误
                                # 3:check光轴夹角，未通过check
                                # 4:check极线距离Err，执行有误
                                # 5:check极线距离Err，未通过check

    #其他参数
    cameraType = 2
    startImgIdx = 3
    endImgIdx = 6
    stepImgIdx = 1
    pauseShowIdx = []
    logFile = "CalibCheck.log"


    calibPath = "xxx/qvrdataset"    #在此选标定文件路径
    
    if(len(sys.argv) > 1):
        mArgv = sys.argv[1:]
        try:
            opts, args = getopt.getopt(mArgv, "f:d:a:e:lr", ["function=", "data_dir=", "optic_axis_angle=", "epiline_err="])
            # opts, args = getopt.getopt(mArgv, "daelr", ["data_dir=", "optic_axis_angle=", "epiline_err="])            
        except:
            print("read sys.argv fail!")
        for opt, arg in opts:
            if(opt in ['-f', '--function']):            #执行功能
                functionId = int(arg)
            if(opt in ['-d', '--data_dir']):            #输入文件夹路径
                calibPath = arg
            if(opt in ['-a', '--optic_axis_angle']):    #光轴有问题的夹角阈值
                badGeoThr = float(arg)
            if(opt in ['-e', '--epiline_err']):         #极线误差有问题的Err阈值
                badEpilineErrThr = float(arg)
            if(opt in ['-l']):         
                leftFishEye = True
            if(opt in ['-r']):        
                rightFishEye = True
    
    mGTCalibChecker = GTCalibChecker(useCxxLib = [False, "./libboard_detector.so"])
    # mGTCalibChecker = GTCalibChecker(useCxxLib = [False, ""])

    if(not os.path.exists(calibPath)):
        print(f"posePath is invalid:{calibPath}")
        raise SystemExit(1)
    
    logFile = os.path.join(calibPath, logFile)
    createFile(logFile, "-"*30 + " create log file " + "-"*30)
    log2File(logFile, f"calibPath={calibPath}")

    log2File(logFile, f"functionId={functionId}")
    if(functionId not in [1,2,3]):
        log2File(logFile, "functionId invalid")
        raise SystemExit(1)

    bRet = mGTCalibChecker.feedCalibRawData(calibPath, { 0:False, 1:False, 2:False, 3:False, 4: not leftFishEye, 5:not rightFishEye })
    if(bRet == False):
        log2File(logFile, "feedCalibRawData fail")
        raise SystemExit(1)
    
    if(1 == functionId or 3 == functionId):
        bRet, dRet = mGTCalibChecker.getGeoInfoBetweenTwo(4,5)
        if(bRet == False or (dRet is None)):
            log2File(logFile, "getGeoInfoBetweenTwo fail")
            raise SystemExit(2)
        # if(abs(dRet[0][0]) > badGeoThr or abs(dRet[0][1]) > badGeoThr or abs(dRet[0][2]) > badGeoThr):
        if(abs(dRet[0]) > badGeoThr):
            log2File(logFile, f"we detected badGeo:theta={dRet[0]}, euler={dRet[1]}")
            raise SystemExit(3)
        log2File(logFile, f"geo check pass:theta={dRet[0]}, euler={dRet[1]}")
    
    if(2 == functionId or 3 == functionId):
        bRet, dRet = mGTCalibChecker.getEpilinesErrBetweenTwo(cameraType, startImgIdx, endImgIdx, stepImgIdx, pauseShowIdx)
        if(bRet == False or (dRet is None)):
            log2File(logFile, "getEpilinesErrBetweenTwo fail")
            raise SystemExit(4)

        validSizeAll = 0
        validErrAll = 0
        validVarAll = 0
        for errRetOne in dRet:
            validSizeAll += errRetOne[0]
            validErrAll += errRetOne[1]*errRetOne[0]
            validVarAll += errRetOne[2]*errRetOne[0]

        if(validSizeAll <= 0):
            log2File(logFile, "summaryRet: validSizeAll=0")
            raise SystemExit(5)
        else:
            log2File(logFile, "summaryRet: validSizeAll={}, validErrMean={}, validVarMean={}".format(validSizeAll, validErrAll/validSizeAll,validVarAll/validSizeAll))
        
        if(validErrAll/validSizeAll > badEpilineErrThr):
            log2File(logFile, f"we detected badEpilineErr:{validErrAll/validSizeAll}")
            raise SystemExit(5)
        
        log2File(logFile, f"epiline Err check pass:{validErrAll/validSizeAll}")
    
    raise SystemExit(0)
