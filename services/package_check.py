"""独立安装包的离线自检，不使用用户文件。"""
from pathlib import Path
import json,traceback,shutil

def run(folder,app):
    folder.mkdir(parents=True,exist_ok=True);report={'状态':'未完成','通过项目':[]}
    try:
        from services.operations import Context,convert,extract,analyze,export_shots,grid_export,wrap
        from services import watermark_engine as watermark,merge_engine as merger
        from PIL import Image
        from main import MainWindow
        ctx=Context();video=folder/'中文测试视频.mp4';tone=folder/'测试音频.wav'
        ctx.run(['ffmpeg','-y','-f','lavfi','-i','color=c=red:s=160x90:r=24:d=1','-f','lavfi','-i','color=c=blue:s=160x90:r=24:d=1','-f','lavfi','-i','sine=frequency=440:duration=2','-filter_complex','[0:v][1:v]concat=n=2:v=1:a=0[v]','-map','[v]','-map','2:a','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac',video])
        ctx.run(['ffmpeg','-y','-f','lavfi','-i','sine=frequency=880:duration=0.5',tone]);report['通过项目'].append('内置 FFmpeg 和 FFprobe')
        result=convert(ctx,str(video),str(folder),6,160,0,1,0,'ffmpeg');assert Image.open(result).size==(160,90);report['通过项目'].append('GIF 导出')
        result=extract(ctx,str(video),str(folder),.5,(320,180));assert len(list((result/'frame').glob('*.jpg')))==4;assert Image.open(next((result/'storyboard').glob('*.jpg'))).size==(3840,2160);report['通过项目'].append('截帧与 4K 镜头表')
        _,duration,cuts=analyze(ctx,str(video),.3,.4);assert len(cuts)==1
        export_shots(ctx,str(video),str(folder),duration,cuts,.4,False);export_shots(ctx,str(video),str(folder),duration,cuts,.4,True);report['通过项目'].append('切镜检测、视频与 MP3 分段')
        image=folder/'测试图片.png';Image.new('RGB',(400,400),'steelblue').save(image)
        result=grid_export(ctx,[(str(image),'中文标题')],1,1,1,2,34,False,str(folder/'拼图.png'));assert result.exists();report['通过项目'].append('PNG 拼图与中文字体')
        assert '\n' in wrap(ctx,'这是一段用于检查文字换行的中文文本',10,'中文',True,True);report['通过项目'].append('中文换行')
        settings=watermark.DEFAULTS.copy();settings.update(key='package-test',hidden_text='安装版验证');result=watermark.export(ctx,str(image),str(folder),settings);assert watermark.verify(ctx,str(result),'package-test')=='安装版验证';report['通过项目'].append('水印绘制、写入与验证')
        result=merger.merge(ctx,str(video),str(tone),str(folder/'合并.mp4'),False,True,30,0);assert merger.probe(result)['audio'];report['通过项目'].append('音视频循环补齐、混音与 H.264 导出')
        window=MainWindow();window.showNormal();window.resize(1160,900);window.show();app.processEvents();assert window.tabs.count()==7
        assert not window.windowIcon().isNull()
        for i in range(7):
            window.tabs.setCurrentIndex(i);app.processEvents();window.grab().save(str(folder/f'安装版界面_{i+1}.png'))
        for page in window.pages:
            if hasattr(page,'timer'):page.timer.stop()
            if hasattr(page,'preview_timer'):page.preview_timer.stop()
            if hasattr(page,'preview_job') and page.preview_job.isRunning():page.preview_job.wait(10000)
        window.hide();window.deleteLater();app.processEvents();report['通过项目'].append('七页真实窗口、主题和图标')
        report.update(状态='通过',FFmpeg路径=shutil.which('ffmpeg'),FFprobe路径=shutil.which('ffprobe'),未验证=['第三方在线翻译服务'])
        code=0
    except Exception:
        report.update(状态='失败',错误=traceback.format_exc());code=1
    (folder/'安装版自检报告.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return code
