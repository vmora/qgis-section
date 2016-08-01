# coding=utf-8

from qgis.core import * # unable to import QgsWKBTypes otherwize (quid?)
from qgis.gui import *

from PyQt4.QtCore import Qt, pyqtSignal, QVariant
from PyQt4.QtGui import QDockWidget, QToolBar, QLineEdit, QLabel

from shapely.wkt import loads
from shapely.geometry import Point, LineString

from section_layer import SectionLayer, hasZ

#@qgsfunction(args="auto", group='Custom')
#def square_buffer(feature, parent):
#    geom = feature.geometry()
#    wkt = geom.exportToWkt().replace('LineStringZ', 'LINESTRING')
#    print wkt
#    return QgsGeometry.fromWkt(geom_from_wkt(wkt).buffer(30., cap_style=2).wkt)

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

class Plugin():
    def __init__(self, iface):
        self.iface = iface

        self.toolbar = QToolBar()
        self.toolbar.addAction('select line').triggered.connect(self.set_section_line)
        self.buffer_width = QLineEdit("100")
        self.buffer_width.setMaximumWidth(50)
        self.toolbar.addWidget(QLabel("Width:"))
        self.toolbar.addWidget(self.buffer_width)
        self.iface.addToolBar(self.toolbar)

        self.tool = None
        self.old_tool = None

        self.layers = {}

        canvas = QgsMapCanvas()
        canvas.setWheelAction(QgsMapCanvas.WheelZoomToMouseCursor)

        self.canvas_dock = QDockWidget('Section View')
        self.canvas = canvas
        self.canvas_dock.setWidget(self.canvas)
        self.iface.addDockWidget(Qt.BottomDockWidgetArea, self.canvas_dock)

        # tool synchro
        self.tool = None
        self.__map_tool_changed(self.iface.mapCanvas().mapTool())
        self.iface.mapCanvas().mapToolSet.connect(self.__map_tool_changed)

        QgsMapLayerRegistry.instance().layersWillBeRemoved.connect(self.__remove_layer) 

        self.highlighter = None

        self.layertreeroot = QgsLayerTreeGroup()
        self.layertreeview = QgsLayerTreeView()
        self.layertreemodel = QgsLayerTreeModel(self.layertreeroot)
        self.layertreeview.setModel(self.layertreemodel)
        self.layertreeview_dock = QDockWidget('Section Layers')
        self.layertreeview_dock.setWidget(self.layertreeview)
        self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.layertreeview_dock)
        self.layertreeview.doubleClicked.connect(self.__open_layer_props)

        self.bridge = QgsLayerTreeMapCanvasBridge(self.layertreeroot, self.canvas)
        self.layertreeview.currentLayerChanged.connect(self.canvas.setCurrentLayer)

    def __open_layer_props(self):
        print "currentLayer", self.canvas.currentLayer(), self.layertreeview.currentNode()
        self.iface.showLayerProperties(self.canvas.currentLayer())

    def __remove_layer(self, layer_ids):
        for layer_id in layer_ids:
            if layer_id in self.layers:
                del self.layers[layer_id]

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
        self.__cleanup()
        self.iface.removeDockWidget(self.canvas_dock)
        self.iface.removeDockWidget(self.layertreeview_dock)
        self.canvas_dock.setParent(None)
        self.layertreeview_dock.setParent(None)
        self.toolbar.setParent(None)
        self.iface.mapCanvas().mapToolSet[QgsMapTool].disconnect()

    def __cleanup(self):
        if self.highlighter is not None:
            self.iface.mapCanvas().scene().removeItem(self.highlighter)
            self.highlighter = None
        
        self.layertreeroot.removeAllChildren()

        # remove memory layers
        self.canvas.setLayerSet([])
        for lid in self.layers.keys():
            QgsMapLayerRegistry.instance().removeMapLayer(lid)
        self.layers = {}

    def set_section_line_(self, line_wkt):
        print "SelecteD", line_wkt
        line = None
        self.__cleanup()
        
        line = QgsGeometry.fromWkt(line_wkt)

        width = float(self.buffer_width.text())

        self.highlighter = QgsRubberBand(self.iface.mapCanvas(), QGis.Line)
        self.highlighter.addGeometry(line, None)
        self.highlighter.setWidth(10)
        self.highlighter.setColor(Qt.red)

        # select features from layers with Z in geometry
        for layer in self.iface.mapCanvas().layers():
            if hasZ(layer):
                section = SectionLayer(line_wkt, width*2, layer)
                QgsMapLayerRegistry.instance().addMapLayer(section, False)
                self.layers[section.id()] = section
                self.layertreeroot.addLayer(section)

        #self.canvas.setLayerSet([QgsMapCanvasLayer(layer) for layer in self.layers.values()])
        self.canvas.zoomToFullExtent()


    def set_section_line(self):
        print "set_section_line"
        self.old_tool = self.iface.mapCanvas().mapTool()
        self.tool = LineSelectTool(self.iface.mapCanvas())
        self.tool.line_clicked.connect(self.set_section_line_)
        self.iface.mapCanvas().setMapTool(self.tool)

