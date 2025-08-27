#!/bin/bash

# Directory to analyze
DIR="data/wikipedia/pages"

echo "=== Top 10 Largest Files in $DIR ==="
echo

# Find and display top 10 largest files
find "$DIR" -type f -exec ls -lh {} \; | sort -k5 -rh | head -10 | awk '{printf "%10s  %s\n", $5, $9}'

echo
echo "=== File Size Statistics ==="
echo

# Calculate average file size
total_size=0
file_count=0

while IFS= read -r size; do
    total_size=$((total_size + size))
    file_count=$((file_count + 1))
done < <(find "$DIR" -type f -exec stat -f%z {} \;)

if [ $file_count -gt 0 ]; then
    avg_size=$((total_size / file_count))
    # Convert to human-readable format
    if [ $avg_size -gt 1048576 ]; then
        avg_human=$(echo "scale=2; $avg_size / 1048576" | bc)
        echo "Average file size: ${avg_human} MB"
    elif [ $avg_size -gt 1024 ]; then
        avg_human=$(echo "scale=2; $avg_size / 1024" | bc)
        echo "Average file size: ${avg_human} KB"
    else
        echo "Average file size: $avg_size bytes"
    fi
    echo "Total files: $file_count"
    echo "Total size: $(echo "scale=2; $total_size / 1048576" | bc) MB"
else
    echo "No files found in $DIR"
fi