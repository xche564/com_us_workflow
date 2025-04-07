#!/bin/bash

# Directory containing the bdp folders
BDP_DIR="/home/xuchen/rfmm/data/allbdps"
PYTHON_SCRIPT="/home/xuchen/rfmm/scripts/windows.py"

# Exception list - add any bdp folders you want to skip to this array
EXCEPTIONS=("bdp0017" "bdp0025" "bdp0154" "bdp0218" "bdp1263" "bdp2185")

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
# Replace these examples with your actual systems that have 'yes' labels
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

# Check if the Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "Error: Python script $PYTHON_SCRIPT does not exist!"
    exit 1
fi

# Count for reporting progress
total=${#YES_LABELED_SYSTEMS[@]}
processed=0
skipped=0
failed=0

echo "Starting to process $total bdp folders with 'yes' labels..."
export LD_LIBRARY_PATH=/home/shared_write/gcc/installation/lib64:$LD_LIBRARY_PATH
export PATH=/home/shared_write/gcc/installation/bin:$PATH


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
    
    # Change to the folder and run the Python script
    (
        cd "$folder_path" || { 
            echo "  Failed to change to directory $folder_path"
            failed=$((failed+1))
            return
        }
        
        echo "  Running Python script in $folder..."
        # Use "yes" to automatically answer "y" to any prompts
        if yes y | python "$PYTHON_SCRIPT"; then
            echo "  Successfully ran Python script in $folder"
        else
            echo "  Failed to run Python script in $folder"
            failed=$((failed+1))
        fi
    )
done

echo "Processing complete!"
echo "Total 'yes' labeled folders: $total"
echo "Processed: $((processed-skipped-failed))"
echo "Skipped: $skipped"
echo "Failed: $failed"