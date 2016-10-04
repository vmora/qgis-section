# coding=utf-8

"""
This modules provides a ready to use section windows containing a section
a canvas and a layer tree
"""

from qgis.core import *
from qgis.gui import *

from PyQt4.QtGui import QMainWindow
from PyQt4.QtCore import Qt

from .section import Section
from .toolbar import Toolbar
from .canvas import Canvas
from .axis_layer import AxisLayer, AxisLayerType
from .tree_view import TreeView

import atexit

AXIS_LAYER_TYPE = AxisLayerType()
QgsPluginLayerRegistry.instance().addPluginLayerType(AXIS_LAYER_TYPE)

@atexit.register
def unload_axi_layer_type():
    print "unload_axi_layer_type"
    QgsPluginLayerRegistry.instance().removePluginLayerType(AxisLayer.LAYER_TYPE)

class MainWindow(QMainWindow):
    def __init__(self, iface, parent=None):
        QMainWindow.__init__(self, parent)
        self.setWindowFlags(Qt.Widget)

        self.__iface = iface
        self.__section = Section()
        self.__canvas = Canvas(self.__section, iface, self)
        self.__toolbar = Toolbar(self.__section.id, iface.mapCanvas())
        self.__tree_view = TreeView(self.__section, self.__canvas)

        self.__toolbar.line_clicked.connect(self.__section.update)

        self.addToolBar(Qt.TopToolBarArea, self.__toolbar)
        self.setCentralWidget(self.__canvas)

    def add_default_section_buttons(self):
        actions = self.__canvas.build_default_section_actions()
        self.__canvas.add_section_actions_to_toolbar(actions, self.__toolbar)

    def unload(self):
        self.__canvas.unload()
        self.__toolbar.unload()
        self.__section.unload()

        self.removeToolBar(self.__toolbar)
        self.__canvas = None
        self.__section = None


    def __getattr__(self, name):
        if name == "canvas":
            return self.__canvas
        elif name == "toolbar":
            return self.__toolbar
        elif name == "tree_view":
            return self.__tree_view
        elif name == "section":
            return self.__section
        raise AttributeError(name)


