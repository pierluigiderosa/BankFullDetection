import math
from qgis.core import QgsPoint
             
def mag(point):
    return math.sqrt(point.x()**2 + point.y()**2)
 
def dist(point1,point2):
    return math.sqrt(point1.sqrDist(point2))
 
def diff(point2, point1):
    return QgsPoint(point2.x()-point1.x(), point2.y() - point1.y())
 
def sum(point2,point1):
    return QgsPoint(point2.x()+point1.x(), point2.y()+point1.y())
 
def sum_k(point, dx,dy):
    return QgsPoint(point.x()+dx, point.y()+dy)
 
def vecxscal(point,k):
    return QgsPoint(point.x()*k, point.y()*k)
 
def norm(point1, point2):
    point = diff(point2,point1)
    m = mag(point)
    return QgsPoint(point.x()/m, point.y()/m)
 
def normpt(point): 
    m = mag(point)
    return QgsPoint(point.x()/m, point.y()/m)
 
def dot_product(point1, point2):
    return (point1.x()*point2.x() + point1.y()*point2.y())
 
def det(point1, point2):
    return (point1.x*point2.y) - (point1.y*point2.x)

def pol_car(dist, angle):
    return QgsPoint(dist * math.cos(math.radians(angle)),dist * math.sin(math.radians(angle)))
 
def cosdir(point):
    cosa = point.x() / mag(point)
    cosb = point.y()/ mag(point)
    return cosa,cosb
 
def cosdir_azim(azim):
    az = math.radians(azim)
    cosa = math.sin(az)
    cosb = math.cos(az)
    return cosa,cosb

def paires(list):
    for i in range(1, len(list)):
        yield list[i-1], list[i]
