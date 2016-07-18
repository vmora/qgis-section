# -*- coding: UTF-8 -*-

from PyQt4.QtCore import Qt
from PyQt4.QtGui import QDockWidget

from .canvas import Canvas

class Plugin():
    def __init__(self, iface):
        self.iface = iface
        self.canvas_dock = QDockWidget('Qgis section')
        self.canvas = Canvas()
        self.canvas_dock.setWidget(self.canvas)
        self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.canvas_dock)

    def initGui(self):
    	pass


    def unload(self):
        self.canvas_dock.setParent(None)
