import subprocess
import sys
import os
from pathlib import Path


def _ensure_dependencies():
    """Check for required packages and install them if missing."""
    try:
        import yt_dlp, typer, rich  # noqa: F401
    except ImportError:
        print("[System] Missing dependencies. Installing from requirements.txt...")
        req_path = Path(__file__).parent / "requirements.txt"
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", str(req_path), "--break-system-packages"]
        )


_ensure_dependencies()

import time
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor

import yt_dlp
import typer
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.table import Table
from rich.progress import (
    Progress,
    TextColumn,
    BarColumn,
    DownloadColumn,
    TransferSpeedColumn,
    TimeRemainingColumn,
)

# ---------------------------------------------------------------------------
# UI & Branding
# ---------------------------------------------------------------------------

console = Console()
app = typer.Typer(help="YouLoader: Professional Media Archiver", add_completion=False)

ASCII_ART = r"""
[bold green]
  __     ______  _    _ _      ____          _____  ______ _____
  \ \   / / __ \| |  | | |    / __ \   /\   |  __ \|  ____|  __ \
   \ \_/ / |  | | |  | | |   | |  | | /  \  | |  | | |__  | |__) |
    \   /| |  | | |  | | |   | |  | |/ /\ \ | |  | |  __| |  _  /
     | | | |__| | |__| | |___| |__| / ____ \| |__| | |____| | \ \
     |_|  \____/ \____/|______\____/_/    \_\_____/|______|_|  \_\
[/bold green]
[cyan]      >> Intelligent YouTube Archival System v4.3 <<[/cyan]
"""

DONATION_PANEL = Panel(
    "[bold cyan]Love using YouLoader?[/bold cyan]\n\n"
    "To help improve and maintain this project, please consider a small tip!\n\n"
    "[bold yellow]PayPal:[/bold yellow] [underline]vwakhungila10@gmail.com[/underline]\n"
    "[bold yellow]Ethereum (ETH):[/bold yellow] "
    "[underline]0x37a6A9094867c331477EDa7D7A3c250D5ba5D048[/underline]\n\n"
    "Thank you for your support! \u2764\ufe0f",
    title="[bold magenta]Support the Project[/bold magenta]",
    border_style="magenta",
    expand=False,
)

# ---------------------------------------------------------------------------
# Output directory resolution
# ---------------------------------------------------------------------------

def _resolve_output_root() -> Path:
    """
    Resolve the YouLoader save directory to the user\'s Desktop, regardless of
    where the script is run from. Works for any user on any machine.

    Resolution strategy per platform:

      Native Windows
        %USERPROFILE%\\Desktop\\YouLoader

      WSL (Windows Subsystem for Linux)
        Uses wslpath + cmd.exe to find the real Windows Desktop -- the only
        method that is correct for any Windows username without relying on
        environment variables that WSL may not populate correctly.
        Fallback: ~/Desktop/YouLoader inside WSL home if Windows interop
        is unavailable (e.g. WSL with interop disabled).

      Linux
        ~/Desktop/YouLoader
        If ~/Desktop does not exist (headless/server Linux with no desktop
        environment), falls back to ~/YouLoader so CLI-only users are covered.

      macOS
        ~/Desktop/YouLoader

    The directory is created automatically on first run.
    archive.txt also lives here -- completely outside the cloned repository
    so nothing is ever accidentally committed or pushed to GitHub.
    """
    # ----------------------------------------------------------------- WSL --
    is_wsl = False
    proc_version = Path("/proc/version")
    if proc_version.exists():
        try:
            content = proc_version.read_text(encoding="utf-8", errors="ignore").lower()
            is_wsl = "microsoft" in content or "wsl" in content
        except OSError:
            pass

    if is_wsl:
        desktop = None

        # Step 1: cmd.exe -> wslpath  (most reliable, works for any username)
        # Ask Windows directly for %USERPROFILE%, then let wslpath convert it.
        # No string manipulation, no assumptions about drive letters or usernames.
        try:
            prof = subprocess.run(
                ["cmd.exe", "/c", "echo %USERPROFILE%"],
                capture_output=True, text=True, timeout=5
            )
            win_profile = prof.stdout.strip()
            if win_profile and "%" not in win_profile:
                wsl = subprocess.run(
                    ["wslpath", "-u", win_profile],
                    capture_output=True, text=True, timeout=5
                )
                linux_profile = wsl.stdout.strip()
                if linux_profile:
                    candidate = Path(linux_profile) / "Desktop"
                    if candidate.exists():
                        desktop = candidate
        except Exception:
            pass

        # Step 2: wslpath on the USERPROFILE env var directly.
        # Covers machines where cmd.exe is slow or WSL interop behaves differently.
        if desktop is None:
            win_profile_env = os.environ.get("USERPROFILE", "")
            if win_profile_env and "%" not in win_profile_env:
                try:
                    wsl = subprocess.run(
                        ["wslpath", "-u", win_profile_env],
                        capture_output=True, text=True, timeout=5
                    )
                    linux_profile = wsl.stdout.strip()
                    if linux_profile:
                        candidate = Path(linux_profile) / "Desktop"
                        if candidate.exists():
                            desktop = candidate
                except Exception:
                    pass

        # Step 3: WSL interop unavailable -- fall back to WSL home Desktop.
        if desktop is None:
            desktop = Path.home() / "Desktop"
            desktop.mkdir(parents=True, exist_ok=True)

        output_root = desktop / "YouLoader"
        output_root.mkdir(parents=True, exist_ok=True)
        return output_root

    # ------------------------------------------------------- Native Windows --
    if sys.platform == "win32":
        output_root = Path(os.environ["USERPROFILE"]) / "Desktop" / "YouLoader"
        output_root.mkdir(parents=True, exist_ok=True)
        return output_root

    # --------------------------------------------------- Linux / macOS -------
    home_desktop = Path.home() / "Desktop"
    if home_desktop.exists():
        output_root = home_desktop / "YouLoader"
    else:
        # Headless Linux or server with no desktop environment
        output_root = Path.home() / "YouLoader"

    output_root.mkdir(parents=True, exist_ok=True)
    return output_root



# Resolved once at import time — every path in the script derives from this.
OUTPUT_ROOT = _resolve_output_root()

# ---------------------------------------------------------------------------
# Progress hook & logger
# ---------------------------------------------------------------------------

class RichProgressHook:
    """yt-dlp progress hook that renders download state into a Rich progress bar."""

    def __init__(self, progress: Progress) -> None:
        self.progress = progress
        self.tasks: dict = {}
        # A lock guards task dict mutation (not atomic across multiple ops).
        # list.append() used elsewhere is atomic in CPython (GIL-protected).
        self.lock = threading.Lock()

    def __call__(self, d: dict) -> None:
        if d["status"] == "downloading":
            filename = Path(d.get("filename", "Unknown")).name
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            with self.lock:
                if filename not in self.tasks:
                    self.tasks[filename] = self.progress.add_task(
                        f"[cyan]{filename[:35]}", total=total
                    )
            self.progress.update(
                self.tasks[filename],
                completed=d.get("downloaded_bytes"),
                total=total,
            )
        elif d["status"] == "finished":
            self.progress.console.print(
                f"[bold green][DONE] Saved:[/bold green] {Path(d['filename']).name}"
            )


class YDLRichLogger:
    """Suppress yt-dlp's verbose internal logs; surface only real ERRORs."""

    def debug(self, msg: str) -> None:
        pass

    def info(self, msg: str) -> None:
        pass

    def warning(self, msg: str) -> None:
        pass

    def error(self, msg: str) -> None:
        if "ERROR" in msg:
            error_text = msg.split(":")[-1].strip() if ":" in msg else msg
            console.print(f"[bold red][ERROR] {error_text}[/bold red]")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clean_up_partials(search_root: Path) -> int:
    """Recursively find and delete leftover .part / .ytdl files under search_root."""
    count = 0
    for path in search_root.rglob("*"):
        if path.suffix in (".part", ".ytdl"):
            try:
                path.unlink()
                count += 1
            except (OSError, PermissionError):
                pass
    return count


def _build_output_template(output_root: Path, organize: str) -> str:
    """
    Return a yt-dlp outtmpl string rooted at output_root.

    Final structure on disk:
      <Desktop>/YouLoader/<Uploader>/<Playlist>/[<year|month|date>/]<NNN - title>.<ext>
    """
    base = str(output_root / "%(uploader)s" / "%(playlist_title|Single Videos)s")
    suffix = {
        "year":  "/%(upload_year)s",
        "month": "/%(upload_year)s/%(upload_month)s",
        "time":  "/%(upload_date)s",
    }.get(organize, "")
    return base + suffix + "/%(playlist_index&{:03d} - |)s%(title)s.%(ext)s"


def _read_archive(archive_path: Path) -> set:
    """Load already-downloaded video IDs from the archive file into a set."""
    if archive_path.exists():
        return {
            line.strip()
            for line in archive_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
    return set()


def _append_to_archive(archive_path: Path, video_ids: list) -> None:
    """Append newly downloaded video IDs to the archive file."""
    with open(archive_path, "a", encoding="utf-8") as f:
        for vid in video_ids:
            f.write(f"{vid}\n")


# ---------------------------------------------------------------------------
# Main command
# ---------------------------------------------------------------------------

@app.command()
def main(
    url: str = typer.Argument(None, help="The target URL (channel, playlist, or video)."),
    quality: str = typer.Option("720", "--quality", "-q", help="Video quality: 480, 720, 1080, or max."),
    shorts: bool = typer.Option(False, "--shorts", help="Include YouTube Shorts (filtered out by default)."),
    live: bool = typer.Option(True, "--live/--no-live", help="Include past live streams."),
    sleep: int = typer.Option(10, "--sleep", "-s", help="Seconds to wait between downloads."),
    list_only: bool = typer.Option(False, "--list", "-l", help="List content without downloading."),
    audio_only: bool = typer.Option(False, "--audio-only", "-x", help="Download audio only and convert to MP3."),
    bitrate: str = typer.Option("192", "--bitrate", "-b", help="MP3 bitrate in kbps (128, 192, 256, 320)."),
    clean: bool = typer.Option(True, "--clean/--no-clean", help="Strip 'Official Video' and similar tags from filenames."),
    m3u: bool = typer.Option(False, "--m3u", help="Generate a .m3u8 playlist file after downloading."),
    organize: str = typer.Option("none", "--organize", help="Organise output by: year, month, time, or none."),
    retries: int = typer.Option(10, "--retries", "-r", help="Number of retries for failed downloads."),
    last_days: int = typer.Option(None, "--last-days", help="Only download videos uploaded in the last X days."),
    start_date: str = typer.Option(None, "--start-date", help="Download videos on or after this date (YYYYMMDD)."),
    end_date: str = typer.Option(None, "--end-date", help="Download videos on or before this date (YYYYMMDD)."),
    keyword: str = typer.Option(None, "--keyword", "-k", help="Only download videos whose title contains this keyword."),
    exclude: str = typer.Option(None, "--exclude", "-e", help="Skip videos whose title contains this keyword."),
    threads: int = typer.Option(
        1, "--threads", "-t",
        help="Number of concurrent downloads. Values > 4 risk YouTube rate-limiting (429)."
    ),
) -> None:
    """
    YouLoader Sync Engine — high-performance archival for YouTube channels and playlists.
    All files are saved to ~/Desktop/YouLoader, regardless of where the script is run from.
    """
    console.print(ASCII_ART)
    console.print(DONATION_PANEL)

    # Always show the user exactly where their files will land
    console.print(
        Panel(
            f"[bold white]Save location:[/bold white] [green]{OUTPUT_ROOT}[/green]",
            title="[bold cyan]YouLoader Output[/bold cyan]",
            border_style="green",
            expand=False,
        )
    )

    # Archive file lives inside YouLoader/, completely outside the repo
    archive_path = OUTPUT_ROOT / "archive.txt"

    # Guard: FFmpeg is required for A/V stream merging
    if not shutil.which("ffmpeg"):
        console.print("[bold red][ERROR] FFmpeg not found![/bold red]")
        console.print(
            "[yellow]FFmpeg is required to merge high-quality video and audio streams.\n"
            "Install it and ensure it is on your PATH, then try again.[/yellow]"
        )
        raise typer.Exit(code=1)

    # Interactive fallback
    if not url:
        url = Prompt.ask("[bold cyan]Paste Target URL[/bold cyan]")

    # Validate --organize value
    valid_orgs = {"none", "year", "month", "time"}
    if organize.lower() not in valid_orgs:
        console.print(
            f"[yellow][WARNING] Invalid --organize value '{organize}'. Defaulting to 'none'.[/yellow]"
        )
        organize = "none"

    # Warn about high thread counts
    if threads > 4:
        console.print(
            "[bold yellow][WARNING] High thread count detected. "
            "If you encounter 429 Too Many Requests, reduce --threads.[/bold yellow]"
        )

    # Build format selector
    if audio_only:
        format_selector = "bestaudio/best"
    else:
        format_map = {
            "480":  "bestvideo[height<=480]+bestaudio/best[height<=480]",
            "720":  "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "1080": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
            "max":  "bestvideo+bestaudio/best",
        }
        format_selector = format_map.get(quality, format_map["720"])

    # Rich progress bar shared across all download paths
    progress = Progress(
        TextColumn("[bold blue]{task.description}", justify="right"),
        BarColumn(bar_width=None),
        "[progress.percentage]{task.percentage:>3.1f}%",
        "•",
        DownloadColumn(),
        "•",
        TransferSpeedColumn(),
        "•",
        TimeRemainingColumn(),
        console=console,
    )

    downloaded_ids = _read_archive(archive_path)

    # Core yt-dlp options
    ydl_opts: dict = {
        "format": format_selector,
        "outtmpl": _build_output_template(OUTPUT_ROOT, organize.lower()),
        "sleep_interval": sleep,
        "max_sleep_interval": sleep + 2,
        "logger": YDLRichLogger(),
        "progress_hooks": [RichProgressHook(progress)],
        # Archive management: delegated to yt-dlp only in single-thread mode.
        # In multi-thread mode we manage the archive ourselves to avoid
        # race conditions when multiple workers write simultaneously.
        "download_archive": str(archive_path) if threads == 1 else None,
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "merge_output_format": "mp4",
        "restrictfilenames": True,
        "prefer_ffmpeg": True,
        "retries": retries,
        "fragment_retries": retries,
        "fixup": "detect_or_warn",
    }

    # Date filters
    if last_days:
        ydl_opts["dateafter"] = f"now-{last_days}days"
    if start_date:
        ydl_opts["dateafter"] = start_date
    if end_date:
        ydl_opts["datebefore"] = end_date

    # Filename cleaning via yt-dlp regex post-processing
    if clean:
        ydl_opts["outtmpl_replace_regex"] = {
            "title": [
                (r"\s*[\(\[][Oo]fficial\s*[Vv]ideo[\)\]]", ""),
                (r"\s*[\(\[][Oo]fficial\s*[Aa]udio[\)\]]", ""),
                (r"\s*[\(\[][Mm]usic\s*[Vv]ideo[\)\]]", ""),
                (r"\s*[\(\[][Ll]yric\s*[Vv]ideo[\)\]]", ""),
                (r"\s*[\(\[]HD[\)\]]", ""),
                (r"\s*[\(\[]4K[\)\]]", ""),
                (r"\s*[\(\[][Vv]ideo\s*[Vv]ersion[\)\]]", ""),
            ]
        }

    # Audio-only post-processor chain: extract → convert thumbnail → embed → metadata
    if audio_only:
        ydl_opts["writethumbnail"] = True
        ydl_opts["postprocessors"] = [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": bitrate},
            {"key": "FFmpegThumbnailsConvertor", "format": "jpg"},
            {"key": "EmbedThumbnail"},
            {"key": "FFmpegMetadata", "add_metadata": True},
        ]

    # Content filters
    filters: list[str] = []
    if not shorts:
        filters.append("original_url!*='/shorts/' & duration > 60")
    if not live:
        filters.append("!is_live & !was_live")
    if keyword:
        filters.append(f"title ~= (?i){keyword}")
    if exclude:
        filters.append(f"title !~= (?i){exclude}")
    if filters:
        ydl_opts["match_filter"] = yt_dlp.utils.match_filter_func(" & ".join(filters))

    if list_only:
        ydl_opts["extract_flat"] = "in_playlist"

    # ---------------------------------------------------------------------------
    # Execution
    # ---------------------------------------------------------------------------
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            if list_only:
                info = ydl.extract_info(url, download=False)
                if info and "entries" in info:
                    table = Table(
                        title=f"Source: {info.get('title', 'Archive')}",
                        header_style="bold magenta",
                    )
                    table.add_column("No.", width=5, justify="right")
                    table.add_column("Title", style="cyan")
                    for i, entry in enumerate(info["entries"], 1):
                        table.add_row(str(i), entry.get("title", "N/A"))
                    console.print(table)
                return

            console.print(
                Panel(
                    f"[white]Target:[/white] [green]{url}[/green]",
                    title="[bold magenta]Task Profile[/bold magenta]",
                    border_style="cyan",
                )
            )

            info = None

            if threads > 1:
                # -----------------------------------------------------------
                # Multi-threaded path: extract metadata first, filter against
                # local archive, then download each video in a thread pool.
                # The archive file is updated once after all threads complete
                # to avoid concurrent write contention.
                # -----------------------------------------------------------
                with console.status("[bold yellow]Extracting metadata for parallel sync...[/bold yellow]"):
                    info = ydl.extract_info(url, download=False)

                if not info or "entries" not in info:
                    # Single video — fall back to normal download
                    with progress:
                        info = ydl.extract_info(url, download=True)
                else:
                    all_entries = [e for e in info["entries"] if e]
                    urls_to_download = [
                        entry.get("webpage_url") or entry.get("url")
                        for entry in all_entries
                        if entry.get("id") not in downloaded_ids
                    ]

                    skipped = len(all_entries) - len(urls_to_download)
                    if skipped:
                        console.print(f"[bold yellow]Skipping {skipped} already-archived item(s).[/bold yellow]")
                    console.print(
                        f"[bold cyan]Queuing {len(urls_to_download)} new item(s) for download...[/bold cyan]"
                    )

                    # Strip archive delegation from per-thread opts
                    thread_ydl_opts = {k: v for k, v in ydl_opts.items() if k != "download_archive"}

                    newly_downloaded_ids: list[str] = []
                    # NOTE: list.append() is atomic in CPython (GIL guarantee).

                    def thread_worker(index_and_url: tuple) -> None:
                        index, item_url = index_and_url
                        # Staggered start prevents a thundering-herd of
                        # simultaneous API requests on session start.
                        if sleep > 0:
                            time.sleep(min(index * 1.5, sleep))
                        with yt_dlp.YoutubeDL(thread_ydl_opts) as t_ydl:
                            try:
                                item_info = t_ydl.extract_info(item_url, download=True)
                                if item_info and item_info.get("id"):
                                    newly_downloaded_ids.append(item_info["id"])
                            except Exception as exc:
                                console.print(
                                    f"[bold red][ERROR] Failed: {item_url} — {exc}[/bold red]"
                                )

                    with progress:
                        with ThreadPoolExecutor(max_workers=threads) as executor:
                            list(executor.map(thread_worker, enumerate(urls_to_download)))

                    # Write all new IDs to the archive in one shot
                    if newly_downloaded_ids:
                        _append_to_archive(archive_path, newly_downloaded_ids)
                        console.print(
                            f"[bold green][SUCCESS] Archive updated with "
                            f"{len(newly_downloaded_ids)} new entry(s).[/bold green]"
                        )

            else:
                # Single-threaded path — yt-dlp handles archive management natively
                with progress:
                    info = ydl.extract_info(url, download=True)

            # ---------------------------------------------------------------
            # Optional .m3u8 playlist generation
            # ---------------------------------------------------------------
            if m3u and info:
                uploader = info.get("uploader", "Unknown Artist")
                playlist_title = (
                    info.get("title", "Single Videos") if "entries" in info else "Single Videos"
                )
                folder_path = OUTPUT_ROOT / uploader / playlist_title

                if folder_path.exists():
                    playlist_file = folder_path / f"{playlist_title}.m3u8"
                    media_files = sorted(
                        f for f in folder_path.rglob("*")
                        if f.suffix in (".mp3", ".mp4", ".m4a", ".mkv")
                    )
                    with open(playlist_file, "w", encoding="utf-8") as f:
                        f.write("#EXTM3U\n")
                        for media in media_files:
                            f.write(f"{media.relative_to(folder_path).as_posix()}\n")
                    console.print(
                        f"[bold green][SUCCESS] Playlist generated:[/bold green] {playlist_file.name}"
                    )

        console.print(
            f"\n[bold green][SUCCESS] ARCHIVE SYNC COMPLETE[/bold green]\n"
            f"[dim]Files saved to: {OUTPUT_ROOT}[/dim]"
        )

    except KeyboardInterrupt:
        console.print("\n[bold red][HALTED] SESSION TERMINATED[/bold red]")
        removed = clean_up_partials(OUTPUT_ROOT)
        if removed:
            console.print(f"[yellow]Cleaned up {removed} partial file(s).[/yellow]")
        raise typer.Exit()


if __name__ == "__main__":
    app()