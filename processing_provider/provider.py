"""Processing provider of BankFullDetection."""

import os

from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon

from .alg_generate_sections import GenerateSectionsAlgorithm

#: Provider id: algorithms are addressed as "bankfulldetection:<algorithm name>".
PROVIDER_ID = "bankfulldetection"


class BankfullProvider(QgsProcessingProvider):
    """Provider holding the BankFullDetection algorithms."""

    def __init__(self, plugin_dir):
        super().__init__()
        self._icon_path = os.path.join(plugin_dir, "icon.png")

    def id(self):
        return PROVIDER_ID

    def name(self):
        return "Bankfull detection"

    def longName(self):
        return "Bankfull detection (De Rosa et al. 2019)"

    def icon(self):
        return QIcon(self._icon_path)

    def loadAlgorithms(self):
        self.addAlgorithm(GenerateSectionsAlgorithm())
