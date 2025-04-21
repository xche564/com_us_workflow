#!/usr/bin/env python3
import os
import numpy as np
import glob
import matplotlib.pyplot as plt

def analyze_restraint_effectiveness(folder, window_prefix="window_", data_file="dist.dat"):
    """Check how effective the restraints are at keeping the CV near target value"""
    results = []
    
    # Fix: Ensure we're only matching directories, not files
    window_dirs = [d for d in glob.glob(os.path.join(folder, f"{window_prefix}*")) 
                  if os.path.isdir(d)]
    
    for window_dir in window_dirs:
        window_name = os.path.basename(window_dir)
        
        # Fix: More robust window number extraction 
        try:
            window_num = int(window_name.replace(window_prefix, ""))
        except ValueError:
            print(f"Warning: Could not extract window number from {window_name}, skipping")
            continue
        
        # Get target from restraint file or estimate based on window number
        target = 0.45 + window_num * 0.1  # Estimated based on your plot
        
        # Load distance data
        dist_file = os.path.join(window_dir, data_file)
        if not os.path.exists(dist_file):
            print(f"Warning: Data file not found for {window_name}: {dist_file}")
            continue
            
        try:
            data = np.loadtxt(dist_file)
            if len(data.shape) == 1:
                if len(data) >= 2:  # Ensure data has at least 2 columns
                    distances = np.array([data[1]])
                else:
                    print(f"Warning: Unexpected data format in {dist_file}")
                    continue
            else:
                if data.shape[1] >= 2:  # Check if there are at least 2 columns
                    distances = data[:, 1]  # Assume column 1 has the distances
                else:
                    print(f"Warning: Not enough columns in {dist_file}")
                    continue
                
            # Calculate how close to target the window stays
            deviation = np.abs(distances - target)
            mean_dev = np.mean(deviation)
            max_dev = np.max(deviation)
            within_01 = np.sum(deviation < 0.1) / len(deviation) * 100
            
            results.append({
                'window': window_num,
                'target': target,
                'mean_deviation': mean_dev,
                'max_deviation': max_dev,
                'pct_within_0.1nm': within_01
            })
            
            print(f"Window {window_num}: Processed {len(distances)} data points")
            
        except Exception as e:
            print(f"Error analyzing {dist_file}: {e}")
    
    # Sort by window number
    results.sort(key=lambda x: x['window'])
    
    # Print results
    if results:
        print("\nResults Summary:")
        print(f"{'Window':<10} {'Target':<10} {'Mean Dev':<10} {'Max Dev':<10} {'% Within 0.1nm':<15}")
        print("-" * 60)
        for r in results:
            print(f"{r['window']:<10} {r['target']:<10.2f} {r['mean_deviation']:<10.3f} "
                  f"{r['max_deviation']:<10.3f} {r['pct_within_0.1nm']:<15.1f}")
    else:
        print("\nNo valid window data was found!")
        print("Common issues to check:")
        print("1. Correct window directory pattern (current: window_*)")
        print("2. Distance data file exists (current: dist.dat)")
        print("3. File format is correct (expecting column 2 to be distances)")
    
    return results

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        folder = sys.argv[1]
    else:
        folder = "."
        
    print(f"Analyzing umbrella sampling in folder: {folder}")
    print(f"Looking for window directories with pattern: window_*")
    print(f"Looking for data files named: dist.dat")
    print("-" * 60)
    
    analyze_restraint_effectiveness(folder)