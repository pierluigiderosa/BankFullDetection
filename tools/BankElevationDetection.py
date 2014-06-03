# -*- coding: utf-8 -*-
"""
/***************************************************************************
 BankFullDetection
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

""" Your Description of the script goes here """


from shapely.geometry import Polygon
from shapely.geometry import box
from shapely.geometry import LineString
import numpy as np

from spline_withR import runAlg as splineR

def WTable(polygon,h):
    minx, miny, maxx, maxy=polygon.bounds
    WTLine = LineString([(minx,h),(maxx,h)])
    return WTLine

def hdepth(polygon,h):
    minx, miny, maxx, maxy=polygon.bounds
    b = box(minx, miny, maxx, h)
    return b

#~ new function for new method for selecting local maxima
def diff_n(Harray,locMax,dist):
    leftIndex = max(locMax-dist,0)
    rightIndex = min(locMax + dist, len(Harray)-1)
    lGrad = Harray[locMax] - Harray[leftIndex]
    rGrad = Harray[rightIndex] - Harray[locMax]
    if ((cmp(lGrad,0)>0) & (cmp(rGrad,0)<0) & (lGrad != rGrad)):
        return True
    else:
        return False
#~ --

def local_maxmin(Harray):
    gradients=np.diff(Harray)
    maxima_num=0
    minima_num=0
    max_locations=[]
    min_locations=[]
    count=0
    #new methods
    ranks = []
    rank = 1
    #--
    for i in gradients[:-1]:
        count+=1
        if ((cmp(i,0)>0) & (cmp(gradients[count],0)<0) & (i != gradients[count])):
            maxima_num+=1
            max_locations.append(count)     
            #new method
            while (diff_n(Harray,count,rank) and rank<len(Harray)):
               rank += 1
            ranks.append(rank)
            #--
        if ((cmp(i,0)<0) & (cmp(gradients[count],0)>0) & (i != gradients[count])):
            minima_num+=1
            min_locations.append(count)
    turning_points = {'maxima_number':maxima_num,'minima_number':minima_num,'maxima_locations':max_locations,'minima_locations':min_locations,
                      #new method
                      'maxima_ranks': ranks
                      #--
    }  
    return turning_points

def mainFun(pointList,nVsteps=100,minVdep=1,Graph=0):
    polygonXSorig = Polygon(pointList)
    #~ definition line of XS
    borderXS = LineString(pointList)
    
    minY=polygonXSorig.bounds[1]
    maxY=polygonXSorig.bounds[-1]
    #~ definition polygon of XS
    pointList.insert(0,(polygonXSorig.bounds[0],maxY+1))
    pointList.append((polygonXSorig.bounds[2],maxY+1))
    polygonXS = Polygon(pointList)
    
    depts = np.linspace(minY+0.1, maxY-0.1, nVsteps)
    
    HydRad = np.array([])
    HydDept = np.array([])
    for dept in depts:
        wdep=hdepth(polygonXSorig,dept)
        wdepLine = WTable(polygonXSorig,dept)
        wetArea = polygonXS.intersection(wdep)
        wetPerimeter=borderXS.intersection(wdep)
        wetWTLine = wdepLine.intersection(polygonXS)
        HydRad = np.append(HydRad,wetArea.area/wetPerimeter.length)
        HydDept = np.append(HydDept,wetArea.area/wetWTLine.length)
    
    #smoothing function
    #estract local maxima of HydDept and depts using smoothing function in R
    deptsLM, HydDeptLM , spar  = splineR(depts,HydDept)
    from scipy.interpolate import UnivariateSpline
    splHydDept= UnivariateSpline(depts, HydDept)
    splHydDept.set_smoothing_factor(spar)
    HydDept_smth=splHydDept(depts)
    
    xfine = np.linspace(min(depts),max(depts),1000)
    HydDept_smthfine= splHydDept(xfine)
    
    #~ first maxima location of HydDept

    if len(deptsLM)>0:
        #~ skip local maxima_locations if lower then value set by user
        #~ previous method now replaced
        max_loc_filtered = [i for i in range(len(HydDeptLM)) if HydDeptLM[i] >= minVdep] 
        
        #~ shapely polygon for bankfull
        bankfullIndex = max_loc_filtered[0]
        bankfullLine = WTable(polygonXSorig,deptsLM[bankfullIndex])
        wdep=hdepth(polygonXSorig,deptsLM[bankfullIndex])
        

    else:
        bankfullLine = WTable(polygonXSorig,depts[-1])
        wdep=hdepth(polygonXSorig,depts[-1])
    
    #~ new method
    turning_points = local_maxmin(HydDept)
    terrace = [] 
    for i in range(len(turning_points['maxima_locations'])):
        if turning_points['maxima_ranks'][i] == max(turning_points['maxima_ranks'])  :
            terrace.append(turning_points['maxima_locations'][i])  
    #~ max_loc_filtered = [i for i in max_loc_filtered if HydDept[i] > minVdep] 
    #~ --
    #~ shapely polygon for terrace
    terraceIndex=terrace[0]
    terraceLine=WTable(polygonXSorig,depts[terraceIndex])
    tdep=hdepth(polygonXSorig,depts[terraceIndex])
    tArea = polygonXS.intersection(tdep)
    
    wetArea = polygonXS.intersection(wdep)
    boundsOK = ()
    Area = 0
    if wetArea.type is 'MultiPolygon':
        for wetPolygon in wetArea:
            if wetPolygon.area > Area:
                Area = wetPolygon.area
                boundsOK = wetPolygon.bounds
    else:
        boundsOK = wetArea.bounds
    
    if Graph == 1:
        #~ definition of figure for XS plot
        from matplotlib import pyplot
        from descartes.patch import PolygonPatch
        from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
        
        
        fig = pyplot.figure(1, figsize=(4,3), dpi=300)
        fig = pyplot.figure()
        ax = fig.add_subplot(211)
        ax.clear()
        #~ plot_coords(ax, borderXS,'#999999')         # plot single points on XS
        plot_line(ax,borderXS,'#6699cc')               # plot line of XS
        plot_line(ax,bankfullLine,'#0000F5')           # plot hor line of bankfull
        plot_line(ax,terraceLine,'#FFE066')           # plot hor line of terrace
        ax.set_title('Cross Section')
        if wetArea.type is 'MultiPolygon':
            for wetPolygon in wetArea:
                patch = PolygonPatch(wetPolygon, fc='#00FFCC', ec='#B8B8B8', alpha=0.5, zorder=2)
                ax.add_patch(patch)
        else:
            patch = PolygonPatch(wetArea, fc='#00FFCC', ec='#B8B8B8', alpha=0.5, zorder=2)
            ax.add_patch(patch)
            
        ax = fig.add_subplot(212)
        ax.clear()
        ax.plot(depts,HydDept,'bo')
        ax.plot(xfine,HydDept_smthfine)
        ax.plot(deptsLM[bankfullIndex],HydDeptLM[bankfullIndex],'rs')
        ax.set_title('hydraulic height')
        
        #~ pyplot.show()
        canvas = FigureCanvas(fig)
        canvas.updateGeometry()
        
        return canvas


    else:
        return boundsOK[0],boundsOK[2],len(wetArea),wetArea.area, wetArea.length

def plot_coords(ax, ob,Ncolor):
    x, y = ob.xy
    ax.plot(x, y, 'o', color=Ncolor, zorder=1)

def plot_line(ax, ob,Ncolor):
    x, y = ob.xy
    ax.plot(x, y, color=Ncolor, alpha=0.7, linewidth=3, solid_capstyle='round', zorder=2)

def plot_lines(ax, ob,Ncolor):
    for line in ob:
        x, y = line.xy
        ax.plot(x, y, color=Ncolor, alpha=0.7, linewidth=3, solid_capstyle='round', zorder=2)

