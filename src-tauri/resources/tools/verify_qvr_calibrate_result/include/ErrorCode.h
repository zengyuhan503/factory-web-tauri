#ifndef ERROR_CODE_H
#define ERROR_CODE_H
typedef unsigned int Error ;
namespace ErrorCode
{
    int OK = 0;
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
}

#endif