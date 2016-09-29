# coding=utf-8

from qgis.core import *
from qgis.gui import *


def projected_layer_to_original(layer):
    return None if layer is None else QgsMapLayerRegistry.instance().mapLayer(layer.customProperty("projected_layer"))

def projected_feature_to_original(source_layer, feature):
    # needed so we can use attribute(name)
    feature.setFields(source_layer.fields(), False)
    source_id = feature.attribute("id")

    it = source_layer.getFeatures(
            QgsFeatureRequest().setFilterExpression ( u'"id" = {0}'.format(source_id)))
    return it.next()


