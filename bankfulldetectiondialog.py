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
        
        #~ connections
        #~ self.iface.clicked.connect(self.runXS)
        QObject.connect(self.genXSbtn, SIGNAL( "clicked()" ), self.genXS)


    def setup_gui(self):
        """ Function to combos creation """
        self.comboVector.clear()
        self.comboDEM.clear()
        curr_map_layers = QgsMapLayerRegistry.instance().mapLayers()
        layerRaster = []
        layerVector = []
        for name, layer in QgsMapLayerRegistry.instance().mapLayers().iteritems():
            if layer.type() == QgsMapLayer.VectorLayer:
                layerVector.append(unicode(layer.name()))
            elif layer.type() == QgsMapLayer.RasterLayer:
                layerRaster.append(unicode(layer.name()))
        self.comboDEM.addItems( layerRaster  )
        self.comboVector.addItems( layerVector )
        

    def genXS(self):
        layer=iface.mapCanvas().currentLayer()
        step=self.stepXSspin.value()
        width=self.widthXSspin.value()
        #~ message(str(step))
       
        create_points_secs(layer,step,width)
                

      
