
#调用接口,采用python脚本调用方式

#接口文件:GT_Calib_Checker_Api.py

    #程序的输入参数
    #-f 执行功能:     携带值:[1:只check两个RGB相机光轴夹角][2:只check两个RGB相机图像的极线距离Err][3:同时check1和check2]
    #-d 数据集路径:   携带值:["/xxx/qvrdataset"]
    #-a check光轴夹角阈值:  携带值:[单位:角度]
    #-e check图像的极线距离Err阈值:  携带值:[单位:像素]
    #-l RGB左相机是否鱼眼模型   携带值:空
    #-r RGB右相机是否鱼眼模型   携带值:空

    #程序返回code:               # 0:通过check
                                # 1:输入参数有误
                                # 2:check光轴夹角，执行有误
                                # 3:check光轴夹角，未通过check
                                # 4:check极线距离Err，执行有误
                                # 5:check极线距离Err，未通过check
#调用示例
    python3 GT_Calib_Checker_Api.py -f 1 -d "qvrdatasetDir"