#ifndef KANNALA_BRABDT8_H
#define KANNALA_BRABDT8_H
#include "Camera.h"
class KannalaBrandt8: public Camera
{
private:
    /* data */
public:
    KannalaBrandt8(double fx, double fy, double cx, double cy, std::vector<double> dist_coeff,int width,int height);
    KannalaBrandt8(){};
    ~KannalaBrandt8();
    Eigen::Vector2d Project(const Eigen::Vector3d &v3D);
    Eigen::Vector2f Project(const Eigen::Vector3f &v3D);
    Eigen::Vector3f Unproject(const Eigen::Vector2f &p2D);
    Eigen::Vector3d Unproject(const Eigen::Vector2d &p2D);
    std::vector<cv::Point2d> Project(std::vector<cv::Point3d> &v3D,Eigen::Matrix4d pose) ;
};



#endif