"""Shared native Qt widget styling."""
DIALOG_STYLE = '''
QDialog, QWidget#panel { background: #10161f; color: #e9eef5; }
QDialog { font-family: 'Segoe UI'; font-size: 12px; }
QLabel, QCheckBox { color: #c4cfdb; }
QLineEdit, QSpinBox, QComboBox, QListWidget, QTreeWidget {
 background: #171f2b; color: #e9eef5; border: 1px solid #303d4f;
 border-radius: 5px; padding: 6px; selection-background-color: #264c59; }
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border-color: #56d9bd; }
QSpinBox { padding-right: 18px; min-height: 21px; }
QComboBox { min-height: 21px; }
QComboBox::drop-down { border: 0; width: 24px; }
QComboBox QAbstractItemView { background: #1c2634; color: #e9eef5; selection-background-color: #264c59; }
QPushButton { background: #222e3d; color: #e3eaf3; border: 1px solid #36465b;
 border-radius: 5px; padding: 8px 12px; min-height: 18px; }
QPushButton:hover { background: #2c3b4e; border-color: #5e728c; }
QPushButton:pressed { background: #172431; }
QPushButton:disabled { color: #667586; border-color: #283340; background: #1b2530; }
QPushButton#primary { background: #5ce0c1; color: #082b29; border-color: #5ce0c1; font-weight: 600; }
QPushButton#primary:hover { background: #85ead2; }
QPushButton#primary:disabled { background: #2d504c; color: #7b9f99; border-color: #2d504c; }
QListWidget::item, QTreeWidget::item { padding: 7px; border-radius: 4px; }
QListWidget::item:selected, QTreeWidget::item:selected { background: #294858; color: #a5ffe6; }
QTabWidget::pane { border: 0; background: #141c27; }
QTabBar::tab { background: transparent; color: #9aabbf; padding: 12px 10px; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: #6ce2c6; border-bottom-color: #6ce2c6; }
QScrollArea { border: 0; background: transparent; }
QScrollBar:vertical { background: #151d28; width: 9px; margin: 0; }
QScrollBar:horizontal { background: #151d28; height: 9px; margin: 0; }
QScrollBar::handle { background: #405167; border-radius: 4px; min-height: 26px; min-width: 26px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QSplitter::handle { background: #273241; width: 1px; }
QMenu { background: #1b2532; color: #e3eaf3; border: 1px solid #38465b; padding: 5px; }
QMenu::item { padding: 8px 22px; }
QMenu::item:selected { background: #294858; }
QToolTip { background: #263447; color: #e7eef8; border: 1px solid #536579; padding: 6px; }
'''
