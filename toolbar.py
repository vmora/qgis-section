# coding=utf-8

from qgis.core import * # unable to import QgsWKBTypes otherwize (quid?)
from qgis.gui import *

from PyQt4.QtCore import pyqtSignal
from PyQt4.QtGui import QToolBar, QLineEdit, QLabel, QIcon

from shapely.geometry import LineString
import os

from .axis_layer import AxisLayer
from .section_tools import LineSelectTool

class Toolbar(QToolBar):
    line_clicked = pyqtSignal(str, float)
    z_autoscale_clicked = pyqtSignal()
    projected_layer_created = pyqtSignal(QgsVectorLayer, QgsVectorLayer)

    def __init__(self, iface, section_id, iface_canvas, section_canvas):
        QToolBar.__init__(self)
        self.__iface = iface
        self.__iface_canvas = iface_canvas
        self.__section_canvas = section_canvas
        self.__section_id = section_id

        icon = lambda name: QIcon(os.path.join(os.path.dirname(__file__), name))

        self.addAction('axis').triggered.connect(self.__add_axis)

        self.addAction(icon('add_layer.svg'), 'add projected layer').triggered.connect(self.__add_layer)
        self.selectLineAction = self.addAction(icon('select_line.svg'), 'select line')
        self.selectLineAction.setCheckable(True)
        self.selectLineAction.triggered.connect(self.__pick_section_line)

        self.buffer_width = QLineEdit("100")
        self.buffer_width.setMaximumWidth(50)
        self.addWidget(QLabel("Width:"))
        self.addWidget(self.buffer_width)

        self.z_autoscale = self.addAction(icon('autoscale.svg'), 'autoscale')
        self.z_autoscale.triggered.connect(self.z_autoscale_clicked.emit)

        self.__tool = None
        self.__old_tool = None
        self.__bridge = None

    def unload(self):
        self.__iface = None
        if self.__iface_canvas.mapTool() == self.__tool:
            self.__iface_canvas.unsetMapTool(self.__tool)
        self.__bridge = None

    def __pick_section_line(self):
        print "set_section_line"
        if not self.selectLineAction.isChecked():
            if self.__iface_canvas.mapTool() == self.__tool:
                self.__iface_canvas.unsetMapTool(self.__tool)
            self.__tool = None
        else:
            self.__tool = LineSelectTool(self.__iface_canvas)
            self.__tool.line_clicked.connect(self.__line_clicked)
            self.__iface_canvas.setMapTool(self.__tool)

    def __line_clicked(self, wkt_):
        self.selectLineAction.setChecked(False)
        self.__iface_canvas.unsetMapTool(self.__tool)
        self.line_clicked.emit(wkt_, float(self.buffer_width.text()))
        group = self.__iface.layerTreeView().layerTreeModel().rootGroup().findGroup(self.__section_id)
        if group:
            self.__bridge = QgsLayerTreeMapCanvasBridge(group, self.__section_canvas)
        else:
            self.__bridge = None

    def __add_layer(self):
        print "add layer"
        layer = self.__iface_canvas.currentLayer()

        if layer is None:
            return
        section = QgsVectorLayer(
            "{geomType}?crs={crs}&index=yes".format(
                geomType={
                    QGis.Point:"Point",
                    QGis.Line:"LineString",
                    QGis.Polygon:"Polygon"
                    }[layer.geometryType()],
                crs=self.__iface_canvas.mapSettings().destinationCrs().authid()
                ), layer.name(), "memory")
        section.setCustomProperty("section_id", self.__section_id)
        section.setCustomProperty("projected_layer", layer.id())

        # cpy attributes structure
        section.dataProvider().addAttributes([layer.fields().field(f) for f in range(layer.fields().count())])
        section.updateFields()

        # cpy style
        section.setRendererV2(layer.rendererV2().clone())
        QgsMapLayerRegistry.instance().addMapLayer(section, False)

        # Add to section group
        group = self.__iface.layerTreeView().layerTreeModel().rootGroup().findGroup(self.__section_id)
        if group is None:
            # Add missing group
            group = self.__iface.layerTreeView().layerTreeModel().rootGroup().addGroup(self.__section_id)
            group.setCustomProperty('section_id', self.__section_id)

        if self.__bridge is None:
            # Create bridge
            self.__bridge = QgsLayerTreeMapCanvasBridge(group, self.__section_canvas)

        assert not(group is None)
        group.addLayer(section)

        self.projected_layer_created.emit(layer, section)

    def __add_axis(self):
        axislayer = AxisLayer(self.__iface_canvas.mapSettings().destinationCrs())
        QgsMapLayerRegistry.instance().addMapLayer(axislayer, False)

