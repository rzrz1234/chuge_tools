from __future__ import annotations
import json
import math
import queue
import shutil
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
APP_DIR = Path(__file__).resolve().parent
STORYBOARD_SIZE = (3840, 2160)
RESOLUTION_PRESETS: dict[str, tuple[int, int] | None] = {'原始分辨率': None, '超小图 320 x 180': (320, 180), '小图 480 x 270': (480, 270), '小图 640 x 360（推荐）': (640, 360), '中等 960 x 540': (960, 540), '高清 1280 x 720': (1280, 720)}

@dataclass
class VideoInfo:
    duration_seconds: float
    width: int
    height: int

@dataclass(frozen=True)
class StoryboardLayout:
    page_width: int
    page_height: int
    columns: int
    top_margin: int
    bottom_margin: int
    side_margin: int
    horizontal_gap: int
    vertical_gap: int
    label_height: int
    thumb_width: int
    thumb_height: int
    max_rows: int

    @property
    def max_frames_per_page(self) -> int:
        return self.columns * self.max_rows

@dataclass
class ExtractionResult:
    frame_count: int
    output_size: tuple[int, int]
    output_dir: Path
    frame_dir: Path
    storyboard_dir: Path
    storyboard_paths: list[Path]

def find_binary(name: str) -> str | None:
    local_path = APP_DIR / f'{name}.exe'
    if local_path.exists():
        return str(local_path)
    return shutil.which(name)

def seconds_to_clock(total_seconds: float) -> str:
    seconds = max(total_seconds, 0.0)
    hours = int(seconds // 3600)
    minutes = int(seconds % 3600 // 60)
    secs = seconds % 60
    return f'{hours:02d}:{minutes:02d}:{secs:05.2f}'

def get_video_info(video_path: Path) -> VideoInfo:
    ffprobe_path = find_binary('ffprobe')
    if not ffprobe_path:
        raise RuntimeError('未找到 ffprobe，请确认 ffmpeg 已安装，或把 ffprobe.exe 放到程序同目录。')
    command = [ffprobe_path, '-v', 'error', '-show_entries', 'format=duration:stream=width,height:stream_tags=rotate:stream_side_data=rotation', '-select_streams', 'v:0', '-of', 'json', str(video_path)]
    completed = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace', check=False)
    if completed.returncode != 0:
        error_text = completed.stderr.strip() or completed.stdout.strip() or '读取视频信息失败。'
        raise RuntimeError(error_text)
    try:
        probe_data = json.loads(completed.stdout)
        duration_seconds = float(probe_data['format']['duration'])
        video_stream = probe_data['streams'][0]
        width = int(video_stream['width'])
        height = int(video_stream['height'])
        rotation = int(video_stream.get('tags', {}).get('rotate', 0))
        for side_data in video_stream.get('side_data_list', []):
            if 'rotation' in side_data:
                rotation = int(side_data['rotation'])
                break
        if abs(rotation) % 180 == 90:
            width, height = (height, width)
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError('无法解析视频时长或分辨率信息。') from exc
    return VideoInfo(duration_seconds=duration_seconds, width=width, height=height)

def build_storyboard_layout(frame_size: tuple[int, int]) -> StoryboardLayout:
    page_width, page_height = STORYBOARD_SIZE
    top_margin = 170
    bottom_margin = 90
    side_margin = 60
    horizontal_gap = 18
    vertical_gap = 34
    label_height = 62
    requested_width, requested_height = frame_size
    available_width = page_width - side_margin * 2
    available_height = page_height - top_margin - bottom_margin - label_height
    thumb_scale = min(1.0, available_width / requested_width, available_height / requested_height)
    thumb_width = max(1, round(requested_width * thumb_scale))
    thumb_height = max(1, round(requested_height * thumb_scale))
    columns = max(1, (available_width + horizontal_gap) // (thumb_width + horizontal_gap))
    max_rows = max(1, (page_height - top_margin - bottom_margin + vertical_gap) // (thumb_height + label_height + vertical_gap))
    return StoryboardLayout(page_width=page_width, page_height=page_height, columns=columns, top_margin=top_margin, bottom_margin=bottom_margin, side_margin=side_margin, horizontal_gap=horizontal_gap, vertical_gap=vertical_gap, label_height=label_height, thumb_width=thumb_width, thumb_height=thumb_height, max_rows=max_rows)

def build_export_dir(base_dir: Path, video_path: Path) -> Path:
    folder_name = f'{video_path.stem}_frames'
    candidate = base_dir / folder_name
    suffix = 2
    while candidate.exists():
        candidate = base_dir / f'{folder_name}_{suffix}'
        suffix += 1
    candidate.mkdir(parents=True, exist_ok=False)
    return candidate

def ensure_subdirs(output_dir: Path) -> tuple[Path, Path]:
    frame_dir = output_dir / 'frame'
    storyboard_dir = output_dir / 'storyboard'
    frame_dir.mkdir(parents=True, exist_ok=True)
    storyboard_dir.mkdir(parents=True, exist_ok=True)
    return (frame_dir, storyboard_dir)

def load_font(size: int) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    font_candidates = ['msyh.ttc', 'msyhbd.ttc', 'simhei.ttf', 'arial.ttf']
    for font_name in font_candidates:
        try:
            return ImageFont.truetype(font_name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()

def draw_centered_text(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], text: str, font: ImageFont.ImageFont | ImageFont.FreeTypeFont, fill: str) -> None:
    left, top, right, bottom = box
    text_box = draw.textbbox((0, 0), text, font=font)
    text_width = text_box[2] - text_box[0]
    text_height = text_box[3] - text_box[1]
    x = left + (right - left - text_width) / 2
    y = top + (bottom - top - text_height) / 2
    draw.text((x, y), text, font=font, fill=fill)

def make_thumb(image_path: Path, layout: StoryboardLayout) -> Image.Image:
    with Image.open(image_path) as source_image:
        frame = source_image.convert('RGB')
        frame.thumbnail((layout.thumb_width, layout.thumb_height))
        frame_canvas = Image.new('RGB', (layout.thumb_width, layout.thumb_height), '#d8cec2')
        paste_x = (layout.thumb_width - frame.width) // 2
        paste_y = (layout.thumb_height - frame.height) // 2
        frame_canvas.paste(frame, (paste_x, paste_y))
        return frame_canvas

def create_storyboard_pages(image_paths: list[Path], storyboard_dir: Path, interval_seconds: float, video_name: str, frame_size: tuple[int, int]) -> list[Path]:
    if not image_paths:
        raise RuntimeError('没有找到可用于合成镜头表的图片。')
    layout = build_storyboard_layout(frame_size)
    title_font = load_font(54)
    sub_font = load_font(24)
    time_font = load_font(24)
    page_paths: list[Path] = []
    page_index = 0
    start_index = 0
    while start_index < len(image_paths):
        remaining = len(image_paths) - start_index
        row_count = min(layout.max_rows, max(1, math.ceil(remaining / layout.columns)))
        frames_this_page = min(remaining, row_count * layout.columns)
        total_pages = math.ceil(len(image_paths) / layout.max_frames_per_page)
        page = Image.new('RGB', STORYBOARD_SIZE, '#f6f1e8')
        draw = ImageDraw.Draw(page)
        end_index = start_index + frames_this_page
        current_images = image_paths[start_index:end_index]
        title_y = 48
        subtitle_y = 110
        draw.text((layout.side_margin, title_y), f'镜头表 | {video_name}', fill='#23170d', font=title_font)
        draw.text((layout.side_margin, subtitle_y), f'分页输出 {layout.page_width}x{layout.page_height}    每排 {layout.columns} 张    自动 {row_count} 行    采样间隔 {interval_seconds:.1f} 秒', fill='#715d4f', font=sub_font)
        draw.text((layout.page_width - layout.side_margin - 280, subtitle_y), f'第 {page_index + 1} / {total_pages} 页', fill='#715d4f', font=sub_font)
        grid_height = row_count * (layout.thumb_height + layout.label_height) + (row_count - 1) * layout.vertical_gap
        grid_width = layout.columns * layout.thumb_width + (layout.columns - 1) * layout.horizontal_gap
        available_top = layout.top_margin
        available_bottom = layout.page_height - layout.bottom_margin
        grid_start_x = layout.side_margin + max(0, (layout.page_width - layout.side_margin * 2 - grid_width) // 2)
        grid_start_y = available_top + max(0, (available_bottom - available_top - grid_height) // 2)
        for local_index, image_path in enumerate(current_images):
            global_index = start_index + local_index
            row = local_index // layout.columns
            column = local_index % layout.columns
            x = grid_start_x + column * (layout.thumb_width + layout.horizontal_gap)
            y = grid_start_y + row * (layout.thumb_height + layout.label_height + layout.vertical_gap)
            thumb = make_thumb(image_path, layout)
            page.paste(thumb, (x, y))
            draw.rectangle((x, y, x + layout.thumb_width, y + layout.thumb_height), outline='#8d7768', width=3)
            time_label = seconds_to_clock(global_index * interval_seconds)
            draw_centered_text(draw, (x, y + layout.thumb_height + 8, x + layout.thumb_width, y + layout.thumb_height + layout.label_height), time_label, time_font, '#2d1f16')
        page_path = storyboard_dir / f'storyboard_page_{page_index + 1:02d}.jpg'
        page.save(page_path, quality=95)
        page_paths.append(page_path)
        page_index += 1
        start_index = end_index
    return page_paths
