import os
import subprocess
import numpy as np
import netCDF4 as nc

########################################################
# Extract frames from pulling trajectory
########################################################

n_windows = 30  # number of windows/frames to extract
pull_dist_file = "pull_dist.dat"  # file with COM distance data
nc_file = "pull.nc"               # trajectory file
parm_file = "bdp-btb-acetonitrile.prmtop"    # parameter/topology file "system.parm"   

# Load the pull_dist.dat file.
# Here we assume the file has four columns and that column 2 (index 1)
# is the measured COM distance.
data = np.loadtxt(pull_dist_file)
# Column indices: 0: target distance, 1: measured COM distance, 2: deviation, 3: force
com_values = data[:, 1]

# ensure that the com_values and number of frames in nc_file are the same
nc_data = nc.Dataset(nc_file, 'r')
n_frames = len(nc_data['coordinates'])
if n_frames != len(com_values):
    print(f"Number of frames in nc file: {n_frames}")
    print(f"Number of com_values: {len(com_values)}")
    raise ValueError("The number of frames in the nc file and the com_values do not match")

# Determine window centers: equally spaced values between the min and max measured COM distance.
min_com = 3.0
max_com = 33.0
window_centers = np.linspace(min_com, max_com, n_windows)

# For each window center, find the frame index with the closest COM distance.
# Note: The frame number is taken as the index in the file (starting at 0).
frame_indices = []
for center in window_centers:
    idx = np.argmin(np.abs(com_values - center))
    frame_indices.append(idx)

# Optional: Print the window centers and corresponding frame indices.
print("Target window centers (COM distances):", window_centers)
print("Chosen frame COM distances:", com_values[frame_indices])

# Write out the cpptraj input script to extract these frames.
with open('frame.cpptraj', 'w') as f:
    f.write(f"parm {parm_file}\n")
    f.write(f"trajin {nc_file}\n")
    for i, frame in enumerate(frame_indices):
        # Note: If cpptraj frames start at 0, use 'frame'. If they start at 1, you might add 1.
        f.write(f"trajout window_{i}.rst restart onlyframes {frame}\n")
    f.write("go\nquit\n")
# From pulling trajectory, 30 configuration were seleting at 0.1nm intervals
command = ['cpptraj', 'frame.cpptraj']
result = subprocess.run(command, capture_output=True, text=True)
# Initialize an empty list to store the job IDs
job_ids = []
#os.system('cp equil.rst fram0.rst')
for i in range(0, len(window_centers)):
    # Create directory
    os.makedirs(f"window_{i}", exist_ok=True)
    # Move required files
    os.chdir(f"./window_{i}")
    os.system("cp ../COM_prod.RST .")
    os.system("cp ../amber.sh .")
    os.system("cp ../prod.in .")
    os.system(f"cp ../window_{i}.rst .")
    os.system("cp ../bdp-btb-acetonitrile.prmtop .") # parameter/topology file "system.parm"
    # Replace DISTHERE with i in COM_dist.RST
    with open("COM_prod.RST", "r") as f:
        contents = f.read()
    contents = contents.replace("dishere", str(i))
    with open("COM_prod.RST", "w") as f:
        f.write(contents)
    # Add command to amber.sh
    with open("amber.sh", "r+") as f:
        lines = f.readlines()
        f.seek(0)
        f.truncate()
        f.writelines(lines[:-12])
        f.write(f"pmemd.cuda -O -i prod.in -o prod_{i}.out -p *.prmtop -c window_{i}.rst -r prod_{i}.rst -x prod_{i}.nc -inf prod_{i}.mdinfo\n")
    # Define the path to your amber.sh script
    script_path = "./amber.sh"
    # Use subprocess to submit the job and capture the job ID
    result = subprocess.run(["sbatch", script_path], capture_output=True, text=True)
    job_id = result.stdout.strip().split()[-1]
    job_ids.append(job_id)
    #Go back to parent directory
    os.chdir("../")