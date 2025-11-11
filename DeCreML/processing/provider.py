from qgis.core import QgsProcessingProvider
from .decreml_algorithm import Decreml120

class DeCreMLProvider(QgsProcessingProvider):
    def loadAlgorithms(self):
        self.addAlgorithm(Decreml120())
    def id(self): return "DeCreML"
    def name(self): return "DeCreML"
    def longName(self): return "Detección de Crecimientos ML"
