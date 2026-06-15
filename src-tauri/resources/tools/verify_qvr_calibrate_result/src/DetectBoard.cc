#include "PointCalibrateBoard.h"
#include "DetectBoard.h"
#include "Utils.h"
#include <opencv2/features2d.hpp>
#include <opencv2/imgproc.hpp>
#include <chrono>
int PointCalibrateBoard::rows = 48;
int PointCalibrateBoard::cols = 24;
int show_scale = 1;

DetectBoard::DetectBoard(/* args */)
{
}

DetectBoard::~DetectBoard()
{
}
void DetectBoard::clear_board_points()
{
    m_global_boards_points.clear();
}
double PointCalibrateBoard_image_distance(std::weak_ptr<PointCalibrateBoard> a, std::weak_ptr<PointCalibrateBoard> b)
{
    auto pa = a.lock();
    auto pb = b.lock();
    if (!pa || !pb)
    {
        std::cout << __FILE__ << ":" << __LINE__ << "PointCalibrateBoard_image_distance pa=" << pa << ",pb=" << pb << std::endl;
        exit(-1);
    }
    return norm(pa->center_image - pb->center_image);
}

// 按照面积进行排序，从大到小
void sort_by_area(std::vector<std::weak_ptr<PointCalibrateBoard>> &board)
{

    std::sort(board.begin(), board.end(), [](const std::weak_ptr<PointCalibrateBoard> &a, const std::weak_ptr<PointCalibrateBoard> &b)
              { 
                auto pa=a.lock();
                auto pb=b.lock();
                if(!pa||!pb)
                {
                    std::cout<<"error line:"<<__LINE__<<"sort_by_area pa="<<pa<<",pb="<<pb<<std::endl;
                    exit(-1);
                }
                return pa->area > pb->area; });
}

// 按照到特定点的距离进行排序，从小到大
void sort_by_distance(std::vector<std::weak_ptr<PointCalibrateBoard>> board)
{
#ifdef MEASURE_RUNNING_TIME
    // 设置开始时间
    auto start = std::chrono::system_clock::now();
#endif
    for (auto it1 = board.begin(); it1 != board.end(); it1++)
    {
        for (auto it2 = it1 + 1; it2 != board.end(); it2++)
        {

            {
                auto p1 = (*it1).lock();
                auto p2 = (*it2).lock();

                if (!p1 || !p2)
                {
                    std::cout << __FILE__ << ":" << __LINE__ << "sort_by_distance p=" << p1 << "," << p2 << std::endl;
                    exit(-1);
                }
                double d = PointCalibrateBoard_image_distance(p1, p2);
                if(d<64)
                {
                    p1->distance_at_image.insert({d, p2});
                    p2->distance_at_image.insert({d, p1});

                }
                
            }
        }
    }
#ifdef MEASURE_RUNNING_TIME
    // 设置结束时间
    auto end = std::chrono::system_clock::now();

    // 精确到微秒，除此之外，还有五种时间单位：hours, minutes, seconds, milliseconds, nanoseconds
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start);

    // duration.count() 返回统计的时间
    // num 和 den分别表示分子(numerator)和分母(denominator)
    // 在代码中，num等于1， den等于1,000,000
    std::cout << "sort_by_distance duration=" << double(duration.count()) * std::chrono::microseconds::period::num / std::chrono::microseconds::period::den << std::endl;
#endif
}

// 按照到特定点的距离进行排序，从小到大
void sort_bigger_by_distance(std::vector<std::weak_ptr<PointCalibrateBoard>> board)
{

    for (auto it1 = board.begin(); it1 != board.end(); it1++)
    {
        for (auto it2 = it1 + 1; it2 != board.end(); it2++)
        {

            {
                auto p1 = (*it1).lock();
                auto p2 = (*it2).lock();

                if (!p1 || !p2)
                {
                    std::cout << __FILE__ << ":" << __LINE__ << "sort_by_distance p=" << p1 << "," << p2 << std::endl;
                    exit(-1);
                }
                double d = PointCalibrateBoard_image_distance(p1, p2);
                p1->bigger_distance_at_image.insert({d, p2});
                p2->bigger_distance_at_image.insert({d, p1});
            }
        }
    }
}

struct error_camera_reproject
{
    /* data */
    double error_max;
    double error_mean;
    double error_std;
};

error_camera_reproject compute_camera_reproject(cv::Mat src)
{
    cv::Mat gray;
    cv::cvtColor(src, gray, cv::COLOR_RGB2GRAY);
    std::vector<std::vector<cv::Point>> contours;
    std::vector<double> contours_perimeter;

    std::vector<cv::Vec4i> hierarchy;
    cv::findContours(gray, contours, hierarchy, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_NONE); // 只找最外层轮廓

    cv::Mat dst;
    cv::cvtColor(gray, dst, cv::COLOR_GRAY2BGR);

    for (int i = 0; i < contours.size(); ++i)
    {                                                                  // 绘制所有轮廓
        cv::drawContours(dst, contours, i, cv::Scalar(0, 255, 0), -1); // thickness为-1时为填充整个轮廓
    }
    double error_max = 0, error_mean = 0, error_std;
    for (auto i = contours.begin(); i != contours.end(); i++)
    {

        double d = 0;
        for (auto j = (*i).begin(); j != (*i).end(); j++)
        {
            for (auto k = j + 1; k != (*i).end(); k++)
            {
                double tmp = norm((*j) - (*k));
                if (tmp > d)
                {
                    d = tmp;
                }
            }
        }
        if (d > error_max)
        {
            error_max = d;
        }

        error_mean += d;
        contours_perimeter.push_back(d);
    }
    error_mean = error_mean / contours_perimeter.size();
    for (auto i = contours_perimeter.begin(); i != contours_perimeter.end(); i++)
    {

        double perimeter = (*i);
        error_std = (perimeter - error_mean) * (perimeter - error_mean);
    }
    error_std = std::sqrt(error_std / contours_perimeter.size());

#ifdef SHOW
    // cv::imwrite("test.png",dst);

    cv::imshow("dst", dst);

#endif
    error_camera_reproject ret{error_max, error_mean, error_std};
    return ret;
}

int analysis(int argc, char **argv)
{
    std::string data_path;
    if (argc == 2)
    {
        data_path = std::string(argv[1]);
        std::cout << data_path << std::endl;
    }
    else
    {
        std::cout << " usage sample:./verify_qvr_calibrate_result /home/home/chuanqi/work/Github/skycalib/calibrat-9.13~9.16/2600047_2023-09-16-15-07-41\n";
        return 0;
    }
    auto data_pathes = get_subdirectory(data_path);

    for (int i = 0; i < data_pathes.size(); i++)
    {
        std::cout << data_pathes[i] << std::endl;
        std::string ctrl_trackingA_path = data_pathes[i] + "/calibDetails/ModelError-ctrl-trackingA-FISHEYE_4_PARAMETERS-Full-Extrinsics+I.png";
        std::string ctrl_trackingB_path = data_pathes[i] + "/calibDetails/ModelError-ctrl-trackingB-FISHEYE_4_PARAMETERS-Full-Extrinsics+I.png";
        std::string trackingA_path = data_pathes[i] + "/calibDetails/ModelError-trackingA-FISHEYE_4_PARAMETERS-Full-Extrinsics+Intrin.png";
        std::string trackingB_path = data_pathes[i] + "/calibDetails/ModelError-trackingB-FISHEYE_4_PARAMETERS-Full-Extrinsics+Intrin.png";
        cv::Mat ctrl_trackingA = cv::imread(ctrl_trackingA_path);
        cv::Mat ctrl_trackingB = cv::imread(ctrl_trackingB_path);
        cv::Mat trackingA = cv::imread(trackingA_path);
        cv::Mat trackingB = cv::imread(trackingB_path);
        auto data = compute_camera_reproject(ctrl_trackingA);
        std::cout << "ModelError-ctrl-trackingA   error_max=" << data.error_max << std::endl;
        std::cout << "ModelError-ctrl-trackingA  error_mean=" << data.error_mean << std::endl;
        std::cout << "ModelError-ctrl-trackingA   error_std=" << data.error_std << std::endl;

        data = compute_camera_reproject(ctrl_trackingB);
        std::cout << "ModelError-ctrl-trackingB   error_max=" << data.error_max << std::endl;
        std::cout << "ModelError-ctrl-trackingB  error_mean=" << data.error_mean << std::endl;
        std::cout << "ModelError-ctrl-trackingB   error_std=" << data.error_std << std::endl;

        data = compute_camera_reproject(trackingA);
        std::cout << "ModelError-trackingA   error_max=" << data.error_max << std::endl;
        std::cout << "ModelError-trackingA  error_mean=" << data.error_mean << std::endl;
        std::cout << "ModelError-trackingA   error_std=" << data.error_std << std::endl;

        data = compute_camera_reproject(trackingB);
        std::cout << "ModelError-trackingB   error_max=" << data.error_max << std::endl;
        std::cout << "ModelError-trackingB  error_mean=" << data.error_mean << std::endl;
        std::cout << "ModelError-trackingB   error_std=" << data.error_std << std::endl;
    }

    return 0;
}
template <typename T>
double distance(T a, T b)
{
    T d = a - b;
    return norm(d);
}
void compute_circle_center(std::vector<std::vector<cv::Point>> &contours, std::vector<cv::Point2d> &centers, int type = 0)
{
    centers.clear();

    // 计算圆心
    for (auto i = contours.begin(); i != contours.end(); i++)
    {
        cv::Point2d center1, center2, center3;
        std::pair<cv::Point2d, cv::Point2d> max_pair;
        double max_d = 0;

        for (auto j = (*i).begin(); j != (*i).end(); j++)
        {
            double max_r = 0;
            std::pair<cv::Point2d, cv::Point2d> max_pair_tmp;
            for (auto k = (*i).begin(); k != (*i).end(); k++)
            {
                double d = distance((*j), (*k));
                if (d > max_r)
                {
                    max_r = d;
                    max_pair_tmp = std::make_pair((*j), (*k));
                }
            }
            if (max_r > max_d)
            {
                max_pair = max_pair_tmp;
                max_d = max_r;
            }
            center2 = center2 + cv::Point2d((*j));
        }

        center1 = (max_pair.first + max_pair.second) / 2;

        centers.push_back(center1);
    }
}

void merge(std::vector<std::weak_ptr<PointCalibrateBoard>> &board, double min_d)
{
    auto tmp = board;
    for (int i = 0; i < tmp.size(); i++)
    {
        for (int j = i + 1; j < tmp.size(); j++)
        {
            auto pi = tmp[i].lock();
            auto pj = tmp[j].lock();
            if (!pi || !pj)
            {
                std::cout << __FILE__ << ":" << __LINE__ << "merge pi=" << pi << ",pj=" << pj << std::endl;
                exit(-1);
            }
            double d = distance(pi->center_image, pj->center_image);
            if (d < min_d)
            {
                pi->contour.insert(pi->contour.end(), pj->contour.begin(), pj->contour.end());
                cv::RotatedRect minrect = cv::minAreaRect(pi->contour); // 最小外接矩形
                pi->center_image = minrect.center;
                pi->area = minrect.size.area();
                tmp.erase(tmp.begin() + j);
            }
        }
    }
    board = tmp;
}

void merge_contours(std::vector<std::vector<cv::Point>> &contours, std::vector<cv::Point2d> &centers, double min_d)
{
    auto it_contours = contours.begin();
    auto it_centers = centers.begin();
    for (size_t i = 0; i < centers.size(); i++)
    {
        for (size_t j = i + 1; j < centers.size(); j++)
        {
            // RotatedRect minrect = minAreaRect(contours[i]); // 最小外接矩形
            // double ratio = minrect.size.width / minrect.size.height;

            double d = distance(centers[i], centers[j]);
            if (d < min_d)
            {
                contours[i].insert(contours[i].end(), contours[j].begin(), contours[j].end());
                contours.erase(it_contours + j);
                centers.erase(it_centers + j);
                j--;
            }
        }
    }
    centers.clear();
    compute_circle_center(contours, centers);
}
void judgment_centers(std::vector<std::vector<cv::Point>> &contours, std::vector<cv::Point2d> &centers)
{
    auto it = centers.begin();
    for (auto i = contours.begin(); i != contours.end(); i++, it++)
    {
        for (auto j = (*i).begin(); j != (*i).end(); j++)
        {
            double d = distance(cv::Point2d(*j), (*it));
            if (d < 1)
            {
                i = contours.erase(i);
                i--;
                it = centers.erase(it);
                it--;
                break;
            }
        }
    }
}
cv::Mat global_dst;
cv::Mat global_binary_img;
std::vector<std::weak_ptr<PointCalibrateBoard>> DetectBoard::get_contours(cv::Mat binary_img)
{
#ifdef MEASURE_RUNNING_TIME
    // 设置开始时间
    auto start = std::chrono::system_clock::now();
#endif

    cv::Scalar mean_gray = cv::mean(binary_img);

    cv::Canny(binary_img, binary_img, mean_gray[0], mean_gray[0] * 2.0, 3, false);
    std::vector<std::vector<cv::Point>> contours;
    std::vector<double> contours_perimeter;

    std::vector<cv::Vec4i> hierarchy;
    cv::findContours(binary_img, contours, hierarchy, cv::RETR_LIST, cv::CHAIN_APPROX_NONE); // 只找最外层轮廓
    cv::Mat dst;

    cv::cvtColor(binary_img, dst, cv::COLOR_GRAY2BGR);
    global_dst = dst.clone();

    std::vector<cv::Point2d> centers;
    compute_circle_center(contours, centers);

    // judgment_centers(contours,centers);
    cv::Mat show;

    cv::resize(dst, show, dst.size() * show_scale);
    std::vector<std::weak_ptr<PointCalibrateBoard>> boards;
    std::vector<std::weak_ptr<PointCalibrateBoard>> boards_tmp;

    for (int i = 0; i < contours.size(); ++i)
    {

        cv::RotatedRect minrect = cv::minAreaRect(contours[i]); // 最小外接矩形
        double area = minrect.size.area();
        double ratio = minrect.size.width / minrect.size.height;
        std::vector<cv::Point2f> points;
        cv::Point2f vertices[4];
        minrect.points(vertices);

        {
            auto contourPoints = contours[i];
            std::shared_ptr<PointCalibrateBoard> p = std::make_shared<PointCalibrateBoard>();
            p->area = area;
            p->center_image = minrect.center;
            p->contour = contourPoints;
            p->ratio = ratio;
            p->vertices.push_back(vertices[0]);
            p->vertices.push_back(vertices[1]);
            p->vertices.push_back(vertices[2]);
            p->vertices.push_back(vertices[3]);
            boards_tmp.push_back(p);
            m_global_boards_points.push_back(p);
        }
    }
    sort_by_area(boards_tmp);
    auto p_midle = boards_tmp[int(boards_tmp.size() / 2)].lock();
    if (!p_midle)
    {
        std::cout << __FILE__ << ":" << __LINE__ << "get_contours p_midle=" << p_midle << std::endl;
        exit(-1);
    }
    double medle_area = p_midle->area;

    for (int i = 0; i < boards_tmp.size(); ++i)
    {
        auto pi = boards_tmp[i].lock();
        if (!pi)
        {
            std::cout << __FILE__ << ":" << __LINE__ << ",pi" << pi << std::endl;
        }
        double area = pi->area;
        double ratio = pi->ratio;

        if (area > 0.1 * medle_area && area < 25 * medle_area && ratio > 0.2 && ratio < 5.0)
        {

            boards.push_back(boards_tmp[i]);
        }
    }
    merge(boards, 5);
#ifdef SHOW
    for (int i = 0; i < boards.size(); ++i)
    {
        auto pi = boards[i].lock();
        if (!pi)
        {
            std::cout << __FILE__ << ":" << __LINE__ << "get_contours boards pi=" << pi << std::endl;
            exit(-1);
        }
        double area = pi->area;
        double ratio = pi->ratio;

        //  double area_ori = contourArea(boards_tmp[i]->contour);
        // double perimeter_ori = arcLength(boards_tmp[i]->contour, true);
        // double circularity = 4 * CV_PI * area_ori / (perimeter_ori * perimeter_ori);

        // if (area > 0.1 * medle_area && area < 25 * medle_area && ratio > 0.2 && ratio < 5.0)
        {
            auto contourPoints = pi->contour;
            for (int j = 0; j < contourPoints.size(); j++)
            {
                circle(show, contourPoints[j] * show_scale, show_scale, cv::Scalar(0, 0, 255), -1);
            }
            if (show_scale > 6)
            {
                cv::putText(show, std::to_string(area), (pi->center_image) * show_scale, 1, 1, cv::Scalar(0, 255, 0));
                cv::putText(show, std::to_string(ratio), ((pi->center_image) + cv::Point2d(0, 5)) * show_scale, 1, 1, cv::Scalar(0, 255, 255));
            }

            // cv::putText(show, std::to_string(circularity), ((boards_tmp[i]->center_image) + cv::Point2d(0, 10)) * show_scale, 1, 1, cv::Scalar(0, 255, 255));
        }
    }

    cv::imwrite("get_contours.png", show);
    cv::namedWindow("get_contours", cv::WINDOW_NORMAL);
    cv::resizeWindow("get_contours", 640, 480);
    cv::imshow("get_contours", show);
#endif
#ifdef MEASURE_RUNNING_TIME
    // 设置结束时间
    auto end = std::chrono::system_clock::now();

    // 精确到微秒，除此之外，还有五种时间单位：hours, minutes, seconds, milliseconds, nanoseconds
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start);

    // duration.count() 返回统计的时间
    // num 和 den分别表示分子(numerator)和分母(denominator)
    // 在代码中，num等于1， den等于1,000,000
    std::cout << "get_contours duration=" << double(duration.count()) * std::chrono::microseconds::period::num / std::chrono::microseconds::period::den << std::endl;
#endif
    return boards;
}

void filter_boards(std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> &boards)
{
    cv::Mat show = global_dst.clone();

    cv::resize(global_dst, show, global_dst.size() * show_scale);
    int num_rings = 0;

    for (auto it = boards.begin(); it < boards.end(); it++)
    {
        num_rings = 0;
        for (auto itt = (*it).begin(); itt != (*it).end(); itt++)
        {
            auto p = (*itt).lock();
            if (!p)
            {
                std::cout << __FILE__ << ":" << __LINE__ << ",p=" << p << std::endl;
                exit(-1);
            }
            if (p->bRing)
            {
                num_rings++;
            }
        }
        if (num_rings == 0 || (*it).size() < 3)
        {
            it = boards.erase(it);
            it--;
            continue;
        }
        bool bDuplicate = false;

        for (auto itt = (*it).begin(); itt != (*it).end(); itt++)
        {
            auto p = (*itt).lock();
            if (!p)
            {
                std::cout << __FILE__ << ":" << __LINE__ << ",p=" << p << std::endl;
                exit(-1);
            }
            if (p->bBigger)
            {
                itt = (*it).erase(itt);
                itt--;
                bDuplicate = true;
                continue;
            }
            p->bBigger = true;
        }
        if (bDuplicate)
        {
            continue;
        }
        if (num_rings > 2 || num_rings == 0)
        {
            it = boards.erase(it);
            it--;
            continue;
        }

        auto p0 = (*it)[0].lock();
        auto p1 = (*it)[1].lock();
        auto p2 = (*it)[2].lock();
        if (!p0 || !p1 || !p2)
        {
            std::cout << __FILE__ << ":" << __LINE__ << ",p0=" << p0 << ",p1=" << p1 << ",p2=" << p2 << std::endl;
            exit(-1);
        }
        double d0 = distance(p0->center_image, p1->center_image);
        double d1 = distance(p0->center_image, p2->center_image);
        double d2 = distance(p1->center_image, p2->center_image);
        double n0 = d0 / d1;
        double n1 = d0 / d2;
        double n2 = d1 / d2;
        if (p0->ratio < 0.6 || p1->ratio < 0.6 || p2->ratio < 0.6 || n0 > 1.5 || n0 < 0.7 || n1 > 1.5 || n1 < 0.7 || n2 > 1.5 || n2 < 0.7 || d0 > 100 || d1 > 100 || d2 > 100)
        {

            for (auto itt = (*it).begin(); itt != (*it).end(); itt++)
            {
                auto p = (*itt).lock();
                if (!p)
                {
                    std::cout << __FILE__ << ":" << __LINE__ << ",p=" << p << std::endl;
                    exit(-1);
                }
                p->bBigger = false;
            }
            it = boards.erase(it);
            it--;
            continue;
        }
        #ifdef SHOW

        {
            for (auto itt = (*it).begin(); itt != (*it).end(); itt++)
            {
                auto p = (*itt).lock();
                if (!p)
                {
                    std::cout << __FILE__ << ":" << __LINE__ << ",p=" << p << std::endl;
                    exit(-1);
                }
                auto contourPoints = p->contour;
                for (int j = 0; j < contourPoints.size(); j++)
                {
                    circle(show, contourPoints[j] * show_scale, show_scale, cv::Scalar(0, 0, 255), -1);
                }

                if (p->bRing && show_scale > 6)
                {
                    cv::putText(show, "ring", p->center_image * show_scale, 1, 1, cv::Scalar(0, 255, 0));
                }
                else if (show_scale > 6)
                {
                    cv::putText(show, "circle", p->center_image * show_scale, 1, 1, cv::Scalar(0, 255, 0));
                }
               // std::cout << " center points =" << p->center_image << std::endl;
            }
        }
        #endif
    }
    for (auto it = boards.begin(); it < boards.end(); it++)
    {
        if ((*it).size() < 3)
        {
            it = boards.erase(it);
            it--;
            continue;
        }
    }
    if (num_rings == 1 && !boards.empty())
    {
        for (auto it = boards.begin(); it != boards.end(); it++)
        {
            for (auto itt = (*it).begin(); itt != (*it).end(); itt++)
            {
                auto p = (*itt).lock();
                if (p)
                {
                    p->type = TARGET_A;
                }
            }
        }
        // cv::imwrite("boardA.png", show);
    }
    if (num_rings == 2 && !boards.empty())
    {
        for (auto it = boards.begin(); it != boards.end(); it++)
        {
            for (auto itt = (*it).begin(); itt != (*it).end(); itt++)
            {
                auto p = (*itt).lock();
                if (p)
                {
                    p->type = TARGET_B;
                }
            }
        }
        // cv::imwrite("boardB.png", show);
    }
}
std::pair<std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>>, std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>>> get_center_bigger_points(std::vector<std::weak_ptr<PointCalibrateBoard>> &targets)
{
#ifdef MEASURE_RUNNING_TIME
    // 设置开始时间
    auto start = std::chrono::system_clock::now();
#endif
    std::vector<std::weak_ptr<PointCalibrateBoard>> rings;
    std::vector<std::weak_ptr<PointCalibrateBoard>> circles;
    std::vector<std::weak_ptr<PointCalibrateBoard>> biggers;

    sort_by_area(targets);

    auto it_meadle = targets[targets.size() / 2];

    cv::Mat show;
    // cv::cvtColor(global_dst,show,COLOR_GRAY2RGB);

    cv::resize(global_dst, show, global_dst.size() * show_scale);

    int ring_count = 0;
    for (auto it = targets.begin(); it != targets.begin() + targets.size() / 2; it++)
    {
        auto p = (*it).lock();
        if (!p)
        {
            std::cout << __FILE__ << ":" << __LINE__ << ",p=" << p << std::endl;
            exit(-1);
        }
        if (p->vertices[0].x <= 0 || p->vertices[0].y <= 0 || p->vertices[1].x <= 0 || p->vertices[1].y <= 0 || p->vertices[2].x <= 0 || p->vertices[2].y <= 0 || p->vertices[3].x <= 0 || p->vertices[3].y <= 0)
        {
            continue;
        }
        if (p->vertices[0].x >= 640 || p->vertices[0].y >= 480 || p->vertices[1].x >= 640 || p->vertices[1].y >= 480 || p->vertices[2].x >= 640 || p->vertices[2].y >= 480 || p->vertices[3].x >= 640 || p->vertices[3].y >= 480)
        {
            continue;
        }

        int pixel_center = global_binary_img.at<uchar>(int(p->center_image.y), int(p->center_image.x));
        // std::cout << "pixel_center=" << int(pixel_center) << std::endl;
        int pixel_1 = global_binary_img.at<uchar>(int(p->vertices[0].y), int(p->vertices[0].x));
        int pixel_2 = global_binary_img.at<uchar>(int(p->vertices[1].y), int(p->vertices[1].x));
        int pixel_3 = global_binary_img.at<uchar>(int(p->vertices[2].y), int(p->vertices[2].x));
        int pixel_4 = global_binary_img.at<uchar>(int(p->vertices[3].y), int(p->vertices[3].x));

        // std::cout << "pixel_center=" << int(pixel_center) << ",pixel_1=" << pixel_1 << std::endl;

        if (pixel_center < pixel_1 && pixel_center < pixel_2 && pixel_center < pixel_3 && pixel_center < pixel_4)
        {
            p->bRing = false;

            circles.push_back(p);
        }
        else if (pixel_center == pixel_1 || pixel_center == pixel_2 || pixel_center == pixel_3 || pixel_center == pixel_4)
        {
            p->bRing = true;
        }

        if (p->bRing == true)
        {
            rings.push_back(p);
        }
#ifdef SHOW
        if (show_scale > 6)
        {
            if (p->bRing)
            {
                cv::putText(show, "ring", p->center_image * show_scale, 1, 1, cv::Scalar(0, 255, 0));
            }
            else
            {
                cv::putText(show, "circle", p->center_image * show_scale, 1, 1, cv::Scalar(0, 255, 0));
            }
        }
#endif
        biggers.push_back(p);
    }

    if (rings.empty() || circles.empty())
    {
        return std::pair<std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>>, std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>>>();
    }

    for (auto it = biggers.begin(); it != biggers.end(); it++)
    {
        auto p = (*it).lock();
        auto p0 = rings[0].lock();
        if (!p || !p0)
        {
            std::cout << __FILE__ << ":" << __LINE__ << ",p=" << p << ",p0=" << p0 << std::endl;
            exit(-1);
        }
        if (p->area / p0->area < 0.3)
        {
            it = biggers.erase(it);
            it--;
        }
    }
    for (auto it = circles.begin(); it != circles.end(); it++)
    {
        auto p = (*it).lock();
        auto p0 = rings[0].lock();
        if (!p || !p0)
        {
            std::cout << __FILE__ << ":" << __LINE__ << ",p=" << p << ",p0=" << p0 << std::endl;
            exit(-1);
        }
        if (p->area / p0->area < 0.3)
        {
            it = circles.erase(it);
            it--;
        }
#ifdef SHOW
        else
        {
            auto contourPoints = p->contour;
            for (int j = 0; j < contourPoints.size(); j++)
            {
                circle(show, contourPoints[j] * show_scale, show_scale, cv::Scalar(0, 255, 255), -1);
            }

            cv::namedWindow("search bigger points", cv::WINDOW_NORMAL);
            cv::resizeWindow("search bigger points", 640, 480);
            cv::imshow("search bigger points", show);
            std::cout << "circles.size=" << circles.size() << std::endl;
            std::cout << "rings.size=" << rings.size() << std::endl;
        }
#endif
        
    }
    for (auto it = rings.begin(); it != rings.end(); it++)
    {
        auto p = (*it).lock();
        auto p0 = rings[0].lock();
        if (!p || !p0)
        {
            std::cout << __FILE__ << ":" << __LINE__ << ",p=" << p << ",p0=" << p0 << std::endl;
            exit(-1);
        }
        if (p->area / p0->area < 0.3)
        {
            it = rings.erase(it);
            it--;
        }
#ifdef SHOW
        else
        {
            auto contourPoints = p->contour;
            for (int j = 0; j < contourPoints.size(); j++)
            {
                circle(show, contourPoints[j] * show_scale, show_scale, cv::Scalar(0, 0, 255), -1);
            }

            cv::namedWindow("search bigger points", cv::WINDOW_NORMAL);
            cv::resizeWindow("search bigger points", 640, 480);
            cv::imshow("search bigger points", show);
            std::cout << "circles.size=" << circles.size() << std::endl;
            std::cout << "rings.size=" << rings.size() << std::endl;
        }
#endif
        
    }
    std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> boardsA;
    std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> boardsB;
    sort_bigger_by_distance(biggers);
    for (int i = 0; i < biggers.size(); i++)
    {

        auto pi = biggers[i].lock();

        auto near_biggers = pi->bigger_distance_at_image;
        int rings_cont = 0;
        int count = 0;
        std::vector<std::weak_ptr<PointCalibrateBoard>> board;
        board.push_back(pi);
        if (pi->bRing)
        {
            rings_cont++;
        }
        for (auto &it : near_biggers)
        {
            auto pj = it.second.lock();

            if (!pj || !pi)
            {
                std::cout << __FILE__ << ":" << __LINE__ << ",pj=" << pj << ",pi=" << pi << std::endl;
                exit(-1);
            }
            if (pj->area / pi->area > 0.5)
            {
                board.push_back(pj);
            }
            else
            {
                continue;
            }
            if (pj->bRing)
            {
                rings_cont++;
            }
            count++;
            if (count == 2)
            {
                break;
            }
        }
        if (board.size() >= 3)
        {
            if (rings_cont == 1)
            {
                boardsA.push_back(board);
            }
            else if (rings_cont == 2)
            {
                boardsB.push_back(board);
            }
        }
    }

    filter_boards(boardsA);
    filter_boards(boardsB);
#ifdef MEASURE_RUNNING_TIME
    // 设置结束时间
    auto end = std::chrono::system_clock::now();

    // 精确到微秒，除此之外，还有五种时间单位：hours, minutes, seconds, milliseconds, nanoseconds
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start);

    // duration.count() 返回统计的时间
    // num 和 den分别表示分子(numerator)和分母(denominator)
    // 在代码中，num等于1， den等于1,000,000
    std::cout << "get_center_bigger_points duration=" << double(duration.count()) * std::chrono::microseconds::period::num / std::chrono::microseconds::period::den << std::endl;
#endif
    return std::make_pair(boardsA, boardsB);
}
void connect_logic_points(std::weak_ptr<PointCalibrateBoard> wp, cv::Mat show_connections)
{
    std::shared_ptr<PointCalibrateBoard> p = wp.lock();
    std::shared_ptr<PointCalibrateBoard> p_left;
    std::shared_ptr<PointCalibrateBoard> p_right;
    std::shared_ptr<PointCalibrateBoard> p_up;
    std::shared_ptr<PointCalibrateBoard> p_down;

    std::shared_ptr<PointCalibrateBoard> p_left_up;
    std::shared_ptr<PointCalibrateBoard> p_left_down;

    std::shared_ptr<PointCalibrateBoard> p_right_up;
    std::shared_ptr<PointCalibrateBoard> p_right_down;

    std::shared_ptr<PointCalibrateBoard> p_up_left;
    std::shared_ptr<PointCalibrateBoard> p_up_right;

    std::shared_ptr<PointCalibrateBoard> p_down_left;
    std::shared_ptr<PointCalibrateBoard> p_down_right;

    std::shared_ptr<PointCalibrateBoard> p_left_up_right;
    std::shared_ptr<PointCalibrateBoard> p_left_down_right;

    std::shared_ptr<PointCalibrateBoard> p_right_up_left;
    std::shared_ptr<PointCalibrateBoard> p_right_down_left;

    std::shared_ptr<PointCalibrateBoard> p_up_left_down;
    std::shared_ptr<PointCalibrateBoard> p_up_right_down;

    std::shared_ptr<PointCalibrateBoard> p_down_left_up;
    std::shared_ptr<PointCalibrateBoard> p_down_right_up;
    if (p)
    {
        p_left = p->left.lock();
        p_right = p->right.lock();
        p_up = p->up.lock();
        p_down = p->down.lock();
    }
    if (p_left)
    {
        p_left_up = p_left->up.lock();
        p_left_down = p_left->down.lock();
    }
    if (p_right)
    {
        p_right_up = p_right->up.lock();
        p_right_down = p_right->down.lock();
    }
    if (p_up)
    {
        p_up_left = p_up->left.lock();
        p_up_right = p_up->right.lock();
    }
    if (p_down)
    {
        p_down_left = p_down->left.lock();
        p_down_right = p_down->right.lock();
    }
    if (p_left_up)
    {
        p_left_up_right = p_left_up->right.lock();
    }
    if (p_left_down)
    {
        p_left_down_right = p_left_down->right.lock();
    }
    if (p_right_up)
    {
        p_right_up_left = p_right_up->left.lock();
    }
    if (p_right_down)
    {
        p_right_down_left = p_right_down->left.lock();
    }
    if (p_up_left)
    {
        p_up_left_down = p_up_left->down.lock();
    }
    if (p_up_right)
    {
        p_up_right_down = p_up_right->down.lock();
    }
    if (p_down_left)
    {
        p_down_left_up = p_down_left->up.lock();
    }
    if (p_down_right)
    {
        p_down_right_up = p_down_right->up.lock();
    }

    if (p && p_left && !p_left_up && p_up && p_up_left)
    {
        p_left->up = p_up_left;
        p_left_up = p_left->up.lock();
        p_left_up->down = p_left;

        p_left_up->direct_left = p_left->direct_left;
        p_left_up->direct_right = p_left->direct_right;
        assert(norm(p_left->direct_right) < 50);
        p_left_up->direct_up = p_left_up->center_image - p_left->center_image;
        p_left_up->direct_down = -p_left_up->direct_up;

        p_left_up->angle_left = p_left->angle_left;
        p_left_up->angle_right = p_left->angle_right;
        p_left_up->angle_up = p_left->angle_up;
        p_left_up->angle_down = p_left->angle_down;

        p_left_up->scale_left = p_left->scale_left;
        p_left_up->scale_right = p_left->scale_right;
        p_left_up->scale_up = p_left->scale_up;
        p_left_up->scale_down = p_left->scale_down;
#ifdef SHOW
        cv::line(show_connections, p_left->center_image * show_scale, p_left_up->center_image * show_scale,
                 cv::Scalar(0, 0, 255), 2, cv::LINE_AA);
        cv::namedWindow("add connect", cv::WINDOW_NORMAL);
        cv::resizeWindow("add connect", 640, 480);
        cv::imshow("add connect", show_connections);
        std::cout << p << "addition add left up " << p_left_up->center_image << std::endl;
#endif
    }
    if (p && p_right && !p_right_up && p_up && p_up_right)
    {
        p_right->up = p_up_right;
        p_right_up = p_right->up.lock();
        p_right_up->down = p_right;

        p_right_up->direct_left = p_right->direct_left;
        p_right_up->direct_right = p_right->direct_right;
        assert(norm(p_right->direct_right) < 50);
        p_right_up->direct_up = p_right_up->center_image - p_right->center_image;
        p_right_up->direct_down = -p_right_up->direct_up;

        p_right_up->angle_left = p_right->angle_left;
        p_right_up->angle_right = p_right->angle_right;
        p_right_up->angle_up = p_right->angle_up;
        p_right_up->angle_down = p_right->angle_down;

        p_right_up->scale_left = p_right->scale_left;
        p_right_up->scale_right = p_right->scale_right;
        p_right_up->scale_up = p_right->scale_up;
        p_right_up->scale_down = p_right->scale_down;
#ifdef SHOW

        cv::line(show_connections, p_right->center_image * show_scale, p_right_up->center_image * show_scale,
                 cv::Scalar(0, 0, 255), 2, cv::LINE_AA);
        cv::namedWindow("add connect", cv::WINDOW_NORMAL);
        cv::resizeWindow("add connect", 640, 480);
        cv::imshow("add connect", show_connections);
        std::cout << p << "addition add right up " << p_right_up->center_image << std::endl;
#endif
    }
    if (p && p_left && !p_left_down && p_down && p_down_left)
    {
        p_left->down = p_down_left;
        p_left_down = p_left->down.lock();
        p_left_down->up = p_left;

        p_left_down->direct_left = p_left->direct_left;
        p_left_down->direct_right = p_left->direct_right;

        p_left_down->direct_down = p_left_down->center_image - p_left->center_image;
        p_left_down->direct_up = -p_left_down->direct_down;

        p_left_down->angle_left = p_left->angle_left;
        p_left_down->angle_right = p_left->angle_right;
        p_left_down->angle_up = p_left->angle_up;
        p_left_down->angle_down = p_left->angle_down;

        p_left_down->scale_left = p_left->scale_left;
        p_left_down->scale_right = p_left->scale_right;
        p_left_down->scale_up = p_left->scale_up;
        p_left_down->scale_down = p_left->scale_down;
#ifdef SHOW

        cv::line(show_connections, p_left->center_image * show_scale, p_left_down->center_image * show_scale,
                 cv::Scalar(0, 0, 255), 2, cv::LINE_AA);
        cv::namedWindow("add connect", cv::WINDOW_NORMAL);
        cv::resizeWindow("add connect", 640, 480);
        cv::imshow("add connect", show_connections);
        std::cout << p << "addition add left down " << p_left_down->center_image << std::endl;
#endif
    }
    if (p && p_right && !p_right_down && p_down && p_down_right)
    {
        p_right->down = p_down_right;
        p_right_down = p_right->down.lock();
        p_right_down->up = p_right;

        p_right_down->direct_left = p_right->direct_left;
        p_right_down->direct_right = p_right->direct_right;
        p_right_down->direct_down = p_right_down->center_image - p_right->center_image;
        p_right_down->direct_up = -p_right_down->direct_down;

        p_right_down->angle_left = p_right->angle_left;
        p_right_down->angle_right = p_right->angle_right;
        p_right_down->angle_up = p_right->angle_up;
        p_right_down->angle_down = p_right->angle_down;

        p_right_down->scale_left = p_right->scale_left;
        p_right_down->scale_right = p_right->scale_right;
        p_right_down->scale_up = p_right->scale_up;
        p_right_down->scale_down = p_right->scale_down;
#ifdef SHOW

        cv::line(show_connections, p_right->center_image * show_scale, p_right_down->center_image * show_scale,
                 cv::Scalar(0, 0, 255), 2, cv::LINE_AA);
        cv::namedWindow("add connect", cv::WINDOW_NORMAL);
        cv::resizeWindow("add connect", 640, 480);
        cv::imshow("add connect", show_connections);
        std::cout << p << "addition add right down " << p_right_down->center_image << std::endl;
#endif
    }
    if (p && p_down && !p_down_left && p_left && p_left_down)
    {
        p_down->left = p_left_down;
        p_down_left = p_down->left.lock();
        p_down_left->right = p_down;

        p_down_left->direct_left = p_down_left->center_image - p_down->center_image;
        p_down_left->direct_right = -p_down_left->direct_left;
        assert(norm(p_down_left->direct_right) < 50);
        p_down_left->direct_up = p_down->direct_up;
        p_down_left->direct_down = p_down->direct_down;

        p_down_left->angle_left = p_down->angle_left;
        p_down_left->angle_right = p_down->angle_right;
        p_down_left->angle_up = p_down->angle_up;
        p_down_left->angle_down = p_down->angle_down;

        p_down_left->scale_left = p_down->scale_left;
        p_down_left->scale_right = p_down->scale_right;
        p_down_left->scale_up = p_down->scale_up;
        p_down_left->scale_down = p_down->scale_down;
#ifdef SHOW

        cv::line(show_connections, p_down->center_image * show_scale, p_down_left->center_image * show_scale,
                 cv::Scalar(0, 0, 255), 2, cv::LINE_AA);
        cv::namedWindow("add connect", cv::WINDOW_NORMAL);
        cv::resizeWindow("add connect", 640, 480);
        cv::imshow("add connect", show_connections);
        std::cout << "addition add down left " << p_down_left->center_image << std::endl;
#endif
    }
    if (p && p_down && !p_down_right && p_right && p_right_down)
    {
        p_down->right = p_right_down;
        p_down_right = p_down->right.lock();
        p_down_right->left = p_down;

        p_down_right->direct_right = p_down_right->center_image - p_down->center_image;
        assert(norm(p_down_right->direct_right) < 50);
        p_down_right->direct_left = -p_down_right->direct_right;
        p_down_right->direct_up = p_down->direct_up;
        p_down_right->direct_down = p_down->direct_down;

        p_down_right->angle_left = p_down->angle_left;
        p_down_right->angle_right = p_down->angle_right;
        p_down_right->angle_up = p_down->angle_up;
        p_down_right->angle_down = p_down->angle_down;

        p_down_right->scale_left = p_down->scale_left;
        p_down_right->scale_right = p_down->scale_right;
        p_down_right->scale_up = p_down->scale_up;
        p_down_right->scale_down = p_down->scale_down;

#ifdef SHOW

        cv::line(show_connections, p_down->center_image * show_scale, p_down_right->center_image * show_scale,
                 cv::Scalar(0, 0, 255), 2, cv::LINE_AA);
        cv::namedWindow("add connect", cv::WINDOW_NORMAL);
        cv::resizeWindow("add connect", 640, 480);
        cv::imshow("add connect", show_connections);
        std::cout << p << "addition add down right " << p_down_right->center_image << std::endl;
#endif
    }
    if (p && p_up && !p_up_left && p_left && p_left_up)
    {
        p_up->left = p_left_up;
        p_up_left = p_up->left.lock();
        p_up_left->right = p_up;
        p_up_left->angle_left = p_up->angle_left;

        p_up_left->direct_left = p_up_left->center_image - p_up->center_image;
        p_up_left->direct_right = -p_up_left->direct_left;
        assert(norm(p_up_left->direct_right) < 50);
        p_up_left->direct_up = p_up->direct_up;
        p_up_left->direct_down = p_up->direct_down;

        p_up_left->angle_left = p_up->angle_left;
        p_up_left->angle_right = p_up->angle_right;
        p_up_left->angle_up = p_up->angle_up;
        p_up_left->angle_down = p_up->angle_down;

        p_up_left->scale_left = p_up->scale_left;
        p_up_left->scale_right = p_up->scale_right;
        p_up_left->scale_up = p_up->scale_up;
        p_up_left->scale_down = p_up->scale_down;

#ifdef SHOW

        cv::line(show_connections, p_up->center_image * show_scale, p_up_left->center_image * show_scale,
                 cv::Scalar(0, 0, 255), 2, cv::LINE_AA);
        cv::namedWindow("add connect", cv::WINDOW_NORMAL);
        cv::resizeWindow("add connect", 640, 480);
        cv::imshow("add connect", show_connections);
        std::cout << p << "addition add up left " << p_up_left->center_image << std::endl;
#endif
    }
    if (p && p_up && !p_up_right && p_right && p_right_up)
    {
        p_up->right = p_right_up;
        p_up_right = p_up->right.lock();
        p_up_right->left = p_up;

        p_up_right->direct_right = p_up_right->center_image - p_up->center_image;
        assert(norm(p_up_right->direct_right) < 50);
        p_up_right->direct_left = -p_up_right->direct_right;
        p_up_right->direct_up = p_up->direct_up;
        p_up_right->direct_down = p_up->direct_down;

        p_up_right->angle_left = p_up->angle_left;
        p_up_right->angle_right = p_up->angle_right;
        p_up_right->angle_up = p_up->angle_up;
        p_up_right->angle_down = p_up->angle_down;

        p_up_right->scale_left = p_up->scale_left;
        p_up_right->scale_right = p_up->scale_right;
        p_up_right->scale_up = p_up->scale_up;
        p_up_right->scale_down = p_up->scale_down;

#ifdef SHOW

        cv::line(show_connections, p_up->center_image * show_scale, p_up_right->center_image * show_scale,
                 cv::Scalar(0, 0, 255), 2, cv::LINE_AA);
        cv::namedWindow("add connect", cv::WINDOW_NORMAL);
        cv::resizeWindow("add connect", 640, 480);
        cv::imshow("add connect", show_connections);
        std::cout << p << "addition add up right " << p_up->center_image << std::endl;
#endif
    }

    if (p && !p_up && p_left && p_left_up && p_left_up_right)
    {
        p->up = p_left_up_right;
        p_up = p->up.lock();
        p_up->down = p;

        p_up->direct_left = p->direct_left;
        p_up->direct_right = p->direct_right;
        p_up->direct_up = p_up->center_image - p->center_image;
        p_up->direct_down = -p_up->direct_up;

        p_up->angle_left = p->angle_left;
        p_up->angle_right = p->angle_right;
        p_up->angle_up = p->angle_up;
        p_up->angle_down = p->angle_down;

        p_up->scale_left = p->scale_left;
        p_up->scale_right = p->scale_right;
        p_up->scale_up = p->scale_up;
        p_up->scale_down = p->scale_down;

#ifdef SHOW

        cv::line(show_connections, p_up->center_image * show_scale, p->center_image * show_scale,
                 cv::Scalar(0, 0, 255), 2, cv::LINE_AA);
        cv::namedWindow("add connect", cv::WINDOW_NORMAL);
        cv::resizeWindow("add connect", 640, 480);
        cv::imshow("add connect", show_connections);
        std::cout << p << "addition add up  " << p_up->center_image << std::endl;
#endif
    }
    if (p && !p_up && p_right && p_right_up && p_right_up_left)
    {
        p->up = p_right_up_left;
        p_up = p->up.lock();
        p_up->down = p;

        p_up->direct_left = p->direct_left;
        p_up->direct_right = p->direct_right;
        p_up->direct_up = p_up->center_image - p->center_image;
        p_up->direct_down = -p_up->direct_up;

        p_up->angle_left = p->angle_left;
        p_up->angle_right = p->angle_right;
        p_up->angle_up = p->angle_up;
        p_up->angle_down = p->angle_down;

        p_up->scale_left = p->scale_left;
        p_up->scale_right = p->scale_right;
        p_up->scale_up = p->scale_up;
        p_up->scale_down = p->scale_down;

#ifdef SHOW

        cv::line(show_connections, p_up->center_image * show_scale, p->center_image * show_scale,
                 cv::Scalar(0, 0, 255), 2, cv::LINE_AA);
        cv::namedWindow("add connect", cv::WINDOW_NORMAL);
        cv::resizeWindow("add connect", 640, 480);
        cv::imshow("add connect", show_connections);
        std::cout << p << "addition add up  " << p_up->center_image << std::endl;
#endif
    }

    if (p && !p_down && p_right && p_right_down && p_right_down_left)
    {
        p->down = p_right_down_left;
        p_down = p->down.lock();
        p_down->up = p;

        p_down->direct_left = p->direct_left;
        p_down->direct_right = p->direct_right;

        p_down->direct_down = p_down->center_image - p->center_image;
        p_down->direct_up = -p_down->direct_down;

        p_down->angle_left = p->angle_left;
        p_down->angle_right = p->angle_right;
        p_down->angle_up = p->angle_up;
        p_down->angle_down = p->angle_down;

        p_down->scale_left = p->scale_left;
        p_down->scale_right = p->scale_right;
        p_down->scale_up = p->scale_up;
        p_down->scale_down = p->scale_down;

#ifdef SHOW

        cv::line(show_connections, p_down->center_image * show_scale, p->center_image * show_scale,
                 cv::Scalar(0, 0, 255), 2, cv::LINE_AA);
        cv::namedWindow("add connect", cv::WINDOW_NORMAL);
        cv::resizeWindow("add connect", 640, 480);
        cv::imshow("add connect", show_connections);
        std::cout << p << "addition add down " << p_down->center_image << std::endl;
#endif
    }

    if (p && !p_down && p_left && p_left_down && p_left_down_right)
    {
        p->down = p_left_down_right;
        p_down = p->down.lock();
        p_down->up = p;

        p_down->direct_left = p->direct_left;
        p_down->direct_right = p->direct_right;
        p_down->direct_down = p_down->center_image - p->center_image;
        p_down->direct_up = -p_down->direct_down;

        p_down->angle_left = p->angle_left;
        p_down->angle_right = p->angle_right;
        p_down->angle_up = p->angle_up;
        p_down->angle_down = p->angle_down;

        p_down->scale_left = p->scale_left;
        p_down->scale_right = p->scale_right;
        p_down->scale_up = p->scale_up;
        p_down->scale_down = p->scale_down;

#ifdef SHOW

        cv::line(show_connections, p_down->center_image * show_scale, p->center_image * show_scale,
                 cv::Scalar(0, 0, 255), 2, cv::LINE_AA);
        cv::namedWindow("add connect", cv::WINDOW_NORMAL);
        cv::resizeWindow("add connect", 640, 480);
        cv::imshow("add connect", show_connections);
        std::cout << p << "addition add down " << p_down->center_image << std::endl;
#endif
    }

    if (p && !p_left && p_up && p_up_left && p_up_left_down)
    {
        p->left = p_up_left_down;
        p_left = p->left.lock();
        p_left->right = p;
        p_left->angle_left = p_up_left_down->angle_left;

        p_left->direct_left = p_left->center_image - p->center_image;
        p_left->direct_right = -p_left->direct_left;
        assert(norm(p_left->direct_right) < 50);
        p_left->direct_up = p->direct_up;
        p_left->direct_down = p->direct_down;

        p_left->angle_left = p->angle_left;
        p_left->angle_right = p->angle_right;
        p_left->angle_up = p->angle_up;
        p_left->angle_down = p->angle_down;

        p_left->scale_left = p->scale_left;
        p_left->scale_right = p->scale_right;
        p_left->scale_up = p->scale_up;
        p_left->scale_down = p->scale_down;

#ifdef SHOW

        cv::line(show_connections, p_left->center_image * show_scale, p->center_image * show_scale,
                 cv::Scalar(0, 0, 255), 2, cv::LINE_AA);
        cv::namedWindow("add connect", cv::WINDOW_NORMAL);
        cv::resizeWindow("add connect", 640, 480);
        cv::imshow("add connect", show_connections);
        std::cout << p << "addition add left " << p_left->center_image << std::endl;
#endif
    }
    if (p && !p_left && p_down && p_down_left && p_down_left_up)
    {
        p->left = p_down_left->up;
        p_left = p->left.lock();
        p_left->right = p;
        p_left->angle_left = p_down_left_up->angle_left;

        p_left->direct_left = p_left->center_image - p->center_image;
        p_left->direct_right = -p_left->direct_left;
        assert(norm(p_left->direct_right) < 50);
        p_left->direct_up = p->direct_up;
        p_left->direct_down = p->direct_down;

        p_left->angle_left = p->angle_left;
        p_left->angle_right = p->angle_right;
        p_left->angle_up = p->angle_up;
        p_left->angle_down = p->angle_down;

        p_left->scale_left = p->scale_left;
        p_left->scale_right = p->scale_right;
        p_left->scale_up = p->scale_up;
        p_left->scale_down = p->scale_down;

#ifdef SHOW

        cv::line(show_connections, p_left->center_image * show_scale, p->center_image * show_scale,
                 cv::Scalar(0, 0, 255), 2, cv::LINE_AA);
        cv::namedWindow("add connect", cv::WINDOW_NORMAL);
        cv::resizeWindow("add connect", 640, 480);
        cv::imshow("add connect", show_connections);
        std::cout << p << "addition add left " << p_left->center_image << std::endl;
#endif
    }

    if (p && !p_right && p_down && p_down_right && p_down_right_up)
    {
        p->right = p_down_right_up;
        p_right = p->right.lock();
        p_right->left = p;

        p_right->direct_right = p_right->center_image - p->center_image;
        p_right->direct_left = -p_right->direct_right;
        assert(norm(p_right->direct_right) < 50);
        p_right->direct_up = p->direct_up;
        p_right->direct_down = p->direct_down;

        p_right->angle_left = p->angle_left;
        p_right->angle_right = p->angle_right;
        p_right->angle_up = p->angle_up;
        p_right->angle_down = p->angle_down;

        p_right->scale_left = p->scale_left;
        p_right->scale_right = p->scale_right;
        p_right->scale_up = p->scale_up;
        p_right->scale_down = p->scale_down;

#ifdef SHOW

        cv::line(show_connections, p_right->center_image * show_scale, p->center_image * show_scale,
                 cv::Scalar(0, 0, 255), 2, cv::LINE_AA);
        cv::namedWindow("add connect", cv::WINDOW_NORMAL);
        cv::resizeWindow("add connect", 640, 480);
        cv::imshow("add connect", show_connections);
        std::cout << p << "addition add right " << p_right->center_image << std::endl;
#endif
    }
    if (p && !p_right && p_up && p_up_right && p_up_right_down)
    {
        p->right = p_up_right_down;
        p_right = p->right.lock();
        p_right->left = p;

        p_right->direct_right = p_right->center_image - p->center_image;
        assert(norm(p_right->direct_right) < 50);
        p_right->direct_left = -p_right->direct_right;
        p_right->direct_up = p->direct_up;
        p_right->direct_down = p->direct_down;

        p_right->angle_left = p->angle_left;
        p_right->angle_right = p->angle_right;
        p_right->angle_up = p->angle_up;
        p_right->angle_down = p->angle_down;

        p_right->scale_left = p->scale_left;
        p_right->scale_right = p->scale_right;
        p_right->scale_up = p->scale_up;
        p_right->scale_down = p->scale_down;

#ifdef SHOW

        cv::line(show_connections, p_right->center_image * show_scale, p->center_image * show_scale,
                 cv::Scalar(0, 0, 255), 2, cv::LINE_AA);
        cv::namedWindow("add connect", cv::WINDOW_NORMAL);
        cv::resizeWindow("add connect", 640, 480);
        cv::imshow("add connect", show_connections);
        std::cout << p << "addition add right " << p_right->center_image << std::endl;
#endif
    }

    if (p_left)
    {
        p->left = p_left;
    }
    if (p_right)
    {
        p->right = p_right;
    }
    if (p_up)
    {
        p->up = p_up;
    }
    if (p_down)
    {
        p->down = p_down;
    }
    if (p_left_up)
    {
        p_left->up = p_left_up;
    }
    if (p_left_down)
    {
        p_left->down = p_left_down;
    }
    if (p_right_up)
    {
        p_right->up = p_right_up;
    }
    if (p_right_down)
    {
        p_right->down = p_right_down;
    }
    if (p_up_left)
    {
        p_up->left = p_up_left;
    }
    if (p_up_right)
    {
        p_up->right = p_up_right;
    }
    if (p_down_left)
    {
        p_down->left = p_down_left;
    }
    if (p_down_right)
    {
        p_down->right = p_down_right;
    }
}
cv::Point2d rotate_vector(cv::Point2d P, double theta)
{
    cv::Point2d Q;
    Q.x = (P.x) * cos(theta) - (P.y) * sin(theta);

    Q.y = (P.x) * sin(theta) + (P.y) * cos(theta);
    return Q;
}

void add_a_point_connections(std::weak_ptr<PointCalibrateBoard> wp, std::vector<std::weak_ptr<PointCalibrateBoard>> &board_points, std::vector<std::weak_ptr<PointCalibrateBoard>> &target_points)
{
    auto p = wp.lock();
    if (!p)
    {
        std::cout << __FILE__ << ":" << __LINE__ << ",p=" << p << std::endl;
        exit(-1);
    }
    target_points.push_back(p);
    auto start_p = p;
    cv::Mat show_connections = global_dst;

    cv::resize(show_connections, show_connections, show_connections.size() * show_scale);

    std::vector<std::weak_ptr<PointCalibrateBoard>> connected_points;
    // connected_points.push_back(p);
    std::shared_ptr<PointCalibrateBoard> p_last;
    while (true)
    {

        for (auto it = connected_points.begin(); it != connected_points.end(); it++)
        {
            int connected_num = 0;
            auto pi = (*it).lock();
            if (!pi)
            {
                std::cout << __FILE__ << ":" << __LINE__ << ",pi=" << pi << std::endl;
                exit(-1);
            }
            if (!pi->bComplete)
            {
                connect_logic_points(pi, show_connections);
                auto p_left = pi->left.lock();
                auto p_right = pi->right.lock();
                auto p_up = pi->up.lock();
                auto p_down = pi->down.lock();
                if (p_left)
                {
                    connected_num++;
                }
                if (p_right)
                {
                    connected_num++;
                }
                if (p_up)
                {
                    connected_num++;
                }
                if (p_down)
                {
                    connected_num++;
                }

                if (connected_num == 4 || pi->times > 0)
                {
                    pi->bComplete = true;
                    continue;
                }
                if (!p_left || !p_right || !p_up || !p_down)
                {

                    pi->times++;
                    p = (*it).lock();
                    break;
                }
            }
        }
       // std::cout << "p=" << p << " " << p->center_image << ",connected_points.size()=" << connected_points.size() << ",times=" << p->times << std::endl;
        if (p_last == p)
        {
            break;
        }
        else
        {
            p_last = p;
        }

        auto point = p->distance_at_image;
        int count = 0;

        for (const auto &it : point)
        {
            auto pi = it.second.lock();
            if (!pi)
            {
                std::cout << __FILE__ << ":" << __LINE__ << ",pi=" << pi << std::endl;
                exit(-1);
            }
            if (count == 4)
            {
                break;
            }
            count++;
            cv::Point2d direct = pi->center_image - p->center_image;
            #ifdef SHOW
            auto contourPoints = pi->contour;


            for (int j = 0; j < contourPoints.size(); j++)
            {
                circle(show_connections, contourPoints[j] * show_scale, 1, cv::Scalar(0, 0, 255), -1);
            }
            #endif

            double d1 = angle(direct, p->direct_left);
            double d2 = angle(direct, p->direct_right);
            double d3 = angle(direct, p->direct_up);
            double d4 = angle(direct, p->direct_down);
           // std::cout << "d1=" << d1 << ",d2=" << d2 << ",d3=" << d3 << ",d4=" << d4 << std::endl;
            if (std::isnan(d1) || std::isnan(d2) || std::isnan(d3) || std::isnan(d4))
            {
                continue;
            }

            double d = std::min(std::min(std::abs(d1), std::abs(d2)), std::min(std::abs(d3), std::abs(d4)));
            if (d > 10)
            {
                continue;
            }
            int bAdded = false;
            #ifdef SHOW
            contourPoints = p->contour;

            for (int j = 0; j < contourPoints.size(); j++)
            {
                circle(show_connections, contourPoints[j] * show_scale, 1, cv::Scalar(0, 255, 255), -1);
            }
            #endif

            if (p->col < p->cols)
            {

                double n1 = norm(direct);
                double n2 = norm(p->direct_left);
                double n = n1 / n2;

               // std::cout << "n1=" << n1 << ",n2=" << n2 << ",n=" << n << std::endl;

                if (std::abs(d1) == d && (n > 0.6 && n < 1.4) && std::abs(p->scale_left - n) < 0.2)
                {

                   // std::cout << "d left=" << d1 << ",p->angle_left=" << p->angle_left << std::endl;

                    p->left = pi;
                    auto p_left = p->left.lock();
                    p_left->col = p->col + 1;
                    p_left->row = p->row;
                    pi->right = p;
                    pi->direct_left = direct;
                    pi->direct_right = -direct;
                    pi->direct_up = p->direct_up;
                    pi->direct_down = p->direct_down;

                    p->direct_left = pi->direct_left;
                    p->direct_right = pi->direct_right;
                    pi->bConnected = true;
                    pi->type = p->type;
                    target_points.push_back(pi);

                    pi->angle_left = d1;
                    pi->angle_right = p->angle_right;
                    pi->angle_up = p->angle_up;
                    pi->angle_down = p->angle_down;

                    pi->scale_left = n;
                    pi->scale_right = p->scale_right;
                    pi->scale_up = p->scale_up;
                    pi->scale_down = p->scale_down;
#ifdef SHOW
                    cv::line(show_connections, p->center_image * show_scale, pi->center_image * show_scale,
                             cv::Scalar(0, 0, 255), 2, cv::LINE_AA);
                    if (show_scale > 6)
                    {
                        cv::putText(show_connections, "(" + std::to_string(pi->col) + "," + std::to_string(pi->row) + ")", (pi->center_image) * show_scale, 1, 1, cv::Scalar(0, 255, 0));
                    }
                    //  cv::putText(show_connections, std::to_string(d1), (p->center_image+ pi->center_image)/2, 1, 1, cv::Scalar(0, 255, 0));

                    cv::namedWindow("add connect", cv::WINDOW_NORMAL);
                    cv::resizeWindow("add connect", 640, 480);
                    cv::imshow("add connect", show_connections);
                    std::cout << p << "add left " << pi->center_image << std::endl;
#endif
                    connected_points.push_back(pi);
                    bAdded = true;
                    //

                    // add_a_point_connections(pi, board_points);
                    // continue;
                }
            }
            if (p->col > 0)
            {

                double n1 = norm(direct);
                double n2 = norm(p->direct_right);
                double n = n1 / n2;

                if (std::abs(d2) == d && (n > 0.6 && n < 1.4) && std::abs(p->scale_right - n) < 0.2)
                {
                   // std::cout << "d right=" << d2 << std::endl;
                    p->right = pi;
                    auto p_right = p->right.lock();
                    p_right->col = p->col - 1;
                    p_right->row = p->row;
                    pi->left = p;
                    pi->direct_left = -direct;
                    pi->direct_right = direct;
                    pi->direct_up = p->direct_up;
                    pi->direct_down = p->direct_down;

                    p->direct_left = pi->direct_left;
                    p->direct_right = pi->direct_right;

                    pi->bConnected = true;
                    pi->type = p->type;
                    target_points.push_back(pi);

                    pi->angle_left = p->angle_left;
                    pi->angle_right = d2;
                    pi->angle_up = p->angle_up;
                    pi->angle_down = p->angle_down;

                    pi->scale_left = p->scale_left;
                    pi->scale_right = n;
                    pi->scale_up = p->scale_up;
                    pi->scale_down = p->scale_down;

#ifdef SHOW

                    cv::line(show_connections, p->center_image * show_scale, pi->center_image * show_scale,
                             cv::Scalar(0, 0, 255), 2, cv::LINE_AA);
                    if (show_scale > 6)
                    {
                        cv::putText(show_connections, "(" + std::to_string(pi->col) + "," + std::to_string(pi->row) + ")", (pi->center_image) * show_scale, 1, 1, cv::Scalar(0, 255, 0));
                    }
                    cv::namedWindow("add connect", cv::WINDOW_NORMAL);
                    cv::resizeWindow("add connect", 640, 480);
                    cv::imshow("add connect", show_connections);
                    std::cout << p << "add right " << pi->center_image << std::endl;
#endif
                    connected_points.push_back(pi);
                    bAdded = true;

                    // add_a_point_connections(pi, board_points);
                    // continue;
                }
            }
            if (p->row < p->rows)
            {

                double n1 = norm(direct);
                double n2 = norm(p->direct_up);
                double n = n1 / n2;

                if (std::abs(d3) == d && (n > 0.6 && n < 1.4) && std::abs(p->scale_up - n) < 0.2)
                {
                    //std::cout << "d up=" << d3 << std::endl;
                    p->up = pi;
                    auto p_up = p->up.lock();

                    p_up->col = p->col;
                    p_up->row = p->row + 1;
                    pi->down = p;
                    pi->direct_down = -direct;
                    pi->direct_up = direct;
                    pi->direct_left = p->direct_left;
                    pi->direct_right = p->direct_right;

                    p->direct_up = pi->direct_up;
                    p->direct_down = pi->direct_down;

                    pi->bConnected = true;
                    pi->type = p->type;
                    target_points.push_back(pi);

                    pi->angle_left = p->angle_left;
                    pi->angle_right = p->angle_right;
                    pi->angle_up = d3;
                    pi->angle_down = p->angle_down;

                    pi->scale_left = p->scale_left;
                    pi->scale_right = p->scale_right;
                    pi->scale_up = n;
                    pi->scale_down = p->scale_down;

#ifdef SHOW

                    cv::line(show_connections, p->center_image * show_scale, pi->center_image * show_scale,
                             cv::Scalar(0, 0, 255), 2, cv::LINE_AA);
                    if (show_scale > 6)
                    {
                        cv::putText(show_connections, "(" + std::to_string(pi->col) + "," + std::to_string(pi->row) + ")", (pi->center_image) * show_scale, 1, 1, cv::Scalar(0, 255, 0));
                    }
                    cv::namedWindow("add connect", cv::WINDOW_NORMAL);
                    cv::resizeWindow("add connect", 640, 480);
                    cv::imshow("add connect", show_connections);

                    std::cout << p << "add up " << pi->center_image << std::endl;
#endif
                    connected_points.push_back(pi);
                    bAdded = true;

                    // add_a_point_connections(pi, board_points);
                    // continue;
                }
            }
            if (p->row > 0)
            {

                double n1 = norm(direct);
                double n2 = norm(p->direct_down);
                double n = n1 / n2;

                if (std::abs(d4) == d && (n > 0.6 && n < 1.4) && std::abs(p->scale_down - n) < 0.2)
                {
                    //std::cout << "d down=" << d4 << std::endl;
                    p->down = pi;
                    auto p_down = p->down.lock();
                    p_down->col = p->col;
                    p_down->row = p->row - 1;
                    pi->up = p;

                    pi->direct_down = direct;
                    pi->direct_up = -direct;
                    pi->direct_left = p->direct_left;
                    pi->direct_right = p->direct_right;
                    p->direct_up = pi->direct_up;
                    p->direct_down = pi->direct_down;
                    pi->bConnected = true;
                    pi->type = p->type;
                    target_points.push_back(pi);

                    pi->angle_left = p->angle_left;
                    pi->angle_right = p->angle_right;
                    pi->angle_up = p->angle_up;
                    pi->angle_down = d4;

                    pi->scale_left = p->scale_left;
                    pi->scale_right = p->scale_right;
                    pi->scale_up = p->scale_up;
                    pi->scale_down = n;
#ifdef SHOW

                    cv::line(show_connections, p->center_image * show_scale, pi->center_image * show_scale,
                             cv::Scalar(0, 0, 255), 2, cv::LINE_AA);
                    if (show_scale > 6)
                    {
                        cv::putText(show_connections, "(" + std::to_string(pi->col) + "," + std::to_string(pi->row) + ")", (pi->center_image) * show_scale, 1, 1, cv::Scalar(0, 255, 0));
                    }
                    cv::namedWindow("add connect", cv::WINDOW_NORMAL);
                    cv::resizeWindow("add connect", 640, 480);
                    cv::imshow("add connect", show_connections);
                    std::cout << p << "add down " << pi->center_image << std::endl;
#endif
                    connected_points.push_back(pi);
                    bAdded = true;

                    // add_a_point_connections(pi, board_points);
                    // continue;
                }
            }
#ifdef SHOW

            for (int j = 0; j < contourPoints.size(); j++)
            {
                circle(show_connections, contourPoints[j] * show_scale, 1, cv::Scalar(0, 0, 255), -1);
            }
            cv::waitKey(1);
#endif
        }
    }

    for (int i = 0; i < board_points.size(); i++)
    {
        auto p = board_points[i];
        connect_logic_points(p, show_connections);
    }
    // cv::imwrite("connect.jpg", show_connections);
    // cv::waitKey(1);
}

void add_connections(std::vector<std::weak_ptr<PointCalibrateBoard>> sigle_bigger_points, std::vector<std::weak_ptr<PointCalibrateBoard>> &board_points, std::vector<std::weak_ptr<PointCalibrateBoard>> &target_points)
{
    if (sigle_bigger_points.empty())
    {
        return;
    }
    auto p0 = sigle_bigger_points[0].lock();
    std::string type = p0->type;
    std::shared_ptr<PointCalibrateBoard> gravity_point[2];
    std::shared_ptr<PointCalibrateBoard> direct_point;
    if (type == TARGET_B)
    {

        int index = 0;

        for (auto it = sigle_bigger_points.begin(); it != sigle_bigger_points.end(); it++)
        {
            auto p = (*it).lock();
            if (p->bRing)
            {
                gravity_point[index] = p;
                index++;
            }
            else
            {
                direct_point = p;
            }
        }
    }
    else
    {
        int index = 0;

        for (auto it = sigle_bigger_points.begin(); it != sigle_bigger_points.end(); it++)
        {
            auto p = (*it).lock();
            if (!p->bRing)
            {
                gravity_point[index] = p;
                index++;
            }
            else
            {
                direct_point = p;
            }
        }
    }
    if (!gravity_point[0] || !gravity_point[1] || !direct_point)
    {
        return;
    }

    // 计算坐标系方向，右手坐标系
    cv::Point2d direct_x_2d = direct_point->center_image - (gravity_point[0]->center_image + gravity_point[1]->center_image) / 2;
    cv::Point2d direct_y_2d = gravity_point[0]->center_image - gravity_point[1]->center_image;
    cv::Point3d direct_x_3d = cv::Point3d(direct_x_2d.x, direct_x_2d.y, 0) / norm(direct_x_2d);
    cv::Point3d direct_y_3d = cv::Point3d(direct_y_2d.x, direct_y_2d.y, 0) / norm(direct_y_2d);
    cv::Point3d direct_z_3d = cv::Point3d(0, 0, 1);
    cv::Point3d direct_z_3d_cross = direct_x_3d.cross(direct_y_3d);

    double d = direct_z_3d.dot(direct_z_3d_cross);
   // /std::cout << "direct_x_2d=" << direct_x_2d << std::endl;
   // std::cout << "direct_y_2d=" << direct_y_2d << std::endl;
    //std::cout << "direct_z_3d_cross=" << direct_z_3d_cross << std::endl;
    //std::cout << "d=" << d << std::endl;
    if (d < 0)
    {
        direct_y_2d = -direct_y_2d;
    }

    direct_point->direct_down = -direct_y_2d / 2;
    direct_point->direct_up = direct_y_2d / 2;
    direct_point->direct_left = direct_x_2d / 2;
    direct_point->direct_right = -direct_x_2d / 2;
    direct_point->bConnected = true;
    direct_point->col = 13;
    direct_point->row = 24;
    direct_point->bCenter = true;
    merge(board_points, 5);

    add_a_point_connections(direct_point, board_points, target_points);
}
bool get_target_points(std::pair<std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>>, std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>>> boards, std::vector<std::weak_ptr<PointCalibrateBoard>> boards_points, std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> &target_a, std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> &target_b)
{

    if (boards.first.empty() && boards.second.empty())
    {
        return false;
    }
    #ifdef MEASURE_RUNNING_TIME
    // 设置开始时间
    auto start = std::chrono::system_clock::now();

    #endif
    cv::Mat show_connections = global_dst.clone();
    cv::resize(show_connections, show_connections, show_connections.size() * show_scale);

    target_a.resize(boards.first.size());
    target_b.resize(boards.second.size());

    std::vector<cv::Point2d> a_center_point(target_a.size());
    std::vector<cv::Point2d> b_center_point(target_b.size());

    for (int j = 0; j < target_a.size(); j++)
    {
        add_connections(boards.first[j], boards_points, target_a[j]);
    }
    for (int j = 0; j < target_b.size(); j++)
    {
        add_connections(boards.second[j], boards_points, target_b[j]);
    }
#ifdef SHOW
    for (int i = 0; i < boards_points.size(); i++)
    {
        auto pi = boards_points[i].lock();
        if (pi)
        {
            if (pi->type == TARGET_A)
            {
                auto contourPoints = pi->contour;
                for (int j = 0; j < contourPoints.size(); j++)
                {
                    circle(show_connections, contourPoints[j] * show_scale, 1, cv::Scalar(0, 0, 255), -1);
                }
            }
            else if (pi->type == TARGET_B)
            {
                auto contourPoints = pi->contour;
                for (int j = 0; j < contourPoints.size(); j++)
                {
                    circle(show_connections, contourPoints[j] * show_scale, 1, cv::Scalar(0, 255, 255), -1);
                }
            }
        }
    }

    cv::namedWindow("Image classify point", cv::WINDOW_NORMAL);
    cv::resizeWindow("Image classify point", 640, 480);
    cv::imshow("Image classify point", show_connections);
#endif
#ifdef MEASURE_RUNNING_TIME
    // 设置结束时间
    auto end = std::chrono::system_clock::now();

    // 精确到微秒，除此之外，还有五种时间单位：hours, minutes, seconds, milliseconds, nanoseconds
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start);

    // duration.count() 返回统计的时间
    // num 和 den分别表示分子(numerator)和分母(denominator)
    // 在代码中，num等于1， den等于1,000,000
    std::cout << "get_target_points duration=" << double(duration.count()) * std::chrono::microseconds::period::num / std::chrono::microseconds::period::den << std::endl;
#endif
    return true;
}

int blok_threshold(cv::Mat src, cv::Mat &dst)
{
    dst = cv::Mat::zeros(src.size(), CV_8UC1);
    int n = 10;
    static int nx = src.cols / n;
    static int ny = src.rows / n;
    for (int i = 0; i < n; i++)
    {
        for (int j = 0; j < n; j++)
        {
            cv::Mat src_roi = src(cv::Rect(i * nx, j * ny, nx, ny));
            cv::Mat dst_roi = dst(cv::Rect(i * nx, j * ny, nx, ny));
            cv::Scalar mean_gray = cv::mean(src_roi);
            int level = 5;
            cv::Mat dst_roi_level[level];

            for (int l = 0; l < level; l++)
            {
                threshold(src_roi, dst_roi_level[l], (0.2 + (2.0 - 0.2) / level * l) * mean_gray.val[0], 255, cv::THRESH_BINARY);
                dst_roi = dst_roi + dst_roi_level[l] / level;
            }

            cv::medianBlur(dst_roi, dst_roi, 3);
        }
    }
#ifdef SHOW
    cv::medianBlur(dst, dst, 3);
    cv::namedWindow("dst", cv::WINDOW_NORMAL);
    cv::resizeWindow("dst", 640, 480);
    cv::imshow("dst", dst);
#endif

    return 0;
}

int DetectBoard::detect_board(cv::Mat src, std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> &board_a_points, std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> &board_b_points)
{
#ifdef MEASURE_RUNNING_TIME
    // 设置开始时间
    auto start = std::chrono::system_clock::now();
#endif
    clear_board_points();
    cv::Mat gray;
    cvtColor(src, gray, cv::COLOR_RGB2GRAY);
#ifdef SHOW
    cv::namedWindow("input", cv::WINDOW_NORMAL);
    cv::resizeWindow("input", 640, 480);
    cv::imshow("input", gray);
#endif
    cv::resize(gray, gray, cv::Size(640, 480));
    cv::Scalar mean_gray = mean(gray);
    cv::Mat dst;

    //  cvtColor(img,gray,COLOR_RGB2GRAY);
    // threshold(gray, dst, mean_gray.val[0], 255, THRESH_BINARY);

    blok_threshold(gray, dst);

    global_binary_img = dst.clone();
#ifdef SHOW
    cv::namedWindow("dst", cv::WINDOW_NORMAL);
    cv::resizeWindow("dst", 640, 480);
    cv::imshow("dst", dst);
    cv::imwrite("dst.png", dst);
    std::cout << "dst size=" << dst.size() << std::endl;
#endif
    

    std::vector<std::weak_ptr<PointCalibrateBoard>> boards_points = get_contours(gray);
    
    sort_by_distance(boards_points);

    auto bigger_points = get_center_bigger_points(boards_points);
    // return 0;
    bool bOK = get_target_points(bigger_points, boards_points, board_a_points, board_b_points);


    double scale_x=1.0*src.cols/640;
    double scale_y=1.0*src.rows/480;

    for(auto p:boards_points)
    {
        auto pp=p.lock();
        pp->center_image.x *=scale_x;
        pp->center_image.y *=scale_y;
    }
#ifdef MEASURE_RUNNING_TIME
    // 设置结束时间
    auto end = std::chrono::system_clock::now();

    // 精确到微秒，除此之外，还有五种时间单位：hours, minutes, seconds, milliseconds, nanoseconds
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start);

    std::cout << "detect_camera duration= " << double(duration.count()) * std::chrono::microseconds::period::num / std::chrono::microseconds::period::den << std::endl;
#endif
    //
    if (!bOK || board_a_points.empty())
    {
        return -1;
    }

    return 0;
}
