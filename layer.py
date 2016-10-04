# coding=utf-8

from qgis.core import * # unable to import QgsWKBTypes otherwize (quid?)

from shapely.geometry import Point, LineString
from shapely.wkt import loads
from shapely.ops import transform

from .helpers import projected_feature_to_original

def hasZ(layer):
    """test if layer has z, necessary because the wkbType returned by lyers in QGSI 2.16
    has lost the information

    note: we return True for a layer with no geometries
    """
    for feat in layer.getFeatures():
        return QgsWKBTypes.hasZ(int(feat.geometry().wkbType()))
    return True

class Layer(object):
    def __init__(self, source_layer, projected_layer):
        self.source_layer = source_layer
        self.projected_layer = projected_layer
        assert hasZ(source_layer) # @todo remove this and configure attribute for z

    def apply(self, section):
        "project source features on section plnae defined by line"

        projected = self.projected_layer
        projected.dataProvider().deleteFeatures(projected.allFeatureIds())

        if not section.is_valid:
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

    def propagateChangesToSourceLayer(self, section):

        edit = self.projected_layer.editBuffer()

        if edit is None:
            return

        print "{} will commit changes".format(self.projected_layer.id())
        self.source_layer.beginEditCommand('unproject transformation')

        print edit.changedGeometries()
        for i in edit.changedGeometries():
            modified_feature = self.projected_layer.getFeatures(QgsFeatureRequest(i)).next()
            feature = projected_feature_to_original(self.source_layer, modified_feature)
            unprojected = section.unproject(edit.changedGeometries()[i])
            self.source_layer.dataProvider().changeGeometryValues({feature.id(): unprojected})

        self.source_layer.endEditCommand()
        self.source_layer.updateExtents()
