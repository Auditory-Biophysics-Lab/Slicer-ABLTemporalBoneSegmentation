import qt
import ctk


def dropdown(title, disabled=False):
    d = ctk.ctkCollapsibleButton()
    d.text = title
    d.enabled = not disabled
    d.collapsed = disabled
    return d


def spin_box(minimum, maximum, click):
    box = qt.QSpinBox()
    box.setMinimum(minimum)
    box.setMaximum(maximum)
    # box.setDecimals(decimals)
    box.connect('valueChanged(int)', click)
    return box


def build_fiducial_tab(fiducial, on_click):
    table = qt.QTableWidget(1, 3)
    table.setSelectionBehavior(qt.QAbstractItemView.SelectRows)
    table.setFixedHeight(46)
    table.setHorizontalHeaderLabels(["X", "Y", "Z"])
    table.horizontalHeader().setSectionResizeMode(qt.QHeaderView.Stretch)
    for i in (range(0, 3)):
        item = qt.QTableWidgetItem("-")
        item.setTextAlignment(qt.Qt.AlignCenter)
        item.setFlags(qt.Qt.ItemIsSelectable)
        table.setItem(0, i, item)
    table.setVerticalHeaderLabels([''])
    # table.verticalHeader().setSectionResizeMode(qt.QHeaderView.Stretch)
    table.verticalHeader().setFixedWidth(0)
    # table.verticalHeader().setDefaultAlignment(qt.Qt.AlignCenter)
    label = (fiducial["label"][:20] + '..') if len(fiducial["label"]) > 20 else fiducial["label"]
    setButton = qt.QPushButton("Set \n" + label + "\nFiducial")
    setButton.setFixedSize(130, 46)

    def set_fiducial(): on_click(fiducial)
    setButton.connect('clicked(bool)', set_fiducial)

    tab = qt.QWidget()
    layout = qt.QHBoxLayout()
    # layout.setFixedHeight(200)
    tab.setLayout(layout)
    tab.layout().addWidget(setButton)
    tab.layout().addWidget(table)
    return tab, table
