
# -*- coding: utf-8 -*-
from qgis.PyQt.QtCore import QObject
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsApplication
from qgis import processing
from qgis.utils import iface
from .processing.provider import DeCreMLProvider
import os

class DeCreMLPlugin(QObject):
    def __init__(self, iface):
        QObject.__init__(self)
        self.iface=iface
        self.provider=None
        self.action=None

    def initGui(self):
        self.provider=DeCreMLProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)
        icon_path=self.pluginIcon()
        self.action=QAction(QIcon(icon_path), "DeCreML", self.iface.mainWindow())
        self.action.triggered.connect(self.openAlgorithmDialog)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&DeCreML", self.action)

    def openAlgorithmDialog(self):
        try:
            processing.execAlgorithmDialog("DeCreML:decreml120")
        except Exception as e:
            self.iface.messageBar().pushWarning("DeCreML", str(e))

    def unload(self):
        try: self.iface.removePluginMenu("&DeCreML", self.action)
        except: pass
        try: self.iface.removeToolBarIcon(self.action)
        except: pass
        try: QgsApplication.processingRegistry().removeProvider(self.provider)
        except: pass

    def pluginIcon(self):
        return os.path.join(os.path.dirname(__file__), "icon.png")
