from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class TabsUI:
    tabs: Any
    sidebar_visible: bool
    home_scroll: Any
    sort_scroll: Any
    convert_scroll: Any
    settings_scroll: Any
    reports_scroll: Any
    tools_scroll: Any
    home_tab: Any
    sort_tab: Any
    convert_tab: Any
    settings_tab: Any
    reports_tab: Any
    tools_tab: Any
    tab_indices: Dict[str, int]
    shell_pages: Dict[str, Any]


def build_tabs_ui(
    QtWidgets,
    sidebar: Any,
    content_layout: Any,
    show_external_tools: bool = False,
) -> TabsUI:
    tabs = QtWidgets.QTabWidget()
    try:
        tabs.tabBar().setVisible(True)
    except Exception:
        pass

    sidebar_visible = False
    sidebar.setVisible(False)
    sidebar.setMaximumWidth(0)
    content_layout.addWidget(sidebar)
    content_layout.addWidget(tabs, 1)

    def _wrap_tab_scroll(widget: Any) -> Any:
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setWidget(widget)
        return scroll

    home_tab = QtWidgets.QWidget()
    sort_tab = QtWidgets.QWidget()
    convert_tab = QtWidgets.QWidget()
    settings_tab = QtWidgets.QWidget()
    reports_tab = QtWidgets.QWidget()
    tools_tab = QtWidgets.QWidget()

    home_scroll = _wrap_tab_scroll(home_tab)
    sort_scroll = sort_tab
    convert_scroll = _wrap_tab_scroll(convert_tab)
    settings_scroll = _wrap_tab_scroll(settings_tab)
    reports_scroll = _wrap_tab_scroll(reports_tab)
    tools_scroll = None

    tabs.addTab(home_scroll, "🏠 Home")
    tabs.addTab(sort_scroll, "🔀 Sortieren")
    tabs.addTab(convert_scroll, "🧰 Konvertieren")
    tabs.addTab(settings_scroll, "⚙️ Einstellungen")
    tabs.addTab(reports_scroll, "📊 Reports")

    if show_external_tools:
        tools_scroll = _wrap_tab_scroll(tools_tab)
        tabs.addTab(tools_scroll, "External Tools")

    tab_indices = {
        "dashboard": tabs.indexOf(home_scroll),
        "sort": tabs.indexOf(sort_scroll),
        "conversions": tabs.indexOf(convert_scroll),
        "settings": tabs.indexOf(settings_scroll),
        "reports": tabs.indexOf(reports_scroll),
    }
    tabs.setCurrentIndex(0)

    shell_pages = {
        "Home": home_scroll,
        "Sortieren": sort_scroll,
        "Konvertieren": convert_scroll,
        "Einstellungen": settings_scroll,
        "Reports": reports_scroll,
    }

    return TabsUI(
        tabs=tabs,
        sidebar_visible=sidebar_visible,
        home_scroll=home_scroll,
        sort_scroll=sort_scroll,
        convert_scroll=convert_scroll,
        settings_scroll=settings_scroll,
        reports_scroll=reports_scroll,
        tools_scroll=tools_scroll,
        home_tab=home_tab,
        sort_tab=sort_tab,
        convert_tab=convert_tab,
        settings_tab=settings_tab,
        reports_tab=reports_tab,
        tools_tab=tools_tab,
        tab_indices=tab_indices,
        shell_pages=shell_pages,
    )
