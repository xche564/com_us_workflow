#!/usr/bin/env python3
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import glob
import pandas as pd
import argparse
from scipy import stats

def load_restraint_data(folder, window_prefix="window_", data_file="dist.dat"):
    """
    Load distance data from all windows.
    Returns a dictionary of {window_num: distance_array}
    """
    windows_data = {}
    
    # Find all window directories
    window_dirs = sorted([d for d in glob.glob(os.path.join(folder, f"{window_prefix}*")) 
                        if os.path.isdir(d)])
    
    if not window_dirs:
        print(f"Error: No window directories found in {folder}")
        return windows_data
        
    for window_dir in window_dirs:
        window_name = os.path.basename(window_dir)
        try:
            window_num = int(window_name.replace(window_prefix, ""))
        except ValueError:
            print(f"Warning: Could not extract window number from {window_name}, skipping")
            continue
        
        # Path to distance data file
        dist_file = os.path.join(window_dir, data_file)
        
        if os.path.exists(dist_file):
            try:
                # Load data - typically 4 columns: r1, r2, r3, f 
                # Where r2 is the actual distance
                data = np.loadtxt(dist_file)
                
                if data.size == 0:
                    print(f"Warning: Empty data file for {window_name}")
                    continue
                    
                # Check if single row or multi-row data
                if len(data.shape) == 1:
                    if len(data) >= 2:  # Assuming second column is the actual distance
                        windows_data[window_num] = np.array([data[1]])
                    else:
                        print(f"Warning: Invalid data format in {dist_file}")
                else:
                    # Use column 1 (0-indexed) which is typically the actual distance
                    windows_data[window_num] = data[:, 1]
                    
                print(f"Loaded {len(windows_data[window_num])} data points from {window_name}")
            except Exception as e:
                print(f"Error loading {dist_file}: {e}")
        else:
            print(f"Warning: Data file not found for {window_name}: {dist_file}")
    
    return windows_data

def get_target_distances(folder, window_prefix="window_", restraint_file="COM_prod.RST"):
    """
    Extract target distances from restraint files.
    Returns a dictionary of {window_num: target_distance}
    """
    target_distances = {}
    
    window_dirs = sorted([d for d in glob.glob(os.path.join(folder, f"{window_prefix}*")) 
                        if os.path.isdir(d)])
    
    for window_dir in window_dirs:
        window_name = os.path.basename(window_dir)
        try:
            window_num = int(window_name.replace(window_prefix, ""))
        except ValueError:
            print(f"Warning: Could not extract window number from {window_name}, skipping")
            continue
        
        # Path to restraint file
        rst_file = os.path.join(window_dir, restraint_file)
        
        if os.path.exists(rst_file):
            try:
                with open(rst_file, 'r') as f:
                    content = f.read()
                    
                # Try to find r2= or r3= in the file
                import re
                r2_match = re.search(r'r2\s*=\s*(\d+\.\d+)', content)
                r3_match = re.search(r'r3\s*=\s*(\d+\.\d+)', content)
                
                if r2_match:
                    target_distances[window_num] = float(r2_match.group(1))
                elif r3_match:
                    target_distances[window_num] = float(r3_match.group(1))
                else:
                    # Fallback - assume the window number corresponds to a sequence from 0.45 to 2.05 nm
                    # This matches your plot's target values
                    target_distances[window_num] = 0.45 + window_num * 0.1
                    print(f"Warning: Could not find target distance in {rst_file}, using estimated value")
            except Exception as e:
                print(f"Error reading {rst_file}: {e}")
                # Fallback
                target_distances[window_num] = 0.45 + window_num * 0.1
        else:
            print(f"Warning: Restraint file not found for {window_name}: {rst_file}")
            # Fallback
            target_distances[window_num] = 0.45 + window_num * 0.1
    
    return target_distances

def plot_window_distributions(windows_data, target_distances, output_file="window_distributions.png", 
                              bins=50, alpha=0.7, figsize=(12, 8)):
    """
    Plot probability distributions for all windows.
    """
    plt.figure(figsize=figsize)
    
    # Create a color map for the windows
    n_windows = len(windows_data)
    cmap = plt.cm.get_cmap('tab20', n_windows)
    
    # Find global min and max for consistent binning
    all_data = np.concatenate([data for data in windows_data.values() if len(data) > 0])
    global_min = np.min(all_data) - 0.1
    global_max = np.max(all_data) + 0.1
    
    bin_edges = np.linspace(global_min, global_max, bins)
    
    # Plot each window's distribution
    for i, (window_num, data) in enumerate(sorted(windows_data.items())):
        if len(data) == 0:
            print(f"Warning: No data for Window {window_num}")
            continue
            
        # Get target distance for this window
        target = target_distances.get(window_num, None)
        
        # Calculate histogram
        counts, bin_edges_window = np.histogram(data, bins=bin_edges, density=True)
        bin_centers = (bin_edges_window[:-1] + bin_edges_window[1:]) / 2
        
        # Plot the histogram as a filled curve
        if target:
            label = f"Window {window_num} (target={target:.2f} nm)"
        else:
            label = f"Window {window_num}"
            
        plt.plot(bin_centers, counts, color=cmap(i), lw=2, label=label)
        plt.fill_between(bin_centers, counts, alpha=alpha, color=cmap(i))
    
    # Add labels and title
    plt.xlabel('Distance (nm)', fontsize=14)
    plt.ylabel('Probability Density', fontsize=14)
    plt.title('CV Distributions for All Windows', fontsize=16)
    plt.grid(True, alpha=0.3)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    
    # Save figure
    plt.savefig(output_file, dpi=300)
    print(f"Plot saved to {output_file}")
    
    return plt.gcf()

def analyze_window_quality(windows_data, target_distances):
    """
    Analyze window quality and provide diagnostics.
    """
    results = []
    
    for window_num, data in sorted(windows_data.items()):
        if len(data) < 10:  # Need enough data for meaningful statistics
            results.append({
                'window': window_num,
                'target': target_distances.get(window_num, np.nan),
                'avg_distance': np.nan,
                'std_deviation': np.nan,
                'samples': len(data),
                'status': 'Insufficient data',
                'quality': 0
            })
            continue
        
        target = target_distances.get(window_num, np.nan)
        avg_dist = np.mean(data)
        std_dev = np.std(data)
        
        # Assess how close the mean is to the target
        if np.isnan(target):
            target_error = np.nan
            status = "Unknown target"
            quality = 1
        else:
            target_error = abs(avg_dist - target)
            # Quality assessment
            if target_error < 0.05:
                status = "Good"
                quality = 3
            elif target_error < 0.1:
                status = "Fair"
                quality = 2
            else:
                status = "Poor"
                quality = 1
        
        results.append({
            'window': window_num,
            'target': target,
            'avg_distance': avg_dist,
            'std_deviation': std_dev,
            'samples': len(data),
            'target_error': target_error,
            'status': status,
            'quality': quality
        })
    
    return pd.DataFrame(results)

def check_window_overlap(windows_data, min_overlap=0.1):
    """
    Check if there's sufficient overlap between adjacent windows.
    Returns a list of window pairs with insufficient overlap.
    """
    insufficient_overlap = []
    
    # Sort window numbers
    window_nums = sorted(windows_data.keys())
    
    for i in range(len(window_nums) - 1):
        w1 = window_nums[i]
        w2 = window_nums[i + 1]
        
        data1 = windows_data[w1]
        data2 = windows_data[w2]
        
        if len(data1) < 10 or len(data2) < 10:
            insufficient_overlap.append((w1, w2, "Insufficient data"))
            continue
        
        # Find min/max of each window
        min1, max1 = np.min(data1), np.max(data1)
        min2, max2 = np.min(data2), np.max(data2)
        
        # Calculate range and overlap
        range1 = max1 - min1
        range2 = max2 - min2
        
        overlap_min = max(min1, min2)
        overlap_max = min(max1, max2)
        
        if overlap_max <= overlap_min:
            insufficient_overlap.append((w1, w2, "No overlap"))
        else:
            overlap = overlap_max - overlap_min
            overlap_ratio1 = overlap / range1
            overlap_ratio2 = overlap / range2
            
            if overlap_ratio1 < min_overlap or overlap_ratio2 < min_overlap:
                insufficient_overlap.append((w1, w2, f"Overlap: {overlap:.3f} nm"))
    
    return insufficient_overlap

def main():
    parser = argparse.ArgumentParser(description='Analyze umbrella sampling windows and plot distributions')
    parser.add_argument('--folder', default='./', help='Path to the folder containing window directories')
    parser.add_argument('--prefix', default='window_', help='Prefix for window directories')
    parser.add_argument('--data-file', default='dist.dat', help='Name of the distance data file')
    parser.add_argument('--restraint-file', default='COM_prod.RST', help='Name of the restraint file')
    parser.add_argument('--output', default='window_distributions.png', help='Output file name for the plot')
    
    args = parser.parse_args()
    
    # Load data
    print(f"Loading data from {args.folder}...")
    windows_data = load_restraint_data(args.folder, args.prefix, args.data_file)
    
    if not windows_data:
        print("Error: No valid window data found. Check paths and file formats.")
        return
    
    # Get target distances
    target_distances = get_target_distances(args.folder, args.prefix, args.restraint_file)
    
    # Plot distributions
    fig = plot_window_distributions(windows_data, target_distances, args.output)
    
    # Analyze window quality
    print("\nAnalyzing window quality...")
    quality_df = analyze_window_quality(windows_data, target_distances)
    print(quality_df)
    
    # Check window overlap
    print("\nChecking window overlap...")
    insufficient_overlap = check_window_overlap(windows_data)
    
    if insufficient_overlap:
        print("Windows with insufficient overlap:")
        for w1, w2, reason in insufficient_overlap:
            print(f"  Window {w1} and Window {w2}: {reason}")
    else:
        print("All adjacent windows have sufficient overlap.")
    
    # Overall assessment
    good_windows = len(quality_df[quality_df['quality'] == 3])
    fair_windows = len(quality_df[quality_df['quality'] == 2])
    poor_windows = len(quality_df[quality_df['quality'] <= 1])
    
    print(f"\nOverall assessment:")
    print(f"  Total windows: {len(windows_data)}")
    print(f"  Good windows: {good_windows}")
    print(f"  Fair windows: {fair_windows}")
    print(f"  Poor windows: {poor_windows}")
    print(f"  Overlap issues: {len(insufficient_overlap)}")
    
    # Final recommendation
    if poor_windows > len(windows_data) / 3 or len(insufficient_overlap) > len(windows_data) / 3:
        print("\nRecommendation: The umbrella sampling appears to have significant issues.")
        print("Consider:")
        print("  1. Checking for simulation stability issues in window trajectories")
        print("  2. Adding more windows to improve coverage")
        print("  3. Using lower force constants to allow broader sampling in each window")
        print("  4. Extending simulation time for better sampling")
    elif fair_windows > len(windows_data) / 2:
        print("\nRecommendation: The umbrella sampling has moderate issues that should be addressed.")
        print("Consider:")
        print("  1. Extending simulations for poorly sampled windows")
        print("  2. Adding windows in regions with poor overlap")
    else:
        print("\nRecommendation: The umbrella sampling appears reasonable.")
        print("If WHAM is still failing, check:")
        print("  1. WHAM input format and parameters")
        print("  2. Whether the range of the reaction coordinate is well-covered")

if __name__ == "__main__":
    main()