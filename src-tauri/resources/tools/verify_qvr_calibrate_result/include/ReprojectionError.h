#ifndef REPREJECTION_ERROR_H
#define REPREJECTION_ERROR_H
#include <Eigen/Geometry>
#include <Eigen/Core>
#include <memory>
#include "Camera.h"
#include "PointCalibrateBoard.h"
#include "ReadQvrCalResult.h"
#include <opencv2/highgui.hpp>
#include "Drawer.h"
class ReprojectionError
{
private:
    std::vector<std::shared_ptr<Camera>> m_cams;
    ReadQvrCalResult m_device_calibration;
#ifdef SHOW
    Drawer* m_drawer;
#endif



public:
#ifdef SHOW
    ReprojectionError(ReadQvrCalResult &device_calibration,Drawer* drawer) ;
#else
    ReprojectionError(ReadQvrCalResult &device_calibration) ;
#endif
    ~ReprojectionError();
    int ComputeError(std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> board_a_points,
                     std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> board_b_points,Eigen::Matrix4d pose,int camera_id,cv::Mat img=cv::Mat());
    
private:
    void Show(cv::Mat show,std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> &board_points,std::string name);
    std::vector<std::weak_ptr<PointCalibrateBoard>> GetCenterBoardPoint(std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> board_points);
    int ComputeWorldCoordinatePoints(std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> &board_points);
    int ComputeCameraCoordinatePoints(std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> &board_points,Eigen::Matrix4d pose);
    int ComputeImageCoordinatePoints(std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> &board_points,Eigen::Matrix4d pose, int camera_id);
    void TestPose(std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> &board_points,Eigen::Matrix4d &pose_calib,Eigen::Matrix4d pose, int camera_id);
};

#endif