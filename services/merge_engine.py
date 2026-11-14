"""视频与音轨合并，保留原工具的循环、截断、混音及帧率模式。"""
import json,subprocess,tempfile
from pathlib import Path
from services.operations import video_path

def probe(path):
    if not str(path).strip() or not Path(path).is_file():raise ValueError('请选择存在的媒体文件。')
    result=subprocess.run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(path)],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=20,creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:raise ValueError('无法读取媒体信息：'+result.stderr[-1000:])
    data=json.loads(result.stdout);streams=data.get('streams',[])
    video=next((s for s in streams if s.get('codec_type')=='video' and not s.get('disposition',{}).get('attached_pic')),None)
    audio=next((s for s in streams if s.get('codec_type')=='audio'),None)
    raw=data.get('format',{}).get('duration') or (video or audio or {}).get('duration') or 0
    duration=float(raw)
    if duration<=0:raise ValueError('媒体时长无效，无法处理该文件。')
    return dict(duration=duration,video=video,audio=audio,size=Path(path).stat().st_size)

def fps(stream):
    if not stream:return 0
    for field in ['avg_frame_rate','r_frame_rate']:
        value=stream.get(field,'0/1')
        try:
            a,b=value.split('/');rate=float(a)/float(b)
            if rate>0:return rate
        except (ValueError,ZeroDivisionError):pass
    return 0

def inspect(ctx,video,audio):
    ctx.check();v=probe(video);a=probe(audio);ctx.check()
    if not v['video']:raise ValueError('输入视频没有可用的视频轨。')
    if not a['audio']:raise ValueError('所选音频源没有音频轨，请换用含声音的文件。')
    return (f"视频：{v['video'].get('width')} × {v['video'].get('height')}  ·  {v['duration']:.3f} 秒  ·  {fps(v['video']):.3f} fps\n"
            f"音频源：{'从视频取音轨' if a['video'] else '音频文件'}  ·  {a['duration']:.3f} 秒\n"
            f"原视频：{'有原声音轨，可替换或混合' if v['audio'] else '无原声音轨，将直接使用新音频'}")

def merge(ctx,video,audio,output,replace=True,fixed=False,rate=30,maximum=15):
    video=video_path(video)
    if not audio.strip() or not Path(audio).is_file():raise ValueError('请选择有效的音频源，支持音频文件或含音轨的视频。')
    if not output.strip():raise ValueError('请选择输出 MP4 文件路径。')
    target=Path(output)
    if target.suffix.lower()!='.mp4':target=target.with_suffix('.mp4')
    if target.resolve() in [video.resolve(),Path(audio).resolve()]:raise ValueError('输出路径不能与输入视频或音频源相同。')
    ctx.log('正在读取视频与音轨信息…');v=probe(video);a=probe(audio);ctx.check()
    if not v['video']:raise ValueError('输入视频没有可用的视频轨。')
    if not a['audio']:raise ValueError('音频源不包含音轨，请换用含声音的音频或视频。')
    duration=min(v['duration'],maximum) if maximum>0 else v['duration']
    ctx.log(f"视频原时长 {v['duration']:.3f} 秒，本次输出 {duration:.3f} 秒。")
    if duration<v['duration']:ctx.log(f'已启用输出时长上限：{maximum:g} 秒。设置为 0 可输出完整视频。')
    target.parent.mkdir(parents=True,exist_ok=True);stem=target.stem;i=2
    while target.exists():target=target.with_name(f'{stem}_{i}.mp4');i+=1
    # 使用临时文件完成整次处理，成功后再发布目标文件。
    with tempfile.TemporaryDirectory(prefix='chuge-merge-') as folder:
        temp=Path(folder);processed=temp/'audio.m4a';done=temp/'result.mp4'
        command=['ffmpeg','-hide_banner','-nostdin','-y']
        if a['duration']<duration:
            command+=['-stream_loop','-1'];ctx.log('音频较短，将循环补齐到视频输出时长。')
        elif a['duration']>duration:ctx.log('音频较长，将截取到视频输出时长。')
        command+=['-i',audio,'-map','0:a:0','-t',f'{duration:.6f}','-vn','-c:a','aac','-b:a','192k',processed]
        ctx.run(command);ctx.progress(40)
        command=['ffmpeg','-hide_banner','-nostdin','-y','-i',video,'-i',processed,'-map_metadata','0']
        if replace or not v['audio']:
            command+=['-map','0:v:0','-map','1:a:0'];ctx.log('使用新音频替换原声。' if replace else '原视频没有音轨，直接使用新音频。')
        else:
            command+=['-filter_complex','[0:a:0]volume=0.3[a0];[1:a:0]volume=0.7[a1];[a0][a1]amix=inputs=2:duration=longest:dropout_transition=0[a]','-map','0:v:0','-map','[a]'];ctx.log('按原工具的原声 0.3 / 新音频 0.7 权重混音。')
        if fixed:
            command+=['-c:v','libx264','-preset','medium','-pix_fmt','yuv420p','-r',str(rate)];ctx.log(f'重新编码为 H.264，固定 {rate} fps。')
        else:command+=['-c:v','copy'];ctx.log('复制原视频流，保留画面与原帧率。')
        command+=['-c:a','aac','-b:a','192k','-t',f'{duration:.6f}','-movflags','+faststart',done]
        ctx.run(command);ctx.progress(95);ctx.check()
        # 独占创建，避免覆盖其他任务同时写入的结果。
        with target.open('xb') as dest,done.open('rb') as src:
            import shutil
            shutil.copyfileobj(src,dest)
    return target
