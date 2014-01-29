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
from qgis.core import (QgsFeature, QgsGeometry,
                        QgsVectorLayer, QgsMapLayerRegistry,
                        QgsField)
from PyQt4.QtCore import QVariant
from qgis.utils import iface
import numpy as np
from BankFullDetection.utils import *
from BankFullDetection.utils.geometry import  *

def createPointsAt(distance, geom):
    length = geom.length()
    currentdistance = distance
    feats = []

    while currentdistance < length:
        # Get a point along the line at the current distance
        point = geom.interpolate(currentdistance)
        # Create a new QgsFeature and assign it the new geometry
        fet = QgsFeature()
        fet.setAttributes( [ 0 , currentdistance ] )
        fet.setGeometry(point)
        feats.append(fet)
        # Increase the distance
        currentdistance = currentdistance + distance

    return feats

def pointsAlongLine(distance):
    ''' Create a new memory layer and add a distance attribute'''
    vl = QgsVectorLayer("Point", "distance nodes", "memory")
    pr = vl.dataProvider()
    pr.addAttributes( [ QgsField("distance", QVariant.Int) ] )
    layer = iface.mapCanvas().currentLayer()
    vl.setCrs(layer.crs())
    # Loop though all the selected features
    for feature in layer.getFeatures():
        geom = feature.geometry()
        features = createPointsAt(distance, geom)
        pr.addFeatures(features)
        vl.updateExtents()

    QgsMapLayerRegistry.instance().addMapLayer(vl)
    
def create_points_secs(layer,step=1000,sez_length=1000):
        '''
        Function to create point at specified distance from initial point line
        author: Giovanni Allegri email: giohappy@gmail.com
        '''
        crs = layer.crs().authid()
        if layer:
            pt_mid  = MemoryLayer("Punti sezioni", "Point",crs)
            sez  = MemoryLayer("Sezioni", "LineString",crs)
            #pydevd.settrace()
            for elem in layer.getFeatures():
                line = elem.geometry()
                line_length = 0
                part_length = step
                for seg_start, seg_end in paires(line.asPolyline()):
                    line_start = QgsPoint(seg_start)
                    line_end = QgsPoint(seg_end)
                    pointm =diff(line_end, line_start)
                    cosa,cosb = cosdir(pointm)
                    seg_length = dist(line_end, line_start)
                    while (line_length+seg_length)>=part_length:
                        step_length = part_length-line_length
                        p0 = line_start.x() + (step_length * cosa)
                        p1 = line_start.y() + (step_length * cosb)
                        p = QgsPoint(p0,p1)           
                        pt_mid.add_point(p)
                        prof_st,prof_end = get_profile_seg(line_start,line_end,p,sez_length)
                        sez.add_line(prof_st, prof_end)
                        part_length += step
                    line_length += seg_length
        
            #~ pt_mid.loadme()
            sez.loadme()
            return sez
            
def get_profile_seg(p0,p1,mid,length):
        '''
        Function to create XS at specified distance from initial point line
        author: Giovanni Allegri email: giohappy@gmail.com'''
        
        disp = np.array([[p1.x()-p0.x()],[p1.y()-p0.y()]])
        rot_anti = np.array([[0, -1], [1, 0]])
        rot_clock = np.array([[0, 1], [-1, 0]])
        vec_anti = np.dot(rot_anti, disp)
        vec_clock = np.dot(rot_clock, disp)
        len_anti = ((vec_anti**2).sum())**0.5
        vec_anti = vec_anti/len_anti
        len_clock = ((vec_clock**2).sum())**0.5
        vec_clock = vec_clock/len_clock
        vec_anti = vec_anti*length
        vec_clock = vec_clock*length
        prof_st = QgsPoint(mid.x() + float(vec_anti[0]), mid.y() + float(vec_anti[1]))
        prof_end = QgsPoint(mid.x() + float(vec_clock[0]), mid.y() + float(vec_clock[1]))
        return prof_st,prof_end
