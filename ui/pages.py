from pathlib import Path
import os
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSettings, QSize
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,QPushButton,QLineEdit,QSpinBox,QDoubleSpinBox,QComboBox,QCheckBox,QProgressBar,QPlainTextEdit,QFileDialog,QMessageBox,QScrollArea,QGridLayout,QListWidget,QSplitter)
from services import operations as op

VIDEO_FILTER='视频文件 (*.mp4 *.mov *.mkv *.avi *.flv *.wmv *.m4v *.webm);;所有文件 (*)'
IMAGE_FILTER='图片 (*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff);;所有文件 (*)'

def button(text, callback):
    b=QPushButton(text); b.clicked.connect(callback)
    if text.startswith(('开始','① 分析','② 导出','导出 PNG')): b.setProperty('role','primary')
    if text in ('取消任务','清空','清空全部','移除'): b.setProperty('role','quiet')
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b

def spin(value, minimum=1, maximum=10000, decimals=None):
    s=QSpinBox() if decimals is None else QDoubleSpinBox()
    s.setRange(minimum,maximum)
    if decimals is not None: s.setDecimals(decimals)
    s.setValue(value); return s

def combo(items):
    c=QComboBox(); c.addItems(items); return c

class Job(QThread):
    message=Signal(str); progress=Signal(int); result=Signal(object); failure=Signal(str)
    def __init__(self,fn,args,parent):
        super().__init__(parent); self.fn,self.args=fn,args
        self.ctx=op.Context(self.message.emit,self.progress.emit)
    def run(self):
        try:
            result=self.fn(self.ctx,*self.args)
            self.progress.emit(100); self.result.emit(result)
        except Exception as e: self.failure.emit(str(e))

class Page(QWidget):
    def __init__(self,title,description):
        super().__init__(); self.job=None; self.last_output=None
        self.layout=QVBoxLayout(self); self.layout.setContentsMargins(28,18,28,18); self.layout.setSpacing(10)
        heading=QLabel(title); heading.setObjectName('heading'); self.layout.addWidget(heading)
        tip=QLabel(description); tip.setWordWrap(True); tip.setObjectName('description'); self.layout.addWidget(tip)
        self.controls=QWidget(); self.controls.setObjectName('controlCard'); self.controls.setAttribute(Qt.WidgetAttribute.WA_StyledBackground,True)
        self.body=QVBoxLayout(self.controls); self.body.setContentsMargins(20,18,20,18); self.body.setSpacing(12)
        self.control_scroll=QScrollArea(); self.control_scroll.setWidgetResizable(True); self.control_scroll.setWidget(self.controls)
        self.layout.addWidget(self.control_scroll,1)
        self.bar=QProgressBar(); self.bar.setRange(0,100); self.bar.setValue(0); self.bar.setTextVisible(False)
        self.status=QLabel('就绪 · 选择素材后即可开始'); self.status.setObjectName('taskStatus')
        self.log=QPlainTextEdit(); self.log.setReadOnly(True); self.log.setMaximumHeight(90); self.log.setMaximumBlockCount(300); self.log.setObjectName('taskLog'); self.log.setPlaceholderText('任务的处理进度和详细信息会显示在这里'); self.log.hide()
        self.layout.addWidget(self.bar); self.layout.addWidget(self.status); self.layout.addWidget(self.log)
        row=QHBoxLayout(); self.cancel_button=button('取消任务',self.cancel); self.cancel_button.setEnabled(False)
        row.addWidget(self.cancel_button); row.addWidget(button('运行日志',lambda: self.log.setVisible(not self.log.isVisible()))); row.addStretch(); row.addWidget(button('打开输出文件夹',self.open_output)); self.layout.addLayout(row)
    def start(self,fn,args,callback=None):
        if self.job and self.job.isRunning(): return
        self.controls.setEnabled(False); self.cancel_button.setEnabled(True); self.bar.setValue(0)
        self.status.setText('正在处理…'); self.log.clear()
        self.job=Job(fn,args,self); self.job.message.connect(self.log.appendPlainText); self.job.progress.connect(self.bar.setValue)
        self.job.result.connect(callback or self.completed); self.job.failure.connect(self.failed); self.job.finished.connect(self.idle); self.job.start()
    def idle(self):
        self.controls.setEnabled(True); self.cancel_button.setEnabled(False)
    def cancel(self):
        if self.job: self.job.ctx.cancel.set(); self.status.setText('正在取消，请稍候…')
    def completed(self,result):
        self.status.setText('处理完成'); self.log.appendPlainText(str(result))
        if isinstance(result,Path): self.last_output=result
    def failed(self,error):
        self.status.setText('任务已取消' if self.job.ctx.cancel.is_set() else '处理失败')
        self.log.appendPlainText(error); self.log.show()
        if not self.job.ctx.cancel.is_set(): QMessageBox.warning(self,'处理失败',error)
    def open_output(self):
        if self.last_output:
            p=self.last_output
            os.startfile(str(p if p.is_dir() else p.parent))
        else: QMessageBox.information(self,'提示','还没有生成输出文件。')
    def file_row(self,form,label,directory=False):
        widget=QWidget(); row=QHBoxLayout(widget); row.setContentsMargins(0,0,0,0); edit=QLineEdit()
        edit.setPlaceholderText('请选择文件夹' if directory else '选择视频，也可以粘贴完整路径')
        def choose():
            value=QFileDialog.getExistingDirectory(self,'选择输出文件夹',edit.text()) if directory else QFileDialog.getOpenFileName(self,'选择视频',edit.text(),VIDEO_FILTER)[0]
            if value: edit.setText(value)
        row.addWidget(edit,1); row.addWidget(button('浏览…',choose)); form.addRow(label,widget); return edit
    def video_form(self):
        form=QFormLayout(); form.setSpacing(9); self.body.addLayout(form)
        self.source=self.file_row(form,'输入视频'); self.output=self.file_row(form,'保存位置',True)
        self.source.textChanged.connect(lambda value: self.output.setText(str(Path(value).parent)) if value and not self.output.text() else None)
        return form

class GifPage(Page):
    def __init__(self):
        super().__init__('视频转 GIF','两遍调色板转换，可设置起点、时长、帧率、宽度和循环次数。输出自动新建目录。')
        f=self.video_form(); self.fps=spin(12,1,60); self.width=spin(640,16,3840); self.start_time=spin(0,0,864000,3); self.duration=spin(0,0,864000,3); self.loop=spin(0,0,65535); self.ffmpeg=QLineEdit('ffmpeg')
        for title,w in [('帧率',self.fps),('输出宽度',self.width),('开始时间（秒）',self.start_time),('时长（秒，0 为直到结尾）',self.duration),('循环次数（0 为无限循环）',self.loop),('FFmpeg 程序',self.ffmpeg)]: f.addRow(title,w)
        self.run_button=button('开始转换',self.run); self.body.addWidget(self.run_button); self.body.addStretch()
    def run(self):
        self.start(op.convert,(self.source.text(),self.output.text(),self.fps.value(),self.width.value(),self.start_time.value(),self.duration.value() or None,self.loop.value(),self.ffmpeg.text()))

class FramePage(Page):
    def __init__(self):
        super().__init__('视频截帧 / 镜头表','按时间间隔导出 JPG，自动生成 3840 × 2160 分页镜头表，自动适配横竖屏。')
        f=self.video_form(); self.interval=spin(.5,.01,36000,3); self.size=combo(list(op.frames.RESOLUTION_PRESETS)); self.size.setCurrentIndex(3)
        f.addRow('截帧间隔（秒）',self.interval); f.addRow('单张图片尺寸',self.size)
        self.run_button=button('开始截帧并生成镜头表',self.run); self.body.addWidget(self.run_button); self.body.addStretch()
    def run(self): self.start(op.extract,(self.source.text(),self.output.text(),self.interval.value(),op.frames.RESOLUTION_PRESETS[self.size.currentText()]))

class Timeline(QWidget):
    seek=Signal(float)
    def __init__(self):
        super().__init__(); self.duration=0.; self.cuts=[]; self.position=0.; self.setMinimumHeight(70)
    def paintEvent(self,event):
        p=QPainter(self); p.fillRect(self.rect(),QColor('#F3F1FC')); width=max(1,self.width()-24)
        if not self.duration: p.drawText(self.rect(),Qt.AlignmentFlag.AlignCenter,'分析后在这里查看切点'); return
        p.setPen(QPen(QColor('#CFCAE4'),2)); p.drawLine(12,35,self.width()-12,35)
        for t in self.cuts:
            x=12+round(t/self.duration*width); p.setPen(QPen(QColor('#9080D8'),2)); p.drawLine(x,10,x,54)
        x=12+round(self.position/self.duration*width); p.setPen(QPen(QColor('#7160D8'),3)); p.drawLine(x,3,x,62)
    def mousePressEvent(self,e):
        if self.duration: self.seek.emit(min(self.duration,max(0,(e.position().x()-12)/max(1,self.width()-24)*self.duration)))

class ShotPage(Page):
    def __init__(self):
        super().__init__('视频切镜拆段','自动检测 → 前后帧审核 → 手动调整切点 → 导出 MP4 或 MP3。灵敏度数值越大，检测越敏感。')
        f=self.video_form(); self.sensitivity=spin(.30,.05,.90,2); self.minimum=spin(.4,.05,60,2)
        f.addRow('切镜灵敏度',self.sensitivity); f.addRow('最短片段（秒）',self.minimum)
        self.body.addWidget(button('① 分析切镜点',self.analyze)); self.timeline=Timeline(); self.body.addWidget(self.timeline); self.timeline.seek.connect(self.seek)
        row=QHBoxLayout(); self.position=spin(0,0,864000,3); row.addWidget(QLabel('定位（秒）')); row.addWidget(self.position)
        row.addWidget(button('查看前后帧',lambda:self.seek(self.position.value()))); row.addWidget(button('添加切点',self.add_cut)); row.addWidget(button('删除选中切点',self.remove_cut)); row.addWidget(button('恢复自动结果',self.restore)); self.body.addLayout(row)
        self.cuts_list=QListWidget(); self.cuts_list.setMaximumHeight(100); self.cuts_list.currentRowChanged.connect(self.select_cut); self.body.addWidget(self.cuts_list)
        preview_row=QHBoxLayout(); self.previews=[]
        for title in ['切点前一帧','切点后一帧']:
            label=QLabel(title); label.setAlignment(Qt.AlignmentFlag.AlignCenter); label.setMinimumHeight(130); label.setStyleSheet('background:#F0F1F8;border:1px solid #E5E5F0;border-radius:8px;color:#9295AB;'); preview_row.addWidget(label); self.previews.append(label)
        self.body.addLayout(preview_row)
        row=QHBoxLayout(); row.addWidget(button('② 导出视频片段',lambda:self.export(False))); row.addWidget(button('③ 导出 MP3 片段',lambda:self.export(True))); self.body.addLayout(row)
        self.cuts=[]; self.original=[]; self.duration=0.; self.analyzed_source=None; self.pending_preview=None
        self.preview_timer=QTimer(self); self.preview_timer.setInterval(100); self.preview_timer.timeout.connect(self.poll_preview); self.preview_timer.start()
    def analyze(self): self.start(op.analyze,(self.source.text(),self.sensitivity.value(),self.minimum.value()),self.analyzed)
    def analyzed(self,result):
        self.analyzed_source,self.duration,self.cuts=result; self.original=self.cuts.copy(); self.refresh(); self.status.setText(f'分析完成：{len(self.cuts)} 个切点'); self.seek(self.cuts[0] if self.cuts else 0)
    def refresh(self):
        self.cuts_list.blockSignals(True); self.cuts_list.clear(); self.cuts_list.addItems([f'{i+1:03d}    {op.shots.format_seconds(t)}' for i,t in enumerate(self.cuts)]); self.cuts_list.blockSignals(False)
        self.timeline.duration=self.duration; self.timeline.cuts=self.cuts.copy(); self.timeline.update()
    def select_cut(self,index):
        if 0<=index<len(self.cuts): self.seek(self.cuts[index])
    def seek(self,t):
        if not self.duration: return
        self.position.setValue(t); self.timeline.position=t; self.timeline.update(); self.pending_preview=t
    def poll_preview(self):
        if self.pending_preview is None or (hasattr(self,'preview_job') and self.preview_job.isRunning()): return
        t=self.pending_preview; self.pending_preview=None
        self.preview_job=Job(op.preview,(self.analyzed_source,t),self); self.preview_job.result.connect(self.show_previews); self.preview_job.failure.connect(self.log.appendPlainText); self.preview_job.start()
    def show_previews(self,images):
        for label,image in zip(self.previews,images):
            if image is None: label.setText('该位置无可用画面')
            else: label.setPixmap(QPixmap.fromImage(image).scaled(360,170,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
    def add_cut(self):
        t=self.position.value()
        if 0<t<self.duration and all(abs(t-x)>.04 for x in self.cuts): self.cuts=sorted(self.cuts+[t]); self.refresh()
    def remove_cut(self):
        i=self.cuts_list.currentRow()
        if 0<=i<len(self.cuts): self.cuts.pop(i); self.refresh()
    def restore(self): self.cuts=self.original.copy(); self.refresh()
    def export(self,audio):
        if not self.duration or self.source.text()!=self.analyzed_source:
            QMessageBox.warning(self,'请先分析','请先分析当前视频的切镜点。'); return
        self.start(op.export_shots,(self.analyzed_source,self.output.text(),self.duration,self.cuts.copy(),self.minimum.value(),audio))

class ImageCell(QWidget):
    def __init__(self,page,index):
        super().__init__(); self.page=page; self.index=index; self.path=''; self.setAcceptDrops(True)
        layout=QVBoxLayout(self); layout.setContentsMargins(3,3,3,3)
        self.image=button(f'{index+1:02d}  选择 / 拖入图片',self.choose); self.image.setMinimumHeight(105); self.image.setStyleSheet('background:#F7F7FC;border:1px dashed #CDC8E3;color:#8A80AC;min-height:96px;'); layout.addWidget(self.image)
        self.title=QLineEdit(); self.title.setPlaceholderText('图片标题'); layout.addWidget(self.title)
        layout.addWidget(button('移除',self.remove))
    def choose(self):
        files=QFileDialog.getOpenFileNames(self,'选择图片','',IMAGE_FILTER)[0]
        self.page.place(self.index,files)
    def set_path(self,path):
        from PySide6.QtGui import QIcon
        pix=QPixmap(path)
        if pix.isNull(): raise ValueError(f'图片无法读取：{path}')
        self.path=path; self.image.setIcon(QIcon(pix)); self.image.setIconSize(QSize(260,96)); self.image.setText('')
    def remove(self):
        from PySide6.QtGui import QIcon
        self.path=''; self.image.setIcon(QIcon()); self.image.setText(f'{self.index+1:02d}  选择 / 拖入图片')
    def dragEnterEvent(self,e):
        if e.mimeData().hasUrls(): e.acceptProposedAction()
    def dropEvent(self,e): self.page.place(self.index,[u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()])

class GridPage(Page):
    def __init__(self):
        super().__init__('图片拼图','批量导入或拖放图片，逐格编辑标题，按网格导出 PNG。支持居中裁切与完整显示。')
        row=QHBoxLayout(); self.preset=combo(['3 × 3','3 × 4','2 × 4','2 × 3','4 × 4','自定义']); self.rows=spin(3,1,8); self.cols=spin(3,1,8); self.ratio=combo(['1:1','4:3','16:9','3:4']); self.gap=spin(2,0,100); self.font_size=spin(34,10,100); self.contain=QCheckBox('完整显示')
        for label,w in [('预设',self.preset),('行',self.rows),('列',self.cols),('比例',self.ratio),('间距',self.gap),('字号',self.font_size)]: row.addWidget(QLabel(label)); row.addWidget(w)
        row.addWidget(self.contain); self.body.addLayout(row)
        self.scroll=QScrollArea(); self.scroll.setWidgetResizable(True); self.container=QWidget(); self.grid=QGridLayout(self.container); self.scroll.setWidget(self.container); self.body.addWidget(self.scroll,1)
        self.cells=[]; self.refresh(); self.rows.valueChanged.connect(self.refresh); self.cols.valueChanged.connect(self.refresh); self.preset.currentIndexChanged.connect(self.apply_preset)
        row=QHBoxLayout(); row.addWidget(button('批量添加图片',self.add_images)); row.addWidget(button('清空全部',self.clear)); row.addWidget(button('导出 PNG',self.export)); self.body.addLayout(row)
    def apply_preset(self,i):
        if i<5:
            r,c=[(3,3),(3,4),(2,4),(2,3),(4,4)][i]; self.rows.setValue(r); self.cols.setValue(c)
    def refresh(self):
        count=self.rows.value()*self.cols.value()
        while len(self.cells)<count: self.cells.append(ImageCell(self,len(self.cells)))
        while self.grid.count(): self.grid.takeAt(0)
        for i,c in enumerate(self.cells):
            c.setVisible(i<count)
            if i<count: self.grid.addWidget(c,i//self.cols.value(),i%self.cols.value())
    def place(self,index,files):
        try:
            for i,path in enumerate(files):
                if index+i>=self.rows.value()*self.cols.value(): break
                self.cells[index+i].set_path(path)
        except Exception as e: QMessageBox.warning(self,'图片导入失败',str(e))
    def add_images(self):
        files=QFileDialog.getOpenFileNames(self,'批量选择图片','',IMAGE_FILTER)[0]
        start=next((i for i,c in enumerate(self.cells[:self.rows.value()*self.cols.value()]) if not c.path),0); self.place(start,files)
    def clear(self):
        for c in self.cells: c.remove(); c.title.clear()
    def export(self):
        cells=[(c.path,c.title.text()) for c in self.cells[:self.rows.value()*self.cols.value()]]
        if not any(p for p,t in cells): QMessageBox.warning(self,'提示','请先添加图片。'); return
        path=QFileDialog.getSaveFileName(self,'保存拼图','拼图.png','PNG 图片 (*.png)')[0]
        if path:
            if not path.lower().endswith('.png'): path+='.png'
            a,b=map(int,self.ratio.currentText().split(':'))
            self.start(op.grid_export,(cells,self.rows.value(),self.cols.value(),a/b,self.gap.value(),self.font_size.value(),self.contain.isChecked(),path))

class TextPage(Page):
    def __init__(self):
        super().__init__('文字换行','支持中英文与混合文本、段落保留、长单词拆分，以及英文翻译为中文。')
        row=QHBoxLayout(); self.width=spin(80,2,2000); self.language=combo(['自动识别','中文','英文','混合']); self.paragraphs=QCheckBox('保留段落'); self.paragraphs.setChecked(True); self.words=QCheckBox('拆分长单词'); self.words.setChecked(True)
        for w in [QLabel('每行宽度'),self.width,self.language,self.paragraphs,self.words]: row.addWidget(w)
        self.body.addLayout(row); split=QSplitter(Qt.Orientation.Vertical); self.input=QPlainTextEdit(); self.input.setPlaceholderText('在这里粘贴输入文本…'); self.output_text=QPlainTextEdit(); self.output_text.setPlaceholderText('处理结果…'); split.addWidget(self.input); split.addWidget(self.output_text); self.body.addWidget(split,1)
        row=QHBoxLayout(); row.addWidget(button('开始换行',self.wrap)); row.addWidget(button('英文翻译为中文',self.translate)); row.addWidget(button('复制结果',lambda: self.output_text.selectAll() or self.output_text.copy())); row.addWidget(button('清空',self.clear)); self.body.addLayout(row)
        self.body.addWidget(QLabel('翻译会将输入文本发送到原工具使用的第三方在线翻译服务，需要网络连接。'))
    def wrap(self): self.start(op.wrap,(self.input.toPlainText(),self.width.value(),self.language.currentText(),self.paragraphs.isChecked(),self.words.isChecked()),self.show_text)
    def translate(self): self.start(op.translate,(self.input.toPlainText(),),self.show_text)
    def show_text(self,result): self.output_text.setPlainText(result); self.status.setText(f'处理完成：{len(result)} 字符，{len(result.splitlines())} 行')
    def clear(self): self.input.clear(); self.output_text.clear()
