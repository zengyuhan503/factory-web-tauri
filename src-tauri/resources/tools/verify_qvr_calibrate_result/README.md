# 验证高通标定结果
##直接脚本运行
    verify_qvr_calibrate.sh data_dir
## 构建
运行根目录下构建脚本
./build.sh
## 使用方法
verify_qvr_calibrate_result data_dir

## 结果
结果保存在data_dir/verify_result.txt
内容如下：

    camera 0 cannot detect calibrate points
    camera 1 cannot detect calibrate points
    camera 2,count =1597
    camera 2,mean reproject error [-0.62346, -0.595244]
    camera 2,max reproject error [0.841507, -3.43785]
    camera 2,std reproject error [0.415344, 0.243445]
    camera 3,count =2309
    camera 3,mean reproject error [-0.923576, 0.302061]
    camera 3,max reproject error [-2.02784, 0.284948]
    camera 3,std reproject error [0.114351, 0.39398]
    totol time duration= 2.00291


## 程序返回值列表

    int CAMERA0_DETECT_DERROR = (1 << 1);
    int CAMERA1_DETECT_DERROR = (1 << 2);
    int CAMERA2_DETECT_DERROR = (1 << 3);
    int CAMERA3_DETECT_DERROR = (1 << 4);
    int CAMERA4_DETECT_DERROR = (1 << 5);
    int CAMERA5_DETECT_DERROR = (1 << 6);
    int CAMERA0_REPROJECT_DERROR = (1 << 7);
    int CAMERA1_REPROJECT_DERROR = (1 << 8);
    int CAMERA2_REPROJECT_DERROR = (1 << 9);
    int CAMERA3_REPROJECT_DERROR = (1 << 10);
    int CAMERA4_REPROJECT_DERROR = (1 << 11);
    int CAMERA5_REPROJECT_DERROR = (1 << 12);


