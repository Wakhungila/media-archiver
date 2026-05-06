# YouLoader: Professional Media Archiver

> **If this tool helps you build your ultimate archive, consider giving it a ⭐. This keeps the repo alive and the commits coming.**

> **And if it made your day a little easier (or at least didn’t crash your machine, we take those wins), you can drop a small tip to keep the coffee flowing ☕.**
> - **PayPal:** [vwakhungila10@gmail.com](mailto:vwakhungila10@gmail.com)
> - **Ethereum (ETH):** `0x37a6A9094867c331477EDa7D7A3c250D5ba5D048`

YouLoader is a high-performance, professional-grade archival system built to sync your favorite YouTube channels and playlists with surgical precision. Stop settling for low-quality rips — start building a robust, organized, and permanent media library today.

### Why YouLoader?

- **Crystal Clear Media:** Merges the highest quality video and audio streams into perfect, high-resolution `.mp4` files.
- **Audiophile's Dream:** Instantly convert music videos or long mixes into high-quality MP3s (up to 320kbps) with **embedded YouTube thumbnails as high-res album art** and full metadata.
- **Zero-Effort Organization:** Automatically sorts files into folders by Uploader, Playlist, Year, or Month.
- **Parallel Power:** Download entire playlists at lightning speed using multi-threaded concurrent downloads.
- **Smart History Sync:** Built-in archive system ensures you never download the same video twice.
- **Robust Cleanup:** Automatically detects and removes leftover `.part` or `.ytdl` files if a session is interrupted.
- **Zero Configuration:** The script automatically checks and installs missing Python dependencies on launch.

---

## Prerequisites

Before running YouLoader, you must have the following installed:

1. **Python 3.7+**
2. **FFmpeg** — essential for merging high-quality video and audio streams.

   | Platform | Install Command |
   | :--- | :--- |
   | **Windows** | Download from [ffmpeg.org](https://ffmpeg.org/download.html), extract to `C:\ffmpeg`, and add `C:\ffmpeg\bin` to your System PATH. Verify with `ffmpeg -version` in CMD. |
   | **macOS** | `brew install ffmpeg` |
   | **Linux / WSL** | `sudo apt update && sudo apt install ffmpeg` |

---

## Installation

```bash
<<<<<<< HEAD
git clone https://github.com/Wakhungila/media-archiver.git
cd media-archiver

# Windows (CMD / PowerShell)
pip install -r requirements.txt
=======
git clone git@github.com:Wakhungila/media-archiver.git
cd media-archiver

# Windows (CMD/PowerShell)
pip install -r requirements.txt --break-system-packages
>>>>>>> d8ff4984e6fe8348ec472fbcbc0394bee1442027

# Linux / WSL / macOS
pip install -r requirements.txt --break-system-packages
```

---

## Usage

YouLoader can be run interactively or via direct CLI commands.

```bash
# Interactive mode — prompts for a URL
python3 youloader.py

# Direct mode — pass URL and options inline
python3 youloader.py "https://www.youtube.com/..." [OPTIONS]
```

### Options

| Option | Short | Description | Default |
| :--- | :---: | :--- | :---: |
| `--quality` | `-q` | Video quality: `480`, `720`, `1080`, or `max` | `720` |
| `--list` | `-l` | List content without downloading | `False` |
| `--sleep` | `-s` | Seconds to wait between downloads | `10` |
| `--archive` | `-a` | Path to the download history file | `archive.txt` |
| `--shorts` | | Include YouTube Shorts (filtered out by default) | `False` |
| `--live / --no-live` | | Include or exclude past live streams | `True` |
| `--audio-only` | `-x` | Download audio only and convert to MP3 | `False` |
| `--bitrate` | `-b` | MP3 bitrate in kbps: `128`, `192`, `256`, `320` | `192` |
| `--clean / --no-clean` | | Strip `Official Video`, `[4K]`, etc. from filenames | `True` |
| `--m3u` | | Generate a `.m3u8` playlist file after downloading | `False` |
| `--organize` | | Organise output by `year`, `month`, `time`, or `none` | `none` |
| `--retries` | `-r` | Number of retries for failed downloads | `10` |
| `--last-days` | | Only download videos from the last X days | `None` |
| `--start-date` | | Download videos on or after this date (`YYYYMMDD`) | `None` |
| `--end-date` | | Download videos on or before this date (`YYYYMMDD`) | `None` |
| `--keyword` | `-k` | Only download videos whose title contains this keyword | `None` |
| `--exclude` | `-e` | Skip videos whose title contains this keyword | `None` |
| `--threads` | `-t` | Number of concurrent downloads (values > 4 risk rate-limiting) | `1` |

### Examples

**Archive a playlist at 1080p:**
```bash
python youloader.py "https://www.youtube.com/playlist?list=..." --quality 1080
```

**Preview channel content without downloading:**
```bash
python youloader.py "https://www.youtube.com/@ChannelName" --list
```

**Download audio-only at 320kbps with embedded album art:**
```bash
python youloader.py "https://www.youtube.com/playlist?list=..." --audio-only --bitrate 320
```

**Download the last 30 days of uploads, organized by year:**
```bash
python youloader.py "https://www.youtube.com/@ChannelName" --last-days 30 --organize year
```

**Parallel download with 3 threads:**
```bash
python youloader.py "https://www.youtube.com/playlist?list=..." --threads 3
```

> **Note on threading:** Values above `--threads 4` risk triggering YouTube's rate-limiter (HTTP 429). If you hit this, reduce the thread count or increase `--sleep`.

---

## Support the Project

If YouLoader saved you time or helped you build your archive, a small tip keeps the project alive:

- **PayPal:** [vwakhungila10@gmail.com](mailto:vwakhungila10@gmail.com)
- **Ethereum (ETH):** `0x37a6A9094867c331477EDa7D7A3c250D5ba5D048`

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

### Guidelines

- **Code Style:** Follow PEP 8. Use clear, readable naming and keep functions modular. All terminal output must use `rich` to maintain a consistent CLI experience.
- **Feature Additions:** Update the CLI options table in the README, include at least one usage example, and ensure backward compatibility where possible.
- **Stability & Performance:** Test against existing multi-threading logic, avoid race conditions or blocking operations, and keep performance overhead minimal.
- **Commit Messages:** Use structured, meaningful messages:
  ```
  feat(download): add batch processing
  fix(cli): resolve argument parsing issue
  ```

### Review Expectations

Pull requests should be focused (one feature or fix per PR), well-described (explain what and why), and tested before submission.

### Code of Conduct

Be respectful, constructive, and collaborative. Good engineering includes good communication.