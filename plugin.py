# coding=utf-8

from qgis.core import * # unable to import QgsWKBTypes otherwize (quid?)
from qgis.gui import *

from PyQt4.QtCore import Qt
from PyQt4.QtGui import QDockWidget, QMenu, QColor

from .section_layer import LayerProjection
from .toolbar import SectionToolbar, LineSelectTool
from .axis_layer import AxisLayer, AxisLayerType

from math import sqrt

#@qgsfunction(args="auto", group='Custom')
#def square_buffer(feature, parent):
#    geom = feature.geometry()
#    wkt = geom.exportToWkt().replace('LineStringZ', 'LINESTRING')
#    print wkt
#    return QgsGeometry.fromWkt(geom_from_wkt(wkt).buffer(30., cap_style=2).wkt)
class ContextMenu(QgsLayerTreeViewMenuProvider):
    def __init__(self, plugin):
        QgsLayerTreeViewMenuProvider.__init__(self)
        self.__plugin = plugin

    def createContextMenu(self):
        menu = QMenu()
        menu.addAction('remove').triggered.connect(self.__plugin.remove_current_layer)
        return menu

class Plugin():
    def __init__(self, iface):
        self.iface = iface

        self.line = None

        self.toolbar = SectionToolbar(iface.mapCanvas())
        self.iface.addToolBar(self.toolbar)
        self.toolbar.line_clicked.connect(self.__set_section_line)

        self.layers = {}
        self.axis_layer = None

        canvas = QgsMapCanvas()
        canvas.setWheelAction(QgsMapCanvas.WheelZoomToMouseCursor)
        canvas.setCrsTransformEnabled(False)

        self.canvas_dock = QDockWidget('Section View')
        self.canvas = canvas
        self.canvas_dock.setWidget(self.canvas)
        self.iface.addDockWidget(Qt.BottomDockWidgetArea, self.canvas_dock)
        self.canvas.extentsChanged.connect(self.extents_changed)

        # tool synchro
        self.tool = None
        self.__map_tool_changed(self.iface.mapCanvas().mapTool())
        self.iface.mapCanvas().mapToolSet.connect(self.__map_tool_changed)

        # project layer synchro
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
        self.layertreeview.setMenuProvider(ContextMenu(self))

        self.bridge = QgsLayerTreeMapCanvasBridge(self.layertreeroot, self.canvas)
        self.layertreeview.currentLayerChanged.connect(self.canvas.setCurrentLayer)
        self.layertreemodel.setFlag(QgsLayerTreeModel.AllowNodeChangeVisibility, True)
        self.layertreemodel.setFlag(QgsLayerTreeModel.AllowLegendChangeState, True)
        self.layertreemodel.setFlag(QgsLayerTreeModel.AllowNodeReorder, True)
        self.layertreemodel.setFlag(QgsLayerTreeModel.AllowNodeRename, True)

        # in case we are reloading
        self.__add_layers(QgsMapLayerRegistry.instance().mapLayers().values())

        self.axis_layer_type = AxisLayerType()
        QgsPluginLayerRegistry.instance().addPluginLayerType(self.axis_layer_type)

        #self.iface.actionZoomFullExtent().triggered.connect(self.canvas.zoomToFullExtent)
        #self.iface.actionZoomToLayer().triggered.connect(lambda x: 
        #        self.canvas.setExtent(self.canvas.currentLayer().extent()))
        self.iface.actionToggleEditing().triggered.connect(self.__toggle_edit)

    def __toggle_edit(self):
        print "__toggle_edit"
        if self.canvas.currentLayer() is None:
            return
        if self.canvas.currentLayer().isEditable():
            self.canvas.currentLayer().rollBack()
        else:
            self.canvas.currentLayer().startEditing()

    def __open_layer_props(self):
        print "currentLayer", self.canvas.currentLayer(), self.layertreeview.currentNode()
        self.iface.showLayerProperties(self.canvas.currentLayer())

    def remove_current_layer(self):
        layer = self.canvas.currentLayer()
        if layer is not None:
            QgsMapLayerRegistry.instance().removeMapLayer(layer.id())

    def __remove_layers(self, layer_ids):
        for layer_id in layer_ids:
            if layer_id in self.layers:
                self.layertreeroot.removeLayer(self.layers[layer_id].projected_layer)
                del self.layers[layer_id]
                print "__remove_layers", layer_id
            if self.axis_layer is not None and layer_id == self.axis_layer.id():
                self.layertreeroot.removeLayer(self.axis_layer)
                self.axis_layer = None

    def __add_layers(self, layers):
        for layer in layers:
            print "adding layer", layer.name()
            if layer.customProperty("projected_layer") is not None:
                source_layer = QgsMapLayerRegistry.instance().mapLayer(
                        layer.customProperty("projected_layer"))
                if source_layer is not None:
                    projection = LayerProjection(source_layer, layer)
                    self.toolbar.line_clicked.disconnect(self.__set_section_line)
                    self.toolbar.line_clicked.connect(projection.apply)
                    self.toolbar.line_clicked.connect(self.__set_section_line)
                    self.layers[layer.id()] = projection
                    self.layertreeroot.addLayer(layer)
                    print "__add_layers", layer.name()
            if isinstance(layer, AxisLayer):
                self.layertreeroot.addLayer(layer)
                self.axis_layer = layer


    def __map_tool_changed(self, map_tool):
        if isinstance(map_tool, QgsMapToolPan):
            self.tool = QgsMapToolPan(self.canvas)
            self.canvas.setMapTool(self.tool)
        elif isinstance(map_tool, QgsMapToolZoom):
            self.tool = QgsMapToolZoom(self.canvas, map_tool.action().text().find(u"+") == -1)
            self.canvas.setMapTool(self.tool)
        elif isinstance(map_tool, LineSelectTool):
            print 'line select tool'
            pass
        else:
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

        QgsPluginLayerRegistry.instance().removePluginLayerType(AxisLayer.LAYER_TYPE)

    def __cleanup(self):
        if self.highlighter is not None:
            self.iface.mapCanvas().scene().removeItem(self.highlighter)
            self.iface.mapCanvas().refresh()
            self.highlighter = None

    def __set_section_line(self, line_wkt, width):
        print "SelecteD", line_wkt
        line = None
        self.__cleanup()

        self.line = QgsGeometry.fromWkt(line_wkt)
        self.highlighter = QgsRubberBand(self.iface.mapCanvas(), QGis.Line)
        self.highlighter.addGeometry(self.line, None)
        self.highlighter.setWidth(width/self.iface.mapCanvas().getCoordinateTransform().mapUnitsPerPixel())
        color = QColor(255, 0, 0, 128)
        self.highlighter.setColor(color)
        #self.canvas.zoomToFullExtent()
        if not len(self.canvas.layers()):
            return
        min_z = min((layer.extent().yMinimum() for layer in self.canvas.layers()))
        max_z = max((layer.extent().yMaximum() for layer in self.canvas.layers()))
        print "z-range", min_z, max_z
        self.canvas.setExtent(QgsRectangle(0, min_z, self.line.length(), max_z))
        self.canvas.refresh()

    def extents_changed(self):
        if self.line is None:
            return
        ext = self.canvas.extent()

        # section visibility bounds
        start = max(0, ext.xMinimum())
        end = start + min(self.line.length(), ext.width())

        vertices = [self.line.interpolate(start).asPoint()]
        vertex_count = len(self.line.asPolyline())
        distance = 0

        for i in range(1, vertex_count):
            vertex_i = self.line.vertexAt(i)
            distance += sqrt(self.line.sqrDistToVertexAt(vertex_i, i-1))
            # 2.16 distance = self.line.distanceToVertex(i)

            if distance <= start:
                pass
            elif distance < end:
                vertices += [vertex_i]
            else:
                break

        vertices += [self.line.interpolate(end).asPoint()]

        self.highlighter.reset()
        self.highlighter.addGeometry(
            QgsGeometry.fromPolyline(vertices),
            None)



