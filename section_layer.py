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

class SectionLayer(QgsVectorLayer):
    """Project layer data on the sz plane where s is the curvilinear coordinate
    on the linestring given to the constructor.
    
    The QgsVectorLayer is a memory layer"""

    def __init__(self, wkt_line, thickness, layer):
        """the line and layer must share the same coordinate system"""
        print "SectionLayer.__init__"
        assert hasZ(layer)
        # 2154 just for the fun, we don't care as long as the unit is meters
        # @todo find a better SRS and take feet properly into account 
        QgsVectorLayer.__init__(self,
            "{geomType}?crs=epsg:2154&index=yes".format(
                geomType={
                    QGis.Point:"Point", 
                    QGis.Line:"LineString", 
                    QGis.Polygon:"Polygon"
                    }[layer.geometryType()]
                ), "projected_"+layer.name(), "memory")
        self.__source_layer = layer
        print "line", wkt_line
        self.__line = loads(wkt_line.replace("Z", " Z"))
        self.__length = self.__line.length
        assert self.__length > 0
        self.__thickness = thickness



        # fetch data that are within thickness/2 of the line
        # since data can be invalid in the xy plane (e.g. a line in the z direction
        # has no length, a plygon has no surface...) the fetch does not
        # use QgsFeatureRequest
        features = []
        # square cap style for the buffer -> less points
        buf = self.__line.buffer(thickness/2, cap_style=2)
        for feature in layer.getFeatures():
            centroid = feature.geometry().boundingBox().center()
            if Point(centroid.x(), centroid.y()).intersects(buf):
                print "here"
                geom = feature.geometry()
                new_feature = QgsFeature()
                new_feature.setGeometry(self.__project(geom))
                new_feature.setAttributes(feature.attributes())
                features.append(new_feature)
                
        provider = self.dataProvider()
        # cpy attributes structure
        provider.addAttributes([layer.fields().field(f) for f in range(layer.fields().count())])
        self.updateFields()
        # put computed feaures in there
        self.beginEditCommand("project")
        provider.addFeatures(features)
        self.endEditCommand()
            
        # cpy source layer style
        self.setRendererV2(layer.rendererV2().clone())
        
        #self.setLabeling(layer.labeling()) not available in python


    def __project(self, qgs_geometry):
        """returns a transformed geometry"""
        #@todo use wkb to optimize ?
        geom = loads(qgs_geometry.exportToWkt().replace('Z', ''))
        length = self.__length
        line = self.__line
        def fun(x, y, z):
            return (line.project(Point(x, y))*length, z, 0)
        return QgsGeometry.fromWkt(transform(fun, geom).wkt)
    
    def writeXml(self, layer_node, doc):
        ret = QgsVectorLayer.writeXml(self, layer_node, doc)
        layer_node.toElement().setAttribute("source_layer", self.__source_layer.id())
        return ret



