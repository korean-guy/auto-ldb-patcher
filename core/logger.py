"""
core/logger.py
콘솔 print() 대신 GUI 하단 로그 패널로 메시지를 출력하기 위한 전역 로거.
core/tabs 어디서든 `from core.logger import log` 로 가져와 log.info()/warning()/error()를
호출하면 됩니다. 로그 패널이 아직 생성되기 전(프로그램 시작 초반)에는 콘솔로만 출력되다가,
main 파일에서 log.attach(text_widget)를 호출한 시점부터 GUI에도 함께 표시됩니다.
"""
import datetime


class Logger:
    def __init__(self):
        self.widget = None

    def attach(self, text_widget):
        """로그를 표시할 tkinter Text 위젯을 연결합니다."""
        self.widget = text_widget

    def _write(self, tag, msg):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}"
        print(line)  # 개발 중 콘솔 디버깅용으로도 계속 출력
        if self.widget is not None:
            try:
                self.widget.configure(state="normal")
                self.widget.insert("end", line + "\n", tag)
                self.widget.see("end")
                self.widget.configure(state="disabled")
            except Exception:
                pass  # 위젯이 파괴된 이후 호출되는 등 예외 상황은 조용히 무시

    def info(self, msg):
        self._write("info", msg)

    def warning(self, msg):
        self._write("warning", f"⚠ {msg}")

    def error(self, msg):
        self._write("error", f"❌ {msg}")


log = Logger()
