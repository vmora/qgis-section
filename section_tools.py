# coding=utf-8

from qgis.core import *
from qgis.gui import *

from PyQt4.QtCore import Qt, pyqtSignal
from PyQt4.QtGui import QApplication

from .helpers import projected_layer_to_original, projected_feature_to_original

class LineSelectTool(QgsMapTool):
    line_clicked = pyqtSignal(str)

    def __init__(self, canvas):
        QgsMapTool.__init__(self, canvas)
        self.canvas = canvas

    def canvasReleaseEvent(self, event):
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


class SelectionTool(QgsMapToolEmitPoint):
    def __init__(self, canvas):
        QgsMapToolEmitPoint.__init__(self, canvas)
        self.canvas = canvas

        self.canvasClicked.connect(self._new_point)

    def __del__(self):
        self.canvasClicked.disconnect(self._new_point)

    def _new_point(self, point, button):
        layer = self.canvas.currentLayer()
        source_layer = projected_layer_to_original(layer)

        if layer is None or source_layer is None:
            return

        if not(QApplication.keyboardModifiers() & Qt.ControlModifier):
            source_layer.removeSelection()
            layer.removeSelection()

        radius = QgsMapTool.searchRadiusMU(self.canvas)
        rect = QgsRectangle(point.x() - radius, point.y() - radius, point.x() + radius, point.y() + radius)
        rect_geom = QgsGeometry.fromRect(rect)

        best_choice = {'distance': 0, 'feature': None }
        for feat in layer.getFeatures(QgsFeatureRequest(rect)):
            dist = feat.geometry().distance(QgsGeometry.fromPoint(QgsPoint(point.x(), point.y())))

            if dist < best_choice['distance'] or best_choice['feature'] is None:
                best_choice['distance'] = dist
                best_choice['feature'] = feat

        if best_choice['feature']:
            layer.select(best_choice['feature'].id())
            source_layer.select(projected_feature_to_original(source_layer, best_choice['feature']).id())
