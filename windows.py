#!/usr/bin/env python3
import os
import subprocess
import numpy as np
import netCDF4 as nc
import argparse
import sys

def debug_print(*args, **kwargs):
    """Print debug information to stderr"""
    print(*args, file=sys.stderr, **kwargs)

def prepare_windows(system_name=None, n_windows=30, submit_jobs=False):
    """
    Prepare umbrella sampling windows for a BDP system.
    
    Args:
        system_name (str): Name of the BDP system folder
        n_windows (int): Number of windows to create
        submit_jobs (bool): Whether to submit individual jobs for each window
    
    Returns:
        list: List of commands for running all window simulations
    """
    # Store current directory to return to it later
    orig_dir = os.getcwd()
    
    # If system_name is provided, check if we're already in that directory
    # or if we need to change to it
    if system_name:
        # Get the current directory name
        current_dir = os.path.basename(orig_dir)
        
        # If we're already in the system directory, don't try to change
        if current_dir == system_name:
            debug_print(f"Already in system directory: {system_name}")
        else:
            # Check if the directory exists relative to current dir
            if os.path.isdir(system_name):
                debug_print(f"Changing to system directory: {system_name}")
                os.chdir(system_name)
            else:
                # If not found, check if it exists in the BDP directory
                bdp_dir = os.environ.get('BDP_DIR', '/pscratch/sd/x/xche564/bdp')
                system_path = os.path.join(bdp_dir, system_name)
                
                if os.path.isdir(system_path):
                    debug_print(f"Changing to system directory: {system_path}")
                    os.chdir(system_path)
                else:
                    debug_print(f"Error: System directory {system_name} not found")
                    return []
    
    # Check for required files
    pull_dist_file = "pull_dist.dat"  # file with COM distance data
    nc_file = "pull.nc"               # trajectory file
    parm_file = "bdp-btb-acetonitrile.prmtop"    # parameter/topology file
    
    required_files = [pull_dist_file, nc_file, parm_file, "COM_prod.RST", "prod.in"]
    for file in required_files:
        if not os.path.exists(file):
            debug_print(f"Error: Required file {file} not found in {os.getcwd()}")
            if system_name:
                os.chdir(orig_dir)
            return []
    
    # Load the pull_dist.dat file.
    # Assume the file has four columns and that column 2 (index 1) is the measured COM distance.
    try:
        data = np.loadtxt(pull_dist_file)
        # Column indices: 0: target distance, 1: measured COM distance, 2: deviation, 3: force
        com_values = data[:, 1]
    except Exception as e:
        debug_print(f"Error loading pull_dist.dat: {e}")
        if system_name:
            os.chdir(orig_dir)
        return []
    
    # Ensure that the com_values and number of frames in nc_file are the same
    try:
        nc_data = nc.Dataset(nc_file, 'r')
        n_frames = len(nc_data['coordinates'])
        if n_frames != len(com_values):
            debug_print(f"Warning: Number of frames in nc file ({n_frames}) doesn't match com_values ({len(com_values)})")
            debug_print("Using minimum of the two values")
            n_frames = min(n_frames, len(com_values))
            com_values = com_values[:n_frames]
    except Exception as e:
        debug_print(f"Error reading NC file: {e}")
        if system_name:
            os.chdir(orig_dir)
        return []
    
    # Determine window centers: equally spaced values between the min and max measured COM distance.
    min_com = 3.0
    max_com = 33.0
    window_centers = np.linspace(min_com, max_com, n_windows)
    
    # For each window center, find the frame index with the closest COM distance.
    frame_indices = []
    for center in window_centers:
        idx = np.argmin(np.abs(com_values - center))
        frame_indices.append(idx)
    
    # Print the window centers and corresponding frame indices.
    debug_print("Target window centers (COM distances):", window_centers)
    debug_print("Chosen frame COM distances:", com_values[frame_indices])
    
    # Write out the cpptraj input script to extract these frames.
    with open('frame.cpptraj', 'w') as f:
        f.write(f"parm {parm_file}\n")
        f.write(f"trajin {nc_file}\n")
        for i, frame in enumerate(frame_indices):
            f.write(f"trajout window_{i}.rst restart onlyframes {frame}\n")
        f.write("go\nquit\n")
    
    # Extract frames from pulling trajectory using cpptraj
    debug_print("Extracting frames with cpptraj...")
    command = ['cpptraj', 'frame.cpptraj']
    result = subprocess.run(command, capture_output=True, text=True)
    
    if result.returncode != 0 or "Error" in result.stdout or "Error" in result.stderr or "Failed" in result.stdout:
        debug_print("Error running cpptraj (return code: {})".format(result.returncode))
        debug_print("STDOUT:")
        debug_print(result.stdout)
        debug_print("STDERR:")
        debug_print(result.stderr)
        # Return from function with empty list
        if system_name:
            os.chdir(orig_dir)
        return []
    
    # List to store window commands
    window_commands = []
    prefix = f"{system_name}/" if system_name else ""
    
    # Create window directories and prepare files
    for i in range(n_windows):
        window_dir = f"window_{i}"
        
        # Create directory
        os.makedirs(window_dir, exist_ok=True)
        
        # Copy required files
        os.system(f"cp COM_prod.RST {window_dir}/")
        os.system(f"cp prod.in {window_dir}/")
        os.system(f"cp window_{i}.rst {window_dir}/")
        os.system(f"cp {parm_file} {window_dir}/")
        
        # Replace DISTHERE with i in COM_prod.RST
        with open(f"{window_dir}/COM_prod.RST", "r") as f:
            contents = f.read()
        contents = contents.replace("dishere", str(window_centers[i]))
        with open(f"{window_dir}/COM_prod.RST", "w") as f:
            f.write(contents)
            
        # Create command for running this window
        # Start from the BDP_DIR to ensure consistent paths
        cmd = f"cd $BDP_DIR && cd {prefix}{window_dir} && "
        cmd += f"srun --cpu-bind=cores --gpu-bind=none --module mpich,gpu shifter pmemd.cuda -O "
        cmd += f"-i prod.in -o prod_{i}.out -p {parm_file} -c window_{i}.rst -r prod_{i}.rst -x prod_{i}.nc -inf prod_{i}.mdinfo"
        window_commands.append(cmd)
        
        # If requested, submit individual job for this window
        if submit_jobs:
            job_script = f"{window_dir}/job.sh"
            with open(job_script, "w") as f:
                f.write("#!/bin/bash -l\n")
                f.write("#SBATCH --image docker:nersc/amber_gpu:22\n")
                f.write("#SBATCH -C gpu\n")
                f.write("#SBATCH -t 00:30:00\n")
                f.write("#SBATCH -J WIN_{}_{}".format(system_name if system_name else "SYS", i))
                f.write("#SBATCH -o window_{}.o%j\n".format(i))
                f.write("#SBATCH -A m3706\n")
                f.write("#SBATCH -N 1\n")
                f.write("#SBATCH --gpus-per-task=1\n")
                f.write("#SBATCH --gpu-bind=none\n")
                f.write("#SBATCH -q shared\n\n")
                f.write("cd $SLURM_SUBMIT_DIR\n\n")
                f.write("# Run the simulation\n")
                f.write(cmd.split("&& ")[1] + "\n")
            
            # Submit the job
            subprocess.run(["sbatch", job_script], capture_output=True, text=True)
            debug_print(f"Submitted job for {window_dir}")
    
    # Return to original directory if we changed
    if system_name:
        os.chdir(orig_dir)
        
    return window_commands

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Prepare umbrella sampling windows for AMBER simulations')
    parser.add_argument('--system', help='BDP system name (folder name)', default=None)
    parser.add_argument('--windows', type=int, help='Number of windows to create', default=30)
    parser.add_argument('--submit', action='store_true', help='Submit individual jobs for each window')
    parser.add_argument('--batch', action='store_true', help='Output commands for batch processing')
    args = parser.parse_args()
    
    # Prepare the windows
    commands = prepare_windows(args.system, args.windows, args.submit)
    
    # If batch mode, output commands for inclusion in a batch script
    if args.batch and commands:
        for cmd in commands:
            print(cmd)
            
    return 0 if commands else 1

if __name__ == "__main__":
    sys.exit(main())