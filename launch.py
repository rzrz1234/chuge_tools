"""独立程序入口，记录启动阶段的异常。"""
import sys,traceback
from runtime_paths import initialize,LOG_ROOT

def launch():
    try:
        initialize()
        from main import main
        return main()
    except Exception:
        LOG_ROOT.mkdir(parents=True,exist_ok=True)
        details=traceback.format_exc();(LOG_ROOT/'启动错误.txt').write_text(details,encoding='utf-8')
        if not any(x.startswith('--self-test=') for x in sys.argv):
            import ctypes
            ctypes.windll.user32.MessageBoxW(0,'程序启动失败，错误详情已写入：\n'+str(LOG_ROOT/'启动错误.txt'),'褚歌工具箱',16)
        return 1

if __name__=='__main__':sys.exit(launch())
