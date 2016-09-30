# coding=utf-8

from qgis.gui import *

from .helpers import projected_layer_to_original

class ContextMenu(QgsLayerTreeViewMenuProvider):
    def __init__(self, tree_view):
        QgsLayerTreeViewMenuProvider.__init__(self)
        self.__tree_view = tree_view

    def createContextMenu(self):
        menu = QMenu()
        menu.addAction('&Remove').triggered.connect(self.__remove_current_layer)
        menu.addAction('&Properties').triggered.connect(self.open_layer_props)
        return menu

    def __remove_current_layer(self):
        layer = self.__tree_view.currentLayer()
        if layer is not None:
            QgsMapLayerRegistry.instance().removeMapLayer(layer.id())

    def open_layer_props(self):
        QgsVectorLayerProperties(self._canvas.currentLayer(), self).__exec()

class TreeView(QgsLayerTreeView):
    def __init__(self, section, canvas):
        QgsLayerTreeView.__init__(self)
        self.setModel(section.layer_tree_model)
        self.__context_menu = ContextMenu(self)
        self.setMenuProvider(self.__context_menu)
        self.doubleClicked.connect(self.__context_menu.open_layer_props)
        self.__bridge = QgsLayerTreeMapCanvasBridge(section.layer_tree_model.rootGroup(), canvas)
        #self.currentLayerChanged.connect(canvas.setCurrentLayer)

