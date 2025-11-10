from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterRasterLayer
from qgis.core import QgsProcessingParameterRasterDestination
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterField
import processing
import os
import inspect


# ============================================================
# FUNCION PARA OBTENER LA RUTA REAL DEL PLUGIN
# ============================================================
def plugin_dir():
    """
    Devuelve la ruta del directorio del plugin, sin importar cómo QGIS lo ejecute.
    """
    return os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))



class Decreml120(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(
            'imagen', 'IMAGEN', defaultValue=None))

        self.addParameter(QgsProcessingParameterRasterDestination(
            'SalidaImagenClasificada', 'Salida Imagen Clasificada', createByDefault=True, defaultValue=''))

        self.addParameter(QgsProcessingParameterVectorLayer(
            'capa_vectorial_clases',
            'Capa Vectorial Clases',
            types=[QgsProcessing.TypeVectorPoint, QgsProcessing.TypeVectorLine, QgsProcessing.TypeVectorPolygon],
            defaultValue=None))

        self.addParameter(QgsProcessingParameterField(
            'nombre_campo',
            'NOMBRE CAMPO',
            type=QgsProcessingParameterField.Any,
            parentLayerParameterName='capa_vectorial_clases',
            allowMultiple=False,
            defaultValue='LABEL'))


    def processAlgorithm(self, parameters, context, model_feedback):

        feedback = QgsProcessingMultiStepFeedback(4, model_feedback)
        results = {}
        outputs = {}

        # ============================================================
        # PASO 1 — ComputeImagesStatistics
        # ============================================================
        temp_dir = context.temporaryFolder()
        stats_xml = os.path.join(temp_dir, 'statistics.xml')

        alg_params = {
            'bv': 0,
            'il': parameters['imagen'],
            'out.xml': stats_xml
        }

        outputs['ComputeImagesStatistics'] = processing.run(
            'otb:ComputeImagesStatistics',
            alg_params, context=context,
            feedback=feedback, is_child_algorithm=True
        )

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}


        # ============================================================
        # PASO 2 — TrainImagesClassifier
        # ============================================================
        model_output = os.path.join(temp_dir, 'model.model')

        alg_params = {
            'classifier': 'rf',
            'classifier.rf.nbtrees': 1000,
            'classifier.rf.max': 10,
            'classifier.rf.min': 10,
            'classifier.rf.acc': 0.01,
            'classifier.rf.var': 0,
            'classifier.rf.ra': 0,
            'classifier.rf.cat': 10,
            'cleanup': True,
            'elev.default': 0,
            'elev.dem': '',
            'elev.geoid': '',
            'io.confmatout': os.path.join(temp_dir, 'confusion_matrix.xml'),
            'io.il': parameters['imagen'],
            'io.imstat': stats_xml,
            'io.out': model_output,
            'io.valid': parameters['capa_vectorial_clases'],
            'io.vd': parameters['capa_vectorial_clases'],
            'rand': 0,
            'sample.bm': 1,
            'sample.mt': 1000,
            'sample.mv': 1000,
            'sample.vfn': parameters['nombre_campo'],
            'sample.vtr': 0.8
        }

        outputs['TrainImagesClassifier'] = processing.run(
            'otb:TrainImagesClassifier',
            alg_params, context=context,
            feedback=feedback, is_child_algorithm=True
        )

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}


        # ============================================================
        # PASO 3 — ImageClassifier (CLASIFICAR IMAGEN)
        # ============================================================
        alg_params = {
            'imstat': stats_xml,
            'in': parameters['imagen'],
            'mask': None,
            'model': model_output,
            'nbclasses': 12,
            'nodatalabel': 0,
            'outputpixeltype': 5,
            'out': parameters['SalidaImagenClasificada']
        }

        outputs['ClasificacionImagen'] = processing.run(
            'otb:ImageClassifier',
            alg_params, context=context,
            feedback=feedback, is_child_algorithm=True
        )

        results['SalidaImagenClasificada'] = outputs['ClasificacionImagen']['out']

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}


        # ============================================================
        # PASO 4 — CARGAR Y APLICAR ESTILO QML AUTOMÁTICAMENTE
        # ============================================================
        try:
            salida_raster = results['SalidaImagenClasificada']

            from qgis.core import QgsRasterLayer, QgsProject
            rl = QgsRasterLayer(salida_raster, "Imagen Clasificada")

            # Buscar el archivo QML en el directorio del plugin
            qml_path = os.path.join(plugin_dir(), "Class_imgGM_12AgsclasesOk.qml")

            if os.path.exists(qml_path):
                ok, error = rl.loadNamedStyle(qml_path)
                rl.triggerRepaint()
            else:
                feedback.reportError(f"❌ No se encontró el archivo QML: {qml_path}")

            # Agregar capa a QGIS
            if rl.isValid():
                QgsProject.instance().addMapLayer(rl)
            else:
                feedback.reportError("❌ No se pudo cargar la imagen clasificada como capa.")

        except Exception as e:
            feedback.reportError(f"❌ Error aplicando estilo automáticamente: {e}")


        return results



    def name(self):
        return 'DeCreML 1.2.0'

    def displayName(self):
        return 'DeCreML 1.2.0'

    def group(self):
        return 'Deteccion Crecimientos'

    def groupId(self):
        return 'Machine Learning'

    def shortHelpString(self):
        return """<html><body><p><!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">
<html><head><meta name="qrichtext" content="1" /><style type="text/css">
p, li { white-space: pre-wrap; }
</style></head><body style=" font-family:'MS Shell Dlg 2'; font-size:8.3pt; font-weight:400; font-style:normal;">
<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:12pt;">Subdirección de Servicios de Información del Marco Geoestadístico </span></p>
<p style="-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;"><br /></p>
<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:12pt;">Herramienta para la Detección de Crecimientos Machine Learning (DeCreML 1.2.0.)</span></p>
<p style="-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;"><br /></p>
<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:12pt;">La presente herramienta utiliza el aprendizaje automático de Machinne Learning (ML) para QGIS basado en librerias de OTB. </span></p>
<p style=" margin-top:12px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:12pt;">El algoritmo se basa en el método de RandomForest (</span><a href="https://scikit-learn.org/1.5/modules/generated/sklearn.ensemble.RandomForestClassifier.html#sklearn.ensemble.RandomForestClassifier"><span style=" font-family:'-apple-system','BlinkMacSystemFont','Segoe UI','Noto Sans','Helvetica','Arial','sans-serif','Apple Color Emoji','Segoe UI Emoji'; font-size:12pt; font-weight:600; text-decoration: underline; color:#0969da; background-color:transparent;">bosque aleatorio</span></a><span style=" font-size:12pt;">), el cual es un algoritmo de aprendizaje automático robusto y conocido para tareas de clasificación y regresión. Funciona creando múltiples árboles de decisión durante el entrenamiento. La salida se genera mediante votación mayoritaria en caso de clasificación o la media de la predicción de los árboles en caso de regresión. </span></p>
<p style=" margin-top:12px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:12pt;">El algoritmo requiere los siguientes parámetros: </span></p>
<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-family:'Symbol'; font-size:12pt;">·</span><span style=" font-family:'Times New Roman'; font-size:12pt;">       </span><span style=" font-size:12pt;">Capa vectorial de clases como dato de entrada para el entrenamiento. </span></p>
<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-family:'Symbol'; font-size:12pt;">·</span><span style=" font-family:'Times New Roman'; font-size:12pt;">       </span><span style=" font-size:12pt;">Campo de clasificación que contiene las etiquetas de clase (LABEL). </span></p>
<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-family:'Symbol'; font-size:12pt;">·</span><span style=" font-family:'Times New Roman'; font-size:12pt;">       </span><span style=" font-size:12pt;">Imagen ráster multiespectral para procesar. </span></p>
<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-family:'Symbol'; font-size:12pt;">·</span><span style=" font-family:'Times New Roman'; font-size:12pt;">       </span><span style=" font-size:12pt;">Nombre para la imagen clasificada de salida (clasificación: 1-construcción, 2-Vialidad, 3-Vegetación, 4-Cuerpo Agua, 5-Suelo desnudo,    6-Cultivo, 7-Poca Vegetación, 8-Sombra, 9-Nubes, 11-Vegetación Mediana, 12-Vegetación Alta).</span></p>
<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-family:'Symbol'; font-size:12pt;">·</span><span style=" font-family:'Times New Roman'; font-size:12pt;">       </span><span style=" font-size:12pt;">Nombre para la imagen confidencial de salida.</span></p>
<p style="-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;"><br /></p>
<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:12pt;">Apartir de la imagen de salida y atravez de la herramienta de poligonización se puede crear el archivo vectorial de la clases que se deseen. </span></p>
<p style="-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:24px; margin-right:0px; -qt-block-indent:1; text-indent:0px; line-height:24px; font-size:10pt;"><br /></p>
<p style="-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:24px; margin-right:0px; -qt-block-indent:1; text-indent:0px; line-height:24px; font-size:10pt;"><br /></p></body></html></p>
<h2>Parámetros de entrada</h2>
<h3>IMAGEN</h3>
<p>Imagen Raster multiespectrar sentinel-2 </p>
<h2>Ejemplos</h2>
<p><!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">
<html><head><meta name="qrichtext" content="1" /><style type="text/css">
p, li { white-space: pre-wrap; }
</style></head><body style=" font-family:'MS Shell Dlg 2'; font-size:8.3pt; font-weight:400; font-style:normal;">
<p style="-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:6.6pt;"><br /></p></body></html></p><br><p align="right">Autor del algoritmo: Edición: 1.2.0 
Subdirección de Servicios de Información del Marco Geoestadístico 
</p><p align="right">Versión del algoritmo: Detección de Crecimiento Machine Learnig versión 1.2.0</p></body></html>"""


    def helpUrl(self):
        return 'Versión 1.2.0'

    def createInstance(self):
        return Decreml120()
