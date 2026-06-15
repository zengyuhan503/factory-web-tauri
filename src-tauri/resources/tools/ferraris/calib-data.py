import tempfile
from pathlib import Path

import pandas as pd
import sys



from imucal.management import find_calibration_info_for_sensor

cals = find_calibration_info_for_sensor(sys.argv[1], sys.argv[2])
cals

# %%
# In any case, we can use :func:`~imucal.management.load_calibration_info` to load the calibration if we know the file
# path.
from imucal.management import load_calibration_info

loaded_cal_info = load_calibration_info(cals[0])
print(loaded_cal_info.to_json())


data = pd.read_csv(sys.argv[3], header=0, index_col=0)
data.head()

calibrated_data = loaded_cal_info.calibrate_df(data, "m/s^2", "rad/s")
print(calibrated_data)
calibrated_data.to_csv(sys.argv[4])

