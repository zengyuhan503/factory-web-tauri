#include "Camera.h"
int Camera::camera_count=0;
Camera::Camera(double fx,double fy,double cx,double cy,std::vector<double> dist_coeff,int width,int height):m_fx(fx),
m_fy(fy),m_cx(cx),m_cy(cy),m_dist_coeff(dist_coeff),m_width(width),m_height(height)
{
    camera_count++;

}

Camera::~Camera()
{
}
Eigen::Matrix3d Camera::K()
{
    Eigen::Matrix3d K;
        K << m_fx, 0.f, m_cx, 0.f, m_fy, m_cy, 0.f, 0.f, 1.f;
        return K;

}
void Camera::SetK(cv::Mat K)
{
    m_fx=K.at<double>(0,0);
    m_fy=K.at<double>(1,1);
    m_cx=K.at<double>(0,2);
    m_cy=K.at<double>(1,2);

}
std::vector<double> Camera::DistCoeff()
{
    return m_dist_coeff;
}