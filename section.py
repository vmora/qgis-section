# coding=utf-8

from qgis.core import * # unable to import QgsWKBTypes otherwize (quid?)

from shapely.geometry import Point, LineString
from shapely.wkt import loads
from shapely.ops import transform


class Section(object):
    def __init__(self):
        self.line = None
        self.width = 0
        self.projectionLayers = {}

    def isValid(self):
        return not(self.line is None)

    def update(self, wkt_line, width = 0):
        try:
            self.line = loads(wkt_line.replace("Z", " Z"))
            self.width = width
        except Exception, e:
            self.line = None

        for sourceId in self.projectionLayers:
            self.updateProjections(sourceId)

            for p in self.projectionLayers[sourceId]:
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
        sourceId = projection.source_layer.id()
        if not sourceId in self.projectionLayers:
            self.projectionLayers[sourceId] = []
            # setup update logic
            projection.source_layer.featureAdded.connect(lambda fid: self.updateProjections(sourceId))
            projection.source_layer.editCommandEnded.connect(lambda : self.updateProjections(sourceId))

        self.projectionLayers[sourceId] += [projection]

    def updateProjections(self, sourceId):
        for p in self.projectionLayers[sourceId]:
            p.apply(self)

    def unregisterProjectedLayer(self, layerId):

        for sourceId in self.projectionLayers:
            sourceLayer = self.projectionLayers[sourceId][0].source_layer

            # removal of source layer
            if sourceId == layerId:
                sourceLayer.featureAdded.disconnect()
                sourceLayer.editCommandEnded.disconnect()
                projection_removed = []

                for p in self.projectionLayers[sourceId]:
                    projection_removed += [ p.projected_layer ]

                del self.projectionLayers[sourceId]
                return projection_removed

            else:
                projections = self.projectionLayers[sourceId]
                for p in projections:
                    if p.projected_layer.id() == layerId:
                        projection_removed = [ p.projected_layer ]

                        self.projectionLayers[sourceId] = [p for p in projections if p.projected_layer.id() != layerId]
                        if len(self.projectionLayers[sourceId]) == 0:
                            sourceLayer.featureAdded.disconnect()
                            sourceLayer.editCommandEnded.disconnect()
                            del self.projectionLayers[sourceId]

                        return projection_removed

        return []

    def __getattr__(self, name):
        if name == "line":
            return self.line
        raise AttributeError(name)
