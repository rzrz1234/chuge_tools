"""水印生成页：原生控件、后台预览和无损水印验证。"""
from pathlib import Path
from PySide6.QtCore import Qt,QTimer,QSize
from PySide6.QtGui import QPixmap,QColor,QIcon
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,QLineEdit,QPlainTextEdit,QCheckBox,QScrollArea,QSplitter,QFileDialog,QColorDialog,QMessageBox
from ui.pages import Page,Job,button,spin,combo,IMAGE_FILTER
from services import watermark_engine as engine

class WatermarkPage(Page):
    def __init__(self):
        super().__init__('水印生成','单个 / 平铺文字水印、密集浅水印和隐形像素水印，全程本地处理，导出保持原图分辨率。')
        self.setAcceptDrops(True);self.pending_preview=False;self.preview_image=None
        form=QFormLayout();self.body.addLayout(form)
        file_widget=QWidget();row=QHBoxLayout(file_widget);row.setContentsMargins(0,0,0,0)
        self.source=QLineEdit();self.source.setPlaceholderText('选择或拖入 PNG / JPG / WEBP 图片');row.addWidget(self.source,1);row.addWidget(button('选择图片',self.choose_image));form.addRow('输入图片',file_widget)
        self.output=self.file_row(form,'保存位置',True);self.output.setText(str(Path.home() / 'Pictures'))
        splitter=QSplitter(Qt.Orientation.Horizontal);self.body.addWidget(splitter,1)
        scroll=QScrollArea();scroll.setWidgetResizable(True);settings_widget=QWidget();settings_layout=QVBoxLayout(settings_widget);settings_layout.setContentsMargins(0,0,12,0);settings_layout.setSpacing(10);scroll.setWidget(settings_widget);splitter.addWidget(scroll)
        self.text=QPlainTextEdit();self.text.setMaximumHeight(70);settings_layout.addWidget(QLabel('可见水印文字'));settings_layout.addWidget(self.text)
        presets=QHBoxLayout()
        for label,text in [('抖音','Rinull_xiaomai'),('小红书','Rinull'),('版权','© Rinull')]:presets.addWidget(button(label,lambda checked=False,t=text:self.preset(t)))
        settings_layout.addLayout(presets)
        fields=QFormLayout();fields.setSpacing(8);settings_layout.addLayout(fields)
        self.mode=combo(['单个','平铺']);self.position=combo(['左上','上中','右上','左中','居中','右中','左下','下中','右下']);fields.addRow('铺放方式',self.mode);fields.addRow('水印位置',self.position)
        self.fill=button('文字颜色',lambda:self.pick_color(self.fill));self.stroke_color=button('描边颜色',lambda:self.pick_color(self.stroke_color));colors=QHBoxLayout();colors.addWidget(self.fill);colors.addWidget(self.stroke_color);settings_layout.addLayout(colors)
        fields2=QFormLayout();fields2.setSpacing(8);settings_layout.addLayout(fields2)
        self.size=spin(6,2,18);self.opacity=spin(38,5,100);self.angle=spin(-18,-45,45);self.margin=spin(4,1,15);self.spacing=spin(18,8,40)
        for label,w in [('大小（%）',self.size),('不透明度（%）',self.opacity),('角度（°）',self.angle),('边距（%）',self.margin),('平铺间距（%）',self.spacing)]:fields2.addRow(label,w)
        self.weight=combo(['常规','加粗','特粗']);self.stroke=combo(['无描边','轻描边','中描边','重描边']);fields2.addRow('字体粗细',self.weight);fields2.addRow('描边强度',self.stroke)
        self.shadow=QCheckBox('显示投影');self.protect=QCheckBox('强保护：叠加密集浅水印');self.hidden=QCheckBox('写入隐形像素水印（自动保存 PNG）')
        for w in [self.shadow,self.protect,self.hidden]:settings_layout.addWidget(w)
        self.hidden_text=QPlainTextEdit();self.hidden_text.setMaximumHeight(65);settings_layout.addWidget(QLabel('隐形水印内容'));settings_layout.addWidget(self.hidden_text)
        self.key=QLineEdit();self.key.setEchoMode(QLineEdit.EchoMode.Password);self.key.setPlaceholderText('导出与验证使用相同密钥');settings_layout.addWidget(QLabel('隐形水印密钥'));settings_layout.addWidget(self.key)
        self.format=combo(['PNG','JPG','WEBP']);format_form=QFormLayout();format_form.addRow('导出格式',self.format);settings_layout.addLayout(format_form)
        note=QLabel('隐形水印兼容原工具的 RWM2 格式。压缩、缩放或截图可能破坏水印；此格式采用简单混淆，并非强加密。');note.setWordWrap(True);note.setObjectName('description');settings_layout.addWidget(note);settings_layout.addStretch()
        preview_widget=QWidget();preview_layout=QVBoxLayout(preview_widget);preview_layout.setContentsMargins(12,0,0,0)
        self.meta=QLabel('预览 · 尚未选择图片');self.meta.setWordWrap(True);preview_layout.addWidget(self.meta)
        self.preview=QLabel('选择或拖入图片\n\n调整设置后自动更新预览');self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter);self.preview.setMinimumSize(280,220);self.preview.setStyleSheet('background:#F1F2F8;border:1px dashed #D5D1E7;border-radius:9px;color:#81779C;');preview_layout.addWidget(self.preview,1)
        self.hint=QLabel('预览显示可见水印；隐形水印在保存时写入。验证读取的是导入图片中的水印。');self.hint.setWordWrap(True);self.hint.setObjectName('description');preview_layout.addWidget(self.hint);splitter.addWidget(preview_widget);splitter.setSizes([360,650])
        actions=QHBoxLayout();self.save_button=button('开始保存图片',self.save);self.verify_button=button('验证导入图片的水印',self.verify);actions.addWidget(self.save_button);actions.addWidget(self.verify_button);actions.addWidget(button('重置设置',self.reset));self.body.addLayout(actions)
        self.reset()
        for w in [self.source,self.key]:w.textChanged.connect(self.schedule_preview)
        self.text.textChanged.connect(self.schedule_preview);self.hidden_text.textChanged.connect(self.schedule_preview)
        for w in [self.mode,self.position,self.weight,self.stroke,self.format]:w.currentIndexChanged.connect(self.schedule_preview)
        for w in [self.size,self.opacity,self.angle,self.margin,self.spacing]:w.valueChanged.connect(self.schedule_preview)
        for w in [self.shadow,self.protect,self.hidden]:w.toggled.connect(self.schedule_preview)
        self.timer=QTimer(self);self.timer.setInterval(250);self.timer.timeout.connect(self.poll_preview);self.timer.start()
    def preset(self,text):
        self.text.setPlainText(text)
        if not self.hidden_text.toPlainText().strip():self.hidden_text.setPlainText(text+' 版权所有')
    def color(self,target,value):
        target.setProperty('color',value);target.setText(value.upper());pix=QPixmap(14,14);pix.fill(QColor(value));target.setIcon(QIcon(pix));target.setIconSize(QSize(14,14))
    def pick_color(self,target):
        value=QColorDialog.getColor(QColor(target.property('color')),self,'选择水印颜色')
        if value.isValid():self.color(target,value.name());self.schedule_preview()
    def reset(self):
        d=engine.DEFAULTS;self.text.setPlainText(d['text']);self.hidden_text.setPlainText(d['hidden_text']);self.key.setText(d['key']);self.mode.setCurrentIndex(0);self.position.setCurrentIndex(8)
        for name in ['size','opacity','angle','margin','spacing']:getattr(self,name).setValue(d[name])
        for name in ['shadow','protect','hidden']:getattr(self,name).setChecked(d[name])
        self.weight.setCurrentIndex(1);self.stroke.setCurrentIndex(1);self.format.setCurrentIndex(0);self.color(self.fill,d['fill']);self.color(self.stroke_color,d['stroke_color']);self.schedule_preview()
    def settings(self):
        d={name:getattr(self,name).value() for name in ['size','opacity','angle','margin','spacing']}
        d.update({name:getattr(self,name).isChecked() for name in ['shadow','protect','hidden']})
        d.update(text=self.text.toPlainText(),hidden_text=self.hidden_text.toPlainText(),key=self.key.text(),mode=self.mode.currentText(),position=self.position.currentIndex(),weight=[500,700,900][self.weight.currentIndex()],stroke=[0,.04,.08,.12][self.stroke.currentIndex()],fill=self.fill.property('color'),stroke_color=self.stroke_color.property('color'),format=self.format.currentText())
        return d
    def choose_image(self):
        path=QFileDialog.getOpenFileName(self,'选择水印图片','',IMAGE_FILTER)[0]
        if path:self.source.setText(path)
    def schedule_preview(self,*args):
        self.pending_preview=True;self.position.setEnabled(self.mode.currentIndex()==0);self.spacing.setEnabled(self.mode.currentIndex()==1);self.format.setEnabled(not self.hidden.isChecked())
    def poll_preview(self):
        if not self.pending_preview or (self.job and self.job.isRunning()) or (hasattr(self,'preview_job') and self.preview_job.isRunning()):return
        self.pending_preview=False
        if not self.source.text().strip():self.preview.clear();self.preview.setText('选择或拖入图片开始');self.preview_image=None;return
        self.preview_job=Job(engine.render,(self.source.text(),self.settings(),True),self);self.preview_job.result.connect(self.show_preview);self.preview_job.failure.connect(self.preview_error);self.preview_job.start()
    def show_preview(self,image):
        if self.pending_preview:return
        self.preview_image=image;self.update_preview();self.meta.setText(f'{Path(self.source.text()).name} · 缩略预览，保存使用原始分辨率')
    def update_preview(self):
        if self.preview_image is not None:self.preview.setPixmap(QPixmap.fromImage(self.preview_image).scaled(self.preview.size()-QSize(16,16),Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
    def preview_error(self,error):
        if not self.pending_preview:self.preview.setText(error);self.preview_image=None
    def resizeEvent(self,event):super().resizeEvent(event);self.update_preview()
    def save(self):self.start(engine.export,(self.source.text(),self.output.text(),self.settings()))
    def verify(self):self.start(engine.verify,(self.source.text(),self.key.text()),self.verified)
    def verified(self,text):self.status.setText('验证成功');self.log.show();self.log.appendPlainText('提取到隐形水印：\n'+text);QMessageBox.information(self,'水印验证成功',text)
    def dragEnterEvent(self,event):
        if event.mimeData().hasUrls():event.acceptProposedAction()
    def dropEvent(self,event):
        files=[u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        if files:self.source.setText(files[0]);event.acceptProposedAction()
