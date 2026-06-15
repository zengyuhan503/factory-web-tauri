echo " usage : ./calibrate *.csv *example_ferraris_session_list.json imu-name"
base_dir=$(pwd)
source_csv=${base_dir}/$1
data_list=${base_dir}/$2
imu_name=$3

sed -i '1c n_samples,gyr_x,gyr_y,gyr_z,acc_x,acc_y,acc_z' ${source_csv}

python3 basic_ferraris.py ${source_csv}  ${data_list} ${imu_name}
