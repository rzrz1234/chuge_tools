import sys,time,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication,QMessageBox,QFileDialog
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt,QTimer
from PIL import Image
from services import operations as op
from main import MainWindow
root=Path(__file__).resolve().parents[1]/'验证产物'
root.mkdir(exist_ok=True)
ctx=op.Context()
source=root/'中文测试视频.mp4'
ctx.run(['ffmpeg','-y','-f','lavfi','-i','color=c=red:s=320x180:r=25:d=1','-f','lavfi','-i','color=c=blue:s=320x180:r=25:d=1','-f','lavfi','-i','sine=frequency=440:duration=2','-filter_complex','[0:v][1:v]concat=n=2:v=1:a=0[v]','-map','[v]','-map','2:a','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac',source])
for name,color in [('红色图.png','red'),('蓝色图.png','blue')]: Image.new('RGB',(360,240),color).save(root/name)
app=QApplication([]); window=MainWindow(); window.show(); app.processEvents()
failures=[]
def dismiss():
    for w in app.topLevelWidgets():
        if isinstance(w,QMessageBox): failures.append(w.text()); w.accept()
timer=QTimer();timer.timeout.connect(dismiss);timer.start(50)
def wait(page):
    limit=time.time()+90
    while page.job and page.job.isRunning():
        app.processEvents(); QTest.qWait(30)
        if time.time()>limit: raise AssertionError('任务超时')
    app.processEvents()
    if failures: raise AssertionError(str(failures))
    assert page.status.text().startswith(('处理完成','分析完成')),page.log.toPlainText()
for p in window.pages:
    if hasattr(p,'source'): p.source.setText(str(source))
    if hasattr(p,'output'): p.output.setText(str(root))
# 点击真实窗口上的按钮，等待后台线程返回。
gif,grid,shot,frame,text=window.pages[:5]
window.tabs.setCurrentIndex(0); gif.width.setValue(160); QTest.mouseClick(gif.run_button,Qt.MouseButton.LeftButton); wait(gif)
assert gif.last_output.is_file(); assert Image.open(gif.last_output).size==(160,90)
window.tabs.setCurrentIndex(3); frame.size.setCurrentIndex(1); QTest.mouseClick(frame.run_button,Qt.MouseButton.LeftButton); wait(frame)
assert len(list((frame.last_output/'frame').glob('*.jpg')))==4
assert Image.open(next((frame.last_output/'storyboard').glob('*.jpg'))).size==(3840,2160)
window.tabs.setCurrentIndex(2);shot.analyze();wait(shot)
assert len(shot.cuts)==1 and abs(shot.cuts[0]-1)<.1,shot.cuts
shot.position.setValue(.5);shot.add_cut();assert len(shot.cuts)==2
shot.cuts_list.setCurrentRow(0);shot.remove_cut();shot.restore();assert len(shot.cuts)==1
shot.export(False);wait(shot);assert len(list(shot.last_output.glob('*.mp4')))==2
shot.export(True);wait(shot);assert len(list(shot.last_output.glob('*.mp3')))==2
window.tabs.setCurrentIndex(1);grid.rows.setValue(1);grid.cols.setValue(2);grid.place(0,[str(root/'红色图.png'),str(root/'蓝色图.png')]);grid.cells[0].title.setText('第一张：红色');grid.cells[1].title.setText('第二张：蓝色')
original=QFileDialog.getSaveFileName;QFileDialog.getSaveFileName=lambda *a,**kw:(str(root/'测试拼图.png'),'')
grid.export();wait(grid);QFileDialog.getSaveFileName=original
assert Image.open(root/'测试拼图.png').width==1446
window.tabs.setCurrentIndex(4);text.input.setPlainText('这是用于检查中文换行功能的示例文字。\n\n第二个段落需要保持。');text.width.setValue(12);text.language.setCurrentText('中文');text.wrap();wait(text);assert '\n\n' in text.output_text.toPlainText()
# 异常流程必须出现中文对话框。
gif.source.setText('不存在.mp4');gif.run()
while gif.job.isRunning():app.processEvents();QTest.qWait(30)
app.processEvents();QTest.qWait(100);app.processEvents();assert any('请选择存在的视频文件' in s for s in failures)
failures.clear();gif.source.setText(str(source))
for i,p in enumerate(window.pages):
    window.tabs.setCurrentIndex(i);app.processEvents();QTest.qWait(150);window.grab().save(str(root/f'界面_{i+1}.png'))
while hasattr(shot,'preview_job') and shot.preview_job.isRunning():app.processEvents();QTest.qWait(50)
# 取消流程与竖屏适配。
ctx2=op.Context();ctx2.cancel.set()
try:ctx2.run(['ffmpeg','-version']);raise AssertionError('取消失效')
except op.Cancelled:pass
portrait=root/'竖屏测试.mp4';ctx.run(['ffmpeg','-y','-f','lavfi','-i','color=c=green:s=180x320:r=25:d=1','-c:v','libx264',portrait])
result=op.extract(ctx,str(portrait),str(root),.5,(320,180));assert Image.open(next((result/'frame').glob('*.jpg'))).size==(180,320)
(root/'测试报告_v001.json').write_text(json.dumps({'状态':'通过','项目':['五个原生标签页','GIF 点击导出及尺寸','间隔截帧与 4K 镜头表','自动检测颜色切镜','手动增删及恢复切点','H.264 视频分段','MP3 音频分段','带中文标题的 PNG 拼图','中文换行与段落保留','错误中文弹窗','取消操作','竖屏适配'],'未验证':['第三方在线翻译服务可用性']},ensure_ascii=False,indent=2),encoding='utf-8')
window.close();print('全部集成检查通过')
