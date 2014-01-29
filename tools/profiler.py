import math
from osgeo import ogr,_ogr
from qgis.core import QgsPoint,QgsRaster,QgsRectangle
#from BankFullDetection.utils import log


class ProfilerTool():
    def __init__(self):
        self.linegeom = None
        self.raster = None
        self.rasterPixelSize = None
        self.identifyFormat = QgsRaster.IdentifyFormatValue
        self.identifyRect = QgsRectangle()
        
    def log(msg):
        logger = QgsMessageLog.instance()
        logger.logMessage(msg,'Bankfull')

    def setRaster(self,raster):
        self.raster = raster
        self.rextent = raster.extent()
        self.rasterPixelSize = self.raster.rasterUnitsPerPixelX() # I take the X resolution supposing its a square pixel
        self.provider = self.raster.dataProvider()

    def doProfile(self,linegeom):
        profile = []
        wkbgeom = linegeom.asWkb()
        ogrgeom = ogr.CreateGeometryFromWkb(wkbgeom)
        err = None
        dist = 0
        prevPoint = None
        if ogrgeom.GetGeometryType() == ogr.wkbLineString:
            try:
                ogrgeom.Segmentize(self.rasterPixelSize)
                points = ogrgeom.GetPoints()
#                log('Numero punti: %s' % len(points))
                i = 0
                for point in points:
                    #log('X: %s' % point[0])
                    p = QgsPoint(point[0],point[1])
                    if self._isInExtent(point):
                        identifyresult = self.provider.identify(p,self.identifyFormat,self.identifyRect)
                        results = identifyresult.results()
                        i += 1
                        #log(str(len(results)))
                        if results and (len(results) > 0):
                            if prevPoint:
                                dist += math.sqrt(prevPoint.sqrDist(p))
                            prevPoint = QgsPoint(p)
                            val = results[1]
                            profile.append((dist,val))
#                            profile.append({'x':point[0],'y':point[1],'dist':dist,'z':val})
                        identifyresult = None
#                log('Punti processati: %s' % i)
            except Exception,e:
                err = e
        else:
            err = 'The geometry is not a linestring'

        return profile,err
        
    def _isInExtent(self,point):
        xMin = self.rextent.xMinimum()
        yMin = self.rextent.yMinimum()
        xMax = self.rextent.xMaximum()
        yMax = self.rextent.yMaximum()
            
        if (xMin<point[0]<xMax) and (yMin<point[1]<yMax):
            return True
        return False
