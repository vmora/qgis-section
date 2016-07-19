# -*- coding: UTF-8 -*-

from qgis.core import QgsMapSettings
                     #QgsExpressionContext
                     #QgsExpressionContextScope
                     #QgsExpressionContextUtils

from PyQt4.QtCore import Qt
from PyQt4.QtGui import QGraphicsView, QGraphicsPixmapItem, QPixmap, QImage, QGraphicsScene

class Canvas(QGraphicsView):

    def __init__(self, parent=None):
        QGraphicsView.__init__(self, QGraphicsScene(), parent)
        self.__map = QGraphicsPixmapItem()
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.__map.setPixmap(QPixmap.fromImage(QImage('/tmp/plop.jpg')))
        self.scene().addItem(self.__map)

        self.__refresh_scheduled = False
        #self.__expression_context_scope = QgsExpressionContextScope("Section Canvas")
        self.__settings = QgsMapSettings()

    # void setMagnificationFactor( double factor );
    # double magnificationFactor() const;


    # void setLayerSet( QList<QgsMapCanvasLayer>& layers );
    # void setCurrentLayer( QgsMapLayer* layer );
    # void updateOverview();
    # void enableOverviewMode( QgsMapOverviewCanvas* overview );
    # const QgsMapSettings& mapSettings() const;


    # void refreshAllLayers();

    # double scale();

    # double mapUnitsPerPixel() const;

    # QgsRectangle extent() const; # ligne support (linestring), largeur (de recup des données) + 2 ordonnees min/max sur la courbe
    # QgsRectangle fullExtent() const;
    # void setExtent( const QgsRectangle &r, bool magnified = false );

    # void setCenter( const QgsPoint& center );
    # QgsPoint center() const;

    # void zoomToFullExtent();
    # void zoomToPreviousExtent(); #plus tard
    # void zoomToNextExtent();#plus tard
    # void clearExtentHistory();#plus tard

    # void zoomToSelected( QgsVectorLayer* layer = nullptr );
    # void zoomToFeatureIds( QgsVectorLayer* layer, const QgsFeatureIds& ids );#plus tard
    # void panToSelected( QgsVectorLayer* layer = nullptr );
    # void setMapTool( QgsMapTool* mapTool );# ? pê
    # void unsetMapTool( QgsMapTool* mapTool );# ? pê
    # QgsMapTool* mapTool();# ? pê

    # virtual void setCanvasColor( const QColor & _newVal );#plus tard
    # virtual QColor canvasColor() const;#plus tard

    # void setSelectionColor( const QColor& color );#plus tard

    # QgsMapLayer *layer( int index );
    # int layerCount() const;
    # QList<QgsMapLayer*> layers() const;

    # void setMapUnits( QGis::UnitType mapUnits );
    # QGis::UnitType mapUnits() const;

    # const QgsMapToPixel* getCoordinateTransform();

    # bool isDrawing();

    # QgsMapLayer* currentLayer();

    # void setWheelFactor( double factor );
    # void zoomScale( double scale ); # plus tard
    # void zoomByFactor( double scaleFactor, const QgsPoint *center = nullptr );
    # void zoomWithCenter( int x, int y, bool zoomIn );

    # QgsSnappingUtils* snappingUtils() const;
    # void setSnappingUtils( QgsSnappingUtils* utils );

    # void setExpressionContextScope( const QgsExpressionContextScope& scope ) { mExpressionContextScope = scope; }
    # QgsExpressionContextScope& expressionContextScope() { return mExpressionContextScope; }
    # const QgsExpressionContextScope& expressionContextScope() const { return mExpressionContextScope; }

    def refresh(self):
        if self.__refresh_scheduled:
            return
        self.__refresh_scheduled = True
        QTimer.singleShot(self.__refresh_map)

    def __refresh_map(self):
        self.stopRendering()
        self.__refresh_scheduled = False
        #expression_context = QgsExpressionContext()
        #expressionContext << QgsExpressionContextUtils.globalScope() \
        #    << QgsExpressionContextUtils.projectScope() \
        #    << QgsExpressionContextUtils.mapSettingsScope(self.__settings) \
        #    << QgsExpressionContextScope(self.__expression_context_scope)
        
        

    # void selectionChangedSlot();
    # void saveAsImage( const QString& theFileName, QPixmap * QPixmap = nullptr, const QString& = "PNG" );
    # void layerStateChange();
    # void setRenderFlag( bool theFlag );
    # bool renderFlag() {return mRenderFlag;}
    # void stopRendering();

    # void readProject( const QDomDocument & );
    # void writeProject( QDomDocument & );
