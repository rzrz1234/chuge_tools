import sys
import traceback
from runtime_paths import initialize,LOG_ROOT
initialize()
from pathlib import Path
from PySide6.QtCore import QSettings
from PySide6.QtGui import QPixmap,QIcon
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication,QMainWindow,QTabWidget,QMessageBox,QWidget,QVBoxLayout,QHBoxLayout,QLabel
from ui.theme import apply_theme
from ui.watermark_page import WatermarkPage
from ui.merge_page import MergePage
from ui.pages import GifPage,GridPage,ShotPage,FramePage,TextPage

ROOT=Path(__file__).resolve().parent

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle('褚歌工具箱 v1.3.0'); self.resize(1160,900); self.setMinimumSize(980,760)
        workspace=QWidget(); workspace.setObjectName('workspace'); outer=QVBoxLayout(workspace); outer.setContentsMargins(0,0,0,0); outer.setSpacing(0)
        header=QWidget(); header.setObjectName('appHeader'); header_row=QHBoxLayout(header); header_row.setContentsMargins(28,16,28,16); header_row.setSpacing(12)
        mark=QLabel(); mark.setObjectName('brandMark'); mark.setFixedSize(44,44); mark.setToolTip('褚歌工具箱')
        from PySide6.QtCore import Qt
        mark.setPixmap(QPixmap(str(ROOT/'assets/logo.jpg')).scaled(44,44,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)); mark.setAlignment(Qt.AlignmentFlag.AlignCenter); header_row.addWidget(mark)
        self.setWindowIcon(QIcon(str(ROOT/'assets/logo.ico')))
        labels=QVBoxLayout(); labels.setSpacing(2); brand=QLabel('褚歌工具箱'); brand.setObjectName('brand'); caption=QLabel('让常用操作，简单一点'); caption.setObjectName('brandCaption'); labels.addWidget(brand); labels.addWidget(caption); header_row.addLayout(labels); header_row.addStretch()
        badge=QLabel('本地工作台  ·  7 项工具'); badge.setObjectName('workspaceBadge'); header_row.addWidget(badge)
        outer.addWidget(header)
        self.tabs=QTabWidget(); self.tabs.setDocumentMode(True); self.tabs.setUsesScrollButtons(True); outer.addWidget(self.tabs,1); self.setCentralWidget(workspace)
        self.pages=[GifPage(),GridPage(),ShotPage(),FramePage(),TextPage(),WatermarkPage(),MergePage()]
        for page,name in zip(self.pages,['视频转 GIF','图片拼图','视频切镜拆段','视频截帧 / 镜头表','文字换行','水印生成','音视频合并']): self.tabs.addTab(page,name)
        self.settings=QSettings('初歌','初歌工具箱')
        geometry=self.settings.value('geometry')
        if geometry: self.restoreGeometry(geometry)
        for i,page in enumerate(self.pages):
            if hasattr(page,'source'): page.source.setText(self.settings.value(f'{i}/source',''))
            if hasattr(page,'output'):
                saved=self.settings.value(f'{i}/output',None)
                if saved is not None: page.output.setText(saved)
            if hasattr(page,'audio'): page.audio.setText(self.settings.value(f'{i}/audio',''))
        self.statusBar().showMessage('  褚歌工具箱  v1.3.0     ·     本地处理，随时切换功能')
    def activate(self):
        while self.server.hasPendingConnections():
            client=self.server.nextPendingConnection(); client.close(); client.deleteLater()
        self.showNormal(); self.raise_(); self.activateWindow()
    def closeEvent(self,event):
        busy=any((p.job and p.job.isRunning()) or (hasattr(p,'preview_job') and p.preview_job.isRunning()) for p in self.pages)
        if busy:
            QMessageBox.information(self,'任务仍在运行','请先取消任务并等待结束，再关闭程序。'); event.ignore(); return
        self.settings.setValue('geometry',self.saveGeometry())
        for i,page in enumerate(self.pages):
            if hasattr(page,'source'): self.settings.setValue(f'{i}/source',page.source.text())
            if hasattr(page,'output'): self.settings.setValue(f'{i}/output',page.output.text())
            if hasattr(page,'audio'): self.settings.setValue(f'{i}/audio',page.audio.text())
        event.accept()

def main():
    app=QApplication(sys.argv); app.setStyle('Fusion'); app.setApplicationName('褚歌工具箱')
    app.setWindowIcon(QIcon(str(ROOT/'assets/logo.ico')))
    apply_theme(app)
    for argument in sys.argv[1:]:
        if argument.startswith('--self-test='):
            from services.package_check import run
            return run(Path(argument.split('=',1)[1]),app)
    socket=QLocalSocket(); socket.connectToServer('chuge_tools_v1')
    if socket.waitForConnected(500): socket.close(); return 0
    server=QLocalServer()
    if not server.listen('chuge_tools_v1'):
        QMessageBox.warning(None,'启动失败','无法取得单实例锁，请检查是否已有程序正在启动。'); return 1
    window=MainWindow(); window.server=server; server.newConnection.connect(window.activate)
    def error_hook(typ,value,tb):
        LOG_ROOT.mkdir(parents=True,exist_ok=True)
        with (LOG_ROOT/'错误日志.txt').open('a',encoding='utf-8') as file: traceback.print_exception(typ,value,tb,file=file)
        QMessageBox.critical(window,'程序错误',f'操作未完成：{value}\n详细信息已记录在用户日志目录。')
    sys.excepthook=error_hook
    window.show(); return app.exec()

if __name__=='__main__': sys.exit(main())
