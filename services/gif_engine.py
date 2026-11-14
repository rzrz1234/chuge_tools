"""Convert a video clip into an optimized GIF with ffmpeg."""
from __future__ import annotations
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Sequence
DEFAULT_FPS = 12
DEFAULT_WIDTH = 640
DEFAULT_LOOP = 0
DEFAULT_DITHER = 'sierra2_4a'

class VideoToGifError(RuntimeError):
    """Raised when the conversion cannot be completed."""

def positive_int(value: str) -> int:
    """Parse an integer that must be greater than zero."""
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError('value must be greater than 0')
    return parsed

def positive_float(value: str) -> float:
    """Parse a float that must be greater than zero."""
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError('value must be greater than 0')
    return parsed

def non_negative_float(value: str) -> float:
    """Parse a float that must be zero or greater."""
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError('value must be 0 or greater')
    return parsed

def non_negative_int(value: str) -> int:
    """Parse an integer that must be zero or greater."""
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError('value must be 0 or greater')
    return parsed

def parse_args(argv: Sequence[str] | None=None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='Convert a video file to an optimized GIF using ffmpeg.')
    parser.add_argument('input', type=Path, help='source video path')
    parser.add_argument('-o', '--output', type=Path, help='output GIF path (default: same name as input with .gif extension)')
    parser.add_argument('--fps', type=positive_int, default=DEFAULT_FPS, help=f'GIF frame rate (default: {DEFAULT_FPS})')
    parser.add_argument('--width', type=positive_int, default=DEFAULT_WIDTH, help=f'output width in pixels (default: {DEFAULT_WIDTH})')
    parser.add_argument('--start', type=non_negative_float, default=0.0, help='start time in seconds (default: 0)')
    parser.add_argument('--duration', type=positive_float, help='clip duration in seconds')
    parser.add_argument('--loop', type=non_negative_int, default=DEFAULT_LOOP, help='GIF loop count; 0 means infinite loop (default: 0)')
    parser.add_argument('--ffmpeg', default='ffmpeg', help='ffmpeg executable to use (default: ffmpeg from PATH)')
    parser.add_argument('--overwrite', action='store_true', help='overwrite the output file if it already exists')
    return parser.parse_args(argv)

def resolve_output_path(input_path: Path, output_path: Path | None) -> Path:
    """Choose the final GIF path."""
    if output_path is not None:
        return output_path
    return input_path.with_suffix('.gif')

def ensure_ffmpeg_available(ffmpeg_bin: str) -> str:
    """Resolve the ffmpeg executable or raise a helpful error."""
    resolved = shutil.which(ffmpeg_bin)
    if resolved:
        return resolved
    direct_path = Path(ffmpeg_bin)
    if direct_path.exists():
        return str(direct_path)
    raise VideoToGifError(f"Could not find ffmpeg executable '{ffmpeg_bin}'. Install FFmpeg or pass --ffmpeg with the full path.")

def build_clip_args(start: float, duration: float | None) -> list[str]:
    """Build the shared clip selection arguments."""
    args: list[str] = []
    if start > 0:
        args.extend(['-ss', f'{start:g}'])
    if duration is not None:
        args.extend(['-t', f'{duration:g}'])
    return args

def build_base_filter(fps: int, width: int) -> str:
    """Build the common video filter chain."""
    return f'fps={fps},scale={width}:-1:flags=lanczos'

def build_palette_command(ffmpeg_bin: str, input_path: Path, palette_path: Path, start: float, duration: float | None, fps: int, width: int, overwrite: bool) -> list[str]:
    """Build the palette generation command."""
    return [ffmpeg_bin, '-hide_banner', '-loglevel', 'error', *build_clip_args(start, duration), '-i', str(input_path), '-vf', f'{build_base_filter(fps, width)},palettegen=stats_mode=diff', '-y' if overwrite else '-n', str(palette_path)]

def build_gif_command(ffmpeg_bin: str, input_path: Path, output_path: Path, palette_path: Path, start: float, duration: float | None, fps: int, width: int, loop: int, overwrite: bool) -> list[str]:
    """Build the GIF encoding command."""
    filter_complex = f'[0:v]{build_base_filter(fps, width)}[video];[video][1:v]paletteuse=dither={DEFAULT_DITHER}:diff_mode=rectangle'
    return [ffmpeg_bin, '-hide_banner', '-loglevel', 'error', *build_clip_args(start, duration), '-i', str(input_path), '-i', str(palette_path), '-filter_complex', filter_complex, '-loop', str(loop), '-y' if overwrite else '-n', str(output_path)]

def run_command(command: Sequence[str]) -> None:
    """Run an ffmpeg command and surface stderr on failure."""
    try:
        subprocess.run(list(command), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.strip() if exc.stderr else 'ffmpeg failed without stderr output'
        raise VideoToGifError(message) from exc

def convert_video_to_gif(input_path: Path, output_path: Path, fps: int=DEFAULT_FPS, width: int=DEFAULT_WIDTH, start: float=0.0, duration: float | None=None, loop: int=DEFAULT_LOOP, ffmpeg_bin: str='ffmpeg', overwrite: bool=False) -> Path:
    """Convert a video to GIF using a two-pass palette workflow."""
    if not input_path.exists():
        raise VideoToGifError(f'Input video not found: {input_path}')
    resolved_ffmpeg = ensure_ffmpeg_available(ffmpeg_bin)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='video-to-gif-') as temp_dir:
        palette_path = Path(temp_dir) / 'palette.png'
        palette_command = build_palette_command(ffmpeg_bin=resolved_ffmpeg, input_path=input_path, palette_path=palette_path, start=start, duration=duration, fps=fps, width=width, overwrite=overwrite)
        gif_command = build_gif_command(ffmpeg_bin=resolved_ffmpeg, input_path=input_path, output_path=output_path, palette_path=palette_path, start=start, duration=duration, fps=fps, width=width, loop=loop, overwrite=overwrite)
        run_command(palette_command)
        run_command(gif_command)
    return output_path

def main(argv: Sequence[str] | None=None) -> int:
    """CLI entrypoint."""
    args = parse_args(argv)
    output_path = resolve_output_path(args.input, args.output)
    try:
        result = convert_video_to_gif(input_path=args.input, output_path=output_path, fps=args.fps, width=args.width, start=args.start, duration=args.duration, loop=args.loop, ffmpeg_bin=args.ffmpeg, overwrite=args.overwrite)
    except VideoToGifError as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1
    print(f'GIF created: {result}')
    return 0
