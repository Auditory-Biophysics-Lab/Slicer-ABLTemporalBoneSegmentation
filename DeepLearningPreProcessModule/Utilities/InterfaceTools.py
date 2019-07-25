import ctk
import qt


class InterfaceTools:
    def __init__(self, parent):
        pass

    @staticmethod
    def build_dropdown(title, disabled=False):
        d = ctk.ctkCollapsibleButton()
        d.text = title
        d.enabled = not disabled
        d.collapsed = disabled
        return d

    @staticmethod
    def build_spin_box(minimum, maximum, click):
        box = qt.QSpinBox()
        box.setMinimum(minimum)
        box.setMaximum(maximum)
        # box.setDecimals(decimals)
        box.connect('valueChanged(int)', click)
        return box

    @staticmethod
    def build_fiducial_tab(fiducial, click_set, click_clear):
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
        table.verticalHeader().setFixedWidth(0)
        label = (fiducial["label"][:20] + '..') if len(fiducial["label"]) > 20 else fiducial["label"]
        setButton = qt.QPushButton("Set \n" + label + "\nFiducial")
        setButton.setFixedSize(150, 46)
        setButton.connect('clicked(bool)', lambda: click_set(fiducial))
        clearButton = qt.QPushButton("Clear")
        clearButton.setFixedSize(46, 46)
        clearButton.connect('clicked(bool)', lambda: click_clear(fiducial))
        tab = qt.QWidget()
        layout = qt.QHBoxLayout(tab)
        layout.addWidget(setButton)
        layout.addWidget(clearButton)
        layout.addWidget(table)
        return tab, table
