"""验证原生水印页、原尺寸导出、隐形水印及旧格式双向兼容。"""
import sys,time,json,subprocess,base64,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication,QMessageBox
from PySide6.QtTest import QTest
from main import MainWindow
from ui.theme import apply_theme
from services import watermark_engine as engine
from services.operations import Context
out=root/'验证产物'/'水印_v005';out.mkdir(exist_ok=True)
app=QApplication([]);apply_theme(app);window=MainWindow();window.showNormal();window.resize(1160,900);window.show();window.tabs.setCurrentIndex(5);app.processEvents();page=window.pages[5]
source=root/'assets/logo.jpg';original=hashlib.sha256(source.read_bytes()).hexdigest();page.source.setText(str(source));page.output.setText(str(out));page.hidden_text.setPlainText('褚歌工具箱 · 中文验证');page.key.setText('中文测试密钥');page.format.setCurrentIndex(1)
messages=[]
from PySide6.QtCore import QTimer
modal=QTimer();modal.setInterval(50)
def dismiss():
    for w in app.topLevelWidgets():
        if isinstance(w,QMessageBox):messages.append((w.windowTitle(),w.text()));w.accept()
modal.timeout.connect(dismiss);modal.start()
def wait():
    limit=time.time()+40
    while page.job and page.job.isRunning():
        app.processEvents();QTest.qWait(30)
        if time.time()>limit:raise AssertionError('任务超时')
    app.processEvents();QTest.qWait(120);app.processEvents()
QTest.mouseClick(page.save_button,Qt.MouseButton.LeftButton);wait()
assert page.status.text()=='处理完成',messages
png=page.last_output;assert png.suffix=='.png';assert Image.open(png).size==Image.open(source).size
with Image.open(png) as image:assert engine.read_hidden(image,'中文测试密钥')=='褚歌工具箱 · 中文验证'
# 原网页算法读取原生导出，并由原网页算法写入后再使用原生算法读取。
legacy=Path(r'K:\tool\水印生成\app.js');script=legacy.read_text(encoding='utf-8') if legacy.exists() else ''
names=['buildHiddenPayload','readHiddenWatermark','writeBytesToPixels','readBytesFromPixels','pixelIndexForBit','xorBytes','xorshift32','hashString','hashBytes','gcd','writeUint32','readUint32']
functions=[]
for name in (names if script else []):
    start=script.index('function '+name+'(');end=script.find('\nfunction ',start+9)
    functions.append(script[start:end if end!=-1 else len(script)].strip())
js='''const fs=require('fs');const packet=JSON.parse(fs.readFileSync(0,'utf8'));const canvas={width:packet.width,height:packet.height};const encoder=new TextEncoder(),decoder=new TextDecoder(),hiddenMagic=[82,87,77,50],hiddenHeaderBytes=12;\n'''+ '\n'.join(functions)+'''
const pixels=Uint8Array.from(Buffer.from(packet.raw,'base64'));
const result=readHiddenWatermark(pixels,canvas.width*canvas.height,packet.key);
if(!result.ok || result.text!==packet.text)throw new Error('旧格式读取失败');
const payload=buildHiddenPayload('旧工具写入的中文水印',packet.key);writeBytesToPixels(pixels,canvas.width*canvas.height,payload,packet.key);
process.stdout.write(Buffer.from(pixels).toString('base64'));
'''
js_path=out/'旧格式互通检查.js'
if script:js_path.write_text(js,encoding='utf-8')
assert js_path.is_file(),'缺少旧格式互通检查样例'
with Image.open(png) as image:
    image=image.convert('RGBA');packet=dict(width=image.width,height=image.height,raw=base64.b64encode(image.tobytes()).decode(),key='中文测试密钥',text='褚歌工具箱 · 中文验证')
result=subprocess.run(['node',str(js_path)],input=json.dumps(packet),capture_output=True,text=True,encoding='utf-8',check=True,timeout=30)
from_js=Image.frombytes('RGBA',(packet['width'],packet['height']),base64.b64decode(result.stdout));assert engine.read_hidden(from_js,packet['key'])=='旧工具写入的中文水印';from_js.save(out/'旧工具格式样例.png')
page.source.setText(str(png));QTest.mouseClick(page.verify_button,Qt.MouseButton.LeftButton);wait();assert page.status.text()=='验证成功',messages
page.key.setText('错误密钥');page.verify();wait();assert any('密钥' in message and title=='处理失败' for title,message in messages)
# 单个九宫格、平铺、JPG 与 WEBP 导出。
ctx=Context();settings=page.settings();settings.update(hidden=False,protect=False,key='中文测试密钥')
for position in range(9):
    settings['position']=position;image=engine.render(ctx,str(source),settings);assert not image.isNull()
settings.update(mode='平铺',protect=True)
for fmt in ['JPG','WEBP']:
    settings['format']=fmt;path=engine.export(ctx,str(source),str(out),settings);assert Image.open(path).size==(834,834)
# 空密钥、容量不足、无水印图片均显示明确失败。
for image,text,key in [(Image.new('RGB',(200,200)),'内容',''),(Image.new('RGB',(8,8)),'内容','key')]:
    try:engine.embed(image,text,key);raise AssertionError('异常分支未触发')
    except ValueError:pass
try:engine.read_hidden(Image.new('RGB',(200,200)),'key');raise AssertionError('无水印误判')
except ValueError:pass
page.source.setText(str(source));page.key.setText('中文测试密钥');page.mode.setCurrentIndex(1)
limit=time.time()+15
while time.time()<limit:
    app.processEvents();QTest.qWait(80)
    if not page.pending_preview and hasattr(page,'preview_job') and not page.preview_job.isRunning():break
assert page.preview_image is not None
page.log.hide();page.status.setText('预览已更新，可保存或验证导入图片');app.processEvents();window.grab().save(str(out/'水印页界面.png'));window.resize(980,760);app.processEvents();QTest.qWait(100);window.grab().save(str(out/'水印页小窗口.png'))
assert window.tabs.count()==7;assert hashlib.sha256(source.read_bytes()).hexdigest()==original
report={'状态':'通过','版本':'v1.2.0','验证项目':['第六个原生标签页','后台预览','按钮触发原分辨率 PNG 保存','隐形开启强制 PNG','中文水印和中文密钥','原网页算法与原生算法双向互通','UI 验证成功与错误密钥中文弹窗','九宫格和平铺绘制','JPG / WEBP 导出','容量不足 / 空密钥 / 无水印错误','源文件保持原样','980×760 小窗口显示'],'原生导出路径':str(png)}
(out/'测试报告_v005.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
page.timer.stop()
while hasattr(page,'preview_job') and page.preview_job.isRunning():app.processEvents();QTest.qWait(30)
window.hide();window.deleteLater();app.processEvents();print('水印功能集成与旧格式双向兼容检查通过')
