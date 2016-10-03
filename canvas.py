# coding=utf-8

from qgis.core import * # unable to import QgsWKBTypes otherwize (quid?)
from qgis.gui import *

from PyQt4.QtCore import Qt, pyqtSignal
from PyQt4.QtGui import QMenu, QColor, QWidget

from .layer import Layer
from .toolbar import Toolbar, LineSelectTool

from .section_tools import SelectionTool

from math import sqrt


class Canvas(QgsMapCanvas):

    def __init__(self, section, iface, parent=None):
        QgsMapCanvas.__init__(self, parent)
        self.setWheelAction(QgsMapCanvas.WheelZoomToMouseCursor)
        self.setCrsTransformEnabled(False)

        self.__iface = iface
        self.__highlighter = None
        self.__section = section

        section.changed.connect(self.__define_section_line)

        self.extentsChanged.connect(self.__extents_changed)
        iface.mapCanvas().extentsChanged.connect(self.__extents_changed)

    def unload(self):
        self.__cleanup()

    def build_default_section_actions(self):
        return [
            { 'icon': QgsApplication.getThemeIcon('/mActionPan.svg'), 'label': 'pan', 'tool': QgsMapToolPan(self) },
            { 'icon': QgsApplication.getThemeIcon('/mActionZoomIn.svg'), 'label': 'zoom in', 'tool': QgsMapToolZoom(self, False) },
            { 'icon': QgsApplication.getThemeIcon('/mActionZoomOut.svg'), 'label': 'zoom out', 'tool': QgsMapToolZoom(self, True) },
            { 'icon': QgsApplication.getThemeIcon('/mActionSelect.svg'), 'label': 'select', 'tool': SelectionTool(self) }
        ]

    def add_section_actions_to_toolbar(self, actions, toolbar):
        self.section_actions = []

        for action in actions:
            if action is None:
                toolbar.addSeparator()
                continue

            act = toolbar.addAction(action['icon'], action['label'])

            if 'tool' in action:
                act.setCheckable(True)
                tl = action['tool']
                act.triggered.connect(lambda checked, tool=tl: self._setSectionCanvasTool(checked, tool))
            elif 'clicked' in action:
                act.setCheckable(False)
                act.triggered.connect(action['clicked'])

            action['action'] = act
            self.section_actions += [ action ]

    def _setSectionCanvasTool(self, checked, tool):
        if not checked:
            return

        self.setMapTool(tool)

        for action in self.section_actions:
            if 'tool' in action:
                action['action'].setChecked(tool == action['tool'])


    def __cleanup(self):
        if self.__highlighter is not None:
            self.__iface.mapCanvas().scene().removeItem(self.__highlighter)
            self.__highlighter = None
            self.__iface.mapCanvas().refresh()

    def __define_section_line(self, line_wkt, width):
        self.__cleanup()
        if not line_wkt:
            return
        self.__highlighter = QgsRubberBand(self.__iface.mapCanvas(), QGis.Line)
        self.__highlighter.addGeometry(QgsGeometry.fromWkt(line_wkt), None) # todo use section.line
        self.__highlighter.setWidth(width/self.__iface.mapCanvas().getCoordinateTransform().mapUnitsPerPixel())
        color = QColor(255, 0, 0, 128)
        self.__highlighter.setColor(color)

        if not len(self.layers()):
            return
        min_z = min((layer.extent().yMinimum() for layer in self.layers()))
        max_z = max((layer.extent().yMaximum() for layer in self.layers()))
        z_range = max_z - min_z
        print "z-range", z_range
        self.setExtent(QgsRectangle(0, min_z - z_range * 0.1, self.__section.line.length, max_z + z_range * 0.1))
        self.refresh()

    def __extents_changed(self):
        if not self.__section.is_valid:
            return

        ext = self.extent()

        line = QgsGeometry.fromWkt(self.__section.line.wkt)

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

        if self.__highlighter is not None:
            self.__highlighter.setWidth(self.__section.width/self.__iface.mapCanvas().getCoordinateTransform().mapUnitsPerPixel())

