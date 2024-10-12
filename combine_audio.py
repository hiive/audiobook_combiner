#!/usr/bin/env python3
# Version 4.5

import os
import argparse
import subprocess
from glob import glob
import json
from decimal import Decimal, getcontext

def infer_book_name_and_extension():
    print("Inferring book name and extensions...")
    files = glob("*(*).mp3") + glob("*(*).m4a") + glob("*(*).aax")
    if not files:
        print("No part files found in the directory.")
        return None, None
    first_file = files[0]
    book_name = first_file.split("(")[0].strip()
    print(f"Book name inferred: '{book_name}'")
    return book_name, files

def get_files(book_name, files):
    print("Gathering list of part files...")
    book_files = [f for f in files if f.startswith(book_name)]
    try:
        sorted_files = sorted(book_files, key=lambda x: int(x.split("(")[-1].split(")")[0]))
    except ValueError as e:
        print(f"Error sorting files: {e}")
        return []
    print(f"Found {len(sorted_files)} part files.")
    return sorted_files

def get_audio_bitrate(file_path):
    print(f"Getting audio bitrate from '{file_path}'...")
    command = [
        "ffprobe",
        "-v", "quiet",
        "-show_entries", "format=bit_rate",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    bitrate_str = result.stdout.decode().strip()
    if bitrate_str and bitrate_str.isdigit():
        bitrate = int(bitrate_str)
        print(f"Input file bitrate: {bitrate} bps")
        return bitrate
    else:
        print("Could not determine input file bitrate.")
        return None

def map_bitrate_to_quality(bitrate):
    # Map input bitrate to approximate VBR quality level
    # This is an estimation; adjust the mapping as needed
    if bitrate >= 256000:
        return 0  # Best quality
    elif bitrate >= 192000:
        return 1
    elif bitrate >= 128000:
        return 2
    elif bitrate >= 96000:
        return 3
    elif bitrate >= 64000:
        return 4
    else:
        return 5  # Lowest quality


def map_bitrate_to_cbr(bitrate):
    # Map input bitrate to approximate CBR bitrate
    # This is an estimation; adjust the mapping as needed
    if bitrate >= 256000:
        return "256k"
    elif bitrate >= 192000:
        return "192k"
    elif bitrate >= 128000:
        return "128k"
    elif bitrate >= 96000:
        return "96k"
    elif bitrate >= 64000:
        return "64k"
    elif bitrate >= 32000:
        return "32k"
    else:
        return "96k"  # default

def get_common_metadata(file_paths):
    print("Collecting metadata from all input files...")
    metadata_list = []
    for file_path in file_paths:
        command = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            file_path
        ]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            data = json.loads(result.stdout.decode())
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from ffprobe output for '{file_path}': {e}")
            continue
        tags = data.get('format', {}).get('tags', {})
        metadata_list.append(tags)
    # Find common metadata entries
    common_metadata = {}
    if metadata_list:
        first_metadata = metadata_list[0]
        for key in first_metadata.keys():
            if all(key in md and md[key] == first_metadata[key] for md in metadata_list):
                common_metadata[key] = first_metadata[key]
    # Adjust 'track' metadata to '1'
    if 'track' in common_metadata:
        common_metadata['track'] = '1'
    print("Common metadata entries:")
    for key, value in common_metadata.items():
        print(f"  {key}: {value}")
    return common_metadata

def extract_cover_image(file_path):
    print(f"Extracting cover image from '{file_path}' (if any)...")
    command = [
        "ffmpeg",
        "-y",
        "-i", file_path,
        "-an",
        "-vcodec", "copy",
        "_temp_cover.jpg"
    ]
    subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if os.path.exists("_temp_cover.jpg") and os.path.getsize("_temp_cover.jpg") > 0:
        print("Cover image extracted successfully.")
        return "_temp_cover.jpg"
    else:
        if os.path.exists("_temp_cover.jpg"):
            os.unlink("_temp_cover.jpg")
        print("No cover image found or extraction failed.")
    return None

def generate_chapter_metadata(offsets, chapter_threshold, common_metadata, chapter_titles=None, chapter_file="_temp_chapters_metadata.txt"):
    print("Generating chapter metadata...")
    with open(chapter_file, "w", encoding='utf-8') as f:
        f.write(";FFMETADATA1\n")
        # Write common metadata entries
        for key, value in common_metadata.items():
            f.write(f"{key}={value}\n")
        total_parts = len(offsets)
        # Determine chapter naming based on threshold
        if total_parts < chapter_threshold:
            chapter_label = "Part"
        else:
            chapter_label = "Chapter"

        for index, (start_time, end_time) in enumerate(offsets):
            chapter_start_ms = int((start_time * 1000).quantize(Decimal('1')))
            chapter_end_ms = int((end_time * 1000).quantize(Decimal('1'))) if end_time is not None else ""
            f.write(f"\n[CHAPTER]\nTIMEBASE=1/1000\nSTART={chapter_start_ms}\n")
            if chapter_end_ms != "":
                f.write(f"END={chapter_end_ms}\n")
            else:
                f.write(f"END={chapter_start_ms}\n")
            # Use chapter title from provided list if available
            if chapter_titles and index < len(chapter_titles):
                title = chapter_titles[index]
            else:
                title = f"{chapter_label} {index + 1}"
            f.write(f"TITLE={title}\n")
            print(f"Added chapter '{title}': START={chapter_start_ms} ms")

def combine_files(book_name, files, vbr=False, vbr_quality=None, cbr_bitrate=None, sample_rate=None, chapter_threshold=6, chapter_titles=None, dry_run=False):
    print("Starting combination process...")
    part_files = get_files(book_name, files)
    if not part_files:
        print(f"No files found for '{book_name}'.")
        return False

    if dry_run:
        print(f"[Dry Run] Would combine the following files for '{book_name}':")
        for file in part_files:
            print(f"  {file}")
        return True

    if chapter_titles and len(chapter_titles) != len(part_files):
        print(f"Error: Number of chapter titles ({len(chapter_titles)}) does not match number of input files ({len(part_files)}).")
        return False

    output_file = f"{book_name}.m4b"

    # Extract cover image if available
    cover_image = extract_cover_image(part_files[0])

    # Determine encoding options
    input_bitrate = get_audio_bitrate(part_files[0])

    if vbr:
        if vbr_quality is not None:
            print(f"Using user-specified VBR quality level: {vbr_quality}")
        else:
            vbr_quality = map_bitrate_to_quality(input_bitrate)
            print(f"Estimated VBR quality level: {vbr_quality} based on input bitrate of {input_bitrate if input_bitrate else 'unknown'}.")
        bitrate_option = ["-q:a", str(vbr_quality)]
    else:
        if cbr_bitrate is not None:
            print(f"Using user-specified CBR bitrate: {cbr_bitrate}")
        else:
            cbr_bitrate = map_bitrate_to_cbr(input_bitrate)
            print(f"Estimated CBR bitrate: {cbr_bitrate} based on input bitrate of {input_bitrate if input_bitrate else 'unknown'}.")
        bitrate_option = ["-b:a", cbr_bitrate]

    # If sample_rate is specified, add it to the encoding options
    if sample_rate is not None:
        if sample_rate <= 0:
            print(f"Invalid sample rate specified: {sample_rate}. It must be a positive integer.")
            return False
        print(f"Setting output sample rate to: {sample_rate} Hz")
        sample_rate_option = ["-ar", str(sample_rate)]
    else:
        sample_rate_option = []

    # Re-encode each file individually to ensure consistent format and get accurate durations
    temp_files = []
    for index, input_file in enumerate(part_files):
        temp_file = f"_temp_{index}.m4b"
        command = [
            "ffmpeg",
            "-y",
            "-i", input_file,
            "-vn",
            "-c:a", "aac",
        ]
        command.extend(bitrate_option)
        command.extend(sample_rate_option)  # Add sample rate if specified
        command.append(temp_file)
        print(f"Re-encoding '{input_file}' to '{temp_file}'...")
        subprocess.run(command, check=True)
        temp_files.append(temp_file)

    # Create file list for concat demuxer
    file_list_path = "_temp_file_list.txt"
    with open(file_list_path, "w", encoding='utf-8') as f:
        for file in temp_files:
            f.write(f"file '{os.path.abspath(file)}'\n")

    # Build ffmpeg command using concat demuxer
    command = [
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", file_list_path,
    ]

    # Add cover image if available
    if cover_image:
        command.extend(["-i", cover_image])
        # Map the audio and cover image streams
        command.extend(["-map", "0:a", "-map", "1:v"])
        # Set the video codec to 'copy' to avoid re-encoding
        command.extend(["-c:v", "copy"])
        # Set disposition
        command.extend(["-disposition:v:0", "attached_pic"])
    else:
        # Map only the audio stream
        command.extend(["-map", "0:a"])

    # Set audio codec to 'copy' since we've re-encoded the parts
    command.extend(["-c:a", "copy"])

    # Add output file
    command.append(output_file)
    print(f"Final ffmpeg command: {' '.join(command)}")

    try:
        print(f"Combining files into '{output_file}'...")
        subprocess.run(command, check=True)
        print(f"Successfully created '{output_file}'")

        # Remove the file list
        os.remove(file_list_path)

        # Extract chapter start times from the concatenated file
        offsets = []
        previous_time = Decimal(0)
        getcontext().prec = 28
        for temp_file in temp_files:
            command_duration = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                temp_file
            ]
            result_duration = subprocess.run(command_duration, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            duration_str = result_duration.stdout.decode().strip()
            if not duration_str:
                print(f"Could not determine duration of '{temp_file}'. Skipping.")
                continue
            duration = Decimal(duration_str)
            start_time = previous_time
            previous_time += duration
            end_time = previous_time
            offsets.append((start_time, end_time))
            # Remove the temp file
            os.remove(temp_file)

        # Generate chapter metadata
        common_metadata = get_common_metadata(part_files)
        generate_chapter_metadata(offsets, chapter_threshold, common_metadata, chapter_titles)

        # Add chapters and metadata
        temp_output_file = output_file.replace('.m4b', '.tmp.m4b')
        final_command = [
            "ffmpeg", "-y",
            "-i", output_file,
            "-i", "_temp_chapters_metadata.txt",
            "-map_metadata", "1",
            "-map_chapters", "1",
            "-c", "copy",
            temp_output_file
        ]
        print(f"Final command for adding chapters and metadata: {' '.join(final_command)}")
        subprocess.run(final_command, check=True)
        print(f"Successfully added chapters and metadata.")

        # Replace the original file with the new file
        os.replace(temp_output_file, output_file)

        # Clean up temporary files
        os.remove("_temp_chapters_metadata.txt")
        if cover_image and os.path.exists(cover_image):
            os.unlink(cover_image)
        # Calculate and display size ratio
        input_size = sum(os.path.getsize(f) for f in part_files)
        output_size = os.path.getsize(output_file)
        if output_size > 0:
            size_ratio = input_size / output_size
            print(f"Total input size: {input_size} bytes")
            print(f"Output file size: {output_size} bytes")
            print(f"Size ratio (input/output): {size_ratio:.2f}")
        else:
            print("Output file size is zero. Cannot compute size ratio.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to combine files into '{output_file}'. Error: {e}")
        return False

def clean_files(book_name, files, dry_run=False):
    print("Starting cleanup process...")
    output_file = f"{book_name}.m4b"
    if os.path.exists(output_file):
        part_files = get_files(book_name, files)
        if dry_run:
            print(f"[Dry Run] Would delete the following part files for '{book_name}':")
            for file in part_files:
                print(f"  {file}")
            return
        print(f"Cleaning up part files for '{book_name}'...")
        for file in part_files:
            try:
                os.remove(file)
                print(f"Deleted '{file}'")
            except OSError as e:
                print(f"Error deleting '{file}': {e}")
        print("Part files deleted.")
    else:
        print(f"Cannot clean. '{output_file}' does not exist.")

def read_chapter_titles(chapter_titles_file):
    print(f"Reading chapter titles from '{chapter_titles_file}'...")
    chapter_titles = []
    try:
        with open(chapter_titles_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                # Remove prefix up to and including the first whitespace after the number
                # E.g., "1. Title" becomes "Title"
                import re
                match = re.match(r'^\s*\d+\S*\s+(.*)', line)
                if match:
                    title = match.group(1)
                else:
                    title = line
                chapter_titles.append(title)
    except FileNotFoundError:
        print(f"Error: Chapter titles file '{chapter_titles_file}' not found.")
        return None
    except Exception as e:
        print(f"Error reading chapter titles file '{chapter_titles_file}': {e}")
        return None
    print(f"Read {len(chapter_titles)} chapter titles.")
    return chapter_titles

def main():
    print("Audio Book Combiner Script - Version 4.5")
    parser = argparse.ArgumentParser(description="Combine and clean audio book parts.")
    parser.add_argument("--combine", action="store_true", help="Combine the parts into a single m4b file")
    parser.add_argument("--clean", action="store_true", help="Clean up part files if the final m4b exists")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without making any changes")
    parser.add_argument("--vbr", action="store_true", help="Use VBR encoding")
    parser.add_argument("--quality", type=int, choices=range(0, 6), metavar="[0-5]", help="Set VBR quality level (0=best, 5=worst)")
    parser.add_argument("--bitrate", type=str, help="Set CBR bitrate (e.g., 64k, 96k)")
    parser.add_argument("--sample-rate", type=int, help="Set output sample rate in Hz (e.g., 22050, 44100)")
    parser.add_argument("--chapter-threshold", type=int, default=6, help="Threshold for naming chapters as 'Part' or 'Chapter' (default: 6)")
    parser.add_argument("--chapter-titles-file", type=str, help="Specify a file containing chapter titles, one per line.")
    args = parser.parse_args()

    book_name, files = infer_book_name_and_extension()
    if not book_name or not files:
        print("Exiting due to missing book name or files.")
        return

    chapter_titles = None
    if args.chapter_titles_file:
        chapter_titles = read_chapter_titles(args.chapter_titles_file)
        if chapter_titles is None:
            print("Exiting due to error reading chapter titles.")
            return

    if args.combine:
        success = combine_files(
            book_name,
            files,
            vbr=args.vbr,
            vbr_quality=args.quality,
            cbr_bitrate=args.bitrate,
            sample_rate=args.sample_rate,  # Pass sample rate to combine_files
            chapter_threshold=args.chapter_threshold,
            chapter_titles=chapter_titles,
            dry_run=args.dry_run
        )
        if not success and not args.dry_run:
            print("Combination failed. Exiting.")
            return

    if args.clean:
        clean_files(book_name, files, dry_run=args.dry_run)

if __name__ == "__main__":
    main()