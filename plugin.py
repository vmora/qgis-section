# -*- coding: UTF-8 -*-

from qgis.core import * # unable to import QgsWKBTypes otherwize (quid?)
from qgis.gui import *

from PyQt4.QtCore import Qt, pyqtSignal, QVariant
from PyQt4.QtGui import QDockWidget, QToolBar, QLineEdit, QLabel

from shapely.wkt import loads
from shapely.ops import transform
from shapely.geometry import Point, LineString

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
                    if feat.geometry().intersects(rect_geom):
                        print "found line in ", layer.name()
                        self.line_clicked.emit(QgsGeometry.exportToWkt(feat.geometry()))
                        return
        # emit a small linestring in the x direction
        layerPoint = self.toMapCoordinates(event.pos())
        self.line_clicked.emit(LineString([(layerPoint.x()-radius, layerPoint.y()), (layerPoint.x()+radius, layerPoint.y())]).wkt)

class SectionTransform():
    def __init__(self, line):
        "line is a QgsGeometry"
        self.__line = loads(line.exportToWkt().replace('Z', ''))
        self.__length = self.__line.length

    def apply(self, geometry):
        "returns a transformed geometry"
        geom = loads(geometry.exportToWkt().replace('Z', ''))
        length = self.__length
        line = self.__line
        def fun(x, y, z):
            return (line.project(Point(x, y))*length, z, 0)
        return QgsGeometry.fromWkt(transform(fun, geom).wkt)


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

        self.layers = []

        canvas = QgsMapCanvas()
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
        self.cleanup()
        self.iface.removeDockWidget(self.canvas_dock)
        self.canvas_dock.setParent(None)
        self.toolbar.setParent(None)
        self.iface.mapCanvas().mapToolSet[QgsMapTool].disconnect()

    def cleanup(self):
        if self.highlighter is not None:
            self.iface.mapCanvas().scene().removeItem(self.highlighter)
            self.highlighter = None

        # remove memory layers
        self.canvas.setLayerSet([])
        for l in self.layers:
            QgsMapLayerRegistry.instance().removeMapLayer(l.id())
        self.layers = []

    def set_section_line_(self, line_wkt):
        print "SelecteD", line_wkt
        line = None
        self.cleanup()
        
        line = QgsGeometry.fromWkt(line_wkt)

        transfo = SectionTransform(line)

        width = float(self.buffer_width.text())
        buff = line.buffer(width, 4)

        self.highlighter = QgsRubberBand(self.iface.mapCanvas(), QGis.Line)
        self.highlighter.addGeometry(line, None)
        self.highlighter.setWidth(10)

        # select features from layers with Z in geometry
        for layer in self.iface.mapCanvas().layers():
            if True or QgsWKBTypes.hasZ(int(layer.wkbType())):
                # 2154 just for the fun, we don't care as long as the unit is meters
                # @todo find a better SRS and take feet properly into account 
                new_layer = QgsVectorLayer(
                        "{geomType}?crs=epsg:2154&index=yes".format(
                            geomType={QGis.Point:"Point", QGis.Line:"LineString", QGis.Polygon:"Polygon"}[layer.geometryType()]
                            ),
                        "projected_"+layer.name(),
                        "memory")
                provider = new_layer.dataProvider()
                provider.addAttributes([layer.fields().field(f) for f in range(layer.fields().count())])
                new_layer.setRendererV2(layer.rendererV2().clone())
                new_layer.updateFields()
                new_layer.beginEditCommand("project")

                features = []
                for feature in layer.getFeatures(QgsFeatureRequest(buff.boundingBox())):
                    # vertical lines and polygons are not valid, so the intersection does not seem to work
                    # we convert them to a multitype of reduced dimension (polygon -> multi line, line -> multi-point
                    inter = QgsGeometry(feature.geometry()) #.intersection(buff)
                    if not QgsWKBTypes.hasZ(int(inter.wkbType())):
                        print "no z for", layer.name()
                        break
                    if inter.type() == QGis.Line:
                        if layer.name() == 'stratigraphies':
                            print "line -> multipoint"
                        inter = QgsGeometry.fromMultiPoint(inter.asPolyline())
                    elif inter.type() == QGis.Polygon:
                        if layer.name() == 'stratigraphies':
                            print "polygon -> multiline"
                        inter = QgsGeometry.fromMultiLine(inter.asPolygon())
                    else:
                        assert False

                    if layer.name() == 'stratigraphies':
                        print inter.exportToWkt()
                        print buf.exportToWkt()
                    if inter.intersects(buff):
                        #print "added"
                        geom =  QgsGeometry(feature.geometry())
                        new_feature = QgsFeature()
                        new_feature.setGeometry(transfo.apply(geom))
                        new_feature.setAttributes(feature.attributes())
                        print new_feature.geometry().exportToWkt()
                        features.append(new_feature)
                provider.addFeatures(features)
                new_layer.endEditCommand()
                print layer.name(), len(features), new_layer.isValid()

                self.layers.append(new_layer)
                QgsMapLayerRegistry.instance().addMapLayer(new_layer, True)

        self.canvas.setLayerSet([QgsMapCanvasLayer(layer) for layer in self.layers])
        self.canvas.zoomToFullExtent()

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

