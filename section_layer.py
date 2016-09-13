# coding=utf-8

from qgis.core import * # unable to import QgsWKBTypes otherwize (quid?)

from shapely.geometry import Point, LineString
from shapely.wkt import loads
from shapely.ops import transform

def hasZ(layer):
    """test if layer has z, necessary because the wkbType returned by lyers in QGSI 2.16
    has lost the information

    note: we return True for a layer with no geometries
    """
    for feat in layer.getFeatures():
        return QgsWKBTypes.hasZ(int(feat.geometry().wkbType()))
    return True

class LayerProjection(object):
    def __init__(self, source_layer, projected_layer):
        self.source_layer = source_layer
        self.projected_layer = projected_layer
        assert hasZ(source_layer) # @todo remove this and configure attribute for z

    def apply(self, section):
        "project source features on section plnae defined by line"

        projected = self.projected_layer
        projected.dataProvider().deleteFeatures(projected.allFeatureIds())

        if not (section.isValid()):
            return None

        print "projecting ", self.source_layer.name(), self.projected_layer.geometryType()

        source = self.source_layer
        line = section.line
        features = []
        # square cap style for the buffer -> less points
        buf = line.buffer(section.width, cap_style=2)
        for feature in source.getFeatures():
            centroid = feature.geometry().boundingBox().center()
            if Point(centroid.x(), centroid.y()).intersects(buf):
                geom = feature.geometry()
                new_feature = QgsFeature(feature.id())
                p = section.project(geom)
                new_feature.setGeometry(section.project(geom))
                new_feature.setAttributes(feature.attributes())
                features.append(new_feature)

        projected.beginEditCommand('layer projection')
        projected.dataProvider().addFeatures(features)
        projected.endEditCommand()
        projected.updateExtents()
