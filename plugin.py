# -*- coding: UTF-8 -*-

from qgis.core import QGis, \
                      QgsFeatureRequest,\
                      QgsRectangle,\
                      QgsMapLayerRegistry,\
                      QgsMapLayer,\
                      QgsVectorLayer,\
                      QgsFeature,\
                      QgsGeometry,\
                      QgsPoint,\
                      QgsCoordinateReferenceSystem

from qgis.gui import QgsMapTool, \
                     QgsMapCanvas, \
                     QgsMapCanvasLayer,\
                     QgsMapToolPan,\
                     QgsMapToolZoom,\
                     QgsMapToolIdentify,\
                     QgsMapToolIdentifyFeature

from PyQt4.QtCore import Qt, pyqtSignal
from PyQt4.QtGui import QDockWidget, QToolBar, QLineEdit, QLabel

from .canvas import Canvas

class LineSelectTool(QgsMapTool):
    line_clicked = pyqtSignal(str, int)
    def __init__(self, canvas):
        QgsMapTool.__init__(self, canvas)

    def canvasReleaseEvent(self, event):
        print "canvasReleaseEvent"
        #Get the click
        radius = QgsMapTool.searchRadiusMU(self.canvas())
        x = event.pos().x()
        y = event.pos().y()
        for layer in self.canvas().layers():
            if layer.type() == QgsMapLayer.VectorLayer and layer.geometryType() == QGis.Line:
                for feat in layer.getFeatures(QgsFeatureRequest(
                    QgsRectangle(x-radius, y-radius, x+radius, y+radius))):
                    self.line_clicked.emit(layer.id(), feat.id())
                    return
        self.line_clicked.emit(None, None)

class Plugin():
    def __init__(self, iface):
        self.iface = iface
        #self.canvas_dock = QDockWidget('Qgis section')
        #self.canvas = Canvas()
        #self.canvas_dock.setWidget(self.canvas)
        #self.iface.addDockWidget(Qt.RightDockWidgetArea, self.canvas_dock)

        self.toolbar = QToolBar()
        self.toolbar.addAction('select line').triggered.connect(self.set_section_line)
        self.buffer_width = QLineEdit("10")
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
    
    def __map_tool_changed(self, map_tool):
        if isinstance(map_tool, QgsMapToolPan):
            self.tool = QgsMapToolPan(self.canvas)
            self.canvas.setMapTool(self.tool)
        elif isinstance(map_tool, QgsMapToolZoom):
            self.tool = QgsMapToolZoom(self.canvas, map_tool.action().text().find(u"+") == -1)
            self.canvas.setMapTool(self.tool)
        else:
            print 'map_tool', map_tool, map_tool.objetName()
            self.canvas.setMapTool(None)
            self.tool = None


    def initGui(self):
    	pass

    def unload(self):
        self.canvas_dock.setParent(None)
        self.toolbar.setParent(None)
        self.iface.mapCanvas().mapToolSet[QgsMapTool].disconnect()

    def set_section_line_(self, layer_id, feature_id):
        print "selected", layer_id, feature_id
        line = None
        #self.canvas.set_section_line(line, float(self.buffer_width.text()))
        self.iface.mapCanvas().setMapTool(self.old_tool)
        self.tool.line_clicked.disconnect()
        self.tool.setParent(None)
        self.tool = None
        self.oldtool = None

    def set_section_line(self):
        print "set_section_line"

        self.old_tool = self.iface.mapCanvas().mapTool()
        self.tool = LineSelectTool(self.iface.mapCanvas())
        self.tool.line_clicked.connect(self.set_section_line_)
        self.iface.mapCanvas().setMapTool(self.tool)

