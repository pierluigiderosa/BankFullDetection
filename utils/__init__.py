from PyQt4.QtGui import QMessageBox
from qgis.core import *

def log(msg):
    logger = QgsMessageLog.instance()
    logger.logMessage(msg,'Bankfull')
    
def message(msg,parent=None):
    QMessageBox.information(parent, "Bankfull", msg)
    
def get_loaded_layers(iface):
        availableLayers = {"vectorLine" : [], "raster" : []}
        loadedLayers = iface.legendInterface().layers()
        for layerObj in loadedLayers:
            layerType = layerObj.type()
            if layerType == 0:
                if layerObj.geometryType() == 1: # it's a line
                    availableLayers["vectorLine"].append(layerObj)
            elif layerType == 1: # it's a raster layer
                availableLayers["raster"].append(layerObj)
        return availableLayers

 
class MemoryLayer(object):
    def __init__(self,name,geomtype,crs=None):
        self.geomtype=geomtype
        if crs:
            self.geomtype+'?crs='+crs.lower()
        self.name = name
        self.layer =  QgsVectorLayer(self.geomtype, self.name , "memory")
        self.pr = self.layer.dataProvider()
        
    def add_point(self,point):
        self.seg = QgsFeature()
        self.seg.setGeometry(QgsGeometry.fromPoint(point))
        self.pr.addFeatures([self.seg])
        self.layer.updateExtents()
        
    def add_line(self, point1,point2):
        self.seg = QgsFeature()
        self.seg.setGeometry(QgsGeometry.fromPolyline([point1,point2]))
        self.pr.addFeatures( [self.seg] )
        self.layer.updateExtents()
        
    def add_poly(self,points):
        self.seg = QgsFeature()  
        self.seg.setGeometry(QgsGeometry.fromPolygon([points]))
        self.pr.addFeatures( [self.seg] )
        self.layer.updateExtents()
    
    def loadme(self):
        QgsMapLayerRegistry.instance().addMapLayers([self.layer])