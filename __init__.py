# -*- coding: UTF-8 -*-

class Dummy():
    def __init__(self, iface):
        self.iface = iface
    def initGui(self):
        pass
    def unload(self):
        pass

    

def classFactory(iface):
    return Dummy(iface)

