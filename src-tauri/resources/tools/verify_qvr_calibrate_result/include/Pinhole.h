#ifndef PINHOLE_H
#define PINHOLE_H
#include "Camera.h"
class Pinhole : public Camera
{
private:
    /* data */
public:
    Pinhole(double fx, double fy, double cx, double cy, std::vector<double> dist_coeff,int width,int height);
    Pinhole(){};
    ~Pinhole();

    Eigen::Vector2d Project(const Eigen::Vector3d &v3D);
    Eigen::Vector2f Project(const Eigen::Vector3f &v3D);
    Eigen::Vector3f Unproject(const Eigen::Vector2f &p2D);
    Eigen::Vector3d Unproject(const Eigen::Vector2d &p2D);

    std::vector<cv::Point2d> Project(std::vector<cv::Point3d> &v3D,Eigen::Matrix4d pose) ;
};

#endif