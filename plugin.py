from .main_window import MainWindow

from PyQt4.QtCore import Qt
from PyQt4.QtGui import QDockWidget

class Plugin():
    def __init__(self, iface):
        self.__section_main = MainWindow(iface)
        self.__dock = QDockWidget('Section')
        self.__dock.setWidget(self.__section_main)
        iface.addDockWidget(Qt.BottomDockWidgetArea, self.__dock)

        self.__legend_dock = QDockWidget('Section Legend')
        self.__legend_dock.setWidget(self.__section_main.tree_view)
        iface.addDockWidget(Qt.LeftDockWidgetArea, self.__legend_dock)

    def initGui(self):
        pass

    def unload(self):
        pass



