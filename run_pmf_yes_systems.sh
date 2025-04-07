#!/bin/bash

# Directory containing the bdp folders
BDP_DIR="/home/xuchen/rfmm/data/allbdps"
OUTPUT_DIR="/home/xuchen/rfmm/data/allbdps/pmf_summary"
# Path to the template pmf.py file - you should place your pmf.py file here
PMF_TEMPLATE="/home/xuchen/rfmm/data/allbdps/pmf.py"

# Create output directory for summary if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Exception list - add any bdp folders you want to skip to this array
EXCEPTIONS=("bdp0017" "bdp0025" "bdp0154" "bdp0218" "bdp1263")

# Function to check if a folder is in the exception list
is_exception() {
    local folder=$1
    for exception in "${EXCEPTIONS[@]}"; do
        if [ "$folder" == "$exception" ]; then
            return 0  # True, it's an exception
        fi
    done
    return 1  # False, it's not an exception
}

# Hardcoded list of bdp systems with 'yes' labels
YES_LABELED_SYSTEMS=(
    "bdp0017"
    "bdp0025"
    "bdp0148"
    "bdp0204"
    "bdp0218"
    "bdp0246"
    "bdp0320"
    "bdp0388"
    "bdp0417"
    "bdp0454"
    "bdp0485"
    "bdp0499"
    "bdp0527"
    "bdp0531"
    "bdp0542"
    "bdp0544"
    "bdp0569"
    "bdp0578"
    "bdp0581"
    "bdp0598"
    "bdp0622"
    "bdp0633"
    "bdp0668"
    "bdp0675"
    "bdp0692"
    "bdp0694"
    "bdp0900"
    "bdp0903"
    "bdp0907"
    "bdp0915"
    "bdp0923"
    "bdp0924"
    "bdp0933"
    "bdp0937"
    "bdp0938"
    "bdp0962"
    "bdp0963"
    "bdp0965"
    "bdp0970"
    "bdp0971"
    "bdp0972"
    "bdp0981"
    "bdp0992"
    "bdp0993"
    "bdp1210"
    "bdp1218"
    "bdp1226"
    "bdp1254"
    "bdp1263"
    "bdp1283"
    "bdp1505"
    "bdp1510"
    "bdp1511"
    "bdp1560"
    "bdp1592"
    "bdp1594"
    "bdp1595"
    "bdp1600"
    "bdp1603"
    "bdp1610"
    "bdp1614"
    "bdp1623"
    "bdp1625"
    "bdp1629"
    "bdp1630"
    "bdp1637"
    "bdp1698"
    "bdp1701"
    "bdp1705"
    "bdp1710"
    "bdp1727"
    "bdp1757"
    "bdp1763"
    "bdp1766"
    "bdp1772"
    "bdp1794"
    "bdp1809"
    "bdp1837"
    "bdp1842"
    "bdp1843"
    "bdp1845"
    "bdp1860"
    "bdp1865"
    "bdp1877"
    "bdp1887"
    "bdp1905"
    "bdp1914"
    "bdp1916"
    "bdp1919"
    "bdp1930"
    "bdp1937"
    "bdp1950"
    "bdp1953"
    "bdp1967"
    "bdp1972"
    "bdp1976"
    "bdp1993"
    "bdp1998"
    "bdp2003"
    "bdp2012"
    "bdp2045"
    "bdp2049"
    "bdp2054"
    "bdp2068"
    "bdp2070"
    "bdp2079"
    "bdp2080"
    "bdp2094"
    "bdp2099"
    "bdp2114"
    "bdp2124"
    "bdp2139"
    "bdp2141"
    "bdp2145"
    "bdp2167"
    "bdp2173"
    "bdp2176"
    "bdp2178"
    "bdp2185"
    # Add more systems with 'yes' labels here
)

# Make sure the BDP directory exists
if [ ! -d "$BDP_DIR" ]; then
    echo "Error: Directory $BDP_DIR does not exist!"
    exit 1
fi

# Make sure the pmf.py template exists
if [ ! -f "$PMF_TEMPLATE" ]; then
    echo "Error: PMF template file $PMF_TEMPLATE does not exist!"
    echo "Please create the PMF template file at $PMF_TEMPLATE or update the PMF_TEMPLATE variable."
    exit 1
fi

# Count for reporting progress
total=${#YES_LABELED_SYSTEMS[@]}
processed=0
skipped=0
failed=0
successful=0

echo "Starting to process $total bdp folders with 'yes' labels..."

# Process each system in the YES_LABELED_SYSTEMS array
for folder in "${YES_LABELED_SYSTEMS[@]}"; do
    folder_path="$BDP_DIR/$folder"
    
    # Increment counter for progress reporting
    processed=$((processed+1))
    
    # Check if the folder should be skipped due to exceptions
    if is_exception "$folder"; then
        echo "[$processed/$total] Skipping $folder (in exception list)"
        skipped=$((skipped+1))
        continue
    fi
    
    # Check if the folder exists
    if [ ! -d "$folder_path" ]; then
        echo "[$processed/$total] Warning: Folder $folder_path does not exist, skipping"
        skipped=$((skipped+1))
        continue
    fi
    
    echo "[$processed/$total] Processing $folder..."
    
    # Change to the folder and run the pmf.py script
    (
        cd "$folder_path" || { 
            echo "  Failed to change to directory $folder_path"
            failed=$((failed+1))
            return
        }
        
        # Copy the pmf.py template to the current directory
        echo "  Copying pmf.py to $folder..."
        cp "$PMF_TEMPLATE" ./pmf.py
        
        echo "  Running pmf.py in $folder..."
        if python pmf.py; then
            echo "  Successfully ran pmf.py in $folder"
            # Copy the PMF plot to the output directory with the folder name as prefix
            if [ -f "plot.png" ]; then
                cp plot.png "$OUTPUT_DIR/${folder}_pmf.png"
                successful=$((successful+1))
            else
                echo "  PMF plot was not generated in $folder"
                failed=$((failed+1))
            fi
        else
            echo "  Failed to run pmf.py in $folder"
            failed=$((failed+1))
        fi
    )
done

# Create a summary HTML file with all PMF images
echo "Creating PMF summary page..."
cat > "$OUTPUT_DIR/pmf_summary.html" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>PMF Summary for Yes-labeled BDP Systems</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .gallery { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
        .item { border: 1px solid #ddd; padding: 10px; text-align: center; }
        .item img { max-width: 100%; height: auto; }
        h1, h2 { color: #333; }
        .stats { margin: 20px 0; padding: 10px; background-color: #f5f5f5; border-radius: 5px; }
    </style>
</head>
<body>
    <h1>PMF Summary for Yes-labeled BDP Systems</h1>
    
    <div class="stats">
        <h2>Processing Statistics</h2>
        <p>Total systems: $total</p>
        <p>Successfully processed: $successful</p>
        <p>Skipped: $skipped</p>
        <p>Failed: $failed</p>
    </div>
    
    <h2>PMF Plots</h2>
    <div class="gallery">
EOF

# Add each image to the HTML file
for image in "$OUTPUT_DIR"/*_pmf.png; do
    if [ -f "$image" ]; then
        basename=$(basename "$image")
        system_name=${basename%_pmf.png}
        echo "        <div class=\"item\">" >> "$OUTPUT_DIR/pmf_summary.html"
        echo "            <h3>$system_name</h3>" >> "$OUTPUT_DIR/pmf_summary.html"
        echo "            <img src=\"$basename\" alt=\"PMF plot for $system_name\">" >> "$OUTPUT_DIR/pmf_summary.html"
        echo "        </div>" >> "$OUTPUT_DIR/pmf_summary.html"
    fi
done

# Finish the HTML file
cat >> "$OUTPUT_DIR/pmf_summary.html" << EOF
    </div>
</body>
</html>
EOF

echo "Processing complete!"
echo "Total 'yes' labeled folders: $total"
echo "Successfully processed: $successful"
echo "Skipped: $skipped"
echo "Failed: $failed"
echo "PMF summary available at: $OUTPUT_DIR/pmf_summary.html"

# Create a Python script to generate a composite summary figure
cat > "$OUTPUT_DIR/generate_summary_figure.py" << EOF
import os
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.gridspec import GridSpec
import matplotlib.image as mpimg
from math import ceil, sqrt

def generate_summary_figure():
    # Get all PMF images
    image_files = [f for f in os.listdir('.') if f.endswith('_pmf.png')]
    n_images = len(image_files)
    
    if n_images == 0:
        print("No PMF images found!")
        return
    
    # Calculate grid size (try to make it somewhat square)
    grid_size = ceil(sqrt(n_images))
    
    # Create figure with subplots
    fig = plt.figure(figsize=(15, 15))
    fig.suptitle('PMF Summary for All Yes-labeled Systems', fontsize=16)
    
    # Sort images by BDP number for consistent ordering
    image_files.sort()
    
    # Add each image to the grid
    for i, img_file in enumerate(image_files):
        if i >= grid_size * grid_size:
            break
            
        ax = plt.subplot(grid_size, grid_size, i+1)
        img = mpimg.imread(img_file)
        ax.imshow(img)
        
        # Extract system name from filename
        system_name = img_file.split('_')[0]
        ax.set_title(system_name, fontsize=8)
        ax.axis('off')
    
    plt.tight_layout(rect=[0, 0, 1, 0.96])  # Adjust for the suptitle
    plt.savefig('pmf_summary_figure.png', dpi=300, bbox_inches='tight')
    print("Generated summary figure: pmf_summary_figure.png")

if __name__ == "__main__":
    generate_summary_figure()
EOF

# Run the Python script to generate the summary figure
echo "Generating summary figure..."
(cd "$OUTPUT_DIR" && python generate_summary_figure.py)

echo "All tasks completed!" 