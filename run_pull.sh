#!/bin/bash

# Directory containing the bdp folders
BDP_DIR="/home/xuchen/rfmm/data/allbdps"
PYTHON_SCRIPT="/home/xuchen/rfmm/scripts/min_heat_equi_pull.py"

# Exception list - add any bdp folders you want to skip to this array
EXCEPTIONS=("bdp0017" "bdp0025")

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
total=10  # From bdp0000 to bdp0009 inclusive
processed=0
skipped=0
failed=0

echo "Starting to process $total bdp folders..."

# Loop through from 0 to 2200 (inclusive)
for i in $(seq -f "%04g" 1 10); do
    folder="bdp$i"
    folder_path="$BDP_DIR/$folder"
    
    # Increment counter for progress reporting
    processed=$((processed+1))
    
    # Check if the folder should be skipped
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
echo "Total folders: $total"
echo "Processed: $((processed-skipped-failed))"
echo "Skipped: $skipped"
echo "Failed: $failed"