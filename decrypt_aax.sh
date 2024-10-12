#!/bin/bash

# Script Name: decrypt_aax.sh
# Description: Converts all .aax files in the current directory to .m4b format using FFmpeg.
#              Requires activation bytes for decrypting Audible AAX files.
# Usage: ./decrypt_aax.sh --activation-bytes <activation_bytes>
# Example: ./decrypt_aax.sh --activation-bytes a0b1b2c3

# Function to display usage information
usage() {
  echo "Usage: $0 --activation-bytes <activation_bytes> [options]"
  echo ""
  echo "Options:"
  echo "  --activation-bytes, -a <bytes>    Required. Secret bytes for Audible AAX files."
  echo "  --help, -h                        Display this help message."
  echo ""
  echo "Example:"
  echo "  $0 --activation-bytes a0b1c2d3"
}

# Initialize variables
activation_bytes=""

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --activation-bytes|-a)
      if [[ -n "$2" && ! "$2" =~ ^- ]]; then
        activation_bytes="$2"
        shift 2
      else
        echo "Error: --activation-bytes requires a non-empty option argument."
        usage
        exit 1
      fi
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      usage
      exit 1
      ;;
  esac
done

# Check if activation_bytes was provided
if [[ -z "$activation_bytes" ]]; then
  echo "Error: --activation-bytes is required."
  usage
  exit 1
fi

# Check if FFmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
  echo "Error: FFmpeg is not installed or not found in PATH."
  echo "Please install FFmpeg and ensure it's accessible from the command line."
  exit 1
fi

# Loop through all .aax files in the current directory
shopt -s nullglob
aax_files=(*.aax)

if [[ ${#aax_files[@]} -eq 0 ]]; then
  echo "No .aax files found in the current directory."
  exit 0
fi

for file in "${aax_files[@]}"; do
  # Remove the .aax extension to get the base filename
  base_filename="${file%.aax}"

  # Define output filename
  output_file="${base_filename}.m4b"

  echo "Converting '$file' to '$output_file'..."

  # Run the ffmpeg command with the specified activation bytes and output as .m4b
  ffmpeg -y -activation_bytes "$activation_bytes" -i "$file" -codec copy -map_chapters 0 "$output_file"
  
  if [ $? -eq 0 ]; then
    echo "Successfully converted '$file' to '$output_file'."
    
    # Remove the original .aax file
    rm "$file"
    echo "Removed original file '$file'."
  else
    echo "Failed to convert '$file'."
  fi
  
  echo "----------------------------------------"
done