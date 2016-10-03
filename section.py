# coding=utf-8

from qgis.core import * # unable to import QgsWKBTypes otherwize (quid?)


from PyQt4.QtCore import QObject, pyqtSignal

from shapely.geometry import Point, LineString
from shapely.wkt import loads
from shapely.ops import transform

from .helpers import projected_layer_to_original
from .layer import Layer

class Section(QObject):

    changed = pyqtSignal(str, float)

    def __init__(self, id_="section", parent=None):
        QObject.__init__(self, parent)
        self.__line = None
        self.__id = id_
        self.__width = 0
        self.__projections = {}
        self.__layer_tree_root = QgsLayerTreeGroup()
        self.__layer_tree_model = QgsLayerTreeModel(self.__layer_tree_root)
        self.__layer_tree_model.setFlag(QgsLayerTreeModel.AllowNodeChangeVisibility, True)
        self.__layer_tree_model.setFlag(QgsLayerTreeModel.AllowLegendChangeState, True)
        self.__layer_tree_model.setFlag(QgsLayerTreeModel.AllowNodeReorder, True)
        self.__layer_tree_model.setFlag(QgsLayerTreeModel.AllowNodeRename, True)

        # in case of reload, or if a project is already opend with layers
        # that belong to this section
        self.__add_layers(QgsMapLayerRegistry.instance().mapLayers().values())

        # for project loading
        QgsMapLayerRegistry.instance().layersAdded.connect(self.__add_layers)
        QgsMapLayerRegistry.instance().layersWillBeRemoved.connect(self.__remove_layers)

    def update(self, wkt_line, width = 0):
        try:
            self.__line = loads(wkt_line.replace("Z", " Z"))
            self.__width = width
        except Exception, e:
            self.__line = None

        for sourceId in self.__projections:
            self.update_projections(sourceId)

        self.changed.emit(wkt_line, width)

    def project(self, qgs_geometry):
        """returns a transformed geometry"""
        #@todo use wkb to optimize ?
        geom = loads(qgs_geometry.exportToWkt().replace("Z", " Z"))
        return QgsGeometry.fromWkt(
                transform(
                    lambda x,y,z: self.project_point(x, y, z),
                    geom).wkt)

    def project_point(self, x, y, z):
        # project a 3d point
        return (self.__line.project(Point(x, y)), z, 0)

    def register_projection_layer(self, projection):
        sourceId = projection.source_layer.id()
        if not sourceId in self.__projections:
            self.__projections[sourceId] = {
                'needs_update_fn': lambda : self.update_projections(sourceId),
                'layers': []
            }
            # setup update logic
            projection.source_layer.featureAdded.connect(self.__projections[sourceId]['needs_update_fn'])
            projection.source_layer.editCommandEnded.connect(self.__projections[sourceId]['needs_update_fn'])

        self.__projections[sourceId]['layers'] += [projection]
        self.changed.emit(self.__line.wkt if self.__line else None, self.__width)

    def update_projections(self, sourceId):
        for p in self.__projections[sourceId]['layers']:
            p.apply(self)

    def unregister_projected_layer(self, layerId):
        for sourceId in self.__projections:
            sourceLayer = QgsMapLayerRegistry.instance().mapLayer(sourceId)

            # removal of source layer
            if sourceId == layerId:
                sourceLayer.featureAdded.disconnect(self.__projections[sourceId]['needs_update_fn'])
                sourceLayer.editCommandEnded.disconnect(self.__projections[sourceId]['needs_update_fn'])
                projection_removed = []

                for p in self.__projections[sourceId]['layers']:
                    projection_removed += [ p.projected_layer ]

                del self.__projections[sourceId]
                return projection_removed

            else:
                projections = self.__projections[sourceId]['layers']
                for p in projections:
                    if p.projected_layer.id() == layerId:
                        projection_removed = [ p.projected_layer ]

                        self.__projections[sourceId]['layers'] = [p for p in projections if p.projected_layer.id() != layerId]
                        if len(self.__projections[sourceId]['layers']) == 0:
                            sourceLayer.featureAdded.disconnect(self.__projections[sourceId]['needs_update_fn'])
                            sourceLayer.editCommandEnded.disconnect(self.__projections[sourceId]['needs_update_fn'])
                            del self.__projections[sourceId]

                        return projection_removed
        return []

    # Maintain section TreeView state
    def __add_layers(self, layers):
        for layer in layers:
            if hasattr(layer, 'customProperty') \
                    and layer.customProperty("section_id") is not None \
                    and layer.customProperty("section_id") == self.__id :
                source_layer = projected_layer_to_original(layer)
                if source_layer is not None:
                    print "add {}/{} to section tree view".format(source_layer.id(), layer.id())
                    self.__layer_tree_root.addLayer(layer)
                    self.register_projection_layer(Layer(source_layer, layer))

    def __remove_layers(self, layer_ids):
        for layer_id in layer_ids:
            projected_layers = self.unregister_projected_layer(layer_id)
            for p in projected_layers:
                print 'remove {}/{} from section tree view'.format(layer_id, p.id())
                self.__layer_tree_root.removeLayer(p)

    def __getattr__(self, name):
        if name == "line":
            return self.__line
        elif name == "width":
            return self.__width
        elif name == "layer_tree_model":
            return self.__layer_tree_model
        elif name == "id":
            return self.__id
        elif name == "is_valid":
            return self.line is not None
        raise AttributeError(name)
