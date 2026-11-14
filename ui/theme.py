"""浅色界面主题，集中维护颜色、尺寸和控件状态。"""
from PySide6.QtGui import QColor, QPalette

STYLE = '''
QWidget { font-family: "Microsoft YaHei UI"; font-size: 13px; color: #30374B; }
QMainWindow, QWidget#workspace { background: #F4F5FA; }
QWidget#appHeader { background: #FFFFFF; border-bottom: 1px solid #E6E8F1; }
QLabel#brand { font-size: 21px; font-weight: 700; color: #262C44; }
QLabel#brandCaption { color: #727A90; font-size: 12px; }
QLabel#brandMark { background: transparent; border: none; padding: 0; }
QLabel#workspaceBadge { color: #6559BC; background: #F0EDFC; border-radius: 12px; padding: 5px 13px; font-size: 12px; }
QTabWidget::pane { border: 0; background: #F4F5FA; }
QTabWidget::tab-bar { left: 24px; }
QTabBar { background: transparent; }
QTabBar::tab { color: #7C8399; background: transparent; padding: 15px 25px 12px; margin-right: 6px; border-bottom: 3px solid transparent; font-weight: 500; }
QTabBar::tab:hover { color: #6354CD; background: #EEECFA; }
QTabBar::tab:selected { color: #6354CD; border-bottom: 3px solid #7565DF; font-weight: 700; }
QLabel#heading { font-size: 23px; font-weight: 700; color: #2B3048; }
QLabel#description { color: #69728A; font-size: 12px; padding-bottom: 4px; }
QWidget#controlCard { background: #FFFFFF; border: 1px solid #E5E7F0; border-radius: 12px; }

QWidget#controlCard QLineEdit, QWidget#controlCard QSpinBox, QWidget#controlCard QDoubleSpinBox,
QWidget#controlCard QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background: #F8F9FC; border: 1px solid #E0E3EE; border-radius: 6px; padding: 7px 10px;
    min-height: 20px; selection-background-color: #DAD3FA; selection-color: #3E337F;
}
QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover { border-color: #B8B0DF; }
QWidget#controlCard QLineEdit:focus, QWidget#controlCard QSpinBox:focus,
QWidget#controlCard QDoubleSpinBox:focus, QWidget#controlCard QComboBox:focus,
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus { background: #FFFFFF; border: 1px solid #8E80DD; }
QWidget#controlCard QPlainTextEdit, QWidget#controlCard QListWidget, QPlainTextEdit, QListWidget {
    background: #FAFBFE; border: 1px solid #E2E5F0; border-radius: 8px; padding: 9px;
    selection-background-color: #E6E0FC; selection-color: #5141A2;
}
QWidget#controlCard QPushButton, QPushButton { background: #FFFFFF; border: 1px solid #DEDFF0; border-radius: 7px; padding: 8px 14px; min-height: 20px; color: #575F78; }
QWidget#controlCard QPushButton:hover, QPushButton:hover { background: #F4F1FF; color: #6552BF; border-color: #BFB5E8; }
QWidget#controlCard QPushButton:pressed, QPushButton:pressed { background: #E9E3FC; }
QWidget#controlCard QPushButton[role="primary"], QPushButton[role="primary"] { background: #7160D8; color: white; border: 1px solid #7160D8; font-weight: 600; }
QWidget#controlCard QPushButton[role="primary"]:hover, QPushButton[role="primary"]:hover { background: #6250C8; border-color: #6250C8; }
QWidget#controlCard QPushButton[role="primary"]:pressed { background: #5440B5; }
QWidget#controlCard QPushButton:disabled, QPushButton:disabled { background: #F0F1F6; border-color: #E5E7EF; color: #A6ABBA; }
QPushButton[role="quiet"] { background: transparent; border-color: transparent; color: #8A90A2; }
QPushButton[role="quiet"]:hover { background: #EBE9F6; color: #6552BF; }
QCheckBox { spacing: 7px; color: #747C91; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #CCD0E0; border-radius: 4px; background: #FFFFFF; }
QCheckBox::indicator:checked { background: #7563DA; border-color: #7563DA; image: url("ui/check.svg"); }
QSpinBox::up-button, QDoubleSpinBox::up-button { subcontrol-origin: border; subcontrol-position: top right; width: 22px; border: none; border-top-right-radius: 6px; background: #F0EFF8; }
QSpinBox::down-button, QDoubleSpinBox::down-button { subcontrol-origin: border; subcontrol-position: bottom right; width: 22px; border: none; border-bottom-right-radius: 6px; background: #F0EFF8; }
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow { image: url("ui/up.svg"); width: 10px; height: 9px; }
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow { image: url("ui/down.svg"); width: 10px; height: 9px; }
QComboBox::drop-down { subcontrol-origin: border; subcontrol-position: top right; width: 26px; border: none; }
QComboBox::down-arrow { image: url("ui/down.svg"); width: 10px; height: 9px; }
QComboBox QAbstractItemView { background: white; border: 1px solid #E0DFEF; padding: 5px; selection-background-color: #EEE9FC; selection-color: #6352BB; }
QProgressBar { background: #E8EAF3; color: #777D94; border: none; border-radius: 3px; min-height: 6px; max-height: 6px; }
QProgressBar::chunk { background: #9A8AE5; border-radius: 3px; }
QLabel#taskStatus { font-size: 12px; color: #6E778F; }
QPlainTextEdit#taskLog { background: #EDEFF6; color: #7A8196; font-family: "Microsoft YaHei UI"; font-size: 12px; border: 0; border-radius: 7px; }
QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 3px 0; }
QScrollBar::handle:vertical { background: #CFD1E0; border-radius: 4px; min-height: 35px; }
QScrollBar::handle:vertical:hover { background: #B7B1D8; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QSplitter::handle { background: #EEEFF6; height: 5px; }
QStatusBar { background: #F4F5FA; color: #9298AA; font-size: 11px; border-top: 1px solid #E8EAF1; }
QStatusBar::item { border: none; }
QToolTip { background: #38334F; color: white; border: none; padding: 6px; }
'''

def apply_theme(app):
    app.setStyle('Fusion')
    palette=QPalette()
    for role,color in [(QPalette.ColorRole.Window,'#F4F5FA'),(QPalette.ColorRole.Base,'#FFFFFF'),(QPalette.ColorRole.Text,'#30374B'),(QPalette.ColorRole.WindowText,'#30374B'),(QPalette.ColorRole.Button,'#FFFFFF'),(QPalette.ColorRole.ButtonText,'#575F78'),(QPalette.ColorRole.Highlight,'#E6E0FC'),(QPalette.ColorRole.HighlightedText,'#5141A2')]: palette.setColor(role,QColor(color))
    from pathlib import Path
    base=Path(__file__).resolve().parent.as_posix()
    app.setPalette(palette); app.setStyleSheet(STYLE.replace('ui/check.svg',base+'/check.svg').replace('ui/up.svg',base+'/up.svg').replace('ui/down.svg',base+'/down.svg'))
