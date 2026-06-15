#include "Utils.h"
bool endWith(const std::string &str, const std::string &tail) {
	return str.compare(str.size() - tail.size(), tail.size(), tail) == 0;
}
cv::Matx44d invMat(const cv::Matx44d &M)
{
    cv::Matx33d R = M.get_minor<3, 3>(0, 0);
    R = R.t();
    cv::Vec3d t(M(0, 3), M(1, 3), M(2, 3));
    t = -R * t;
    cv::Matx44d out(
        R(0, 0), R(0, 1), R(0, 2), t(0),
        R(1, 0), R(1, 1), R(1, 2), t(1),
        R(2, 0), R(2, 1), R(2, 2), t(2),
        0.0, 0.0, 0.0, 1.0);

    return out;
}

std::vector<cv::Mat> toDescriptorVector(const cv::Mat &Descriptors)
{
    std::vector<cv::Mat> vDesc;
    vDesc.reserve(Descriptors.rows);
    for (int j = 0; j < Descriptors.rows; j++)
        vDesc.push_back(Descriptors.row(j));

    return vDesc;
}

cv::Mat toCvMat(const Eigen::Matrix<double, 4, 4> &m)
{
    cv::Mat cvMat(4, 4, CV_32F);
    for (int i = 0; i < 4; i++)
        for (int j = 0; j < 4; j++)
            cvMat.at<float>(i, j) = m(i, j);

    return cvMat.clone();
}

cv::Mat toCvMat(const Eigen::Matrix<float, 4, 4> &m)
{
    cv::Mat cvMat(4, 4, CV_32F);
    for (int i = 0; i < 4; i++)
        for (int j = 0; j < 4; j++)
            cvMat.at<float>(i, j) = m(i, j);

    return cvMat.clone();
}
cv::Mat toCvMat(const cv::Matx44d &matx44d)
{
    cv::Mat out = cv::Mat::zeros(4, 4, CV_64FC1);
    for (int c = 0; c < 4; ++c)
        for (int r = 0; r < 4; ++r)
            out.ptr<double>(r)[c] = matx44d(r, c);
    return out;
}

cv::Mat toCvMat(const Eigen::Matrix<float, 3, 4> &m)
{
    cv::Mat cvMat(3, 4, CV_32F);
    for (int i = 0; i < 3; i++)
        for (int j = 0; j < 4; j++)
            cvMat.at<float>(i, j) = m(i, j);

    return cvMat.clone();
}

cv::Mat toCvMat(const Eigen::Matrix3d &m)
{
    cv::Mat cvMat(3, 3, CV_64F);
    for (int i = 0; i < 3; i++)
        for (int j = 0; j < 3; j++)
            cvMat.at<double>(i, j) = m(i, j);

    return cvMat.clone();
}

cv::Mat toCvMat(const Eigen::Matrix3f &m)
{
    cv::Mat cvMat(3, 3, CV_32F);
    for (int i = 0; i < 3; i++)
        for (int j = 0; j < 3; j++)
            cvMat.at<float>(i, j) = m(i, j);

    return cvMat.clone();
}

cv::Mat toCvMat(const Eigen::MatrixXf &m)
{
    cv::Mat cvMat(m.rows(), m.cols(), CV_32F);
    for (int i = 0; i < m.rows(); i++)
        for (int j = 0; j < m.cols(); j++)
            cvMat.at<float>(i, j) = m(i, j);

    return cvMat.clone();
}

cv::Mat toCvMat(const Eigen::MatrixXd &m)
{
    cv::Mat cvMat(m.rows(), m.cols(), CV_32F);
    for (int i = 0; i < m.rows(); i++)
        for (int j = 0; j < m.cols(); j++)
            cvMat.at<float>(i, j) = m(i, j);

    return cvMat.clone();
}
cv::Mat toCvMat(const Eigen::Vector3d &m)
{
    int rows=m.size();
    cv::Mat cvMat(rows, 1, CV_64F);
    for (int i = 0; i < rows; i++)
        cvMat.at<double>(i) = m[i];
    return cvMat.clone();
}
cv::Mat toCvMat(std::vector<double> m)
{
    int rows=m.size();
    cv::Mat cvMat(1,rows, CV_64F);
    for (int i = 0; i < rows; i++)
        cvMat.at<double>(0,i) = m[i];
    return cvMat.clone();
}


cv::Mat toCvMat(const Eigen::Matrix<float, 3, 1> &m)
{
    cv::Mat cvMat(3, 1, CV_32F);
    for (int i = 0; i < 3; i++)
        cvMat.at<float>(i) = m(i);

    return cvMat.clone();
}

cv::Mat toCvSE3(const Eigen::Matrix<double, 3, 3> &R, const Eigen::Matrix<double, 3, 1> &t)
{
    cv::Mat cvMat = cv::Mat::eye(4, 4, CV_32F);
    for (int i = 0; i < 3; i++)
    {
        for (int j = 0; j < 3; j++)
        {
            cvMat.at<float>(i, j) = R(i, j);
        }
    }
    for (int i = 0; i < 3; i++)
    {
        cvMat.at<float>(i, 3) = t(i);
    }

    return cvMat.clone();
}
cv::Mat toCvSE3(const Eigen::Matrix<float, 3, 3> &R, const Eigen::Matrix<float, 3, 1> &t)
{
    cv::Mat cvMat = cv::Mat::eye(4, 4, CV_32F);
    for (int i = 0; i < 3; i++)
    {
        for (int j = 0; j < 3; j++)
        {
            cvMat.at<float>(i, j) = R(i, j);
        }
    }
    for (int i = 0; i < 3; i++)
    {
        cvMat.at<float>(i, 3) = t(i);
    }

    return cvMat.clone();
}



Eigen::Matrix<double, 3, 1> toVector3d(const cv::Mat &cvVector)
{
    Eigen::Matrix<double, 3, 1> v;
    v << cvVector.at<double>(0), cvVector.at<double>(1), cvVector.at<double>(2);

    return v;
}

Eigen::Matrix<float, 3, 1> toVector3f(const cv::Mat &cvVector)
{
    Eigen::Matrix<float, 3, 1> v;
    v << cvVector.at<float>(0), cvVector.at<float>(1), cvVector.at<float>(2);

    return v;
}

Eigen::Matrix<double, 3, 1> toVector3d(const cv::Point3f &cvPoint)
{
    Eigen::Matrix<double, 3, 1> v;
    v << cvPoint.x, cvPoint.y, cvPoint.z;

    return v;
}

Eigen::Matrix<double, 3, 3> toMatrix3d(const cv::Mat &cvMat3)
{
    Eigen::Matrix<double, 3, 3> M;

    M << cvMat3.at<double>(0, 0), cvMat3.at<double>(0, 1), cvMat3.at<double>(0, 2),
        cvMat3.at<double>(1, 0), cvMat3.at<double>(1, 1), cvMat3.at<double>(1, 2),
        cvMat3.at<double>(2, 0), cvMat3.at<double>(2, 1), cvMat3.at<double>(2, 2);

    return M;
}
Eigen::Matrix<double, 3, 3> toMatrix3d(const cv::Matx33d &cvMat3)
{
    Eigen::Matrix<double, 3, 3> M;

    M << cvMat3(0, 0), cvMat3(0, 1), cvMat3(0, 2),
        cvMat3(1, 0), cvMat3(1, 1), cvMat3(1, 2),
        cvMat3(2, 0), cvMat3(2, 1), cvMat3(2, 2);

    return M;
}
Eigen::Matrix<double, 3, 1> toVector3d(const cv::Matx31d &cvPoint)
{
    Eigen::Matrix<double, 3, 1> v;
    v << cvPoint(0), cvPoint(1), cvPoint(2);

    return v;
}

Eigen::Matrix<double, 4, 4> toMatrix4d(const cv::Mat &cvMat4)
{
    Eigen::Matrix<double, 4, 4> M;

    M << cvMat4.at<float>(0, 0), cvMat4.at<float>(0, 1), cvMat4.at<float>(0, 2), cvMat4.at<float>(0, 3),
        cvMat4.at<float>(1, 0), cvMat4.at<float>(1, 1), cvMat4.at<float>(1, 2), cvMat4.at<float>(1, 3),
        cvMat4.at<float>(2, 0), cvMat4.at<float>(2, 1), cvMat4.at<float>(2, 2), cvMat4.at<float>(2, 3),
        cvMat4.at<float>(3, 0), cvMat4.at<float>(3, 1), cvMat4.at<float>(3, 2), cvMat4.at<float>(3, 3);
    return M;
}

Eigen::Matrix<float, 3, 3> toMatrix3f(const cv::Mat &cvMat3)
{
    Eigen::Matrix<float, 3, 3> M;

    M << cvMat3.at<float>(0, 0), cvMat3.at<float>(0, 1), cvMat3.at<float>(0, 2),
        cvMat3.at<float>(1, 0), cvMat3.at<float>(1, 1), cvMat3.at<float>(1, 2),
        cvMat3.at<float>(2, 0), cvMat3.at<float>(2, 1), cvMat3.at<float>(2, 2);

    return M;
}

Eigen::Matrix<float, 4, 4> toMatrix4f(const cv::Mat &cvMat4)
{
    Eigen::Matrix<float, 4, 4> M;

    M << cvMat4.at<float>(0, 0), cvMat4.at<float>(0, 1), cvMat4.at<float>(0, 2), cvMat4.at<float>(0, 3),
        cvMat4.at<float>(1, 0), cvMat4.at<float>(1, 1), cvMat4.at<float>(1, 2), cvMat4.at<float>(1, 3),
        cvMat4.at<float>(2, 0), cvMat4.at<float>(2, 1), cvMat4.at<float>(2, 2), cvMat4.at<float>(2, 3),
        cvMat4.at<float>(3, 0), cvMat4.at<float>(3, 1), cvMat4.at<float>(3, 2), cvMat4.at<float>(3, 3);
    return M;
}

std::vector<float> toQuaternion(const cv::Mat &M)
{
    Eigen::Matrix<double, 3, 3> eigMat = toMatrix3d(M);
    Eigen::Quaterniond q(eigMat);

    std::vector<float> v(4);
    v[0] = q.x();
    v[1] = q.y();
    v[2] = q.z();
    v[3] = q.w();

    return v;
}

cv::Mat tocvSkewMatrix(const cv::Mat &v)
{
    return (cv::Mat_<float>(3, 3) << 0, -v.at<float>(2), v.at<float>(1),
            v.at<float>(2), 0, -v.at<float>(0),
            -v.at<float>(1), v.at<float>(0), 0);
}

bool isRotationMatrix(const cv::Mat &R)
{
    cv::Mat Rt;
    cv::transpose(R, Rt);
    cv::Mat shouldBeIdentity = Rt * R;
    cv::Mat I = cv::Mat::eye(3, 3, shouldBeIdentity.type());

    return cv::norm(I, shouldBeIdentity) < 1e-6;
}

std::vector<float> toEuler(const cv::Mat &R)
{
    assert(isRotationMatrix(R));
    float sy = sqrt(R.at<float>(0, 0) * R.at<float>(0, 0) + R.at<float>(1, 0) * R.at<float>(1, 0));

    bool singular = sy < 1e-6; // If

    float x, y, z;
    if (!singular)
    {
        x = atan2(R.at<float>(2, 1), R.at<float>(2, 2));
        y = atan2(-R.at<float>(2, 0), sy);
        z = atan2(R.at<float>(1, 0), R.at<float>(0, 0));
    }
    else
    {
        x = atan2(-R.at<float>(1, 2), R.at<float>(1, 1));
        y = atan2(-R.at<float>(2, 0), sy);
        z = 0;
    }

    std::vector<float> v_euler(3);
    v_euler[0] = x;
    v_euler[1] = y;
    v_euler[2] = z;

    return v_euler;
}




cv::Matx33d Hom2R(const cv::Matx44d &homCV)
{
    return cv::Matx33d(homCV(0, 0), homCV(0, 1), homCV(0, 2),
                       homCV(1, 0), homCV(1, 1), homCV(1, 2),
                       homCV(2, 0), homCV(2, 1), homCV(2, 2));
}

cv::Vec3d Hom2T(const cv::Matx44d &homCV)
{
    return cv::Vec3d(homCV(0, 3), homCV(1, 3), homCV(2, 3));
}

int split(std::string pszSrc, const char *flag, std::vector<std::string> &vecDat)
{
    if (pszSrc.empty() || !flag)
        return -1;

    std::string strContent, strTemp;
    strContent = pszSrc;
    std::string::size_type nBeginPos = 0, nEndPos = 0;
    while (true)
    {
        nEndPos = strContent.find(flag, nBeginPos);
        if (nEndPos == std::string::npos)
        {
            strTemp = strContent.substr(nBeginPos, strContent.length());
            if (!strTemp.empty())
            {
                vecDat.push_back(strTemp);
            }
            break;
        }
        strTemp = strContent.substr(nBeginPos, nEndPos - nBeginPos);
        nBeginPos = nEndPos + strlen(flag);
        vecDat.push_back(strTemp);
    }
    return vecDat.size();
}

void print_directory(const boost::filesystem::path &path, const std::string &indent = "")
{
    // 如果路径存在
    if (boost::filesystem::exists(path))
    {
        // 如果路径是一个目录
        if (boost::filesystem::is_directory(path))
        {
           // std::cout << indent << "[目录] " << path << std::endl;
            // 遍历目录下的所有子项
            for (const auto &entry : boost::filesystem::directory_iterator(path))
            {
                print_directory(entry.path(), indent + "  ");
            }
        }
        else
        {
           // std::cout << indent << "[文件] " << path << std::endl;
        }
    }
}

std::vector<std::string> get_subdirectory(const boost::filesystem::path &path)
{
    // 如果路径存在
    std::vector<std::string> ret;
    if (boost::filesystem::exists(path))
    {
        // 如果路径是一个目录
        if (boost::filesystem::is_directory(path))
        {

            // 遍历目录下的所有子项
            for (const auto &entry : boost::filesystem::directory_iterator(path))
            {
                if (boost::filesystem::is_directory(entry.path()))
                {
                    ret.push_back(entry.path().string());
                }
            }
        }
    }
    return ret;
}
std::vector<std::string> get_directory_files(const boost::filesystem::path &path)
{
    // 如果路径存在
    std::vector<std::string> ret;
    if (boost::filesystem::exists(path))
    {
        // 如果路径是一个目录
        if (boost::filesystem::is_directory(path))
        {

            // 遍历目录下的所有子项
            for (const auto &entry : boost::filesystem::directory_iterator(path))
            {
                if (!boost::filesystem::is_directory(entry.path()))
                {
                    ret.push_back(entry.path().string());
                }
            }
        }
    }
    return ret;
}

template <typename T>
double norm(T x)
{
    return sqrt(x.x * x.x + x.y * x.y);
}
double angle(cv::Point2d a, cv::Point2d b)
{
    double t = a.x * b.x + a.y * b.y;
    double theta = acos(t / (norm(a) * norm(b))) * 180 / 3.141592654;
    double d = a.cross(b);
    if (d < 0.0000001)
    {
        theta = -theta;
    }
    return theta;
}