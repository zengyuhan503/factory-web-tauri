#ifndef POINT_CALIBRATE_BOARD_H
#define POINT_CALIBRATE_BOARD_H
#define TARGET_A std::string("A")
#define TARGET_B std::string("B")
#include <opencv2/highgui.hpp>
#include <map>
#include <memory>
struct PointCalibrateBoard
{
    /* data */
    cv::Point2d center_image=cv::Point2d(-1,-1);
    cv::Point2d center_image_reproject=cv::Point2d(-1,-1);
    cv::Point3d center_world_coordinate;
    cv::Point3d center_camera_coordinate;
    std::vector<cv::Point2f> vertices;
    double area = 0;   // 圆面积
    double ratio = 0;  // 最小外接矩形长宽比
    double sort_d = 0; // 用于排序的距离d
    std::vector<cv::Point> contour;
    std::weak_ptr<PointCalibrateBoard> left;
    std::weak_ptr<PointCalibrateBoard> right;
    std::weak_ptr<PointCalibrateBoard> up;
    std::weak_ptr<PointCalibrateBoard> down;


    std::multimap<double,std::weak_ptr<PointCalibrateBoard>>  distance_at_image;
    std::multimap<double,std::weak_ptr<PointCalibrateBoard>>  bigger_distance_at_image;

    cv::Point2d direct_left;
    cv::Point2d direct_right;
    cv::Point2d direct_up;
    cv::Point2d direct_down;

    double angle_left = 0;
    double angle_right = 0;
    double angle_up = 0;
    double angle_down = 0;

    double scale_left = 1;
    double scale_right = 1;
    double scale_up = 1;
    double scale_down = 1;

    bool bBigger = false;
    bool bRing = false;
    bool bConnected = false;
    bool bComplete = false;
    bool bChoosed = false;
    bool bCenter =false;
    bool bWorld =false;
    bool bReProject =false;
    int times = 0;
    std::string type = ""; // TARGET_A  TARGET_B
    int col = 0;
    int row = 0;
    static int rows;
    static int cols;
};

#endif