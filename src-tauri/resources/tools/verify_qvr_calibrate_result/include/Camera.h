#ifndef CAMERA_H
#define CAMERA_H
#include <vector>
#include <Eigen/Core>
#include <opencv2/highgui.hpp>
#include <Eigen/Core>
class Camera
{
protected:
    double m_fx;
    double m_fy;
    double m_cx;
    double m_cy;
    std::vector<double> m_dist_coeff;
    int m_id = 0;
    static int camera_count;
    int m_width;
    int m_height;
    int m_type;
    Eigen::Matrix4d m_pose_to_camera0;

public:
    Camera(double fx, double fy, double cx, double cy, std::vector<double> dist_coeff, int width, int height);
    Camera(){};
    ~Camera();
    Eigen::Matrix3d K();
    void SetK(cv::Mat K);
    std::vector<double> DistCoeff();
    void SetDistCoeff(std::vector<double>coeff){m_dist_coeff=coeff;};
    int GetWidth() { return m_width; };
    int GetHeight() { return m_height; };
    void SetSize(int width,int height){m_width=width;m_height=height;};
    void SetId(int id) { m_id = id; }
    int  GetId(){return m_id;}
    void SetType(int type){m_type=type;};
    void SetPoseToCamera0(Eigen::Matrix4d pose){m_pose_to_camera0=pose;}
    Eigen::Matrix4d GetPoseToCamera0(){return m_pose_to_camera0;}

    virtual Eigen::Vector2d Project(const Eigen::Vector3d &v3D) = 0;
    virtual Eigen::Vector2f Project(const Eigen::Vector3f &v3D) = 0;

    virtual std::vector<cv::Point2d> Project(std::vector<cv::Point3d> &v3D,Eigen::Matrix4d pose) = 0;


    virtual Eigen::Vector3f Unproject(const Eigen::Vector2f &p2D) = 0;
    virtual Eigen::Vector3d Unproject(const Eigen::Vector2d &p2D) = 0;

    const static unsigned int CAM_PINHOLE = 0;
    const static unsigned int CAM_FISHEYE = 1;
};

#endif