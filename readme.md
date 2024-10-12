# Audio Book Combiner Script

An efficient Python script to combine audiobook parts into a single .m4b file with accurate chapters and embedded cover art. The script supports both Constant Bitrate (CBR) and Variable Bitrate (VBR) encoding, allows custom chapter titles, and preserves common metadata from the input files.

## Features

- Combine Multiple Audio Files: Merges multiple audiobook parts into a single .m4b file.
- Accurate Chapter Timing: Generates chapters with precise start and end times.
- Custom Chapter Titles: Supports specifying custom chapter titles through a text file.
- Cover Art Inclusion: Extracts and embeds the cover image from the first input file.
- Metadata Preservation: Retains common metadata (e.g., title, artist) from the input files.
- Encoding Options: Supports both VBR and CBR encoding with user-specified quality or bitrate.
- Error Handling: Provides informative messages for missing files, mismatched chapter titles, and other errors.
- Cross-Platform: Works on Windows, macOS, and Linux.

## Prerequisites

- Python 3.6 or higher: Make sure Python is installed on your system.
- FFmpeg and FFprobe: The script relies on FFmpeg and FFprobe for audio processing.

### Installing FFmpeg and FFprobe

#### macOS

You can install FFmpeg and FFprobe using Homebrew:

Install Homebrew if not already installed
`/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`

Install FFmpeg (includes FFprobe)
`brew install ffmpeg`

####  Windows

Download the pre-built binaries:

1.	Go to the FFmpeg download page and choose a Windows build (e.g., from gyan.dev).
2. Download the “Essentials” or “Full” build. 
3. Extract the downloaded ZIP file. 
4. Add the bin folder (which contains ffmpeg.exe and ffprobe.exe) to your system’s PATH environment variable.

#### Linux

Install FFmpeg using your distribution’s package manager:

**Ubuntu/Debian:**

`sudo apt update`
`sudo apt install ffmpeg`


**Fedora:**

`sudo dnf install ffmpeg`


**Arch Linux:**

`sudo pacman -S ffmpeg`



## Installation

1. Clone the Repository:

    `git clone https://github.com/hiive/audiobook-combiner.git`


2. Navigate to the Directory:

    `cd audiobook-combiner`


4. Make the Script Executable (Optional):

    On Unix-based systems:

    `chmod +x combine_audio.py`



## Usage

### Basic Command

`python combine_audio.py --combine`

Or, if the script is executable:

`./combine_audio.py --combine`

### Command-Line Options

- `--combine`: Combine the audiobook parts into a single .m4b file.
- `--clean`: Delete the original part files after combining (if the final .m4b exists).
- `--dry-run`: Perform a dry run without making any changes.
- `--vbr`: Use Variable Bitrate (VBR) encoding. (Default: Disabled)
- `--quality [0-5]`: Set VBR quality level (0=best, 5=worst). (Default: Estimated based on input bitrate)
- `--bitrate BITRATE`: Set Constant Bitrate (CBR) (e.g., 64k, 96k). (Default: Estimated based on input bitrate)
- `--chapter-threshold NUMBER`: Threshold for naming chapters as ‘Part’ or ‘Chapter’. (Default: 6)
- `--chapter-titles-file FILE`: Specify a file containing chapter titles, one per line.
-   `--sample-rate SAMPLE_RATE`: Set the output sample rate in Hz (e.g., `22050`, `44100`). (Default: Retains input file's sample rate)	
-   `--help`: Show help message and exit.

## Preparing Your Audio Files

- Naming Convention: Name your audiobook part files in the format Book Name (1).mp3, Book Name (2).mp3, etc.
- Supported Formats: Input files can be in .mp3 or .m4a format.
- Directory: Place all part files in the same directory as the script.

### Examples

#### Combine Files with Default Settings

`python combine_audio.py --combine`

- Default Behavior:
  - Uses CBR encoding.
  - CBR bitrate is estimated based on the input file’s bitrate.
  - Chapters are named ‘Part’ or ‘Chapter’ based on the default threshold (6).

#### Combine Files Using VBR Encoding

`python combine_audio.py --combine --vbr`

- Default VBR Quality: Estimated based on the input file’s bitrate.

#### Combine Files with Specific VBR Quality

`python combine_audio.py --combine --vbr --quality 2`

- VBR Quality Level: Sets the quality to level 2 (0=best, 5=worst).

#### Combine Files with Specific CBR Bitrate

`python combine_audio.py --combine --bitrate 64k`

- CBR Bitrate: Sets the bitrate to 64 kbps.

#### Combine Files with Custom Chapter Titles

1.	Create a Chapter Titles File (e.g., chapter_titles.txt):
```
1. Introduction
2. Getting Started
3. Advanced Topics
4. Conclusion
```

2.	Run the Script:

`python combine_audio.py --combine --chapter-titles-file chapter_titles.txt`

- Note: The number of chapter titles must match the number of input files.

#### Combine Files with Specific Sample Rate

You can specify the output sample rate using the `--sample-rate` flag. Common sample rates include `22050`, `44100`, `48000`, etc.

**Example:**

`python combine_audio.py --combine --sample-rate 22050`

#### Perform a Dry Run

`python combine_audio.py --combine --dry-run`

- Dry Run: Simulates the combination process without creating or modifying files.

#### Clean Up Part Files After Combining

`python combine_audio.py --clean`

 - Clean Up: Deletes the original part files if the final .m4b file exists.

### Detailed Explanation of Options

- `--combine`: Initiates the combining process.
- `--clean:` Deletes the original part files if the final .m4b file exists.
- `--dry-run`: Simulates the combination process without actual file operations.
- `--vbr`: Enables Variable Bitrate encoding for the output file. Default: Disabled (uses CBR encoding).
- `--quality`: Sets the VBR quality level when `--vbr` is used. Accepts values from 0 (best) to 5 (worst).  Default: Estimated based on the input file’s bitrate if not specified.
- `--bitrate`: Sets the Constant Bitrate for the output file (e.g., 64k, 128k).  Default: Estimated based on the input file’s bitrate if not specified.
- `--chapter-threshold`: Determines whether to label chapters as ‘Part’ or ‘Chapter’ based on the number of parts. Default: `6`
  - Behavior:
      - If the number of parts is less than the threshold, chapters are labeled as ‘Part 1’, ‘Part 2’, etc.
      -	If the number of parts is equal to or greater than the threshold, chapters are labeled as ‘Chapter 1’, ‘Chapter 2’, etc.
      -	`--chapter-titles-file`: Specifies a text file containing custom chapter titles, one per line.
  - Note:
       - The number of lines in the chapter titles file must match the number of input files.
       - Lines starting with a number and a period (e.g., `1. Title`) will have the number and period removed.
- `--sample-rate SAMPLE_RATE`: Sets the output sample rate for the audio in Hertz (Hz). Specify the desired sample rate for the output `.m4b` file. Common values include `22050` (lower quality, smaller file size), `44100` (CD quality), and `48000` (commonly used in video audio tracks).
  - **Usage Considerations:**
    - **Quality vs. File Size:*- Lower sample rates reduce file size but may degrade audio quality. Choose a sample rate that balances your quality requirements with file size constraints.
    - **Compatibility:*- Ensure that the chosen sample rate is compatible with your playback devices and preferences.
    - **Default Behavior:*- If not specified, the script retains the sample rate of the input files to maintain original audio quality.
- `--help`: Displays the help message with descriptions of all options.

## Notes and Tips

- Audio Format Consistency: The script re-encodes all input files to ensure consistent audio format and compatibility with the .m4b container.
- Cover Art: The cover image is extracted from the first input file if available and embedded into the final .m4b file.
- Metadata Preservation: Common metadata from the input files is retained in the output file.
- Temporary Files: The script creates temporary files prefixed with _temp_. These are cleaned up after processing.
- Estimated Bitrate and Quality: If you do not specify --quality or --bitrate, the script estimates them based on the bitrate of the first input file.
- VBR Quality Estimation:
  - Bitrate ≥ 256 kbps: Quality level 0 (best)
  - Bitrate ≥ 192 kbps: Quality level 1
  - Bitrate ≥ 128 kbps: Quality level 2
  - Bitrate ≥ 96 kbps: Quality level 3
  - Bitrate ≥ 64 kbps: Quality level 4
  - Bitrate < 64 kbps: Quality level 5 (lowest)
- CBR Bitrate Estimation:
  - Bitrate ≥ 256 kbps: 256k
  - Bitrate ≥ 192 kbps: 192k
  - Bitrate ≥ 128 kbps: 128k
  - Bitrate ≥ 96 kbps: 96k
  - Bitrate ≥ 64 kbps: 64k
  - Bitrate < 64 kbps: 48k
- Sample Rate Impact:
  - Lower Sample Rates (e.g., `22050` Hz):*- Reduce file size but may result in lower audio quality. Suitable for environments where storage space is limited.
  - Standard Sample Rates (e.g., `44100` Hz):*- Offer a balance between audio quality and file size, matching CD quality.
  - Higher Sample Rates (e.g., `48000` Hz):*- Provide better audio fidelity, commonly used in professional audio and video production.

## Troubleshooting

- Mismatched Chapter Titles: If you receive an error about mismatched chapter titles, ensure that the number of titles in your chapter titles file matches the number of input files.
- Missing FFmpeg or FFprobe: If the script cannot find FFmpeg or FFprobe, make sure they are installed and added to your system’s PATH environment variable.
- File Not Found Errors: Ensure that your audio files are named correctly and placed in the same directory as the script.
- Permission Issues: If you encounter permission errors, you may need to run the script with elevated privileges or adjust file permissions.
- Encoding Errors: If the script fails during the encoding process, check that your input files are not corrupted and are in a supported format.

## License

This project is licensed under the MIT License.

## Acknowledgments

- FFmpeg: A complete, cross-platform solution to record, convert and stream audio and video.
- Python: A versatile programming language that makes this script possible.

Feel free to contribute to this project by opening issues or submitting pull requests on GitHub.

## Postscript
[This](https://audible-tools.kamsker.at/) link might be useful for anyone wanting to take advantage of the
`decrypt_aax.sh` file in this repository. For testing and research purposes only, of course!

Also, [this](https://github.com/audible-tools/audible-tools.github.io) link if you're curious how it works.