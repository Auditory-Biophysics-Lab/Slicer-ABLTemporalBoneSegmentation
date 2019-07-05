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
    table = qt.QTableWidget(0, 4)
    table.setSelectionBehavior(qt.QAbstractItemView.SelectRows)
    table.setFixedHeight(46)
    table.setHorizontalHeaderLabels(["Label", "X", "Y", "Z"])
    table.horizontalHeader().setSectionResizeMode(qt.QHeaderView.Stretch)
    # table.setVerticalHeaderLabels([label])
    # table.verticalHeader().setSectionResizeMode(qt.QHeaderView.Stretch)
    # table.verticalHeader().setFixedWidth(46)
    # table.verticalHeader().setDefaultAlignment(qt.Qt.AlignCenter)
    setButton = qt.QPushButton("Set \n" + fiducial["label"] + "\nFiducial")
    setButton.setFixedSize(120, 46)

    def set_fiducial(): on_click(fiducial)

    setButton.connect('clicked(bool)', set_fiducial)

    tab = qt.QWidget()
    tab.setLayout(qt.QHBoxLayout())
    tab.layout().addWidget(setButton)
    tab.layout().addWidget(table)
    return tab
