# coding=utf-8

from qgis.core import * # unable to import QgsWKBTypes otherwize (quid?)
from qgis.gui import *

from PyQt4.QtCore import pyqtSignal
from PyQt4.QtGui import QToolBar, QLineEdit, QLabel, QIcon

from shapely.geometry import LineString
import os

from .axis_layer import AxisLayer
from .section_tools import LineSelectTool

class SectionToolbar(QToolBar):
    line_clicked = pyqtSignal(str, float)
    projected_layer_created = pyqtSignal(QgsVectorLayer, QgsVectorLayer)

    def __init__(self, canvas):
        QToolBar.__init__(self)
        self.__canvas = canvas

        icon = lambda name: QIcon(os.path.join(os.path.dirname(__file__), name))

        self.addAction('axis').triggered.connect(self.__add_axis)

        self.addAction(icon('add_layer.svg'), 'add projected layer').triggered.connect(self.__add_layer)
        self.selectLineAction = self.addAction(icon('select_line.svg'), 'select line')
        self.selectLineAction.setCheckable(True)
        self.selectLineAction.triggered.connect(self.__set_section_line)

        self.buffer_width = QLineEdit("100")
        self.buffer_width.setMaximumWidth(50)
        self.addWidget(QLabel("Width:"))
        self.addWidget(self.buffer_width)

        self.__tool = None
        self.__old_tool = None

    def __set_section_line(self):
        print "set_section_line"
        self.__tool = LineSelectTool(self.__canvas)
        self.__tool.line_clicked.connect(lambda wkt_: self.line_clicked.emit(wkt_, float(self.buffer_width.text())))
        self.__canvas.setMapTool(self.__tool)

    def __add_layer(self):
        print "add layer"
        layer = self.__canvas.currentLayer()

        if layer is None:
            return
        section = QgsVectorLayer(
            "{geomType}?crs={crs}&index=yes".format(
                geomType={
                    QGis.Point:"Point",
                    QGis.Line:"LineString",
                    QGis.Polygon:"Polygon"
                    }[layer.geometryType()],
                crs=self.__canvas.mapSettings().destinationCrs().authid()
                ), layer.name(), "memory")
        section.setCustomProperty("projected_layer", layer.id())

        # cpy attributes structure
        section.dataProvider().addAttributes([layer.fields().field(f) for f in range(layer.fields().count())])
        section.updateFields()

        # cpy style
        section.setRendererV2(layer.rendererV2().clone())

        QgsMapLayerRegistry.instance().addMapLayer(section, False)

        self.projected_layer_created.emit(layer, section)

    def __add_axis(self):
        self.axislayer = AxisLayer(self.__canvas.mapSettings().destinationCrs())
        QgsMapLayerRegistry.instance().addMapLayer(self.axislayer, False)

