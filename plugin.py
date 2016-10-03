from .main_window import MainWindow

from PyQt4.QtCore import Qt
from PyQt4.QtGui import QDockWidget

class Plugin():
    def __init__(self, iface):
        self.__iface = iface
        self.__section_main = MainWindow(iface)
        self.__dock = QDockWidget('Section')
        self.__dock.setWidget(self.__section_main)

        self.__legend_dock = QDockWidget('Section Legend')
        self.__legend_dock.setWidget(self.__section_main.tree_view)

    def initGui(self):
        self.__section_main.add_default_section_buttons()
        self.__iface.addDockWidget(Qt.BottomDockWidgetArea, self.__dock)
        self.__iface.addDockWidget(Qt.LeftDockWidgetArea, self.__legend_dock)

    def unload(self):
        self.__iface.removeDockWidget(self.__dock)
        self.__iface.removeDockWidget(self.__legend_dock)

        self.__section_main.unload()
