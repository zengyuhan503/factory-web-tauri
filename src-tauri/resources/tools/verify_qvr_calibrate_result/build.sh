rm -rf build
rm -rf ThirdParty/Pangolin/build
sudo apt update
DEBIAN_FRONTEND=noninteractive apt install -y tzdata
sudo apt install  libeigen3-dev -y
sudo apt install libjsoncpp-dev -y
sudo apt install libopencv-dev -y
sudo apt install cmake -y
sudo apt install libgl1-mesa-dev mesa-common-dev libglu1-mesa-dev -y
sudo apt install libglew-dev -y
sudo apt install libboost-all-dev -y
cd ThirdParty/
cd Pangolin/
mkdir build
cd build
cmake ..
make -j
sudo make install
cd ../../..
mkdir -p build
cd build
cmake ..
make -j
sudo cp verify_qvr_calibrate_result /usr/bin/
sudo ldconfig

