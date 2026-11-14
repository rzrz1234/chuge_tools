"""启动真实 Qt 窗口，检查五页显示并保存本轮界面预览。"""
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from PySide6.QtWidgets import QApplication,QPushButton,QLineEdit,QCheckBox
from PySide6.QtCore import Qt,QPoint
from PySide6.QtTest import QTest
from main import MainWindow
from ui.theme import apply_theme
app=QApplication([]);apply_theme(app);window=MainWindow();window.showNormal();window.resize(1160,900);window.show()
output=root/'验证产物'/'界面_v002';output.mkdir(exist_ok=True)
for i,name in enumerate(['视频转GIF','图片拼图','视频切镜','视频截帧','文字换行']):
    window.tabs.setCurrentIndex(i);app.processEvents();QTest.qWait(120)
    assert window.pages[i].controls.isVisible()
    if i==1:
        page=window.pages[i]
        page.place(0,[str(root/'验证产物'/'红色图.png'),str(root/'验证产物'/'蓝色图.png')]);page.cells[0].title.setText('画面 01');page.cells[1].title.setText('画面 02')
    if i==4:
        page=window.pages[i];page.input.setPlainText('把常用工具放在一起，让每一次操作都更顺手。\n\n浅色背景、清晰层级、专注当前任务。');page.output_text.setPlainText('把常用工具放在一起，\n让每一次操作都更顺手。')
    app.processEvents();window.grab().save(str(output/f'{i+1:02d}_{name}.png'))
# 窄窗口检查：页面保留滚动入口，五个标签均可访问。
window.resize(980,760);window.tabs.setCurrentIndex(2);app.processEvents();QTest.qWait(100);window.grab().save(str(output/'06_小窗口切镜页.png'))
assert window.pages[2].control_scroll.verticalScrollBar().maximum()>0
# 检查日志展开、表单可编辑以及主题下复选框可交互。
page=window.pages[4];window.tabs.setCurrentIndex(4);app.processEvents()
old=page.paragraphs.isChecked();QTest.mouseClick(page.paragraphs,Qt.MouseButton.LeftButton,pos=QPoint(8,page.paragraphs.height()//2));assert page.paragraphs.isChecked()!=old
for b in page.findChildren(QPushButton):
    if b.text()=='运行日志':QTest.mouseClick(b,Qt.MouseButton.LeftButton);assert page.log.isVisible();QTest.mouseClick(b,Qt.MouseButton.LeftButton);assert not page.log.isVisible()
# 本次检查不保存测试内容或改变用户的窗口位置和路径。
window.hide();window.deleteLater();app.processEvents();print('五页显示、窄窗口滚动、日志切换与控件交互检查通过')
