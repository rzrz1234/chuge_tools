import queue
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
import cv2
from scenedetect import SceneManager, open_video
from scenedetect.detectors import ContentDetector
APP_TITLE = '视频切镜拆段工具'
VIDEO_TYPES = [('Video Files', '*.mp4 *.mov *.mkv *.avi *.flv *.wmv *.m4v *.webm'), ('All Files', '*.*')]
TIMELINE_WIDTH = 880
TIMELINE_HEIGHT = 120
PREVIEW_SIZE = (320, 180)

@dataclass
class Segment:
    index: int
    start: float
    end: float

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)

def format_seconds(seconds: float) -> str:
    total_ms = max(0, int(round(seconds * 1000)))
    hours, remainder = divmod(total_ms, 3600000)
    minutes, remainder = divmod(remainder, 60000)
    secs, ms = divmod(remainder, 1000)
    return f'{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}'

def get_video_duration(input_path: Path) -> float:
    command = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(input_path)]
    result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace', check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or '无法读取视频时长。')
    try:
        return float(result.stdout.strip())
    except ValueError as exc:
        raise RuntimeError('ffprobe 返回的时长无效。') from exc

def sensitivity_to_content_threshold(sensitivity: float) -> float:
    normalized = min(max(sensitivity, 0.05), 0.9)
    return 42.0 - (normalized - 0.05) / 0.85 * 30.0

def detect_cuts(input_path: Path, threshold: float, min_duration: float, log) -> list[float]:
    log('正在使用专业切镜检测器分析视频...')
    detector_threshold = sensitivity_to_content_threshold(threshold)
    log(f'切镜灵敏度: {threshold:.2f}')
    log(f'检测器阈值: {detector_threshold:.2f}')
    video = open_video(str(input_path))
    if video is None:
        raise RuntimeError('无法打开视频进行切镜检测。')
    fps = video.frame_rate
    min_scene_frames = max(4, int(round(fps * max(min_duration, 0.15))))
    log(f'最短检测片段: {min_duration:.2f} 秒 / {min_scene_frames} 帧')
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector(threshold=detector_threshold, min_scene_len=min_scene_frames))
    scene_manager.detect_scenes(video=video, show_progress=False)
    scene_list = scene_manager.get_scene_list()
    cut_times = [scene[0].get_seconds() for scene in scene_list[1:]]
    log(f'检测到 {len(cut_times)} 个候选切镜点。')
    return cut_times

def build_segments(duration: float, cut_times: list[float], min_duration: float) -> list[Segment]:
    points = [0.0]
    for cut_time in sorted(cut_times):
        if 0 < cut_time < duration:
            points.append(cut_time)
    points.append(duration)
    segments: list[Segment] = []
    index = 1
    for start, end in zip(points, points[1:]):
        if end - start <= 0.05:
            continue
        if segments and end - start < min_duration:
            previous = segments[-1]
            segments[-1] = Segment(index=previous.index, start=previous.start, end=end)
            continue
        segments.append(Segment(index=index, start=start, end=end))
        index += 1
    if not segments and duration > 0.05:
        segments.append(Segment(index=1, start=0.0, end=duration))
    return segments

def export_segments(input_path: Path, output_dir: Path, segments: list[Segment], log, progress) -> None:
    stem = input_path.stem
    total = len(segments)
    for segment in segments:
        output_file = output_dir / f'{stem}_part_{segment.index:03d}_{format_seconds(segment.start).replace(':', '-')}_{format_seconds(segment.end).replace(':', '-')}.mp4'
        command = ['ffmpeg', '-hide_banner', '-y', '-ss', format_seconds(segment.start), '-to', format_seconds(segment.end), '-i', str(input_path), '-c:v', 'libx264', '-preset', 'fast', '-crf', '18', '-c:a', 'aac', '-movflags', '+faststart', str(output_file)]
        log(f'[{segment.index}/{total}] 导出片段 {format_seconds(segment.start)} -> {format_seconds(segment.end)}')
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace', check=False)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or f'导出片段 {segment.index} 失败。')
        progress(segment.index, total)

def export_mp3_segments(input_path: Path, output_dir: Path, segments: list[Segment], log, progress) -> None:
    stem = input_path.stem
    total = len(segments)
    for segment in segments:
        output_file = output_dir / f'{stem}_part_{segment.index:03d}_{format_seconds(segment.start).replace(':', '-')}_{format_seconds(segment.end).replace(':', '-')}.mp3'
        command = ['ffmpeg', '-hide_banner', '-y', '-ss', format_seconds(segment.start), '-to', format_seconds(segment.end), '-i', str(input_path), '-vn', '-codec:a', 'libmp3lame', '-q:a', '2', str(output_file)]
        log(f'[{segment.index}/{total}] export mp3 segment {format_seconds(segment.start)} -> {format_seconds(segment.end)}')
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace', check=False)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or f'export mp3 segment {segment.index} failed')
        progress(segment.index, total)
