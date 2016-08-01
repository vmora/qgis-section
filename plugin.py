# coding=utf-8

from qgis.core import * # unable to import QgsWKBTypes otherwize (quid?)
from qgis.gui import *

from PyQt4.QtCore import Qt
from PyQt4.QtGui import QDockWidget

from section_layer import SectionLayer, hasZ
from toolbar import SectionToolbar, LineSelectTool

#@qgsfunction(args="auto", group='Custom')
#def square_buffer(feature, parent):
#    geom = feature.geometry()
#    wkt = geom.exportToWkt().replace('LineStringZ', 'LINESTRING')
#    print wkt
#    return QgsGeometry.fromWkt(geom_from_wkt(wkt).buffer(30., cap_style=2).wkt)

class Plugin():
    def __init__(self, iface):
        self.iface = iface

        self.toolbar = SectionToolbar(iface.mapCanvas())
        self.iface.addToolBar(self.toolbar)
        self.toolbar.line_clicked.connect(self.__set_section_line)

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

        QgsMapLayerRegistry.instance().layersWillBeRemoved.connect(self.__remove_layers) 
        QgsMapLayerRegistry.instance().layersAdded.connect(self.__add_layers) 

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
        self.layertreemodel.setFlag(QgsLayerTreeModel.AllowNodeChangeVisibility, True)
        self.layertreemodel.setFlag(QgsLayerTreeModel.AllowLegendChangeState, True)

    def __open_layer_props(self):
        print "currentLayer", self.canvas.currentLayer(), self.layertreeview.currentNode()
        self.iface.showLayerProperties(self.canvas.currentLayer())

    def __remove_layers(self, layer_ids):
        for layer_id in layer_ids:
            if layer_id in self.layers:
                del self.layers[layer_id]

    def __add_layers(self, layers):
        for layer in layers:
            print "__add_layers", layer.name()

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

        QgsMapLayerRegistry.instance().layersWillBeRemoved.disconnect(self.__remove_layers) 
        QgsMapLayerRegistry.instance().layersAdded.disconnect(self.__add_layers) 

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

    def __set_section_line(self, line_wkt, width):
        print "SelecteD", line_wkt
        line = None
        self.__cleanup()
        
        line = QgsGeometry.fromWkt(line_wkt)

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



