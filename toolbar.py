# coding=utf-8

from qgis.core import * # unable to import QgsWKBTypes otherwize (quid?)
from qgis.gui import *

from PyQt4.QtCore import pyqtSignal
from PyQt4.QtGui import QToolBar, QLineEdit, QLabel

from shapely.geometry import LineString

class LineSelectTool(QgsMapTool):
    line_clicked = pyqtSignal(str)
    def __init__(self, canvas):
        QgsMapTool.__init__(self, canvas)
        self.canvas = canvas

    def canvasReleaseEvent(self, event):
        print "canvasReleaseEvent"
        #Get the click
        radius = QgsMapTool.searchRadiusMU(self.canvas)
        for layer in self.canvas.layers():
            layerPoint = self.toLayerCoordinates(layer, event.pos())
            rect = QgsRectangle(layerPoint.x() - radius, layerPoint.y() - radius, layerPoint.x() + radius, layerPoint.y() + radius)
            rect_geom = QgsGeometry.fromRect(rect)
            if layer.type() == QgsMapLayer.VectorLayer and layer.geometryType() == QGis.Line:
                for feat in layer.getFeatures(QgsFeatureRequest(rect)):
                    if feat.geometry().intersects(rect_geom) and feat.geometry().length() > 0:
                        print "found line in ", layer.name()
                        self.line_clicked.emit(QgsGeometry.exportToWkt(feat.geometry()))
                        return
        # emit a small linestring in the x direction
        layerPoint = self.toMapCoordinates(event.pos())
        self.line_clicked.emit(LineString([(layerPoint.x()-radius, layerPoint.y()), (layerPoint.x()+radius, layerPoint.y())]).wkt)

class SectionToolbar(QToolBar):
    line_clicked = pyqtSignal(str, float)
    
    def __init__(self, canvas):
        QToolBar.__init__(self)
        self.__canvas = canvas
        self.addAction('select line').triggered.connect(self.__set_section_line)

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
