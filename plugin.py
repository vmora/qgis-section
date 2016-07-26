# -*- coding: UTF-8 -*-

#from qgis.core import QGis, \
#                      QgsFeatureRequest,\
#                      QgsRectangle,\
#                      QgsMapLayerRegistry,\
#                      QgsMapLayer,\
#                      QgsVectorLayer,\
#                      QgsFeature,\
#                      QgsGeometry,\
#                      QgsPoint,\
#                      QgsCoordinateReferenceSystem

from qgis.core import * # unable to import QgsWKBTypes otherwize (quid?)

from qgis.gui import QgsMapTool, \
                     QgsMapCanvas, \
                     QgsMapCanvasLayer,\
                     QgsMapToolPan,\
                     QgsMapToolZoom,\
                     QgsMapToolIdentify,\
                     QgsMapToolIdentifyFeature,\
                     QgsRubberBand

from PyQt4.QtCore import Qt, pyqtSignal
from PyQt4.QtGui import QDockWidget, QToolBar, QLineEdit, QLabel


#@qgsfunction(args="auto", group='Custom')
#def square_buffer(feature, parent):
#    geom = feature.geometry()
#    wkt = geom.exportToWkt().replace('LineStringZ', 'LINESTRING')
#    print wkt
#    return QgsGeometry.fromWkt(geom_from_wkt(wkt).buffer(30., cap_style=2).wkt)


class LineSelectTool(QgsMapTool):
    line_clicked = pyqtSignal(str, int)
    def __init__(self, canvas):
        QgsMapTool.__init__(self, canvas)
        self.canvas = canvas

    def canvasReleaseEvent(self, event):
        print "canvasReleaseEvent"
        #Get the click
        radius = QgsMapTool.searchRadiusMU(self.canvas)
        x = event.pos().x()
        y = event.pos().y()
        for layer in self.canvas.layers():
            layerPoint = self.toLayerCoordinates(layer, event.pos())
            if layer.type() == QgsMapLayer.VectorLayer and layer.geometryType() == QGis.Line:

                for feat in layer.getFeatures(QgsFeatureRequest(
                    QgsRectangle(layerPoint.x() - radius, layerPoint.y() - radius, layerPoint.x() + radius, layerPoint.y() + radius))):
                    self.line_clicked.emit(layer.id(), feat.id())
                    return
        self.line_clicked.emit(None, None)

class Plugin():
    def __init__(self, iface):
        self.iface = iface

        self.toolbar = QToolBar()
        self.toolbar.addAction('select line').triggered.connect(self.set_section_line)
        self.buffer_width = QLineEdit("0.5")
        self.buffer_width.setMaximumWidth(50)
        self.toolbar.addWidget(QLabel("Width:"))
        self.toolbar.addWidget(self.buffer_width)
        self.iface.addToolBar(self.toolbar)

        self.tool = None
        self.old_tool = None

        # 2154 just for the fun, we don't care as long as the unit is meters
        layer = QgsVectorLayer("Point?crs=epsg:2154&field=id:integer&field=name:string(20)&index=yes",
                "temporary_points",
                "memory")
        layer.beginEditCommand("test")
        provider = layer.dataProvider()
        for pt in [[0,0], [0,-100], [10,10]]:
            fet = QgsFeature()
            fet.setGeometry(QgsGeometry.fromPoint(QgsPoint(*pt)))
            fet.setAttributes([1, "Johny"])
            provider.addFeatures([fet])
        layer.endEditCommand()

        QgsMapLayerRegistry.instance().addMapLayer(layer, False)

        print 'validity', layer.isValid(), layer.extent().xMaximum(), layer.featureCount()
        self.layer= layer

        canvas = QgsMapCanvas()
        canvas.setLayerSet([QgsMapCanvasLayer(layer)])

        canvas.setCurrentLayer(layer)
        canvas.zoomToFullExtent()
        canvas.setWheelAction(QgsMapCanvas.WheelZoomToMouseCursor)

        self.canvas_dock = QDockWidget('Qgis section other')
        self.canvas = canvas
        self.canvas_dock.setWidget(self.canvas)
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.canvas_dock)

        # tool synchro
        self.tool = None
        self.__map_tool_changed(self.iface.mapCanvas().mapTool())
        self.iface.mapCanvas().mapToolSet.connect(self.__map_tool_changed)

        self.highlighter = None

    def __map_tool_changed(self, map_tool):
        if isinstance(map_tool, QgsMapToolPan):
            self.tool = QgsMapToolPan(self.canvas)
            self.canvas.setMapTool(self.tool)
        elif isinstance(map_tool, QgsMapToolZoom):
            self.tool = QgsMapToolZoom(self.canvas, map_tool.action().text().find(u"+") == -1)
            self.canvas.setMapTool(self.tool)
        elif isinstance(map_tool, LineSelectTool):
            pass
        else:
            print 'map_tool', map_tool
            self.canvas.setMapTool(None)
            self.tool = None

    def initGui(self):
    	pass

    def unload(self):
        self.iface.removeDockWidget(self.canvas_dock)
        self.canvas_dock.setParent(None)
        self.toolbar.setParent(None)
        self.iface.mapCanvas().mapToolSet[QgsMapTool].disconnect()
        if self.highlighter is not None:
            self.iface.mapCanvas().scene().removeItem(self.highlighter)

    def set_section_line_(self, layer_id, feature_id):
        print "SelecteD", layer_id, feature_id
        line = None
        self.tool.line_clicked.disconnect()
        self.tool.setParent(None)
        self.tool = None
        self.iface.mapCanvas().setMapTool(self.old_tool)
        self.oldtool = None

        layer = QgsMapLayerRegistry.instance().mapLayer(layer_id)
        line = None
        for f in layer.getFeatures(QgsFeatureRequest(feature_id)):
            line = QgsGeometry(f.geometry())
            break

        if line is None:
            iface.messageBar().pushInfo("note", "no selected line")
            return

        width = float(self.buffer_width.text())
        buff = line.buffer(width, 4)
        if self.highlighter is not None:
            self.iface.mapCanvas().scene().removeItem(self.highlighter)
        self.highlighter = QgsRubberBand(self.iface.mapCanvas(), QGis.Polygon)
        self.highlighter.addGeometry(buff, None)
         
        # select features from layers with Z in geometry
        for layer in self.iface.mapCanvas().layers():
            if QgsWKBTypes.hasZ(int(layer.wkbType())):
                for feature in layer.getFeatures(QgsFeatureRequest(buff.boundingBox())):
                    if feature.geometry().intersects(buff):
                        print layer.name(), feature.id()

        
            # debug visu
            # ___layer = QgsVectorLayer("polygon?crs=epsg:2154&field=id:integer&field=name:string(20)&index=yes",
            #         "temporary_poly",
            #         "memory")
            # ___layer.beginEditCommand("test")
            # provider = ___layer.dataProvider()
            # fet = QgsFeature()
            # fet.setGeometry(buffer)
            # fet.setAttributes([1, "Johny"])
            # provider.addFeatures([fet])
            # ___layer.endEditCommand()
            # QgsMapLayerRegistry.instance().addMapLayer(___layer, False)

            # self.iface.mapCanvas().setLayerSet([QgsMapCanvasLayer(___layer)])
            # self.iface.mapCanvas().refreshAllLayers()


    def set_section_line(self):
        print "set_section_line"
        self.old_tool = self.iface.mapCanvas().mapTool()
        self.tool = LineSelectTool(self.iface.mapCanvas())
        self.tool.line_clicked.connect(self.set_section_line_)
        self.iface.mapCanvas().setMapTool(self.tool)

