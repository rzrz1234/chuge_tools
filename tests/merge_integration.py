"""音视频合并实际导出与第七个标签页的集成验证。"""
import sys,time,json,subprocess,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
import numpy as np
from PySide6.QtCore import Qt,QTimer
from PySide6.QtWidgets import QApplication,QMessageBox
from PySide6.QtTest import QTest
from services.operations import Context,Cancelled
from services import merge_engine as engine
from main import MainWindow
from ui.theme import apply_theme
out=root/'验证产物'/'音视频合并_v006';out.mkdir(exist_ok=True);ctx=Context()
video=out/'原视频_48帧_18秒.mp4';audio=out/'短音频_880赫兹.wav';silent=out/'无声视频.mp4'
ctx.run(['ffmpeg','-y','-f','lavfi','-i','color=c=steelblue:s=160x90:r=48:d=18','-f','lavfi','-i','sine=frequency=440:duration=18','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-shortest',video])
ctx.run(['ffmpeg','-y','-f','lavfi','-i','sine=frequency=880:duration=1',audio])
ctx.run(['ffmpeg','-y','-f','lavfi','-i','color=c=orange:s=160x90:r=48:d=2','-c:v','libx264',silent])
original=hashlib.sha256(video.read_bytes()).hexdigest()
app=QApplication([]);apply_theme(app);window=MainWindow();window.showNormal();window.resize(1160,900);window.show();window.tabs.setCurrentIndex(6);app.processEvents();page=window.pages[6]
messages=[]
def dismiss():
    for w in app.topLevelWidgets():
        if isinstance(w,QMessageBox):messages.append(w.text());w.accept()
timer=QTimer();timer.setInterval(50);timer.timeout.connect(dismiss);timer.start()
def wait():
    limit=time.time()+60
    while page.job and page.job.isRunning():
        app.processEvents();QTest.qWait(30)
        if time.time()>limit:raise AssertionError('任务超时')
    app.processEvents();QTest.qWait(100);app.processEvents()
page.source.setText(str(video));page.audio.setText(str(audio));page.output.setText(str(out/'默认替换.mp4'));page.inspect();wait();assert '48.000' in page.info.text()
QTest.mouseClick(page.run_button,Qt.MouseButton.LeftButton);wait();assert page.status.text()=='处理完成',messages
first=page.last_output;info=engine.probe(first);assert abs(info['duration']-15)<.15,info['duration'];assert abs(engine.fps(info['video'])-48)<.01
# 码流复制模式的压缩视频包应保持逐包一致。
def packets(path):
    r=subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_packets','-show_data_hash','sha256','-of','json',str(path)],capture_output=True,text=True,encoding='utf-8',check=True)
    return [p['data_hash'] for p in json.loads(r.stdout)['packets']]
assert packets(first)[:100]==packets(video)[:100]
# 短音频循环后的末尾仍有新音轨声音；原声应已被替换。
def spectrum(path,start):
    r=subprocess.run(['ffmpeg','-v','error','-ss',str(start),'-i',str(path),'-t','0.5','-vn','-ac','1','-ar','8000','-f','f32le','pipe:1'],capture_output=True,check=True)
    samples=np.frombuffer(r.stdout,dtype='<f4');assert len(samples)>1000
    spec=np.abs(np.fft.rfft(samples));freq=np.fft.rfftfreq(len(samples),1/8000)
    def peak(f):return float(spec[np.abs(freq-f)<4].max())
    return peak(440),peak(880)
a,b=spectrum(first,13);assert b>a*10,(a,b)
# 混音与固定帧率重编码，输出完整 18 秒。
page.output.setText(str(out/'完整混音24帧.mp4'));page.maximum.setValue(0);page.replace.setChecked(False);page.mode.setCurrentIndex(1);page.rate.setValue(24);page.run();wait();assert page.status.text()=='处理完成',messages
mixed=page.last_output;info=engine.probe(mixed);assert abs(info['duration']-18)<.15;assert abs(engine.fps(info['video'])-24)<.01;assert info['video']['codec_name']=='h264'
a,b=spectrum(mixed,16);assert a>5 and b>5,(a,b)
# 视频作为音频源，长音轨截断；无原声时直接使用新音频。
page.source.setText(str(silent));page.audio.setText(str(video));page.output.setText(str(out/'视频取音轨.mp4'));page.mode.setCurrentIndex(0);page.run();wait();assert page.status.text()=='处理完成',messages
assert abs(engine.probe(page.last_output)['duration']-2)<.15
# 重复导出不得覆盖已存在文件。
previous=page.last_output;page.run();wait();assert page.last_output!=previous and previous.exists()
# 音频源无音轨时中文失败，原始文件不变。
page.audio.setText(str(silent));page.run();wait();assert any('不包含音轨' in s for s in messages)
assert hashlib.sha256(video.read_bytes()).hexdigest()==original
cancel=Context();cancel.cancel.set()
try:engine.merge(cancel,str(video),str(audio),str(out/'不应生成.mp4'));raise AssertionError('未取消')
except Cancelled:pass
assert not (out/'不应生成.mp4').exists()
page.audio.setText(str(audio));page.source.setText(str(video));page.output.setText(str(out/'合并结果.mp4'));page.maximum.setValue(15);page.replace.setChecked(True);page.inspect();wait();page.log.hide();app.processEvents();QTest.qWait(100)
window.grab().save(str(out/'音视频合并页.png'));window.resize(980,760);app.processEvents();QTest.qWait(100);window.grab().save(str(out/'音视频合并页_小窗口.png'))
assert window.tabs.count()==7
report=dict(状态='通过',版本='v1.3.0',验证项目=['真实 Windows 窗口第七个标签页','按钮触发合并','默认 15 秒上限','短音频循环至末尾','原声替换音频频谱检查','压缩视频包一致，保持原帧率','完整 18 秒输出','原声与新音频混音频谱检查','固定 24fps H.264 输出','视频提取音轨','无原声视频直接配音','长音轨截断','同名输出自动编号','无音轨中文错误弹窗','取消与原文件保留','小窗口显示'])
(out/'测试报告_v006.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
window.hide();window.deleteLater();app.processEvents();print('音视频合并集成检查通过')
