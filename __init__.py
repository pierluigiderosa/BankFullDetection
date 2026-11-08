"""BankFullDetection QGIS plugin: entry point.

Copyright (C) 2014 by Pierluigi De Rosa (pierluigi.derosa@gmail.com).
This program is free software; you can redistribute it and/or modify it under the terms of
the GNU General Public License as published by the Free Software Foundation; either
version 2 of the License, or (at your option) any later version.
"""


def classFactory(iface):
    """Return the plugin instance (called by QGIS when the plugin is loaded)."""
    from .bankfulldetection import BankFullDetectionPlugin

    return BankFullDetectionPlugin(iface)
