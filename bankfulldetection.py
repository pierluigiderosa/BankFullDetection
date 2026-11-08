"""BankFullDetection QGIS plugin: Processing provider registration and toolbar action.

The plugin holds no computation: the method lives in ``bankfull_core`` and the QGIS side
(sampling, layers) in the Processing algorithms of ``processing_provider``.

Copyright (C) 2014 by Pierluigi De Rosa (pierluigi.derosa@gmail.com).
This program is free software; you can redistribute it and/or modify it under the terms of
the GNU General Public License as published by the Free Software Foundation; either
version 2 of the License, or (at your option) any later version.
"""

import os

from qgis.core import Qgis, QgsApplication
from qgis.PyQt.QtCore import QCoreApplication, QTranslator
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from .processing_provider.provider import PROVIDER_ID, BankfullProvider

#: Algorithm opened by the toolbar / menu action.
MAIN_ALGORITHM_ID = f"{PROVIDER_ID}:detectbankfull"

_MENU = "&Bankfull width detection"


class BankFullDetectionPlugin:
    """QGIS plugin object returned by ``classFactory``."""

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.provider = None
        self.action = None
        self.translator = None
        self._install_translator()

    def _install_translator(self):
        locale = (QgsApplication.locale() or "")[:2]
        qm_path = os.path.join(self.plugin_dir, "i18n", f"bankfulldetection_{locale}.qm")
        if locale and os.path.exists(qm_path):
            self.translator = QTranslator()
            if self.translator.load(qm_path):
                QCoreApplication.installTranslator(self.translator)
            else:
                self.translator = None

    @staticmethod
    def tr(message):
        return QCoreApplication.translate("BankFullDetection", message)

    def initProcessing(self):
        """Register the Processing provider (also called by qgis_process, without GUI)."""
        if self.provider is None:
            self.provider = BankfullProvider(self.plugin_dir)
            QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        self.initProcessing()
        icon = QIcon(os.path.join(self.plugin_dir, "icon.png"))
        self.action = QAction(icon, self.tr("Automatic bankfull width detection"),
                              self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(self.tr(_MENU), self.action)

    def unload(self):
        if self.action is not None:
            self.iface.removePluginMenu(self.tr(_MENU), self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action.deleteLater()
            self.action = None
        if self.provider is not None:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None
        if self.translator is not None:
            QCoreApplication.removeTranslator(self.translator)
            self.translator = None

    def run(self):
        """Open the Processing dialog of the main algorithm."""
        registry = QgsApplication.processingRegistry()
        if registry.algorithmById(MAIN_ALGORITHM_ID) is None:
            self.iface.messageBar().pushMessage(
                "BankFullDetection",
                self.tr("The bankfull detection algorithm is not available yet."),
                level=Qgis.Info,
            )
            return
        import processing  # QGIS Processing plugin, imported only when needed

        processing.execAlgorithmDialog(MAIN_ALGORITHM_ID)
