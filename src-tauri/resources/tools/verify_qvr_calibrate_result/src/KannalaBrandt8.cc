#include "KannalaBrandt8.h"
#include <opencv2/highgui.hpp>
#include <opencv2/calib3d.hpp>
#include "Utils.h"
KannalaBrandt8::KannalaBrandt8(double fx, double fy, double cx, double cy, std::vector<double> dist_coeff, int width, int height) : Camera(fx, fy, cx, cy, dist_coeff, width, height)
{
    m_type=Camera::CAM_FISHEYE;
}

KannalaBrandt8::~KannalaBrandt8()
{
}
std::vector<cv::Point2d> KannalaBrandt8::Project(std::vector<cv::Point3d> &v3D,Eigen::Matrix4d pose) 
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


    assert(cameraMatrix.type() == CV_64F);
    assert(distCoeffs.type() == CV_64F);
    assert( distCoeffs.total() == 4);

    std::vector<cv::Point2d> img_pts;
    cv::fisheye::projectPoints(v3D,img_pts, rvec, tvec, cameraMatrix, distCoeffs);
    return img_pts;

}
Eigen::Vector2d KannalaBrandt8::Project(const Eigen::Vector3d &v3D)
{
    const double x2_plus_y2 = v3D[0] * v3D[0] + v3D[1] * v3D[1];
    const double theta = atan2f(sqrtf(x2_plus_y2), v3D[2]);
    const double psi = atan2f(v3D[1], v3D[0]);

    const double theta2 = theta * theta;
    const double theta3 = theta * theta2;
    const double theta5 = theta3 * theta2;
    const double theta7 = theta5 * theta2;
    const double theta9 = theta7 * theta2;
    const double r = theta + m_dist_coeff[0] * theta3 + m_dist_coeff[1] * theta5 + m_dist_coeff[2] * theta7 + m_dist_coeff[3] * theta9;

    Eigen::Vector2d res;
    res[0] = m_fx * r * cos(psi) + m_cx;
    res[1] = m_fy * r * sin(psi) + m_cy;

    return res;
}
Eigen::Vector2f KannalaBrandt8::Project(const Eigen::Vector3f &v3D)
{
    const double x2_plus_y2 = v3D[0] * v3D[0] + v3D[1] * v3D[1];
    const double theta = atan2f(sqrtf(x2_plus_y2), v3D[2]);
    const double psi = atan2f(v3D[1], v3D[0]);

    const double theta2 = theta * theta;
    const double theta3 = theta * theta2;
    const double theta5 = theta3 * theta2;
    const double theta7 = theta5 * theta2;
    const double theta9 = theta7 * theta2;
    const double r = theta + m_dist_coeff[0] * theta3 + m_dist_coeff[1] * theta5 + m_dist_coeff[2] * theta7 + m_dist_coeff[3] * theta9;

    Eigen::Vector2f res;
    res[0] = m_fx * r * cos(psi) + m_cx;
    res[1] = m_fy * r * sin(psi) + m_cy;

    return res;
}
Eigen::Vector3f KannalaBrandt8::Unproject(const Eigen::Vector2f &p2D)
{
    Eigen::Vector2f pw((p2D.x() - m_cx) / m_fx, (p2D.y() - m_cy) / m_fy);
    float scale = 1.f;
    float theta_d = sqrtf(pw.x() * pw.x() + pw.y() * pw.y());
    theta_d = fminf(fmaxf(-CV_PI / 2.f, theta_d), CV_PI / 2.f);

    if (theta_d > 1e-8)
    {
        // Compensate distortion iteratively
        float theta = theta_d;

        for (int j = 0; j < 10; j++)
        {
            float theta2 = theta * theta, theta4 = theta2 * theta2, theta6 = theta4 * theta2, theta8 = theta4 * theta4;
            float k0_theta2 = m_dist_coeff[0] * theta2, k1_theta4 = m_dist_coeff[1] * theta4;
            float k2_theta6 = m_dist_coeff[2] * theta6, k3_theta8 = m_dist_coeff[3] * theta8;
            float theta_fix = (theta * (1 + k0_theta2 + k1_theta4 + k2_theta6 + k3_theta8) - theta_d) /
                              (1 + 3 * k0_theta2 + 5 * k1_theta4 + 7 * k2_theta6 + 9 * k3_theta8);
            theta = theta - theta_fix;
            if (fabsf(theta_fix) < 1e-6)
                break;
        }
        // scale = theta - theta_d;
        scale = std::tan(theta) / theta_d;
    }

    return Eigen::Vector3f(pw.x() * scale, pw.y() * scale, 1.f);
}
Eigen::Vector3d KannalaBrandt8::Unproject(const Eigen::Vector2d &p2D)
{
    // Use Newthon method to solve for theta with good precision (err ~ e-6)
    Eigen::Vector2d pw((p2D.x() - m_cx) / m_fx, (p2D.y() - m_cy) / m_fy);
    double scale = 1.f;
    double theta_d = sqrtf(pw.x() * pw.x() + pw.y() * pw.y());
    theta_d = fminf(fmaxf(-CV_PI / 2.f, theta_d), CV_PI / 2.f);

    if (theta_d > 1e-8)
    {
        // Compensate distortion iteratively
        double theta = theta_d;

        for (int j = 0; j < 10; j++)
        {
            double theta2 = theta * theta, theta4 = theta2 * theta2, theta6 = theta4 * theta2, theta8 = theta4 * theta4;
            double k0_theta2 = m_dist_coeff[0] * theta2, k1_theta4 = m_dist_coeff[1] * theta4;
            double k2_theta6 = m_dist_coeff[2] * theta6, k3_theta8 = m_dist_coeff[3] * theta8;
            double theta_fix = (theta * (1 + k0_theta2 + k1_theta4 + k2_theta6 + k3_theta8) - theta_d) /
                              (1 + 3 * k0_theta2 + 5 * k1_theta4 + 7 * k2_theta6 + 9 * k3_theta8);
            theta = theta - theta_fix;
            if (fabsf(theta_fix) < 1e-6)
                break;
        }
        // scale = theta - theta_d;
        scale = std::tan(theta) / theta_d;
    }

    return Eigen::Vector3d(pw.x() * scale, pw.y() * scale, 1.f);
}