from .main_window import MainWindow

from PyQt4.QtCore import Qt
from PyQt4.QtGui import QDockWidget, QAction

class Plugin():
    def __init__(self, iface):
        self.__iface = iface
        self.__sections = []

    def initGui(self):
        self.action = QAction('Add section', None)
        self.__iface.addToolBarIcon(self.action)
        self.action.triggered.connect(self._add_section)

    def unload(self):
        for section in self.__sections:
            self.__iface.removeDockWidget(section['dock'])
            section['main'].unload()

        self.action.triggered.disconnect()
        self.__iface.removeToolBarIcon(self.action)

    def _add_section(self):
        self.add_section('section{}'.format(len(self.__sections) + 1))

    def add_section(self, id_):
        main = MainWindow(self.__iface, id_)
        dock = QDockWidget(id_)
        dock.setWidget(main)
        main.add_default_section_buttons()
        self.__iface.addDockWidget(Qt.BottomDockWidgetArea, dock)

        self.__sections += [ { 'id': id_, 'main': main, 'dock': dock }]
