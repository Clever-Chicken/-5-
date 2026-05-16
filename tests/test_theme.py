from PySide6.QtWidgets import QTableView, QWidget

from app.theme import apply_app_theme


def test_apply_app_theme_sets_light_table_stylesheet(qt_app):
    widget = QWidget()
    table = QTableView(widget)

    apply_app_theme(widget)

    stylesheet = widget.styleSheet()
    assert table.parent() is widget
    assert stylesheet
    assert "QTableView" in stylesheet
    assert "QTableWidget" in stylesheet
    assert "QLineEdit" in stylesheet
    assert "QHeaderView" in stylesheet
    assert "QScrollBar:horizontal" in stylesheet
    assert "QScrollBar:vertical" in stylesheet
    assert "gridline-color" in stylesheet
    assert "#ffffff" in stylesheet
    assert "selection-background-color" in stylesheet
    assert "selection-color" in stylesheet
    assert "#dbeafe" in stylesheet


def test_apply_app_theme_includes_control_object_styles(qt_app):
    widget = QWidget()

    apply_app_theme(widget)

    stylesheet = widget.styleSheet()
    assert "QPushButton#primaryButton" in stylesheet
    assert "QPushButton#secondaryButton" in stylesheet
    assert "QPushButton#sortChip" in stylesheet
    assert "QLabel#sortChip" in stylesheet
    assert "QPushButton#paginationButton" in stylesheet
    assert "qlineargradient" not in stylesheet
