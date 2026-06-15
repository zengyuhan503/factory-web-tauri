#include "Pinhole.h"
#include <opencv2/highgui.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/calib3d.hpp>
#include "Utils.h"
Pinhole::Pinhole(double fx, double fy, double cx, double cy, std::vector<double> dist_coeff, int width, int height) : Camera(fx, fy, cx, cy, dist_coeff, width, height)
{
    m_type = Camera::CAM_PINHOLE;
}

Pinhole::~Pinhole()
{
}

std::vector<cv::Point2d> Pinhole::Project(std::vector<cv::Point3d> &v3D,Eigen::Matrix4d pose) 
{
    cv::Mat rvec,tvec;
    Eigen::Matrix3d rotationMatrix;
    rotationMatrix = pose.block(0, 0, 3, 3);
    Eigen::AngleAxisd rotate_v;
    rotate_v.fromRotationMatrix(rotationMatrix);
    Eigen::Vector3d rv=rotate_v.angle()*rotate_v.axis();
    rvec=toCvMat(rv);
    Eigen::Vector3d tv;  
    tv = pose.block(0, 3, 3, 1);
    tvec=toCvMat(tv);
   
    auto K=this->K();
    cv::Mat cameraMatrix=toCvMat(K);
    auto coeff=this->DistCoeff();
    cv::Mat distCoeffs=toCvMat(coeff);

    std::vector<cv::Point2d> img_pts;

    cv::projectPoints(v3D, rvec, tvec, cameraMatrix, distCoeffs,img_pts);
    return img_pts;

}
Eigen::Vector2d Pinhole::Project(const Eigen::Vector3d &v3D)
{
    static double fx = m_fx;
    static double fy = m_fy;
    static double cx = m_cx;
    static double cy = m_cy;
    static double invfx = 1.0f / fx;
    static double invfy = 1.0f / fy;

    double u = fx * v3D[0] / v3D[2] + cx;
    double v = fy * v3D[1] / v3D[2] + cy;

    double u_distort, v_distort;
    double x = (u - cx) * invfx;
    double y = (v - cy) * invfy;
    if (u < 0 || u > GetWidth())
        return Eigen::Vector2d(-1, -1);
    if (v < 0 || v > GetHeight())
        return Eigen::Vector2d(-1, -1);
    double r2 = x * x + y * y;
    double r4 = r2 * r2;
    double r6 = r2 * r4;
    double k1 = m_dist_coeff[0];
    double k2 = m_dist_coeff[1];
    double p1 = m_dist_coeff[2];
    double p2 = m_dist_coeff[3];
    double k3 = 0;
    double k4 = 0;
    double k5 = 0;
    double k6 = 0;
    if (m_dist_coeff.size() > 4)
    {
        k3 = m_dist_coeff[4];
        if (m_dist_coeff.size() > 5)
        {
            k4 = m_dist_coeff[5];
            k5 = m_dist_coeff[6];
            k6 = m_dist_coeff[7];
        }
    }

    // Radial distorsion
    double x_distort = x * ((1 + k1 * r2 + k2 * r4 + k3 * r6) / (1 + k4 * r2 + k5 * r4 + k6 * r6));
    double y_distort = y * ((1 + k1 * r2 + k2 * r4 + k3 * r6) / (1 + k4 * r2 + k5 * r4 + k6 * r6));

    // Tangential distorsion
    x_distort = x_distort + (2 * p1 * x * y + p2 * (r2 + 2 * x * x));
    y_distort = y_distort + (p1 * (r2 + 2 * y * y) + 2 * p2 * x * y);

    u_distort = x_distort * fx + cx;
    v_distort = y_distort * fy + cy;

    Eigen::Vector2d res;
    res[0] = u_distort;
    res[1] = v_distort;

    return res;
}
Eigen::Vector2f Pinhole::Project(const Eigen::Vector3f &v3D)
{
    static float fx = m_fx;
    static float fy = m_fy;
    static float cx = m_cx;
    static float cy = m_cy;
    static float invfx = 1.0f / fx;
    static float invfy = 1.0f / fy;

    float u = fx * v3D[0] / v3D[2] + cx;
    float v = fy * v3D[1] / v3D[2] + cy;

    float u_distort, v_distort;
    float x = (u - cx) * invfx;
    float y = (v - cy) * invfy;
    if (u < 0 || u > GetWidth())
        return Eigen::Vector2f(-1, -1);
    if (v < 0 || v > GetHeight())
        return Eigen::Vector2f(-1, -1);
    float r2 = x * x + y * y;
    float r4 = r2 * r2;
    float r6 = r2 * r4;
    float k1 = m_dist_coeff[0];
    float k2 = m_dist_coeff[1];
    float p1 = m_dist_coeff[2];
    float p2 = m_dist_coeff[3];
    double k3 = 0;
    double k4 = 0;
    double k5 = 0;
    double k6 = 0;
    if (m_dist_coeff.size() > 4)
    {
        k3 = m_dist_coeff[4];
        if (m_dist_coeff.size() > 5)
        {
            k4 = m_dist_coeff[5];
            k5 = m_dist_coeff[6];
            k6 = m_dist_coeff[7];
        }
    }

    // Radial distorsion
    float x_distort = x * (1 + k1 * r2 + k2 * r4 + k3 * r6) / (1 + k4 * r2 + k5 * r4 + k6 * r6);
    float y_distort = y * (1 + k1 * r2 + k2 * r4 + k3 * r6) / (1 + k4 * r2 + k5 * r4 + k6 * r6);

    // Tangential distorsion
    x_distort = x_distort + (2 * p1 * x * y + p2 * (r2 + 2 * x * x));
    y_distort = y_distort + (p1 * (r2 + 2 * y * y) + 2 * p2 * x * y);

    u_distort = x_distort * fx + cx;
    v_distort = y_distort * fy + cy;

    Eigen::Vector2f res;
    res[0] = u_distort;
    res[1] = v_distort;

    return res;
}
Eigen::Vector3f Pinhole::Unproject(const Eigen::Vector2f &p2D)
{
    cv::Mat mat(1, 2, CV_32F);
    mat.at<float>(0, 0) = p2D.x();
    mat.at<float>(0, 1) = p2D.y();
    cv::Mat K = (cv::Mat_<float>(3, 3)
                     << m_fx,
                 0.f, m_cx, 0.f, m_fy, m_cy, 0.f, 0.f, 1.f);
    cv::Mat DistCoef = (cv::Mat_<float>(8, 1)
                            << m_dist_coeff[0],
                        m_dist_coeff[1], m_dist_coeff[2], m_dist_coeff[3], m_dist_coeff[4], m_dist_coeff[5], m_dist_coeff[6], m_dist_coeff[7]);
    cv::undistortPoints(mat, mat, K, DistCoef);
    return Eigen::Vector3f((mat.at<float>(0, 0) - m_cx) / m_fx, (mat.at<float>(0, 1) - m_cy) / m_fy,
                           1.f);
}
Eigen::Vector3d Pinhole::Unproject(const Eigen::Vector2d &p2D)
{
    cv::Mat mat(1, 2, CV_64F);
    mat.at<double>(0, 0) = p2D.x();
    mat.at<double>(0, 1) = p2D.y();
    cv::Mat K = (cv::Mat_<double>(3, 3)
                     << m_fx,
                 0.f, m_cx, 0.f, m_fy, m_cy, 0.f, 0.f, 1.f);
    cv::Mat DistCoef = (cv::Mat_<double>(8, 1)
                            << m_dist_coeff[0],
                        m_dist_coeff[1], m_dist_coeff[2], m_dist_coeff[3], m_dist_coeff[4], m_dist_coeff[5], m_dist_coeff[6], m_dist_coeff[7]);
    cv::undistortPoints(mat, mat, K, DistCoef);
    return Eigen::Vector3d((mat.at<double>(0, 0) - m_cx) / m_fx, (mat.at<float>(0, 1) - m_cy) / m_fy,
                           1.f);
}