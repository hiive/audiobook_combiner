#!/usr/bin/env python3
"""
Script Name: extract_chapters.py
Version: 0.1
Description: Splits an input .m4b audiobook file into separate .m4b files for each chapter.
             Preserves original metadata and applies individual chapter metadata.
             Output files are named sequentially as "<book title> (n).m4b", where n is the chapter number.
             If the input .m4b contains only one chapter, no extraction or display is performed.
             Additionally, a '--display' flag can be used to display the full chapter structure without performing extraction.
             Chapters with a duration less than 1 second are skipped in both extraction and display.
Usage:
    - To Extract Chapters:
        python extract_chapters.py -i <input_file.m4b> -o <output_directory>
    - To Display Chapter Structure:
        python extract_chapters.py -i <input_file.m4b> -d
    Example:
        python extract_chapters.py -i "MyAudiobook.m4b" -o "./Chapters"
        python extract_chapters.py -i "MyAudiobook.m4b" -d
"""

import os
import argparse
import copy
import subprocess
import json
import re
import sys
import shutil


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Split an .m4b audiobook into separate chapters with preserved metadata."
    )
    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Path to the input .m4b file."
    )
    parser.add_argument(
        "-o", "--output",
        help="Directory to save the extracted chapter files."
    )
    parser.add_argument(
        "-d", "--display",
        action="store_true",
        help="Display the full chapter structure of the input file without extracting chapters."
    )
    return parser.parse_args()


def check_ffmpeg_installed():
    """Check if FFmpeg and FFprobe are installed and accessible."""
    for cmd in ['ffmpeg', 'ffprobe']:
        if not shutil.which(cmd):
            sys.exit(1)


def get_metadata(input_file):
    """Retrieve metadata and chapter information from the input .m4b file."""
    # Get general metadata
    metadata_command = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        input_file
    ]
    metadata_result = subprocess.run(metadata_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        metadata = json.loads(metadata_result.stdout.decode())
    except json.JSONDecodeError:
        sys.exit(1)

    # Extract tags
    tags = metadata.get('format', {}).get('tags', {})

    # Get chapters
    chapters_command = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_chapters",
        input_file
    ]
    chapters_result = subprocess.run(chapters_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        chapters = json.loads(chapters_result.stdout.decode())
    except json.JSONDecodeError:
        sys.exit(1)

    return tags, chapters.get('chapters', [])


def sanitize_filename(name):
    """Sanitize the filename by removing or replacing invalid characters."""
    return re.sub(r'[\\/*?:"<>|]', '', name)


def build_chapter_hierarchy(chapters):
    """
    Build a hierarchical structure of chapters based on their start and end times.
    This function assumes that parent chapters fully encompass their subchapters.
    """
    sorted_chapters = sorted(chapters, key=lambda x: float(x.get('start_time', 0)))
    hierarchy = []
    stack = []

    for chapter in sorted_chapters:
        chapter_start = float(chapter.get('start_time', 0))
        chapter_end = float(chapter.get('end_time', 0))
        node = {
            'title': chapter.get('tags', {}).get('title', f"Chapter {chapter.get('id', 'Unknown')}"),
            'start_time': chapter_start,
            'end_time': chapter_end,
            'subchapters': []
        }

        # Determine where to place this chapter in the hierarchy
        while stack and chapter_start >= stack[-1]['end_time']:
            stack.pop()

        if stack:
            stack[-1]['subchapters'].append(node)
        else:
            hierarchy.append(node)

        stack.append(node)

    return hierarchy


def display_chapter_hierarchy(hierarchy, level=0):
    """
    Recursively display the chapter hierarchy with indentation representing nesting levels.
    """
    for chapter in hierarchy:
        indent = "  " * level
        duration = chapter['end_time'] - chapter['start_time']
        print(f"{indent}- {chapter['title']} (Start: {chapter['start_time']}s, Duration: {duration}s)")
        if chapter['subchapters']:
            display_chapter_hierarchy(chapter['subchapters'], level + 1)


class ChapterExtractor:
    def __init__(self, input_file, output_dir, book_title, file_prefix):
        self.input_file = os.path.abspath(input_file)
        self.output_dir = os.path.abspath(output_dir)
        self.book_title = sanitize_filename(book_title)
        self.file_prefix = file_prefix
        self.chapter_counter = 1
        self.chapter_names = []  # List to store names of extracted chapters
        self.processed_chapters = set()  # To avoid processing chapters with same title and time ranges

    def extract_chapters(self):
        """Extract all chapters and return their names."""
        tags, chapters = get_metadata(self.input_file)

        if not chapters:
            return []

        # Check if there's only one chapter with duration >=1s
        filtered_chapters = [c for c in chapters if float(c.get('end_time', 0)) - float(c.get('start_time', 0)) >= 1.0]
        if len(filtered_chapters) <= 1:
            return []

        for chapter in filtered_chapters: # [:6]:
            chapter_tags = chapter.get('tags', {})
            chapter_title = chapter_tags.get('title', f"Chapter {chapter.get('id', 'Unknown')}")
            start_time = float(chapter.get('start_time', 0))
            end_time = float(chapter.get('end_time', 0))
            duration = end_time - start_time

            # Skip chapters with duration less than 1 second
            if duration < 1.0:
                print("Shouldn't happen.")
                continue

            # Define a unique key for the chapter based on title and time range
            chapter_key = (chapter_title, start_time, end_time)
            if chapter_key in self.processed_chapters:
                print(f"{chapter_title} already processed." )
                continue
            self.processed_chapters.add(chapter_key)

            # Define output filename
            sanitized_title = sanitize_filename(chapter_title)
            output_filename = f"{self.book_title}[{self.file_prefix}] ({self.chapter_counter}).m4b"
            output_path = os.path.join(self.output_dir, output_filename)
            print(f"Processing {sanitized_title} : {output_filename}...")

            # Extract the chapter
            ffmpeg_command = [
                "ffmpeg",
                "-y",  # Overwrite without asking
                "-i", self.input_file,
                "-ss", f"{start_time}",
                "-t", f"{duration}",
                "-c", "copy",
                "-metadata", f"title={chapter_title}",
                output_path
            ]

            try:
                subprocess.run(ffmpeg_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.chapter_names.append(output_filename)
                self.chapter_counter += 1
            except subprocess.CalledProcessError:
                continue

        return self.chapter_names


def extract_chapters(input_file, output_dir, file_prefix):
    """
    Extract chapters from the given .m4b file and save them to the output directory.

    Parameters:
        input_file (str): Path to the input .m4b file.
        output_dir (str): Directory to save the extracted chapter files.

    Returns:
        list: A list of filenames for the extracted chapters.
    """
    # Check if FFmpeg and FFprobe are installed
    check_ffmpeg_installed()

    # Check if input file exists
    if not os.path.isfile(input_file):
        print(f"Input file not found: {input_file}")
        return []

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Retrieve metadata and chapters
    tags, chapters = get_metadata(input_file)

    # Filter chapters with duration >=1s
    filtered_chapters = [c for c in chapters if float(c.get('end_time', 0)) - float(c.get('start_time', 0)) >= 1.0]

    # If one or no chapters with duration >=1s, do nothing
    if len(filtered_chapters) <= 1:
        return []

    # Get book title from metadata
    book_title = tags.get('title', 'Untitled')

    # Initialize the ChapterExtractor
    extractor = ChapterExtractor(input_file, output_dir, book_title, file_prefix)

    # Start the extraction process and return the list of chapter names
    return extractor.extract_chapters()


def display_chapters(input_file):
    """
    Display the full chapter structure of the input .m4b file, including nested chapters.
    Skips chapters with duration less than 1 second.

    Parameters:
        input_file (str): Path to the input .m4b file.
    """
    tags, chapters = get_metadata(input_file)

    if not chapters:
        return

    # Filter out chapters with duration less than 1 second
    filtered_chapters = [c for c in chapters if float(c.get('end_time', 0)) - float(c.get('start_time', 0)) >= 1.0]

    # If there are no chapters after filtering, do nothing
    if not filtered_chapters:
        return

    book_title = tags.get('format', {}).get('tags', {}).get('title', 'Untitled')
    print(f"Book Title: {book_title}")
    print(f"Total Chapters: {len(filtered_chapters)}\n")

    hierarchy = build_chapter_hierarchy(filtered_chapters)
    display_chapter_hierarchy(hierarchy)

def recurse_extract_chapters(chapter_names, input_file, output_dir, depth):
    chapters_to_examine = extract_chapters(input_file=input_file, output_dir=output_dir, file_prefix=f"{depth}")

    chapters_copy = copy.deepcopy(chapters_to_examine)

    for i in range(len(chapters_to_examine)):
        chapter_name = chapters_copy[i]

        chapter_file = f"{output_dir}{os.sep}{chapter_name}"
        sub_chapters = recurse_extract_chapters(chapter_names=chapter_name,
                                                input_file=chapter_file,
                                                output_dir=output_dir,
                                                depth=depth + 1)
        print(f"{depth}: Chapter {i + 1}: {chapter_name}")


    return chapter_names


def extract_all_chapters(input_file, output_dir):

    chapter_names = extract_chapters(input_file=input_file, output_dir=output_dir, file_prefix="0")
    if chapter_names:
        for name in chapter_names:
            # chapter_file = f"{output_dir}{os.sep}{name}"
            # sub_chapters = recurse_extract_chapters(chapter_names=chapter_names,
            #                          input_file=chapter_file,
            #                          output_dir=output_dir,
            #                          depth=1)
            print(f"Chapter {name} extracted.")
    pass

# The following block is only executed when running the script directly
if __name__ == "__main__":
    args = parse_arguments()

    if args.display:
        # Display chapter structure and exit if there is at least one chapter with duration >=1s
        tags, chapters = get_metadata(input_file=args.input)
        filtered_chapters = [c for c in chapters if float(c.get('end_time', 0)) - float(c.get('start_time', 0)) >= 1.0]
        if len(filtered_chapters) >= 1:
            display_chapters(input_file=args.input)
    else:
        if not args.output:
            sys.exit(1)
        extract_all_chapters(input_file=args.input, output_dir=args.output)
        # If no chapters extracted, do nothing