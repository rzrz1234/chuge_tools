from pathlib import Path
import subprocess
import threading
from PIL import Image, ImageOps, ImageDraw
from services import gif_engine as gif, frame_engine as frames, shot_engine as shots
from services.text_engine import TextWrapperApp

class Cancelled(Exception):
    pass

class Context:
    def __init__(self, log=lambda x: None, progress=lambda x: None):
        self.log, self.progress = log, progress
        self.cancel = threading.Event()
    def check(self):
        if self.cancel.is_set(): raise Cancelled('任务已取消，已生成的文件予以保留。')
    def run(self, args):
        self.check()
        import tempfile
        with tempfile.TemporaryFile() as errors:
            proc = subprocess.Popen([str(x) for x in args], stdout=errors, stderr=errors,
                                    creationflags=subprocess.CREATE_NO_WINDOW)
            while True:
                try:
                    code = proc.wait(timeout=0.15)
                    break
                except subprocess.TimeoutExpired:
                    if self.cancel.is_set():
                        proc.terminate()
                        proc.wait()
                        self.check()
            if code:
                errors.seek(0)
                raise RuntimeError('处理失败：\n'+errors.read().decode('utf-8', errors='replace')[-2500:])
        self.check()

def video_path(value):
    p = Path(value)
    if not value.strip() or not p.is_file(): raise ValueError('请选择存在的视频文件。')
    return p

def make_dir(base, name):
    if not str(base).strip(): raise ValueError('请选择输出文件夹。')
    p=Path(base)/name
    i=2
    while p.exists():
        p=Path(base)/f'{name}_{i}'
        i+=1
    p.mkdir(parents=True)
    return p

def convert(ctx, src, out, fps, width, start, duration, loop, ffmpeg):
    src=video_path(src)
    target=make_dir(out,src.stem+'_GIF')/(src.stem+'.gif')
    import tempfile
    binary=gif.ensure_ffmpeg_available(ffmpeg)
    with tempfile.TemporaryDirectory() as folder:
        palette=Path(folder)/'palette.png'
        ctx.log('正在生成调色板…')
        ctx.run(gif.build_palette_command(binary,src,palette,start,duration,fps,width,True))
        ctx.progress(50)
        ctx.log('正在生成 GIF…')
        ctx.run(gif.build_gif_command(binary,src,target,palette,start,duration,fps,width,loop,True))
    return target

def extract(ctx, src, out, interval, size):
    src=video_path(src)
    info=frames.get_video_info(src)
    target=make_dir(out,src.stem+'_frames')
    fdir,sdir=frames.ensure_subdirs(target)
    actual=size or (info.width,info.height)
    if size and info.height>info.width: actual=actual[::-1]
    vf=[f'fps=1/{interval}']
    if size:
        w,h=actual
        vf += [f'scale={w}:{h}:force_original_aspect_ratio=increase',f'crop={w}:{h}','setsar=1']
    ctx.log('正在截取图片…')
    ctx.run([frames.find_binary('ffmpeg') or 'ffmpeg','-hide_banner','-y','-i',src,'-vf',','.join(vf),'-q:v','2',fdir/'frame_%04d.jpg'])
    ctx.progress(85)
    paths=sorted(fdir.glob('*.jpg'))
    if not paths: raise RuntimeError('没有生成图片，请减小截帧间隔。')
    ctx.log(f'已生成 {len(paths)} 张图片，正在排列 4K 镜头表…')
    frames.create_storyboard_pages(paths,sdir,interval,src.stem,actual)
    ctx.check()
    return target

def analyze(ctx, src, sensitivity, minimum):
    from scenedetect import SceneManager, open_video
    from scenedetect.detectors import ContentDetector
    src=video_path(src)
    duration=shots.get_video_duration(src)
    video=open_video(str(src))
    manager=SceneManager()
    manager.add_detector(ContentDetector(threshold=shots.sensitivity_to_content_threshold(sensitivity),min_scene_len=max(4,round(video.frame_rate*minimum))))
    def callback(frame, number):
        if ctx.cancel.is_set(): manager.stop()
        ctx.progress(min(99,int((number.get_seconds() if hasattr(number, "get_seconds") else number/float(video.frame_rate))/duration*100)))
    ctx.log('正在分析切镜点…')
    manager.detect_scenes(video=video,callback=callback,show_progress=False)
    ctx.check()
    return (str(src),duration,[s[0].get_seconds() for s in manager.get_scene_list()[1:]])

def export_shots(ctx, src, out, duration, cuts, minimum, audio):
    src=video_path(src)
    target=make_dir(out,src.stem+('_音频分段' if audio else '_视频分段'))
    segments=shots.build_segments(duration,cuts,minimum)
    for i,seg in enumerate(segments):
        ctx.log(f'导出 {i+1}/{len(segments)}：{seg.start:.3f} → {seg.end:.3f} 秒')
        args=['ffmpeg','-hide_banner','-y','-ss',seg.start,'-to',seg.end,'-i',src]
        args+=['-vn','-codec:a','libmp3lame','-q:a','2'] if audio else ['-c:v','libx264','-preset','fast','-crf','18','-c:a','aac','-movflags','+faststart']
        ctx.run(args+[target/f'{src.stem}_{i+1:03d}.{ "mp3" if audio else "mp4"}'])
        ctx.progress(round((i+1)/len(segments)*100))
    return target

def preview(ctx, src, t):
    import cv2
    import numpy as np
    cap=cv2.VideoCapture(str(src))
    try:
        fps=cap.get(cv2.CAP_PROP_FPS) or 25
        images=[]
        for sec in [max(0,t-1/fps),t]:
            cap.set(cv2.CAP_PROP_POS_MSEC,sec*1000)
            ok,frame=cap.read()
            if not ok: images.append(None); continue
            frame=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
            h,w=frame.shape[:2]
            from PySide6.QtGui import QImage
            images.append(QImage(frame.data,w,h,w*3,QImage.Format.Format_RGB888).copy())
        return images
    finally: cap.release()

def grid_export(ctx, cells, rows, cols, ratio, gap, font_size, contain, output):
    w=720; h=round(w/ratio); label_h=max(86,round(font_size*2.7))
    canvas=Image.new('RGB',(cols*w+(cols+1)*gap,rows*(h+label_h)+(rows+1)*gap),'white')
    draw=ImageDraw.Draw(canvas); font=frames.load_font(font_size)
    for i,(path,title) in enumerate(cells):
        ctx.check()
        x=gap+(i%cols)*(w+gap); y=gap+(i//cols)*(h+label_h+gap)
        draw.rectangle((x,y,x+w,y+h),fill='#f1f3f1')
        if path:
            with Image.open(path) as image:
                image=ImageOps.exif_transpose(image).convert('RGB')
                thumb=ImageOps.contain(image,(w,h)) if contain else ImageOps.fit(image,(w,h))
                canvas.paste(thumb,(x+(w-thumb.width)//2,y+(h-thumb.height)//2))
        lines=[]; line=''
        for char in title:
            if char=='\n' or draw.textlength(line+char,font=font)>w-24:
                lines.append(line); line='' if char=='\n' else char
            else: line+=char
        lines.append(line)
        for j,line in enumerate(lines[:2]):
            draw.text((x+w/2,y+h+8+j*round(font_size*1.2)),line,fill='#1d2424',font=font,anchor='mt')
        ctx.progress(round((i+1)/len(cells)*100))
    canvas.save(output,'PNG')
    return Path(output)

def wrap(ctx, text, width, language, paragraphs, words):
    if not text.strip(): raise ValueError('请输入需要处理的文本。')
    engine=TextWrapperApp()
    language=engine.detect_language(text) if language=='自动识别' else language
    return engine.advanced_text_wrap(text,width,language,paragraphs,words)

def translate(ctx,text):
    if not text.strip(): raise ValueError('请输入需要翻译的英文。')
    return TextWrapperApp()._translate_to_chinese(text)[0]
