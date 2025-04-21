import os
import matplotlib.pyplot as plt
import numpy as np

num_windows = 30
NORMALIZE = True
min_com = 3.0
max_com = 33.0
window_centers = np.linspace(min_com, max_com, num_windows)

with open("metadata.dat", "w") as f:
    for i in range(num_windows):
        f.write(f"window_{i}/dist.dat {window_centers[i]} 2.0\n")

os.system(f"/pscratch/sd/x/xche564/bdp/wham/wham/wham {min_com} {max_com} 100 0.01 298.15 0 metadata.dat out.pmf")

# Delete the first line of the file
os.system("tail -n +2 out.pmf > temp.pmf && mv temp.pmf out.pmf")

# Delete all lines after the "WindowFree" string
os.system("sed -i '/Window/,$d' out.pmf")

# Extract the first two columns of data and save to pmf.dat
os.system("awk '{print $1, $2}' out.pmf > pmf.dat")

# Load data from file
x, y = [], []
with open('pmf.dat') as f:
    for line in f:
        cols = line.split()
        x.append(float(cols[0]))
        y.append(float(cols[1]))
if NORMALIZE:
    # remove inf and nan
    mask = np.isfinite(y)
    x = np.array(x)[mask]
    y = np.array(y)[mask]


    last_34_values = y[-34:]
    average_y = sum(last_34_values) / len(last_34_values)
    y = [i - average_y for i in y]

# Create plot
plt.plot(x, y)
plt.xlabel('Distance (A)')
plt.ylabel('PMF (kJ/mol)')
plt.title('PMF vs distance')

# Save plot as PDF
plt.savefig('plot.png')