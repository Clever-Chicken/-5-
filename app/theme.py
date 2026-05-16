APP_STYLE = """
QMainWindow {
    background: #f5f7fb;
}
QWidget#glassPanel {
    background: #ffffff;
    border: 1px solid #dbe3ef;
    border-radius: 8px;
}
QLineEdit {
    min-height: 30px;
    padding: 3px 10px;
    border-radius: 6px;
    color: #344054;
    background: #ffffff;
    border: 1px solid #cbd5e1;
    selection-background-color: #dbeafe;
}
QLineEdit:focus {
    border: 1px solid #2563eb;
}
QPushButton {
    min-height: 30px;
    padding: 0 12px;
    border-radius: 6px;
    color: #273548;
    font-weight: 600;
    background: #ffffff;
    border: 1px solid #cbd5e1;
}
QPushButton:hover {
    background: #f8fafc;
    border: 1px solid #94a3b8;
}
QPushButton:pressed {
    background: #e2e8f0;
}
QPushButton:disabled {
    color: #94a3b8;
    background: #f1f5f9;
    border: 1px solid #e2e8f0;
}
QPushButton#primaryButton {
    color: #ffffff;
    background: #2563eb;
    border: 1px solid #2563eb;
}
QPushButton#primaryButton:hover {
    background: #1d4ed8;
    border: 1px solid #1d4ed8;
}
QPushButton#primaryButton:pressed {
    background: #1e40af;
    border: 1px solid #1e40af;
}
QPushButton#secondaryButton,
QPushButton#paginationButton {
    color: #1f2937;
    background: #ffffff;
    border: 1px solid #cbd5e1;
}
QPushButton#secondaryButton:hover,
QPushButton#paginationButton:hover {
    color: #1d4ed8;
    background: #eff6ff;
    border: 1px solid #93c5fd;
}
QPushButton#paginationButton {
    min-width: 30px;
    padding: 0 8px;
}
QLabel {
    color: #344054;
}
QPushButton#sortChip,
QLabel#sortChip {
    color: #1d4ed8;
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 10px;
    padding: 3px 8px;
    font-weight: 600;
}
QTableView,
QTableWidget {
    color: #344054;
    gridline-color: #e5e7eb;
    border-radius: 6px;
    border: 1px solid #dbe3ef;
    background: #ffffff;
    alternate-background-color: #f8fafc;
    selection-background-color: #dbeafe;
    selection-color: #172033;
}
QTableView::item,
QTableWidget::item {
    border: 0;
    padding: 4px;
}
QTableView::item:selected,
QTableWidget::item:selected {
    color: #172033;
    background: #dbeafe;
}
QTableView QTableCornerButton::section,
QTableWidget QTableCornerButton::section {
    border: 0;
    background: #f8fafc;
}
QHeaderView::section {
    color: #344054;
    font-weight: 700;
    padding: 7px 8px;
    border: 0;
    border-right: 1px solid #e5e7eb;
    border-bottom: 1px solid #dbe3ef;
    background: #f8fafc;
}
QScrollBar:horizontal,
QScrollBar:vertical {
    background: #ffffff;
    border: 0;
}
QScrollBar:horizontal {
    height: 10px;
    margin: 0;
}
QScrollBar:vertical {
    width: 10px;
    margin: 0;
}
QScrollBar::handle:horizontal,
QScrollBar::handle:vertical {
    background: #cbd5e1;
    border-radius: 5px;
    min-height: 24px;
    min-width: 24px;
}
QScrollBar::handle:horizontal:hover,
QScrollBar::handle:vertical:hover {
    background: #93c5fd;
}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal,
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    border: 0;
    background: transparent;
    height: 0;
    width: 0;
}
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal,
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: transparent;
}
"""


def apply_app_theme(widget):
    widget.setStyleSheet(APP_STYLE)
