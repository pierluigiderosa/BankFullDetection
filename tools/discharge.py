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

import math

def discharge(area,perimeter,manning=0.033,i):
    Raggio=area/perimeter
    x=(1/manning)*(Raggio**(1/6.))
    i=1/100.
    Q=area*x * math.sqrt (i*Raggio)
    return Q
