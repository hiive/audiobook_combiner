#!/usr/bin/env python3
"""
Script Name: overwrite_chapters.py
Description: Overwrites the chapter information of an existing .m4b/.m4p audiobook file using a structured text file.
             The text file should contain lines with the chapter title followed by its duration, allowing for fractional seconds.
Usage:
    python overwrite_chapters.py -i <input_file.m4b> -c <chapters.txt> -o <output_file.m4b>
Example:
    python overwrite_chapters.py -i "MyAudiobook.m4b" -c "chapters.txt" -o "MyAudiobook_New.m4b"
"""

import os
import argparse
import subprocess
import json
import re
import sys
import shutil
from decimal import Decimal, InvalidOperation


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Overwrite chapters in an .m4b/.m4p audiobook file using a structured text file."
    )
    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Path to the input .m4b or .m4p file."
    )
    parser.add_argument(
        "-c", "--chapters",
        required=True,
        help="Path to the text file containing chapter titles and durations."
    )
    parser.add_argument(
        "-o", "--output",
        required=True,
        help="Path for the output .m4b or .m4p file with updated chapters."
    )
    return parser.parse_args()


def check_ffmpeg_installed():
    """Check if FFmpeg and FFprobe are installed and accessible."""
    missing = []
    for cmd in ['ffmpeg', 'ffprobe']:
        if not shutil.which(cmd):
            missing.append(cmd)
    if missing:
        print(f"Error: The following required tools are not installed or not found in PATH: {', '.join(missing)}")
        sys.exit(1)
    else:
        print("FFmpeg and FFprobe are installed.\n")


def parse_duration(duration_str):
    """
    Parse a duration string formatted as HH:MM:SS.ss or MM:SS.ss into total seconds (float).
    Examples:
        "01:26:43.50" -> 1*3600 + 26*60 + 43.50 = 5203.50 seconds
        "00:17.90"    -> 17.90 seconds
    """
    parts = duration_str.strip().split(':')
    try:
        if len(parts) == 3:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = Decimal(parts[2])
        elif len(parts) == 2:
            hours = 0
            minutes = int(parts[0])
            seconds = Decimal(parts[1])
        else:
            raise ValueError
    except (ValueError, InvalidOperation):
        print(f"Error: Invalid duration format '{duration_str}'. Use HH:MM:SS.ss or MM:SS.ss.")
        sys.exit(1)

    total_seconds = float(hours * 3600 + minutes * 60 + seconds)
    return total_seconds


def read_chapters(chapters_file):
    """
    Read the chapters from the text file.
    Each line should contain the chapter title followed by its duration.
    Example:
        Opening Credits 00:17.90
        Dedication 00:11.50
        Prologue 06:06.25
    Returns a list of tuples: [(title, duration_in_seconds), ...]
    """
    chapters = []
    with open(chapters_file, 'r', encoding='utf-8') as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue  # Skip empty lines or comments
            # Split the line into title and duration using the last whitespace as separator
            match = re.match(r'^(.*?)\s+(\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?)$', line)
            if not match:
                print(f"Error: Invalid format in line {line_number}: '{line}'")
                print("Each line should contain the chapter title followed by its duration, e.g.,")
                print("Opening Credits 00:17.90")
                sys.exit(1)
            title, duration_str = match.groups()
            duration_seconds = parse_duration(duration_str)
            chapters.append((title, duration_seconds))
    print(f"Successfully read {len(chapters)} chapters from '{chapters_file}'.\n")
    return chapters


def create_metadata_file(chapters, metadata_path):
    """
    Create an FFMETADATA1 file with the provided chapters.
    """
    with open(metadata_path, 'w', encoding='utf-8') as f:
        f.write(";FFMETADATA1\n")
        current_time = 0.0
        for idx, (title, duration) in enumerate(chapters, start=1):
            start = Decimal(current_time * 1000).quantize(Decimal('1'))
            end = Decimal((current_time + duration) * 1000).quantize(Decimal('1'))
            f.write("[CHAPTER]\n")
            f.write("TIMEBASE=1/1000\n")
            f.write(f"START={int(start)}\n")
            f.write(f"END={int(end)}\n")
            # Escape special characters in title
            escaped_title = title.replace('\\', '\\\\').replace(';', '\\;').replace('\n', '\\n').replace('\r', '\\r')
            f.write(f"title={escaped_title}\n\n")
            print(f"Chapter {idx}: '{title}' | Start: {format_time(current_time)} | Duration: {format_time(duration)}")
            current_time += duration
    print(f"\nMetadata file '{metadata_path}' created successfully.\n")


def apply_metadata(input_file, output_file, metadata_file):
    """
    Use FFmpeg to copy the input file to the output file and apply the new metadata.
    Includes '-map_chapters 1' to ensure chapters are mapped from the metadata file.
    """
    command = [
        "ffmpeg",
        "-y",  # Overwrite output file if it exists
        "-i", input_file,
        "-i", metadata_file,
        "-map_metadata", "1",  # Map global metadata from metadata_file
        "-map_chapters", "1",  # Map chapters from metadata_file
        "-codec", "copy",
        output_file
    ]
    print(f"Applying new chapter metadata to '{output_file}'...")
    try:
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("Metadata successfully applied.\n")
    except subprocess.CalledProcessError as e:
        print(f"Error: FFmpeg failed to apply metadata.\n{e.stderr.decode()}")
        sys.exit(1)


def format_time(seconds):
    """Convert seconds to H:MM:SS.ss or M:SS.ss format."""
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    # Format to two decimal places for fractional seconds
    if hours >= 1:
        return f"{int(hours)}:{int(minutes):02}:{secs:05.2f}"
    else:
        return f"{int(minutes)}:{secs:05.2f}"


def main():
    args = parse_arguments()
    input_file = args.input
    chapters_file = args.chapters
    output_file = args.output

    # Check if FFmpeg and FFprobe are installed
    check_ffmpeg_installed()

    # Check if input file exists
    if not os.path.isfile(input_file):
        print(f"Error: Input file '{input_file}' does not exist.")
        sys.exit(1)

    # Check if chapters file exists
    if not os.path.isfile(chapters_file):
        print(f"Error: Chapters file '{chapters_file}' does not exist.")
        sys.exit(1)

    # Read and parse chapters
    print(f"Reading chapters from '{chapters_file}'...")
    chapters = read_chapters(chapters_file)
    if not chapters:
        print("Error: No valid chapters found in the chapters file.")
        sys.exit(1)

    # Create metadata file
    metadata_file = "chapters_metadata.txt"
    print(f"Creating metadata file '{metadata_file}'...")
    create_metadata_file(chapters, metadata_file)

    # Apply metadata to create a new audiobook file
    apply_metadata(input_file, output_file, metadata_file)

    # Clean up metadata file
    try:
        os.remove(metadata_file)
        print(f"Cleaned up temporary metadata file '{metadata_file}'.")
    except OSError as e:
        print(f"Warning: Failed to delete temporary metadata file '{metadata_file}'. Error: {e}")

    print(f"\nNew audiobook with updated chapters saved as '{output_file}'.\n")


if __name__ == "__main__":
    main()