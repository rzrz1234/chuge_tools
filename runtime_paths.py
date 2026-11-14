"""源码运行和独立 EXE 共用的路径初始化。"""
import os,sys
from pathlib import Path

RESOURCE_ROOT=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))
USER_ROOT=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'ChugeTools'
LOG_ROOT=USER_ROOT/'logs'

def initialize():
    binary=RESOURCE_ROOT/'bin'
    if binary.is_dir():os.environ['PATH']=str(binary)+os.pathsep+os.environ.get('PATH','')
    if sys.platform=='win32':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('Chuge.Tools.Desktop')
