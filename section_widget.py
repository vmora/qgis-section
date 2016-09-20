# coding=utf-8

from qgis.core import * # unable to import QgsWKBTypes otherwize (quid?)
from qgis.gui import *

from PyQt4.QtCore import Qt, pyqtSignal
from PyQt4.QtGui import QDockWidget, QMenu, QColor

from .section_layer import LayerProjection
from .toolbar import SectionToolbar, LineSelectTool
from .axis_layer import AxisLayer, AxisLayerType
from .section import Section

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

class SectionWidget(object):
    def canvas(self):
        return self._canvas

    def toolbar(self):
        return self._toolbar

    def section_layers_tree(self):
        return self.layertreeview

    def section(self):
        return self._section

    def __init__(self, iface):
        self.iface = iface

        self.line = None

        self._toolbar = SectionToolbar(iface.mapCanvas())
        # self.iface.addToolBar(self._toolbar)
        self._toolbar.line_clicked.connect(self.__define_section_line)

        self.axis_layer = None

        canvas = QgsMapCanvas()
        canvas.setWheelAction(QgsMapCanvas.WheelZoomToMouseCursor)
        canvas.setCrsTransformEnabled(False)

        self._section = Section()

        self._canvas = canvas
        self._canvas.extentsChanged.connect(self.extents_changed)

        # tool synchro
        self.tool = None
        self.__map_tool_changed(iface.mapCanvas().mapTool())
        iface.mapCanvas().mapToolSet.connect(self.__map_tool_changed)

        # project layer synchro
        QgsMapLayerRegistry.instance().layersWillBeRemoved.connect(self.__remove_layers)
        QgsMapLayerRegistry.instance().layersAdded.connect(self.__add_layers)

        self.highlighter = None

        self.layertreeroot = QgsLayerTreeGroup()
        self.layertreeview = QgsLayerTreeView()
        self.layertreemodel = QgsLayerTreeModel(self.layertreeroot)
        self.layertreeview.setModel(self.layertreemodel)
        self.layertreeview.doubleClicked.connect(self.__open_layer_props)
        self.layertreeview.setMenuProvider(ContextMenu(self))

        self.bridge = QgsLayerTreeMapCanvasBridge(self.layertreeroot, self._canvas)
        self.layertreeview.currentLayerChanged.connect(self._canvas.setCurrentLayer)
        self.layertreemodel.setFlag(QgsLayerTreeModel.AllowNodeChangeVisibility, True)
        self.layertreemodel.setFlag(QgsLayerTreeModel.AllowLegendChangeState, True)
        self.layertreemodel.setFlag(QgsLayerTreeModel.AllowNodeReorder, True)
        self.layertreemodel.setFlag(QgsLayerTreeModel.AllowNodeRename, True)

        # in case we are reloading
        self.__add_layers(QgsMapLayerRegistry.instance().mapLayers().values())

        self.axis_layer_type = AxisLayerType()
        QgsPluginLayerRegistry.instance().addPluginLayerType(self.axis_layer_type)

        #self.iface.actionZoomFullExtent().triggered.connect(self._canvas.zoomToFullExtent)
        #self.iface.actionZoomToLayer().triggered.connect(lambda x:
        #        self._canvas.setExtent(self._canvas.currentLayer().extent()))
        iface.actionToggleEditing().triggered.connect(self.__toggle_edit)

        iface.mapCanvas().currentLayerChanged.connect(self.__current_layer_changed)


    def cleanup(self):
        self._canvas.extentsChanged.disconnect(self.extents_changed)
        self._toolbar.line_clicked.disconnect(self.__define_section_line)
        self.iface.actionToggleEditing().triggered.disconnect(self.__toggle_edit)
        self.layertreeview.currentLayerChanged.disconnect(self._canvas.setCurrentLayer)
        self.iface.mapCanvas().currentLayerChanged.disconnect(self.__current_layer_changed)
        self.iface.mapCanvas().mapToolSet[QgsMapTool].disconnect(self.__map_tool_changed)
        self.__cleanup()

        QgsMapLayerRegistry.instance().layersWillBeRemoved.disconnect(self.__remove_layers)
        QgsMapLayerRegistry.instance().layersAdded.disconnect(self.__add_layers)

        QgsPluginLayerRegistry.instance().removePluginLayerType(AxisLayer.LAYER_TYPE)
        self._canvas.clear()


    def __current_layer_changed(self, layer):
        if layer is None:
            self.layertreeview.setCurrentLayer(None)
        else:
            for l in self._canvas.layers():
                if l.customProperty("projected_layer") == layer.id():
                    self.layertreeview.setCurrentLayer(l)

    def __toggle_edit(self):
        currentLayer = self._canvas.currentLayer()
        if currentLayer is None:
            pass
        elif currentLayer.isEditable():
            currentLayer.rollBack()
        else:
            currentLayer.startEditing()

    def __open_layer_props(self):
        print "currentLayer", self._canvas.currentLayer(), self.layertreeview.currentNode()
        self.iface.showLayerProperties(self._canvas.currentLayer())

    def remove_current_layer(self):
        layer = self._canvas.currentLayer()
        if layer is not None:
            QgsMapLayerRegistry.instance().removeMapLayer(layer.id())

    def __remove_layers(self, layer_ids):
        for layer_id in layer_ids:
            print 'remove ', layer_id
            if self.axis_layer is not None and layer_id == self.axis_layer.id():
                self.layertreeroot.removeLayer(self.axis_layer)
                self.axis_layer = None
            else:
                projected_layers = self._section.unregisterProjectedLayer(layer_id)
                for p in projected_layers:
                    self.layertreeroot.removeLayer(p)

    def __add_layers(self, layers):
        for layer in layers:
            print "adding layer", layer.name()
            if layer.customProperty("projected_layer") is not None:
                source_layer = QgsMapLayerRegistry.instance().mapLayer(
                        layer.customProperty("projected_layer"))
                if source_layer is not None:
                    self.layertreeroot.addLayer(layer)
                    self._section.registerProjectionLayer(LayerProjection(source_layer, layer))
            if isinstance(layer, AxisLayer):
                self.layertreeroot.addLayer(layer)
                self.axis_layer = layer

    def __map_tool_changed(self, map_tool):
        print '_maptoolchanged'

        self._toolbar.selectLineAction.setChecked(isinstance(map_tool, LineSelectTool))

    def __cleanup(self):
        if self.highlighter is not None:
            self.iface.mapCanvas().scene().removeItem(self.highlighter)
            self.iface.mapCanvas().refresh()
            self.highlighter = None
        self._section.update(None)

    def __define_section_line(self, line_wkt, width):
        print "Selected section line", line_wkt
        self.__cleanup()

        self._section.update(line_wkt, width)

        self.highlighter = QgsRubberBand(self.iface.mapCanvas(), QGis.Line)
        self.highlighter.addGeometry(QgsGeometry.fromWkt(self._section.line.wkt), None) # todo use section.line
        self.highlighter.setWidth(width/self.iface.mapCanvas().getCoordinateTransform().mapUnitsPerPixel())
        color = QColor(255, 0, 0, 128)
        self.highlighter.setColor(color)

        if not len(self._canvas.layers()):
            return
        min_z = min((layer.extent().yMinimum() for layer in self._canvas.layers()))
        max_z = max((layer.extent().yMaximum() for layer in self._canvas.layers()))
        z_range = max_z - min_z
        print "z-range", z_range
        self._canvas.setExtent(QgsRectangle(0, min_z - z_range * 0.1, self._section.line.length, max_z + z_range * 0.1))
        self._canvas.refresh()

    def extents_changed(self):
        if not self._section.isValid():
            return

        ext = self._canvas.extent()

        line = QgsGeometry.fromWkt(self._section.line.wkt)

        # section visibility bounds
        start = max(0, ext.xMinimum())
        end = start + min(line.length(), ext.width())

        vertices = [line.interpolate(start).asPoint()]
        vertex_count = len(line.asPolyline())
        distance = 0

        for i in range(1, vertex_count):
            vertex_i = line.vertexAt(i)
            distance += sqrt(line.sqrDistToVertexAt(vertex_i, i-1))
            # 2.16 distance = line.distanceToVertex(i)

            if distance <= start:
                pass
            elif distance < end:
                vertices += [vertex_i]
            else:
                break

        vertices += [line.interpolate(end).asPoint()]

        self.highlighter.reset()
        self.highlighter.addGeometry(
            QgsGeometry.fromPolyline(vertices),
            None)
