# YouLoader: Professional Media Archiver

> **If this tool helps you build your ultimate archive, consider giving it a ⭐. This keeps the repo alive and the commits coming.**

> **And if it made your day a little easier (or at least didn’t crash your machine, we take those wins), you can drop a small tip to keep the coffee flowing ☕.**
> - **PayPal:** [vwakhungila10@gmail.com](mailto:vwakhungila10@gmail.com)
> - **Ethereum (ETH):** `0x37a6A9094867c331477EDa7D7A3c250D5ba5D048`

YouLoader is a high-performance, professional-grade archival system built to sync your favorite YouTube channels and playlists with surgical precision. Stop settling for low-quality rips—start building a robust, organized, and permanent media library today.

### Why YouLoader?
- **Crystal Clear Media:** Merges the highest quality video and audio streams into perfect, high-resolution `.mp4` files.
- **Audiophile's Dream:** Instantly convert music videos or long mixes into high-quality MP3s (up to 320kbps) with **embedded YouTube thumbnails as high-res album art** and full metadata.
- **Zero-Effort Organization:** Automatically sorts files into folders by Uploader, Playlist, Year, or Month.
- **Parallel Power:** Download entire playlists at lightning speed using multi-threaded concurrent downloads.
- **Smart History Sync:** Built-in archive system ensures you never download the same video twice.
- **Robust Cleanup:** Automatically detects and removes leftover `.part` or `.ytdl` files if a session is interrupted.
- **Zero Configuration:** The script automatically checks and installs missing Python dependencies on launch.

## Prerequisites

Before running YouLoader, you must have the following installed:

1.  **Python 3.7+**
2.  **FFmpeg**: Essential for merging high-quality video and audio streams.
    *   **Windows**: 
        1. Download FFmpeg essentials.
        2. Extract to `C:\ffmpeg`.
        3. Add `C:\ffmpeg\bin` to your **System Path** via Environment Variables.
        4. Verify by typing `ffmpeg -version` in CMD.
    *   **macOS**: `brew install ffmpeg`
    *   **Linux/wsl**: `sudo apt update && sudo apt install ffmpeg`

## Installation

Clone this repository and install the required dependencies: 

```bash
git clone git@github.com:Wakhungila/media-archiver.git
cd media-archiver

# Windows (CMD/PowerShell)
pip install -r requirements.txt --break-system-packages

# Linux/WSL
pip install -r requirements.txt --break-system-packages
```

## Usage
YouLoader can be run interactively or via direct CLI commands.

```bash
# Interactive Mode: Prompt for URL
python3 youloader.py

# Direct Mode: Pass URL and Options
python3 youloader.py "https://www.youtube.com/..." [OPTIONS]
```

### Options

| Option | Short | Description | Default |
| :--- | :--- | :--- | :--- |
| `--quality` | `-q` | Video quality: `480`, `720`, `1080`, or `max` | `720` |
| `--list` | `-l` | List content without downloading | `False` |
| `--sleep` | `-s` | Seconds to wait between downloads | `10` |
| `--archive` | `-a` | Path to the download history file | `archive.txt` |
| `--shorts` | | Include YouTube Shorts (filtered out by default) | `False` |
| `--no-live` | | Exclude past live streams | `True` |
| `--audio-only` | `-x` | Download audio only and convert to MP3 | `False` |
| `--bitrate` | `-b` | MP3 bitrate (e.g., 128, 192, 256, 320) | `192` |
| `--clean` | | Strip 'Official Video' from filenames | `True` |
| `--m3u` | | Generate a .m3u8 playlist file | `False` |
| `--organize` | | Organize by `year`, `month`, `time`, or `none` | `none` |
| `--retries` | `-r` | Number of retries for failed downloads | `10` |
| `--last-days` | | Download only videos from the last X days | `None` |
| `--start-date` | | Download videos on or after (YYYYMMDD) | `None` |
| `--end-date` | | Download videos on or before (YYYYMMDD) | `None` |
| `--keyword` | `-k` | Only download videos with this keyword | `None` |
| `--exclude` | `-e` | Exclude videos with this keyword | `None` |
| `--threads` | `-t` | Number of concurrent downloads | `1` |

### Examples

**Archive a playlist at 1080p:**
```bash
python youloader.py "https://www.youtube.com/playlist?list=..." --quality 1080
```

**Preview channel content without downloading:**
```bash
python youloader.py "https://www.youtube.com/@ChannelName" --list
```
---

## 🤝 Contributing

Contributions are welcome and appreciated. Whether you're fixing a bug, improving performance, or introducing new features, your work helps make **YouLoader** better for everyone.

### Workflow

1. **Fork the repository**
2. **Create a feature branch**

   ```bash
   git checkout -b feature/<scope>-<feature>
   ```
3. **Commit your changes**

   ```bash
   git commit -m "feat(<scope>): <short description>"
   ```
4. **Push to your fork**

   ```bash
   git push origin feature/<scope>-<feature>
   ```
5. **Open a Pull Request**

---

### Guidelines

* **Code Style**
  Follow PEP 8 conventions. Use clear, readable naming and keep functions modular.
  All terminal output should use `rich` to maintain a consistent CLI experience.

* **Feature Additions**

  * Update the CLI options documentation in the README
  * Include at least one usage example
  * Ensure backward compatibility where possible

* **Stability & Performance**

  * Test against existing multi-threading logic
  * Avoid introducing race conditions or blocking operations
  * Keep performance overhead minimal

* **Commit Messages**
  Use structured, meaningful messages:

  ```
  feat(download): add batch processing
  fix(cli): resolve argument parsing issue
  ```

---

### Review Expectations

Pull requests should be:

* Focused (one feature/fix per PR)
* Well-described (what + why)
* Tested before submission

---

### Code of Conduct

Be respectful, constructive, and collaborative. Good engineering includes good communication.

