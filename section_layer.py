# coding=utf-8

from qgis.core import * # unable to import QgsWKBTypes otherwize (quid?)

from shapely.geometry import Point, LineString
from shapely.wkt import loads
from shapely.ops import transform

def hasZ(layer):
    """test if layer has z, necessary because the wkbType returned by lyers in QGSI 2.16
    has lost the information

    note: we return False for a layer with no geometries
    """
    for feat in layer.getFeatures():
        return QgsWKBTypes.hasZ(int(feat.geometry().wkbType()))
    return False

class LayerProjection(object):
    def __init__(self, source_layer, projected_layer):
        self.__source_layer = source_layer
        self.projected_layer = projected_layer
        assert hasZ(source_layer) # @todo remove this and configure attribute for z

    def apply(self, wkt_line, width):
        "project source features on section plnae defined by line"
        print "projecting ", self.__source_layer.name()

        def project(line, qgs_geometry):
            """returns a transformed geometry"""
            #@todo use wkb to optimize ?
            geom = loads(qgs_geometry.exportToWkt().replace('Z', ' Z'))
            return QgsGeometry.fromWkt(
                    transform(
                        lambda x,y,z: (line.project(Point(x, y)), z, 0), 
                        geom).wkt)

        source = self.__source_layer
        line = loads(wkt_line.replace("Z", " Z"))
        features = []
        # square cap style for the buffer -> less points
        buf = line.buffer(width, cap_style=2)
        for feature in source.getFeatures():
            centroid = feature.geometry().boundingBox().center()
            if Point(centroid.x(), centroid.y()).intersects(buf):
                geom = feature.geometry()
                new_feature = QgsFeature()
                new_feature.setGeometry(project(line, geom))
                new_feature.setAttributes(feature.attributes())
                features.append(new_feature)

        projected = self.projected_layer
        projected.dataProvider().deleteFeatures(projected.allFeatureIds())
        projected.beginEditCommand('layer projection')
        projected.dataProvider().addFeatures(features)
        projected.endEditCommand()


