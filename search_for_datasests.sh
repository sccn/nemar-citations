#!/bin/bash

# Initialize variables
SEARCH_DIR=""
PATTERN=""

# Function to show usage
usage() {
    echo "Usage: $0 -d <directory> -p <pattern>"
    exit 1
}

# Parse command-line options
while getopts "d:p:" opt; do
    case $opt in
        d) SEARCH_DIR=$OPTARG;;
        p) PATTERN="$OPTARG*";;
        *) usage;;
    esac
done

# Check if both arguments were provided
if [ -z "$SEARCH_DIR" ] || [ -z "$PATTERN" ]; then
    usage
fi

# Define the output file
OUTPUT_FILE="directories_list_feb.txt"

# Find directories matching the pattern at the first level
# and write only their names to the file
find "$SEARCH_DIR" -maxdepth 1 -type d -name "$PATTERN" | while read -r dir; do
    basename "$dir"
done > "$OUTPUT_FILE"
