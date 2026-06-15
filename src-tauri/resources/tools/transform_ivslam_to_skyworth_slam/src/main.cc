#include "Settings.h"
#include <map>
#include <jsoncpp/json/json.h>
#include <fstream>
#include <sys/stat.h>

enum DataType
{
    isInt,
    isFloat,
    isDouble,
    isString,
    isEigenMatrix,
    isEigenVec,
    isCvMat
};
struct VarData
{
    /* data */
    void *data;
    DataType data_type;
};


void readcfg(cv::FileStorage &fSettings, std::map<std::string, VarData> &cfg)
{
    cv::FileNode node = fSettings.root();
    for (auto it = node.begin(); it != node.end(); it++)
    {
        cv::FileNode node = *it;

        if (node.isInt())
        {
            std::cout << "read int " << node.name() << "=" << node.operator int() << std::endl;
            VarData data;
            data.data = new int();
            data.data_type = isInt;
            int *p = (int *)data.data;
            *p = node.operator int();
            cfg[node.name()] = data;
        }
        else if (node.isReal())
        {

            std::cout << "read  real " << node.name() << "=" << node.real() << std::endl;
            VarData data;
            data.data = new double();
            data.data_type = isDouble;
            double *p = (double *)data.data;
            *p = node.real();
            cfg[node.name()] = data;
        }
        else if (node.isString())
        {
            std::cout << "read string " << node.name() << "=" << node.string() << std::endl;
            VarData data;
            data.data = new std::string();
            data.data_type = isString;
            std::string *p = (std::string *)data.data;
            *p = node.string();
            cfg[node.name()] = data;
        }
        else
        {
            std::cout << "read mat " << node.name();
            std::cout << "read mat " << node.name() << "=" << node.mat() << std::endl;
            VarData data;
            data.data = new cv::Mat();
            data.data_type = isCvMat;
            cv::Mat *p = (cv::Mat *)data.data;
            *p = node.mat();
            cfg[node.name()] = data;
        }
    }
}

void writecfg(cv::FileStorage &fSettings, std::map<std::string, VarData> &cfg)
{
    for (auto it : cfg)
    {
        std::string key = it.first;
        VarData value = it.second;

        if (value.data_type == isInt)
        {
            int *p = (int *)value.data;
            writeParameter(fSettings, key, *p);
        }
        else if (value.data_type == isFloat)
        {
            float *p = (float *)value.data;
            writeParameter(fSettings, key, *p);
        }
        else if (value.data_type == isDouble)
        {
            double *p = (double *)value.data;
            writeParameter(fSettings, key, *p);
        }
        else if (value.data_type == isString)
        {
            std::string *p = (std::string *)value.data;
            writeParameter(fSettings, key, *p);
        }
        else if (value.data_type == isCvMat)
        {
            cv::Mat *p = (cv::Mat *)value.data;
            writeParameter(fSettings, key, *p);
        }
    }
}

void addJsonPara(Json::Value &root, std::map<std::string, VarData> &cfg, std::string name)
{
    Json::Value my_plugins = root[name];

    int row = my_plugins.size();
    int col = my_plugins[0].size();
    std::cout << "row=" << row << "col=" << col << std::endl;
    if (row > 0 && col > 0)
    {
        cv::Mat ka = cv::Mat::eye(cv::Size(row, col), CV_32FC1);
        for (int i = 0; i < my_plugins.size(); i++)
        {
            Json::Value value = my_plugins[i];
            for (int j = 0; j < value.size(); j++)
            {
                ka.at<float>(i, j) = value[j].asFloat();
            }
        }
        std::cout << "Imucal_" << name << "=" << ka << std::endl;

        VarData data;
        data.data = new cv::Mat();
        data.data_type = isCvMat;
        cv::Mat *p = (cv::Mat *)data.data;
        *p = ka;
        cfg["Imucal_" + name] = data;
    }
    else if (row > 0)
    {
        cv::Mat ka = cv::Mat::zeros(cv::Size(row, 1), CV_32F);
        for (int i = 0; i < my_plugins.size(); i++)
        {
            Json::Value value = my_plugins[i];
            std::cout << "i=" << i << " value=" << value.asFloat() << std::endl;
            ;
            ka.at<float>(0, i) = value.asFloat();
        }
        std::cout << "Imucal_" << name << "=" << ka << std::endl;
        VarData data;
        data.data = new cv::Mat();
        data.data_type = isCvMat;
        cv::Mat *p = (cv::Mat *)data.data;
        *p = ka;
        cfg["Imucal_" + name] = data;
    }
}

void addYamlKalibrParam(cv::FileStorage &fSettings, std::map<std::string, VarData> &cfg, std::string cam, std::string param)
{

    cv::FileNode node = fSettings[cam][param];
    std::cout << node.size() << std::endl;
    int sz = node.size();
    if (sz == 16)
    {
        cv::Mat a = cv::Mat::zeros(cv::Size(4, 4), CV_32F);
        for (int i = 0; i < 4; i++)
        {
            for (int j = 0; j < 4; j++)
            {
                a.at<float>(i, j) = node[i * 4 + j].operator float();
            }
        }
        if (cam == "cam0" && param == "T_cam_imu")
        {
            VarData data;
            data.data = new cv::Mat();
            data.data_type = isCvMat;
            cv::Mat *p = (cv::Mat *)data.data;
            *p = a;
            cfg["IMU_T_c1_b"] = data;
        }
        if (cam == "cam1" && param == "T_cam_imu")
        {
            VarData data;
            data.data = new cv::Mat();
            data.data_type = isCvMat;
            cv::Mat *p = (cv::Mat *)data.data;
            *p = a;
            cfg["IMU_T_c2_b"] = data;
        }
        if (cam == "cam2" && param == "T_cam_imu")
        {
            VarData data;
            data.data = new cv::Mat();
            data.data_type = isCvMat;
            cv::Mat *p = (cv::Mat *)data.data;
            *p = a;
            cfg["IMU_T_c3_b"] = data;
        }
        if (cam == "cam3" && param == "T_cam_imu")
        {
            VarData data;
            data.data = new cv::Mat();
            data.data_type = isCvMat;
            cv::Mat *p = (cv::Mat *)data.data;
            *p = a;
            cfg["IMU_T_c4_b"] = data;
        }

        std::cout << "read " << cam << "." << param << "=" << a << std::endl;
    }
    else if (sz == 4)
    {
        cv::Mat a = cv::Mat::zeros(cv::Size(4, 1), CV_32F);
        for (int i = 0; i < 4; i++)
        {
            a.at<float>(i) = node[i].operator float();
        }
        if (cam == "cam0" && param == "intrinsics")
        {
            VarData fx;
            fx.data = new float();
            fx.data_type = isFloat;
            float *p = (float *)fx.data;
            *p = a.at<float>(0);
            cfg["Camera1_fx"] = fx;

            VarData fy;
            fy.data = new float();
            fy.data_type = isFloat;
            p = (float *)fy.data;
            *p = a.at<float>(1);
            cfg["Camera1_fy"] = fy;

            VarData cx;
            cx.data = new float();
            cx.data_type = isFloat;
            p = (float *)cx.data;
            *p = a.at<float>(2);
            cfg["Camera1_cx"] = cx;

            VarData cy;
            cy.data = new float();
            cy.data_type = isFloat;
            p = (float *)cy.data;
            *p = a.at<float>(3);
            cfg["Camera1_cy"] = cy;
        }
        if (cam == "cam1" && param == "intrinsics")
        {
            VarData fx;
            fx.data = new float();
            fx.data_type = isFloat;
            float *p = (float *)fx.data;
            *p = a.at<float>(0);
            cfg["Camera2_fx"] = fx;

            VarData fy;
            fy.data = new float();
            fy.data_type = isFloat;
            p = (float *)fy.data;
            *p = a.at<float>(1);
            cfg["Camera2_fy"] = fy;

            VarData cx;
            cx.data = new float();
            cx.data_type = isFloat;
            p = (float *)cx.data;
            *p = a.at<float>(2);
            cfg["Camera2_cx"] = cx;

            VarData cy;
            cy.data = new float();
            cy.data_type = isFloat;
            p = (float *)cy.data;
            *p = a.at<float>(3);
            cfg["Camera2_cy"] = cy;
        }
        if (cam == "cam2" && param == "intrinsics")
        {
            VarData fx;
            fx.data = new float();
            fx.data_type = isFloat;
            float *p = (float *)fx.data;
            *p = a.at<float>(0);
            cfg["Camera3_fx"] = fx;

            VarData fy;
            fy.data = new float();
            fy.data_type = isFloat;
            p = (float *)fy.data;
            *p = a.at<float>(1);
            cfg["Camera3_fy"] = fy;

            VarData cx;
            cx.data = new float();
            cx.data_type = isFloat;
            p = (float *)cx.data;
            *p = a.at<float>(2);
            cfg["Camera3_cx"] = cx;

            VarData cy;
            cy.data = new float();
            cy.data_type = isFloat;
            p = (float *)cy.data;
            *p = a.at<float>(3);
            cfg["Camera3_cy"] = cy;
        }
        if (cam == "cam3" && param == "intrinsics")
        {
            VarData fx;
            fx.data = new float();
            fx.data_type = isFloat;
            float *p = (float *)fx.data;
            *p = a.at<float>(0);
            cfg["Camera4_fx"] = fx;

            VarData fy;
            fy.data = new float();
            fy.data_type = isFloat;
            p = (float *)fy.data;
            *p = a.at<float>(1);
            cfg["Camera4_fy"] = fy;

            VarData cx;
            cx.data = new float();
            cx.data_type = isFloat;
            p = (float *)cx.data;
            *p = a.at<float>(2);
            cfg["Camera4_cx"] = cx;

            VarData cy;
            cy.data = new float();
            cy.data_type = isFloat;
            p = (float *)cy.data;
            *p = a.at<float>(3);
            cfg["Camera4_cy"] = cy;
        }
        if (cam == "cam0" && param == "distortion_coeffs")
        {

            VarData k1;
            k1.data = new float();
            k1.data_type = isFloat;
            float *p = (float *)k1.data;
            *p = a.at<float>(0);
            cfg["Camera1_k1"] = k1;

            VarData k2;
            k2.data = new float();
            k2.data_type = isFloat;
            p = (float *)k2.data;
            *p = a.at<float>(1);
            cfg["Camera1_k2"] = k2;

            VarData k3;
            k3.data = new float();
            k3.data_type = isFloat;
            p = (float *)k3.data;
            *p = a.at<float>(2);
            cfg["Camera1_k3"] = k3;

            VarData k4;
            k4.data = new float();
            k4.data_type = isFloat;
            p = (float *)k4.data;
            *p = a.at<float>(3);
            cfg["Camera1_k4"] = k4;
        }
        if (cam == "cam1" && param == "distortion_coeffs")
        {
            VarData k1;
            k1.data = new float();
            k1.data_type = isFloat;
            float *p = (float *)k1.data;
            *p = a.at<float>(0);
            cfg["Camera2_k1"] = k1;

            VarData k2;
            k2.data = new float();
            k2.data_type = isFloat;
            p = (float *)k2.data;
            *p = a.at<float>(1);
            cfg["Camera2_k2"] = k2;

            VarData k3;
            k3.data = new float();
            k3.data_type = isFloat;
            p = (float *)k3.data;
            *p = a.at<float>(2);
            cfg["Camera2_k3"] = k3;

            VarData k4;
            k4.data = new float();
            k4.data_type = isFloat;
            p = (float *)k4.data;
            *p = a.at<float>(3);
            cfg["Camera2_k4"] = k4;
        }
        if (cam == "cam2" && param == "distortion_coeffs")
        {
            VarData k1;
            k1.data = new float();
            k1.data_type = isFloat;
            float *p = (float *)k1.data;
            *p = a.at<float>(0);
            cfg["Camera3_k1"] = k1;

            VarData k2;
            k2.data = new float();
            k2.data_type = isFloat;
            p = (float *)k2.data;
            *p = a.at<float>(1);
            cfg["Camera3_k2"] = k2;

            VarData k3;
            k3.data = new float();
            k3.data_type = isFloat;
            p = (float *)k3.data;
            *p = a.at<float>(2);
            cfg["Camera3_k3"] = k3;

            VarData k4;
            k4.data = new float();
            k4.data_type = isFloat;
            p = (float *)k4.data;
            *p = a.at<float>(3);
            cfg["Camera3_k4"] = k4;
        }
        if (cam == "cam3" && param == "distortion_coeffs")
        {
            VarData k1;
            k1.data = new float();
            k1.data_type = isFloat;
            float *p = (float *)k1.data;
            *p = a.at<float>(0);
            cfg["Camera4_k1"] = k1;

            VarData k2;
            k2.data = new float();
            k2.data_type = isFloat;
            p = (float *)k2.data;
            *p = a.at<float>(1);
            cfg["Camera4_k2"] = k2;

            VarData k3;
            k3.data = new float();
            k3.data_type = isFloat;
            p = (float *)k3.data;
            *p = a.at<float>(2);
            cfg["Camera4_k3"] = k3;

            VarData k4;
            k4.data = new float();
            k4.data_type = isFloat;
            p = (float *)k4.data;
            *p = a.at<float>(3);
            cfg["Camera4_k4"] = k4;
        }

        std::cout << "read " << cam << "." << param << "=" << a << std::endl;
    }
    else if (sz == 1)
    {

        if (node.isInt())
        {
            std::cout << "read int " << cam << "." << param << "=" << node.operator int() << std::endl;
            VarData val;
            val.data = new int();
            val.data_type = isInt;
            int *p = (int *)val.data;
            *p = node.operator int();
            cfg[cam + "_" + param] = val;
        }
        else if (node.isReal())
        {

            std::cout << "read  real " << cam << "." << param << "=" << node.real() << std::endl;
            VarData val;
            val.data = new float();
            val.data_type = isFloat;
            float *p = (float *)val.data;
            *p = node.real();
            cfg[cam + "_" + param] = val;
        }
        else if (node.isString())
        {
            std::cout << "read string " << cam << "." << param << "=" << node.string() << std::endl;
            VarData val;
            val.data = new std::string();
            val.data_type = isString;
            std::string *p = (std::string *)val.data;
            *p = node.string();
            cfg[cam + "_" + param] = val;
        }
        else
        {
            std::cout << "read mat " << cam << "." << param;
            std::cout << "read mat " << cam << "." << param << "=" << node.mat() << std::endl;
            VarData val;
            val.data = new cv::Mat();
            val.data_type = isCvMat;
            cv::Mat *p = (cv::Mat *)val.data;
            *p = node.mat();
            cfg[cam + "_" + param] = val;
        }
    }
}

void addIvslamKalibrParam(cv::FileStorage &fSettings, std::map<std::string, VarData> &cfg, std::string cam, std::string param)
{

    cv::FileNode node = fSettings[cam][param];
    std::cout << node.size() << std::endl;
    int sz = node.size();
    if (sz == 16)
    {
        cv::Mat a = cv::Mat::zeros(cv::Size(4, 4), CV_32F);
        for (int i = 0; i < 4; i++)
        {
            for (int j = 0; j < 4; j++)
            {
                a.at<float>(i, j) = node[i * 4 + j].operator float();
            }
        }
        if (cam == "cam0" && param == "Tbc")
        {
            VarData data;
            data.data = new cv::Mat();
            data.data_type = isCvMat;
            cv::Mat *p = (cv::Mat *)data.data;
            *p = a.inv();
            cfg["IMU_T_c1_b"] = data;
        }
        if (cam == "cam1" && param == "Tbc")
        {
            VarData data;
            data.data = new cv::Mat();
            data.data_type = isCvMat;
            cv::Mat *p = (cv::Mat *)data.data;
            *p = a.inv();
            cfg["IMU_T_c2_b"] = data;
        }
        if (cam == "cam2" && param == "Tbc")
        {
            VarData data;
            data.data = new cv::Mat();
            data.data_type = isCvMat;
            cv::Mat *p = (cv::Mat *)data.data;
            *p = a.inv();
            cfg["IMU_T_c3_b"] = data;
        }
        if (cam == "cam3" && param == "Tbc")
        {
            VarData data;
            data.data = new cv::Mat();
            data.data_type = isCvMat;
            cv::Mat *p = (cv::Mat *)data.data;
            *p = a.inv();
            cfg["IMU_T_c4_b"] = data;
        }

        std::cout << "read " << cam << "." << param << "=" << a << std::endl;
    }
    else if (sz == 4)
    {
        cv::Mat a = cv::Mat::zeros(cv::Size(4, 1), CV_32F);
        for (int i = 0; i < 4; i++)
        {
            a.at<float>(i) = node[i].operator float();
        }
        if (cam == "cam0" && param == "intrinsics")
        {
            VarData fx;
            fx.data = new float();
            fx.data_type = isFloat;
            float *p = (float *)fx.data;
            *p = a.at<float>(0);
            cfg["Camera1_fx"] = fx;

            VarData fy;
            fy.data = new float();
            fy.data_type = isFloat;
            p = (float *)fy.data;
            *p = a.at<float>(1);
            cfg["Camera1_fy"] = fy;

            VarData cx;
            cx.data = new float();
            cx.data_type = isFloat;
            p = (float *)cx.data;
            *p = a.at<float>(2);
            cfg["Camera1_cx"] = cx;

            VarData cy;
            cy.data = new float();
            cy.data_type = isFloat;
            p = (float *)cy.data;
            *p = a.at<float>(3);
            cfg["Camera1_cy"] = cy;
        }
        if (cam == "cam1" && param == "intrinsics")
        {
            VarData fx;
            fx.data = new float();
            fx.data_type = isFloat;
            float *p = (float *)fx.data;
            *p = a.at<float>(0);
            cfg["Camera2_fx"] = fx;

            VarData fy;
            fy.data = new float();
            fy.data_type = isFloat;
            p = (float *)fy.data;
            *p = a.at<float>(1);
            cfg["Camera2_fy"] = fy;

            VarData cx;
            cx.data = new float();
            cx.data_type = isFloat;
            p = (float *)cx.data;
            *p = a.at<float>(2);
            cfg["Camera2_cx"] = cx;

            VarData cy;
            cy.data = new float();
            cy.data_type = isFloat;
            p = (float *)cy.data;
            *p = a.at<float>(3);
            cfg["Camera2_cy"] = cy;
        }
        if (cam == "cam2" && param == "intrinsics")
        {
            VarData fx;
            fx.data = new float();
            fx.data_type = isFloat;
            float *p = (float *)fx.data;
            *p = a.at<float>(0);
            cfg["Camera3_fx"] = fx;

            VarData fy;
            fy.data = new float();
            fy.data_type = isFloat;
            p = (float *)fy.data;
            *p = a.at<float>(1);
            cfg["Camera3_fy"] = fy;

            VarData cx;
            cx.data = new float();
            cx.data_type = isFloat;
            p = (float *)cx.data;
            *p = a.at<float>(2);
            cfg["Camera3_cx"] = cx;

            VarData cy;
            cy.data = new float();
            cy.data_type = isFloat;
            p = (float *)cy.data;
            *p = a.at<float>(3);
            cfg["Camera3_cy"] = cy;
        }
        if (cam == "cam3" && param == "intrinsics")
        {
            VarData fx;
            fx.data = new float();
            fx.data_type = isFloat;
            float *p = (float *)fx.data;
            *p = a.at<float>(0);
            cfg["Camera4_fx"] = fx;

            VarData fy;
            fy.data = new float();
            fy.data_type = isFloat;
            p = (float *)fy.data;
            *p = a.at<float>(1);
            cfg["Camera4_fy"] = fy;

            VarData cx;
            cx.data = new float();
            cx.data_type = isFloat;
            p = (float *)cx.data;
            *p = a.at<float>(2);
            cfg["Camera4_cx"] = cx;

            VarData cy;
            cy.data = new float();
            cy.data_type = isFloat;
            p = (float *)cy.data;
            *p = a.at<float>(3);
            cfg["Camera4_cy"] = cy;
        }
        if (cam == "cam0" && param == "distortion_coeffs")
        {

            VarData k1;
            k1.data = new float();
            k1.data_type = isFloat;
            float *p = (float *)k1.data;
            *p = a.at<float>(0);
            cfg["Camera1_k1"] = k1;

            VarData k2;
            k2.data = new float();
            k2.data_type = isFloat;
            p = (float *)k2.data;
            *p = a.at<float>(1);
            cfg["Camera1_k2"] = k2;

            VarData k3;
            k3.data = new float();
            k3.data_type = isFloat;
            p = (float *)k3.data;
            *p = a.at<float>(2);
            cfg["Camera1_k3"] = k3;

            VarData k4;
            k4.data = new float();
            k4.data_type = isFloat;
            p = (float *)k4.data;
            *p = a.at<float>(3);
            cfg["Camera1_k4"] = k4;
        }
        if (cam == "cam1" && param == "distortion_coeffs")
        {
            VarData k1;
            k1.data = new float();
            k1.data_type = isFloat;
            float *p = (float *)k1.data;
            *p = a.at<float>(0);
            cfg["Camera2_k1"] = k1;

            VarData k2;
            k2.data = new float();
            k2.data_type = isFloat;
            p = (float *)k2.data;
            *p = a.at<float>(1);
            cfg["Camera2_k2"] = k2;

            VarData k3;
            k3.data = new float();
            k3.data_type = isFloat;
            p = (float *)k3.data;
            *p = a.at<float>(2);
            cfg["Camera2_k3"] = k3;

            VarData k4;
            k4.data = new float();
            k4.data_type = isFloat;
            p = (float *)k4.data;
            *p = a.at<float>(3);
            cfg["Camera2_k4"] = k4;
        }
        if (cam == "cam2" && param == "distortion_coeffs")
        {
            VarData k1;
            k1.data = new float();
            k1.data_type = isFloat;
            float *p = (float *)k1.data;
            *p = a.at<float>(0);
            cfg["Camera3_k1"] = k1;

            VarData k2;
            k2.data = new float();
            k2.data_type = isFloat;
            p = (float *)k2.data;
            *p = a.at<float>(1);
            cfg["Camera3_k2"] = k2;

            VarData k3;
            k3.data = new float();
            k3.data_type = isFloat;
            p = (float *)k3.data;
            *p = a.at<float>(2);
            cfg["Camera3_k3"] = k3;

            VarData k4;
            k4.data = new float();
            k4.data_type = isFloat;
            p = (float *)k4.data;
            *p = a.at<float>(3);
            cfg["Camera3_k4"] = k4;
        }
        if (cam == "cam3" && param == "distortion_coeffs")
        {
            VarData k1;
            k1.data = new float();
            k1.data_type = isFloat;
            float *p = (float *)k1.data;
            *p = a.at<float>(0);
            cfg["Camera4_k1"] = k1;

            VarData k2;
            k2.data = new float();
            k2.data_type = isFloat;
            p = (float *)k2.data;
            *p = a.at<float>(1);
            cfg["Camera4_k2"] = k2;

            VarData k3;
            k3.data = new float();
            k3.data_type = isFloat;
            p = (float *)k3.data;
            *p = a.at<float>(2);
            cfg["Camera4_k3"] = k3;

            VarData k4;
            k4.data = new float();
            k4.data_type = isFloat;
            p = (float *)k4.data;
            *p = a.at<float>(3);
            cfg["Camera4_k4"] = k4;
        }

        std::cout << "read " << cam << "." << param << "=" << a << std::endl;
    }
    else if (sz == 1)
    {

        if (node.isInt())
        {
            std::cout << "read int " << cam << "." << param << "=" << node.operator int() << std::endl;
            VarData val;
            val.data = new int();
            val.data_type = isInt;
            int *p = (int *)val.data;
            *p = node.operator int();
            cfg[cam + "_" + param] = val;
        }
        else if (node.isReal())
        {

            std::cout << "read  real " << cam << "." << param << "=" << node.real() << std::endl;
            VarData val;
            val.data = new float();
            val.data_type = isFloat;
            float *p = (float *)val.data;
            *p = node.real();
            cfg[cam + "_" + param] = val;
        }
        else if (node.isString())
        {
            std::cout << "read string " << cam << "." << param << "=" << node.string() << std::endl;
            VarData val;
            val.data = new std::string();
            val.data_type = isString;
            std::string *p = (std::string *)val.data;
            *p = node.string();
            cfg[cam + "_" + param] = val;
        }
        else
        {
            std::cout << "read mat " << cam << "." << param;
            std::cout << "read mat " << cam << "." << param << "=" << node.mat() << std::endl;
            VarData val;
            val.data = new cv::Mat();
            val.data_type = isCvMat;
            cv::Mat *p = (cv::Mat *)val.data;
            *p = node.mat();
            cfg[cam + "_" + param] = val;
        }
    }
}

void addImuCalParam(Json::Value &root, std::map<std::string, VarData> &cfg)
{
    addJsonPara(root, cfg, "K_a");
    addJsonPara(root, cfg, "K_g");
    addJsonPara(root, cfg, "R_a");
    addJsonPara(root, cfg, "R_g");
    addJsonPara(root, cfg, "b_a");
    addJsonPara(root, cfg, "b_g");
}

void addKalibrParam(cv::FileStorage &fSettings, std::map<std::string, VarData> &cfg)
{
    addYamlKalibrParam(fSettings, cfg, "cam0", "T_cam_imu");
    addYamlKalibrParam(fSettings, cfg, "cam0", "intrinsics");
    addYamlKalibrParam(fSettings, cfg, "cam0", "distortion_coeffs");

    addYamlKalibrParam(fSettings, cfg, "cam1", "T_cam_imu");
    addYamlKalibrParam(fSettings, cfg, "cam1", "intrinsics");
    addYamlKalibrParam(fSettings, cfg, "cam1", "distortion_coeffs");

    addYamlKalibrParam(fSettings, cfg, "cam2", "T_cam_imu");
    addYamlKalibrParam(fSettings, cfg, "cam2", "intrinsics");
    addYamlKalibrParam(fSettings, cfg, "cam2", "distortion_coeffs");

    addYamlKalibrParam(fSettings, cfg, "cam3", "T_cam_imu");
    addYamlKalibrParam(fSettings, cfg, "cam3", "intrinsics");
    addYamlKalibrParam(fSettings, cfg, "cam3", "distortion_coeffs");
}

void addIvslamParam(cv::FileStorage &fSettings, std::map<std::string, VarData> &cfg)
{
    addIvslamKalibrParam(fSettings, cfg, "cam0", "Tbc");
    addIvslamKalibrParam(fSettings, cfg, "cam0", "intrinsics");
    addIvslamKalibrParam(fSettings, cfg, "cam0", "distortion_coeffs");

    addIvslamKalibrParam(fSettings, cfg, "cam1", "Tbc");
    addIvslamKalibrParam(fSettings, cfg, "cam1", "intrinsics");
    addIvslamKalibrParam(fSettings, cfg, "cam1", "distortion_coeffs");

    addIvslamKalibrParam(fSettings, cfg, "cam2", "Tbc");
    addIvslamKalibrParam(fSettings, cfg, "cam2", "intrinsics");
    addIvslamKalibrParam(fSettings, cfg, "cam2", "distortion_coeffs");

    addIvslamKalibrParam(fSettings, cfg, "cam3", "Tbc");
    addIvslamKalibrParam(fSettings, cfg, "cam3", "intrinsics");
    addIvslamKalibrParam(fSettings, cfg, "cam3", "distortion_coeffs");
}

inline bool FileExists(const std::string &name)
{
    struct stat buffer;
    return (stat(name.c_str(), &buffer) == 0);
}
int main(int argc, char **argv)
{
    std::string configFileTmp = "xr2-template.yaml";
    std::string configFileOut;
    std::string ivslamConfig = "ivslam.yaml";
    if (argc != 4)
    {
        std::cout << "useage: ./transform_result_to_slam ivslam.yaml xr2-template.yaml out.yaml\n";
        exit(0);
    }
    ivslamConfig=argv[1];
    configFileTmp = argv[2];
    configFileOut = argv[3];

    if (!FileExists(configFileTmp))
    {
        std::cout << "file " << configFileTmp << " is not exist" << std::endl;
    }
    if (!FileExists(ivslamConfig))
    {
        std::cout << "file " << ivslamConfig << " is not exist" << std::endl;
    }


    std::map<std::string, VarData> cfg;

    // std::cout<<root<<std::endl;

    // Open settings file
    cv::FileStorage frSettings(configFileTmp, cv::FileStorage::READ);

    cv::FileStorage frCalib(ivslamConfig, cv::FileStorage::READ);

    cv::FileStorage fwSettings(configFileOut, cv::FileStorage::WRITE);

    readcfg(frSettings, cfg);
    //addImuCalParam(root,cfg);
    addIvslamParam(frCalib,cfg);
    writecfg(fwSettings, cfg);
    fwSettings.release();
}
