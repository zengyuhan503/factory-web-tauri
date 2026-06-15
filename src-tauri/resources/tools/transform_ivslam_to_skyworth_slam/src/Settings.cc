   #include "Settings.h"
   #include <iostream>
   #include <string.h>
   #include <cstdlib>
   using namespace std;
    template<>
    float readParameter<float>(cv::FileStorage& fSettings, const std::string& name, bool& found, const bool required){
        cv::FileNode node = fSettings[name];
        if(node.empty()){
            if(required){
                std::cout << name << " required parameter does not exist, aborting..." << std::endl;
                exit(-1);
            }
            else{
                std::cout << name << " optional parameter does not exist..." << std::endl;
                found = false;
                return 0.0f;
            }
        }
        else if(!node.isReal()){
            std::cout << name << " parameter must be a real number, aborting..." << std::endl;
            exit(-1);
        }
        else{
            found = true;
             std::cout<<"read "<<name<<"="<<node.real()<<std::endl;
            return node.real();
        }
    }

    template<>
    double readParameter<double>(cv::FileStorage& fSettings, const std::string& name, bool& found, const bool required){
        cv::FileNode node = fSettings[name];
        if(node.empty()){
            if(required){
                std::cout << name << " required parameter does not exist, aborting..." << std::endl;
                exit(-1);
            }
            else{
                std::cout << name << " optional parameter does not exist..." << std::endl;
                found = false;
                return 0.0f;
            }
        }
        else if(!node.isReal()){
            std::cout << name << " parameter must be a real number, aborting..." << std::endl;
            exit(-1);
        }
        else{
            found = true;
             std::cout<<"read "<<name<<"="<<node.real()<<std::endl;
            return node.real();
        }
    }

    template<>
    int readParameter<int>(cv::FileStorage& fSettings, const std::string& name, bool& found, const bool required){
        cv::FileNode node = fSettings[name];
        if(node.empty()){
            if(required){
                std::cout << name << " required parameter does not exist, aborting..." << std::endl;
                exit(-1);
            }
            else{
                std::cout << name << " optional parameter does not exist..." << std::endl;
                found = false;
                return 0;
            }
        }
        else if(!node.isInt()){
            std::cout << name << " parameter must be an integer number, aborting..." << std::endl;
            exit(-1);
        }
        else{
            found = true;
             std::cout<<"read "<<name<<"="<<node.operator int()<<std::endl;
            return node.operator int();
        }
    }

    template<>
    string readParameter<string>(cv::FileStorage& fSettings, const std::string& name, bool& found, const bool required){
        cv::FileNode node = fSettings[name];
        if(node.empty()){
            if(required){
                std::cout << name << " required parameter does not exist, aborting..." << std::endl;
                exit(-1);
            }
            else{
                std::cout << name << " optional parameter does not exist..." << std::endl;
                found = false;
                return string();
            }
        }
        else if(!node.isString()){
            std::cout << name << " parameter must be a string, aborting..." << std::endl;
            exit(-1);
        }
        else{
            found = true;
             std::cout<<"read "<<name<<"="<<node.string()<<std::endl;
            return node.string();
        }
    }

    template<>
    cv::Mat readParameter<cv::Mat>(cv::FileStorage& fSettings, const std::string& name, bool& found, const bool required){
        cv::FileNode node = fSettings[name];
        if(node.empty()){
            if(required){
                std::cout << name << " required parameter does not exist, aborting..." << std::endl;
                exit(-1);
            }
            else{
                std::cout << name << " optional parameter does not exist..." << std::endl;
                found = false;
                return cv::Mat();
            }
        }
        else{
            found = true;
            std::cout<<"read "<<name<<"="<<node.mat()<<std::endl;
            return node.mat();
        }
    }
 

    template<>
    bool writeParameter<int>(cv::FileStorage& fSettings, const std::string& name, int value)
    {
        std::cout<<"write int "<<name<<"="<<value<<std::endl;
        fSettings<<name<<value;
        return true;

    }
    template<>
    bool writeParameter<float>(cv::FileStorage& fSettings, const std::string& name, float value)
    {
        std::cout<<"write float"<<name<<"="<<value<<std::endl;
        fSettings<<name<<value;
        return true;

    }
    template<>
    bool writeParameter<string>(cv::FileStorage& fSettings, const std::string& name, string value)
    {
        std::cout<<"write string "<<name<<"="<<value<<std::endl;
        fSettings<<name<<value;
        return true;
    }
    template<>
    bool writeParameter<double>(cv::FileStorage& fSettings, const std::string& name, double value)
    {
        std::cout<<"write string "<<name<<"="<<value<<std::endl;
        fSettings<<name<<value;
        return true;
    }
    template<>
    bool writeParameter<cv::Mat>(cv::FileStorage& fSettings, const std::string& name, cv::Mat value)
    {
        std::cout<<"write mat "<<name<<"="<<value<<std::endl;
        fSettings<<name<<value;
        return true;
    }