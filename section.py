# coding=utf-8

from qgis.core import * # unable to import QgsWKBTypes otherwize (quid?)

from shapely.geometry import Point, LineString
from shapely.wkt import loads
from shapely.ops import transform


class Section(object):
    def __init__(self):
        self.line = None
        self.width = 0
        self.projectionLayers = []

    def isValid(self):
        return not(self.line is None)

    def update(self, wkt_line, width = 0):
        try:
            self.line = loads(wkt_line.replace("Z", " Z"))
            self.width = width
        except Exception, e:
            self.line = None

        for p in self.projectionLayers:
            print p.source_layer.name(), '->', p.projected_layer.name()
            p.apply(self)

    def project(self, qgs_geometry):
        """returns a transformed geometry"""
        #@todo use wkb to optimize ?
        geom = loads(qgs_geometry.exportToWkt().replace("Z", " Z"))
        return QgsGeometry.fromWkt(
                transform(
                    lambda x,y,z: self.projectPoint(x, y, z),
                    geom).wkt)

    def projectPoint(self, x, y, z):
        # project a 3d point
        return (self.line.project(Point(x, y)), z, 0)

    def registerProjectionLayer(self, projection):
        print 'registerProjectionLayer:', projection.projected_layer.name()
        self.projectionLayers += [projection]
        # setup update logic
        projection.source_layer.featureAdded.connect(lambda fid: projection.apply(self))
        projection.source_layer.editCommandEnded.connect(lambda : projection.apply(self))

    def unregisterProjectedLayer(self, layerId):
        for p in self.projectionLayers:
            if p.source_layer.id() == layerId:
                projection.source_layer.featureAdded.disconnect()
                projection.source_layer.editCommandEnded.disconnect()
        self.projectionLayers = [p for p in self.projectionLayers if p.source_layer.id() != layerId]


    def __getattr__(self, name):
        if name == "line":
            return self.line
        raise AttributeError(name)
