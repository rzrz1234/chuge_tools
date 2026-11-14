"""音视频合并原生标签页。"""
from pathlib import Path
from PySide6.QtWidgets import QWidget,QHBoxLayout,QFormLayout,QLineEdit,QCheckBox,QLabel,QFileDialog
from ui.pages import Page,button,spin,combo
from services import merge_engine as engine

AUDIO_FILTER='音频或视频 (*.mp3 *.wav *.flac *.aac *.m4a *.ogg *.opus *.wma *.aiff *.mp4 *.mov *.mkv *.avi *.webm *.m4v *.wmv *.flv);;所有文件 (*)'

class MergePage(Page):
    def __init__(self):
        super().__init__('音视频合并','从音频或视频取音轨，自动循环补齐或截断；支持替换原声、混音及保留原视频画面和帧率。')
        form=QFormLayout();form.setSpacing(12);self.body.addLayout(form)
        self.source=self.file_row(form,'输入视频');self.audio=QLineEdit();self.audio.setPlaceholderText('选择音频文件，或另一个含声音的视频')
        row_widget=QWidget();row=QHBoxLayout(row_widget);row.setContentsMargins(0,0,0,0);row.addWidget(self.audio,1);row.addWidget(button('选择音频源',self.choose_audio));form.addRow('音频来源',row_widget)
        self.output=QLineEdit();self.output.setPlaceholderText('选择输出 MP4 路径，同名文件自动编号')
        row_widget=QWidget();row=QHBoxLayout(row_widget);row.setContentsMargins(0,0,0,0);row.addWidget(self.output,1);row.addWidget(button('保存为…',self.choose_output));form.addRow('输出文件',row_widget)
        self.replace=QCheckBox('替换原视频音轨（取消勾选则混合原声与新音频）');self.replace.setChecked(True);form.addRow('声音处理',self.replace)
        self.mode=combo(['保持原画面和原帧率（推荐）','固定帧率，重新编码 H.264']);form.addRow('视频处理',self.mode)
        self.rate=spin(30,1,240);self.rate.setEnabled(False);form.addRow('固定帧率（fps）',self.rate);self.mode.currentIndexChanged.connect(lambda i:self.rate.setEnabled(i==1))
        self.maximum=spin(15,0,864000,3);form.addRow('最长输出（秒）',self.maximum)
        note=QLabel('时长为 0 时输出完整视频；默认 15 秒，沿用旧工具行为。音频较短会循环，较长会截断。\n混音沿用原工具的原声 0.3 / 新音频 0.7 权重。保留原画面模式若遇封装不兼容，可选 H.264 重编码。');note.setWordWrap(True);note.setObjectName('description');self.body.addWidget(note)
        self.info=QLabel('选择视频与音频源后，可读取时长和音轨信息。');self.info.setWordWrap(True);self.info.setStyleSheet('background:#F2F0FB;border-radius:8px;padding:16px;color:#6B628A;');self.body.addWidget(self.info)
        actions=QHBoxLayout();actions.addWidget(button('读取媒体信息',self.inspect));self.run_button=button('开始合并',self.run);actions.addWidget(self.run_button);actions.addWidget(button('重置',self.reset));self.body.addLayout(actions);self.body.addStretch()
        self.source.textChanged.connect(self.default_output)
    def default_output(self,value):
        if value and not self.output.text():self.output.setText(str(Path(value).with_name(Path(value).stem+'_merged.mp4')))
    def choose_audio(self):
        value=QFileDialog.getOpenFileName(self,'选择音频源，可使用含声音的视频',self.audio.text(),AUDIO_FILTER)[0]
        if value:self.audio.setText(value)
    def choose_output(self):
        value=QFileDialog.getSaveFileName(self,'保存合并结果',self.output.text() or '合并结果.mp4','MP4 视频 (*.mp4)')[0]
        if value:self.output.setText(value if value.lower().endswith('.mp4') else value+'.mp4')
    def inspect(self):self.start(engine.inspect,(self.source.text(),self.audio.text()),self.inspected)
    def inspected(self,result):self.info.setText(result);self.status.setText('媒体信息读取完成')
    def run(self):self.start(engine.merge,(self.source.text(),self.audio.text(),self.output.text(),self.replace.isChecked(),self.mode.currentIndex()==1,self.rate.value(),self.maximum.value()))
    def reset(self):self.source.clear();self.audio.clear();self.output.clear();self.mode.setCurrentIndex(0);self.rate.setValue(30);self.maximum.setValue(15);self.replace.setChecked(True);self.info.setText('选择视频与音频源后，可读取时长和音轨信息。')
