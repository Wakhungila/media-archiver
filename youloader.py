import subprocess
import sys
from pathlib import Path

def _ensure_dependencies():
    """Check for required packages and install them if missing."""
    try:
        import yt_dlp, typer, rich
    except ImportError:
        print("[System] Missing dependencies. Installing from requirements.txt...")
        req_path = Path(__file__).parent / "requirements.txt"
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(req_path), "--break-system-packages"])

_ensure_dependencies()

import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
import yt_dlp
import typer
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, TextColumn, BarColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn

# --- UI & Branding ---
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
[cyan]      >> Intelligent YouTube Archival System v4.2 <<[/cyan]
"""

class RichProgressHook:
    def __init__(self, progress):
        self.progress = progress
        self.tasks = {}
        self.lock = threading.Lock()

    def __call__(self, d):
        if d['status'] == 'downloading':
            filename = Path(d.get('filename', 'Unknown')).name
            with self.lock:
                if filename not in self.tasks:
                    # Create a new task for each unique file (handles video+audio merging)
                    self.tasks[filename] = self.progress.add_task(
                        f"[cyan]{filename[:30]}", 
                        total=d.get('total_bytes') or d.get('total_bytes_estimate')
                    )
            self.progress.update(
                self.tasks[filename], 
                completed=d.get('downloaded_bytes'), 
                total=d.get('total_bytes') or d.get('total_bytes_estimate')
            )
        elif d['status'] == 'finished':
            self.progress.console.print(f"[bold green][DONE] Saved:[/bold green] {Path(d['filename']).name}")

class YDLRichLogger:
    def debug(self, msg): pass
    def info(self, msg): pass
    def warning(self, msg): pass 
    def error(self, msg):
        if "ERROR" in msg:
            error_text = msg.split(':')[-1].strip() if ':' in msg else msg
            console.print(f"[bold red][ERROR] {error_text}[/bold red]")

def clean_up_partials():
    count = 0
    # Using pathlib to recursively find and remove partials
    for path in Path(".").rglob("*"):
        if path.suffix in [".part", ".ytdl"]:
            try:
                path.unlink()
                count += 1
            except (OSError, PermissionError): pass
    return count

@app.command()
def main(
    url: str = typer.Argument(None, help="The target URL."),
    quality: str = typer.Option("720", "--quality", "-q", help="480, 720, 1080, or max."),
    shorts: bool = typer.Option(False, "--shorts", help="Include Shorts."),
    live: bool = typer.Option(True, "--live", help="Include past Live Streams."),
    sleep: int = typer.Option(10, "--sleep", "-s", help="Seconds between downloads."),
    list_only: bool = typer.Option(False, "--list", "-l", help="List content without downloading."),
    archive: str = typer.Option("archive.txt", "--archive", "-a", help="Download history file."),
    audio_only: bool = typer.Option(False, "--audio-only", "-x", help="Download audio only and convert to MP3."),
    bitrate: str = typer.Option("192", "--bitrate", "-b", help="MP3 bitrate (e.g., 128, 192, 256, 320)."),
    clean: bool = typer.Option(True, "--clean", help="Remove 'Official Video' suffixes from filenames."),
    m3u: bool = typer.Option(False, "--m3u", help="Create a .m3u8 playlist file for the download."),
    organize: str = typer.Option("none", "--organize", help="Organize content by 'year', 'month', 'time', or 'none'."),
    retries: int = typer.Option(10, "--retries", "-r", help="Number of retries for failed downloads."),
    last_days: int = typer.Option(None, "--last-days", help="Download only videos from the last X days."),
    start_date: str = typer.Option(None, "--start-date", help="Download videos uploaded on or after this date (YYYYMMDD)."),
    end_date: str = typer.Option(None, "--end-date", help="Download videos uploaded on or before this date (YYYYMMDD)."),
    keyword: str = typer.Option(None, "--keyword", "-k", help="Only download videos with this keyword in the title."),
    exclude: str = typer.Option(None, "--exclude", "-e", help="Exclude videos with this keyword in the title."),
    threads: int = typer.Option(1, "--threads", "-t", help="Number of concurrent downloads for playlists.")
):
    """
    YouLoader Sync Engine:
    High-performance archival for security research channels.
    """
    console.print(ASCII_ART)

    donation_panel = Panel(
        "[bold cyan]Love using YouLoader?[/bold cyan]\n\n"
        "To help improve and maintain this project, please consider a small tip!\n\n"
        "[bold yellow]PayPal:[/bold yellow] [underline]vwakhungila10@gmail.com[/underline]\n"
        "[bold yellow]Ethereum (ETH):[/bold yellow] [underline]0x37a6A9094867c331477EDa7D7A3c250D5ba5D048[/underline]\n\n"
        "Thank you for your support!❤️",
        title="[bold magenta]Support the Project[/bold magenta]",
        border_style="magenta",
        expand=False
    )
    console.print(donation_panel)
    # Removed the redundant emoji from the donation panel.

    # Ensure FFmpeg is installed; it's required for merging A/V and maintaining sync
    if not shutil.which("ffmpeg"):
        console.print("[bold red][ERROR] FFmpeg not found![/bold red]")
        console.print("[yellow]FFmpeg is required to merge high-quality video and audio tracks accurately.[/yellow]")
        raise typer.Exit(code=1)
    
    if not url:
        url = Prompt.ask("[bold cyan]Paste Target URL[/bold cyan]")

    if audio_only:
        format_selector = "bestaudio/best"
    else:
        format_selector = {
            "480": "bestvideo[height<=480]+bestaudio/best[height<=480]",
            "720": "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "1080": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
            "max": "bestvideo+bestaudio/best"
        }.get(quality, "bestvideo[height<=720]+bestaudio/best[height<=720]")

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
        console=console
    )

    # Read existing archive IDs
    downloaded_ids = set()
    if Path(archive).exists():
        with open(archive, 'r') as f:
            for line in f:
                downloaded_ids.add(line.strip())


    # Sanitize organization input
    valid_orgs = ["none", "year", "month", "time"]
    if organize.lower() not in valid_orgs:
        console.print(f"[yellow]Warning: Invalid organize option '{organize}'. Defaulting to 'none'.[/yellow]")
        organize = "none"

    # Build dynamic output template based on organization preference
    template_path = "%(uploader)s/%(playlist_title|Single Videos)s/"
    if organize.lower() == "year":
        template_path += "%(upload_year)s/"
    elif organize.lower() == "month":
        template_path += "%(upload_year)s/%(upload_month)s/"
    elif organize.lower() == "time":
        template_path += "%(upload_date)s/"

    ydl_opts = {
        'format': format_selector,
        'outtmpl': f"{template_path}%(playlist_index&{{:03d}} - |)s%(title)s.%(ext)s",
        'download_archive': archive,
        'sleep_interval': sleep,
        'max_sleep_interval': sleep + 2,
        'logger': YDLRichLogger(),
        'progress_hooks': [RichProgressHook(progress)],
        # Only use download_archive for the main YDL instance if not multi-threading
        # For multi-threading, we manage archive filtering and updating manually
        'download_archive': archive if threads == 1 else None,

        # General yt-dlp options
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'merge_output_format': 'mp4',
        'restrictfilenames': True,
        'prefer_ffmpeg': True,
        'retries': retries,
        'fragment_retries': retries,
        'fixup': 'detect_or_warn',  # Automatically fixes stream sync/container issues
    }

    if last_days:
        ydl_opts['dateafter'] = f"now-{last_days}days"
    if start_date:
        ydl_opts['dateafter'] = start_date
    if end_date:
        ydl_opts['datebefore'] = end_date

    if clean:
        ydl_opts['outtmpl_replace_regex'] = {
            'title': [
                (r'\s*[\(\[][Oo]fficial\s*[Vv]ideo[\)\]]', ''),
                (r'\s*[\(\[][Oo]fficial\s*[Aa]udio[\)\]]', ''),
                (r'\s*[\(\[][Mm]usic\s*[Vv]ideo[\)\]]', ''),
                (r'\s*[\(\[][Ll]yric\s*[Vv]ideo[\)\]]', ''),
                (r'\s*[\(\[]HD[\)\]]', ''),
                (r'\s*[\(\[]4K[\)\]]', ''),
                (r'\s*[\(\[][Vv]ideo\s*[Vv]ersion[\)\]]', ''),
            ]
        }

    if audio_only:
        ydl_opts['writethumbnail'] = True
        ydl_opts['postprocessors'] = [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': bitrate,
            },
            {
                'key': 'FFmpegThumbnailsConvertor',
                'format': 'jpg',
            },
            {
                'key': 'EmbedThumbnail',
            },
            {
                'key': 'FFmpegMetadata',
                'add_metadata': True,
            }
        ]

    # Filters
    filters = []
    if not shorts: filters.append("original_url!*='/shorts/' & duration > 60")
    if not live: filters.append("!is_live & !was_live")
    if keyword: filters.append(f"title ~= (?i){keyword}")
    if exclude: filters.append(f"title !~= (?i){exclude}")
    if filters: ydl_opts['match_filter'] = yt_dlp.utils.match_filter_func(" & ".join(filters))

    if list_only: ydl_opts['extract_flat'] = 'in_playlist'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            if list_only:
                info = ydl.extract_info(url, download=False)
                if 'entries' in info:
                    table = Table(title=f"Source: {info.get('title', 'Archive')}", header_style="bold magenta")
                    table.add_column("No.", width=5, justify="right")
                    table.add_column("Title", style="cyan")
                    for i, entry in enumerate(info['entries'], 1):
                        table.add_row(str(i), entry.get('title', 'N/A'))
                    console.print(table)
            else:
                console.print(Panel(f"[white]Target:[/white] [green]{url}[/green]", title="[bold magenta]Task Profile[/bold magenta]", border_style="cyan"))
                
                if threads > 1:
                    with console.status("[bold yellow]Extracting metadata for parallel sync...[/bold yellow]"):
                        info = ydl.extract_info(url, download=False)
                    
                    if info and 'entries' in info:
                        all_entries = [e for e in info['entries'] if e]
                        urls_to_download = []
                        newly_downloaded_ids = []

                        for entry in all_entries:
                            video_id = entry.get('id')
                            if video_id and video_id in downloaded_ids:
                                console.print(f"[bold yellow]Skipping:[/bold yellow] {entry.get('title', 'Unknown')} (already in archive)")
                            else:
                                urls_to_download.append(entry.get('webpage_url') or entry.get('url'))
                        
                        # Create a copy of ydl_opts for threads, but without download_archive
                        thread_ydl_opts = ydl_opts.copy()
                        if 'download_archive' in thread_ydl_opts:
                            del thread_ydl_opts['download_archive']

                        def thread_worker(item_url):
                            with yt_dlp.YoutubeDL(thread_ydl_opts) as t_ydl:
                                try:
                                    item_info = t_ydl.extract_info(item_url, download=True)
                                    if item_info and item_info.get('id'):
                                        newly_downloaded_ids.append(item_info['id'])
                                except Exception as e:
                                    console.print(f"[bold red][ERROR] Failed to download {item_url}: {e}[/bold red]")

                        with progress:
                            with ThreadPoolExecutor(max_workers=threads) as executor:
                                list(executor.map(thread_worker, urls_to_download)) # Pass filtered URLs
                        
                        # Update the archive file after all threads complete
                        if newly_downloaded_ids:
                            with open(archive, 'a') as f: # 'a' for append
                                for video_id in newly_downloaded_ids:
                                    f.write(f"{video_id}\n")
                            console.print(f"[bold green][SUCCESS] Archive updated with {len(newly_downloaded_ids)} new entries.[/bold green]")
                    else:
                        with progress:
                            info = ydl.extract_info(url, download=True)
                else:
                    with progress:
                        info = ydl.extract_info(url, download=True)

                # --- Playlist Generation ---
                if m3u and info:
                    uploader = info.get('uploader', 'Unknown Artist')
                    playlist_title = info.get('title', 'Single Videos') if 'entries' in info else 'Single Videos'
                    folder_path = Path(uploader) / playlist_title
                    
                    if folder_path.exists():
                        playlist_file = folder_path / f"{playlist_title}.m3u8"
                        media_files = sorted([f for f in folder_path.rglob("*") if f.suffix in ['.mp3', '.mp4', '.m4a', '.mkv']])
                        
                        with open(playlist_file, "w", encoding="utf-8") as f:
                            f.write("#EXTM3U\n")
                            for media in media_files:
                                f.write(f"{media.relative_to(folder_path).as_posix()}\n")
                        console.print(f"[bold green][SUCCESS] Playlist Generated:[/bold green] {playlist_file.name}")

        if not list_only:
            console.print("\n[bold green][SUCCESS] ARCHIVE SYNC COMPLETE[/bold green]")

    except KeyboardInterrupt:
        console.print("\n[bold red][HALTED] SESSION TERMINATED[/bold red]")
        clean_up_partials()
        raise typer.Exit()

if __name__ == "__main__":
    app()