#ifndef UTILS_H
#define UTILS_H
#include <vector>
#include <fstream>
#include <sys/stat.h>
#include <iostream>
#include <memory>
#include <boost/filesystem.hpp>
#include <opencv2/highgui.hpp>
#include <Eigen/Geometry>
#include <Eigen/Dense>

bool endWith(const std::string &str, const std::string &tail) ;
int split(std::string pszSrc, const char *flag, std::vector<std::string> &vecDat);
double angle(cv::Point2d a, cv::Point2d b);
std::vector<std::string> get_subdirectory(const boost::filesystem::path &path);
std::vector<std::string> get_directory_files(const boost::filesystem::path &path);
template <typename T>
double norm(T x);

template <typename Time, typename InterpolateType>
void linearInterpolation(
    const Time t1, const InterpolateType &x1, const Time t2,
    const InterpolateType &x2, const Time t_interpolated,
    InterpolateType &x_interpolated)
{

  if (t1 == t2)
  {
    // CHECK_EQ(x1, x2);
    x_interpolated = x1;
    return;
  }
  x_interpolated = x1 + (x2 - x1) / (t2 - t1) * (t_interpolated - t1);
}

template <typename Time>
void interpolateRotation(
    const Time t1, const Eigen::Quaterniond &q_A_B1, const Time t2,
    const Eigen::Quaterniond &q_A_B2, const Time t_interpolated,
    Eigen::Quaterniond &q_A_B_interpolated)
{
  double d=(t2-t_interpolated)*1.0/(t2-t1);
  q_A_B_interpolated=q_A_B1.slerp(d,q_A_B2);
}

template <typename Time>
void interpolateTransformation(
    const Time t1, const Eigen::Matrix4d &T_A_B1, const Time t2,
    const Eigen::Matrix4d &T_A_B2, const Time t_interpolated,
    Eigen::Matrix4d &T_A_B_interpolated)
{
  Eigen::Matrix3d rotate1=T_A_B1.block(0,0,3,3);
  Eigen::Quaterniond p1(rotate1);

  Eigen::Matrix3d rotate2=T_A_B2.block(0,0,3,3);
  Eigen::Quaterniond p2(rotate2);

  Eigen::Quaterniond rotate_inter;
  interpolateRotation(t1,p1,t2,p2,t_interpolated,rotate_inter);


  Eigen::Vector3d transtion1=T_A_B1.block(0,3,3,1);
  Eigen::Vector3d transtion2=T_A_B2.block(0,3,3,1);
  Eigen::Vector3d transtion_inter;


  linearInterpolation(t1,transtion1,t2,transtion2,t_interpolated,transtion_inter);

  T_A_B_interpolated.block(0,0,3,3)=rotate_inter.matrix();
  T_A_B_interpolated.block(0,3,3,1)=transtion_inter;


}

cv::Matx44d invMat(const cv::Matx44d &M);
std::vector<cv::Mat> toDescriptorVector(const cv::Mat &Descriptors);

// TODO templetize these functions

cv::Mat toCvMat(const Eigen::Matrix<double, 4, 4> &m);
cv::Mat toCvMat(const Eigen::Matrix<float, 4, 4> &m);
cv::Mat toCvMat(const Eigen::Matrix<float, 3, 4> &m);
cv::Mat toCvMat(const Eigen::Matrix3d &m);
cv::Mat toCvMat(const Eigen::Matrix<float, 3, 1> &m);
cv::Mat toCvMat(const Eigen::Matrix<float, 3, 3> &m);
cv::Mat toCvMat(const cv::Matx44d &matx44d);

cv::Mat toCvMat(const Eigen::MatrixXf &m);
cv::Mat toCvMat(const Eigen::MatrixXd &m);

cv::Mat toCvMat(const Eigen::Vector3d &m);

cv::Mat toCvMat(std::vector<double> m);

cv::Mat toCvSE3(const Eigen::Matrix<double, 3, 3> &R, const Eigen::Matrix<double, 3, 1> &t);
cv::Mat toCvSE3(const Eigen::Matrix<float, 3, 3> &R, const Eigen::Matrix<float, 3, 1> &t);

cv::Mat tocvSkewMatrix(const cv::Mat &v);

Eigen::Matrix<double, 3, 1> toVector3d(const cv::Mat &cvVector);
Eigen::Matrix<float, 3, 1> toVector3f(const cv::Mat &cvVector);
Eigen::Matrix<double, 3, 1> toVector3d(const cv::Point3f &cvPoint);
Eigen::Matrix<double, 3, 3> toMatrix3d(const cv::Mat &cvMat3);
Eigen::Matrix<double, 3, 3> toMatrix3d(const cv::Matx33d &cvMat3);
Eigen::Matrix<double, 3, 1> toVector3d(const cv::Matx31d &cvMat3);
Eigen::Matrix<double, 4, 4> toMatrix4d(const cv::Mat &cvMat4);
Eigen::Matrix<float, 3, 3> toMatrix3f(const cv::Mat &cvMat3);
Eigen::Matrix<float, 4, 4> toMatrix4f(const cv::Mat &cvMat4);
std::vector<float> toQuaternion(const cv::Mat &M);

bool isRotationMatrix(const cv::Mat &R);
std::vector<float> toEuler(const cv::Mat &R);





cv::Matx33d Hom2R(const cv::Matx44d &homCV);

cv::Vec3d Hom2T(const cv::Matx44d &homCV);
#endif