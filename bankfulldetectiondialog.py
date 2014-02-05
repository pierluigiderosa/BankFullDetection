# -*- coding: utf-8 -*-
"""
/***************************************************************************
 BankFullDetectionDialog
                                 A QGIS plugin
 Automatic bankfull width detection
                             -------------------
        begin                : 2014-01-20
        copyright            : (C) 2014 by Pierluigi De Rosa
        email                : pierluigi.derosa@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from ui_bankfulldetection import Ui_BankFullDetection
from qgis.core import *
from tools.XSGenerator import *
from tools.profiler import ProfilerTool
from tools.BankElevationDetection import mainFun
# create the dialog for zoom to point


class BankFullDetectionDialog(QDialog, Ui_BankFullDetection):
    def __init__(self,iface):
        QDialog.__init__(self)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect

        self.setupUi(self)
        self.iface = iface
        self.setup_gui()

        self.progressBar.setValue(0)
        
        #general variables
        self.vLayer = None
        self.rLayer = None
        
        #~ connections
        #~ self.iface.clicked.connect(self.runXS)
        QObject.connect(self.genXSbtn, SIGNAL( "clicked()" ), self.genXS)
        QObject.connect(self.buttonProf, SIGNAL( "clicked()" ), self.runProfile)


    def setup_gui(self):
        """ Function to combos creation """
        self.comboVector.clear()
        self.comboDEM.clear()
        curr_map_layers = QgsMapLayerRegistry.instance().mapLayers()
        layerRasters = []
        layerVectors = []
        for name, layer in curr_map_layers.iteritems():
            if layer.type() == QgsMapLayer.VectorLayer:
                layerVectors.append(unicode(layer.name()))
            elif layer.type() == QgsMapLayer.RasterLayer:
                layerRasters.append(unicode(layer.name()))
        self.comboDEM.addItems( layerRasters  )
        self.comboVector.addItems( layerVectors )
        
    def getLayerByName(self,LayerName):
        layer = QgsMapLayerRegistry.instance().mapLayersByName(LayerName)[0]
        return layer

                
    def genXS(self):
        vectorName = self.comboVector.currentText()
        layer = self.getLayerByName(vectorName)
        step=self.stepXSspin.value()
        width=self.widthXSspin.value()
        #~ message(str(step))
        create_points_secs(layer,step,width)

                
    def runProfile(self):
        self.progressBar.show()
        
        rasterName = self.comboDEM.currentText()
        self.rLayer = self.getLayerByName(rasterName)
        XSlayer = self.getLayerByName(str(QCoreApplication.translate( "dialog","Sezioni")))
        profiler = ProfilerTool()
        profiler.setRaster( self.rLayer )
        leftPoints = []
        rightPoints = []
        ringPoints = []
        nfeats = int( XSlayer.featureCount() )
        self.progressBar.setMaximum(nfeats)
        i = 0
        self.progressBar.setValue(i)
        nVsteps = self.nVsteps.value()
        minVdep = self.minVdep.value()
        for feat in XSlayer.getFeatures():
            #~ feat = feats[0]
            geom = feat.geometry()
            profileList,e = profiler.doProfile(geom)
            startDis, endDis = mainFun(profileList,nVsteps,minVdep)
            
            StartPoint = geom.interpolate( startDis)
            EndPoint = geom.interpolate(endDis)
            
            leftPoints.append(StartPoint.asPoint() )
            rightPoints.append(EndPoint.asPoint() )
            #~ rightPoints.reverse()
            ringPoints = leftPoints+rightPoints[::-1]
            i = i +1 
            self.progressBar.setValue(i)
        
        vl = QgsVectorLayer("Polygon", "output finale", "memory")
        pr = vl.dataProvider()
        fet = QgsFeature()
        fet.setGeometry( QgsGeometry.fromPolygon( [ ringPoints ] ) )
        pr.addFeatures( [fet] )
        QgsMapLayerRegistry.instance().addMapLayer(vl)
        
        #~ QMessageBox.warning(self.iface.mainWindow(),"BankFullDetection",str(ringPoints) )
        
        #~ debugging
        #~ punto = QgsVectorLayer("Point", "output finale", "memory")
        #~ punto_prov = punto.dataProvider()
        #~ features = []
        #~ for j in ringPoints:
            #~ fet= QgsFeature()
            #~ fet.setGeometry( QgsGeometry.fromPoint( j ) )
            #~ features.append(fet)
        #~ punto_prov.addFeatures( features )
        #~ QgsMapLayerRegistry.instance().addMapLayer(punto)
        


