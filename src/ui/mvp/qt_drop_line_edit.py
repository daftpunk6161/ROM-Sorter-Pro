from __future__ import annotations

from pathlib import Path
import os


def build_drop_line_edit(QtWidgets):
    class DropLineEdit(QtWidgets.QLineEdit):
        def __init__(self, on_drop, *args, enabled: bool = True, **kwargs):
            super().__init__(*args, **kwargs)
            self._on_drop = on_drop
            self.setAcceptDrops(bool(enabled))

        def dragEnterEvent(self, event):
            if event.mimeData().hasUrls():
                event.acceptProposedAction()
            else:
                event.ignore()

        def dropEvent(self, event):
            urls = event.mimeData().urls() if event.mimeData().hasUrls() else []
            if not urls:
                return
            try:
                paths = []
                for url in urls:
                    path = Path(url.toLocalFile())
                    if path.is_file():
                        path = path.parent
                    if path.exists():
                        paths.append(str(path))
                if not paths:
                    return
                if len(paths) == 1:
                    self._on_drop(paths[0])
                    return
                try:
                    common = os.path.commonpath(paths)
                except Exception:
                    common = paths[0]
                if common and Path(common).exists():
                    self._on_drop(str(common))
            except Exception:
                return

    return DropLineEdit
