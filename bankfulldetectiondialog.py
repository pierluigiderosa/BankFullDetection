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

import os
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from ui_bankfulldetection import Ui_BankFullDetection
from qgis.core import *
from tools.XSGenerator import *
from tools.profiler import ProfilerTool
from tools.BankElevationDetection import mainFun


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
        self.ShpFileFolder = None
        self.vlName = None
        
        #~ connections
        #~ self.iface.clicked.connect(self.runXS)
        QObject.connect(self.genXSbtn, SIGNAL( "clicked()" ), self.genXS)
        QObject.connect(self.buttonProf, SIGNAL( "clicked()" ), self.runProfile)
        QObject.connect(self.ShpSaveBtn, SIGNAL( "clicked()" ), self.writeLayer)
        QObject.connect(self.selXS, SIGNAL( "clicked()" ), self.runProfileXS)


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
            self.iface.mainWindow().statusBar().showMessage( "Elaboro la sez "+str(i) )
            startDis, endDis = mainFun(profileList,nVsteps,minVdep,Graph=0)
            
            StartPoint = geom.interpolate( startDis)
            EndPoint = geom.interpolate(endDis)
            
            leftPoints.append(StartPoint.asPoint() )
            rightPoints.append(EndPoint.asPoint() )
            #~ rightPoints reversing
            ringPoints = leftPoints+rightPoints[::-1]
            i = i +1 
            self.progressBar.setValue(i)
        
        vl = QgsVectorLayer("Polygon", self.vlName, "memory")
        pr = vl.dataProvider()
        fet = QgsFeature()
        fet.setGeometry( QgsGeometry.fromPolygon( [ ringPoints ] ) )
        pr.addFeatures( [fet] )
        QgsMapLayerRegistry.instance().addMapLayer(vl)
        
        #check if output file is selected
        shapefilename = self.ShpSaveLine.text()
        if shapefilename == None:
            QMessageBox.critical(self.iface.mainWindow(),QCoreApplication.translate( "message","Error"), QCoreApplication.translate( "message","You have to select output file first"))
        else:
            #~ save vector layer to shapefile
            error = QgsVectorFileWriter.writeAsVectorFormat(vl, shapefilename, "CP1250", None, "ESRI Shapefile")
            if error == QgsVectorFileWriter.NoError:
                QMessageBox.information( self.iface.mainWindow(),"Info",
                str("File %s " %(str(unicode(vl.name())).upper())) + QCoreApplication.translate( "message","succesfully saved"))
        

        
    def writeLayer(self):
        fileName = QFileDialog.getSaveFileName(self, 'Save file', 
                                        "", "Shapefile (*.shp);;All files (*)")
        fileName = os.path.splitext(str(fileName))[0]+'.shp'
        self.ShpSaveLine.setText(fileName)
        base=os.path.basename(fileName)
        os.path.splitext(base)
        self.vlName = os.path.splitext(base)[0]
        
    def runProfileXS(self):
        from matplotlib.backends.backend_qt4agg import NavigationToolbar2QTAgg as NavigationToolbar

        #~ take input parameters fron GUI
        rasterName = self.comboDEM.currentText()
        self.rLayer = self.getLayerByName(rasterName)
        nVsteps = self.nVsteps.value()
        minVdep = self.minVdep.value()
        profiler = ProfilerTool()
        profiler.setRaster( self.rLayer )
        layer = self.iface.activeLayer()
        if layer.selectedFeatureCount() == 1:
            feat = layer.selectedFeatures()[0]
            geomSinXS = feat.geometry()
            profileList,e = profiler.doProfile(geomSinXS)
            canvasPlot = mainFun(profileList,nVsteps,minVdep,Graph=1)
            self.clearLayout(self.layout_plot)
            toolbar = NavigationToolbar(canvasPlot,self.layout_plot.widget())
            #~ self.layout_plot.insertWidget(0, canvasPlot )
            self.layout_plot.addWidget( canvasPlot )
            self.layout_plot.addWidget( toolbar )
            #~ self.setLayout( self.layout_plot)
            
        else:
            QMessageBox.information( self.iface.mainWindow(),"Info",
            str('select feature for ' + str( unicode(layer.name().upper() ) ) ) )
    
    def clearLayout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.clearLayout(item.layout())
