from flask import Flask, render_template, Response, request, send_from_directory
import cv2
import numpy as np
import cv2.aruco as aruco
import requests
import time
import os
from threading import Thread
from queue import Queue
from functools import lru_cache
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

app = Flask(__name__)

# Configurar logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BlynkReader:
    def __init__(self, token, pin):
        self.token = token
        self.pin = pin
        self.url = f'https://blynk.cloud/external/api/get?token={token}&{pin}'
        self.latest_value = "0"
        self.running = True
        self._last_stable_value = "0"
        self.last_update_time = time.time()
        self._cache_duration = 2
        self._session = requests.Session()
        
    def start(self):
        Thread(target=self._read_blynk, daemon=True).start()
        logger.info("BlynkReader iniciado")
        
    def _read_blynk(self):
        while self.running:
            try:
                current_time = time.time()
                if current_time - self.last_update_time >= self._cache_duration:
                    response = self._session.get(self.url, timeout=5)
                    if response.status_code == 200:
                        new_value = response.text
                        if new_value != self._last_stable_value:
                            self._last_stable_value = new_value
                            self.latest_value = new_value
                            self.last_update_time = current_time
                            logger.debug(f"Nuevo valor de Blynk: {new_value}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Error en la conexión con Blynk: {e}")
            time.sleep(2)
            
    def get_value(self):
        return self.latest_value
    
    def stop(self):
        self.running = False
        self._session.close()
        logger.info("BlynkReader detenido")

# Configuraciones globales
token = os.environ.get('BLYNK_TOKEN')
pin_virtual = "V5"
blynk_reader = BlynkReader(token, pin_virtual)
blynk_reader.start()

# Configuración de ArUco optimizada
parameters = cv2.aruco.DetectorParameters()
parameters.adaptiveThreshWinSizeMin = 3
parameters.adaptiveThreshWinSizeMax = 23
parameters.adaptiveThreshWinSizeStep = 10
parameters.adaptiveThreshConstant = 7
parameters.minMarkerPerimeterRate = 0.01  # Reducido para detectar marcadores más pequeños
parameters.maxMarkerPerimeterRate = 4.0    # Aumentado para detectar marcadores más grandes
parameters.polygonalApproxAccuracyRate = 0.05
parameters.minCornerDistanceRate = 0.05
parameters.minDistanceToBorder = 3
parameters.minMarkerDistanceRate = 0.05
parameters.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
parameters.cornerRefinementWinSize = 5
parameters.cornerRefinementMaxIterations = 30
parameters.cornerRefinementMinAccuracy = 0.1

dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_100)
detector = cv2.aruco.ArucoDetector(dictionary, parameters)

# Asegurarse de que el directorio de imágenes existe
UPLOAD_FOLDER = os.path.join('static', 'images')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
logger.info(f"Directorio de imágenes creado/verificado: {UPLOAD_FOLDER}")

def generate_marker():
    """Genera un marcador ArUco de prueba si no existe"""
    marker_path = os.path.join(UPLOAD_FOLDER, 'marker.png')
    if not os.path.exists(marker_path):
        logger.info("Generando marcador ArUco de prueba...")
        marker = np.zeros((300, 300), dtype=np.uint8)
        marker = dictionary.generateImageMarker(1, 300, marker, 1)
        cv2.imwrite(marker_path, marker)
        logger.info(f"Marcador ArUco generado en: {marker_path}")

# Generar marcador de prueba
generate_marker()

@lru_cache(maxsize=1)
def get_overlay_image():
    """Carga la imagen de superposición con mejor manejo de errores"""
    image_path = os.path.join('static', 'images', 'overlay.jpg')
    logger.info(f"Intentando cargar imagen desde: {os.path.abspath(image_path)}")
    
    if not os.path.exists(image_path):
        logger.error(f"Error: La imagen de superposición no existe en {image_path}")
        return None
    
    img = cv2.imread(image_path)
    if img is None:
        logger.error(f"Error: No se pudo cargar la imagen desde {image_path}")
        return None
    
    logger.info(f"Imagen cargada exitosamente. Dimensiones: {img.shape}")
    resized = cv2.resize(img, (160, 120))
    logger.info(f"Imagen redimensionada. Nuevas dimensiones: {resized.shape}")
    return resized

overlay_image = get_overlay_image()
if overlay_image is None:
    logger.warning("Advertencia: No se pudo cargar la imagen de superposición")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route('/process_frame', methods=['POST'])
def process_frame():
    if 'frame' not in request.files:
        logger.error("No se recibió frame en la petición")
        return 'No frame received', 400

    try:
        # Leer y procesar el frame
        filestr = request.files['frame'].read()
        npimg = np.frombuffer(filestr, np.uint8)
        frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
        
        if frame is None:
            logger.error("No se pudo decodificar el frame")
            return 'Error decoding frame', 500
            
        # Reducir el tamaño del frame para procesamiento más rápido
        frame = cv2.resize(frame, (320, 240))
        logger.debug(f"Frame shape: {frame.shape}")

        # Mejorar el preprocesamiento de la imagen
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Aplicar suavizado para reducir ruido
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Mejorar el contraste
        gray = cv2.equalizeHist(gray)
        
        # Detectar marcadores
        corners, ids, rejected = detector.detectMarkers(gray)
        
        # Debug información sobre la detección de marcadores
        logger.debug("Búsqueda de marcadores ArUco completada")
        logger.debug(f"¿Se encontraron marcadores?: {ids is not None}")
        if ids is not None:
            logger.debug(f"Número de marcadores encontrados: {len(ids)}")
            logger.debug(f"IDs de marcadores encontrados: {ids.flatten()}")
        logger.debug(f"Número de marcadores rechazados: {len(rejected)}")
        
        # Dibujar los marcadores rechazados para debug
        frame = cv2.aruco.drawDetectedMarkers(frame, rejected, None, (0, 0, 255))
        
        if ids is not None and len(ids) > 0:
            # Dibujar los marcadores detectados
            frame = cv2.aruco.drawDetectedMarkers(frame, corners, ids, (0, 255, 0))
            valor = blynk_reader.get_value()
            logger.debug(f"Valor del sensor: {valor}")

            for i in range(len(ids)):
                marker_corners = corners[i][0]
                x, y, w, h = cv2.boundingRect(marker_corners)
                logger.debug(f"Marcador {ids[i][0]}: posición=({x}, {y}), tamaño=({w}, {h})")

                try:
                    if overlay_image is not None:
                        if w > 0 and h > 0:
                            logger.debug(f"Redimensionando overlay para marcador {ids[i][0]}")
                            overlay_resized = cv2.resize(overlay_image, (w, h))
                            logger.debug(f"Overlay redimensionado: {overlay_resized.shape}")
                            
                            if y >= 0 and y + h <= frame.shape[0] and x >= 0 and x + w <= frame.shape[1]:
                                roi = frame[y:y+h, x:x+w]
                                frame[y:y+h, x:x+w] = cv2.addWeighted(
                                    roi, 0.1,
                                    overlay_resized, 0.9,
                                    0
                                )
                                logger.debug(f"Overlay aplicado exitosamente para marcador {ids[i][0]}")
                    
                    # Renderizar el texto con fondo negro
                    text = f"SensorLuz: {valor}"
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    font_scale = 0.5
                    thickness = 1
                    
                    # Calcular dimensiones del texto
                    (text_width, text_height), _ = cv2.getTextSize(text, font, font_scale, thickness)
                    
                    # Posicionar el texto
                    text_x = x
                    text_y = y + h + 15
                    
                    # Verificar límites para el texto
                    if (text_y + 2) <= frame.shape[0] and (text_x + text_width + 2) <= frame.shape[1]:
                        # Dibujar fondo negro para el texto
                        cv2.rectangle(frame,
                                    (text_x - 2, text_y - text_height - 2),
                                    (text_x + text_width + 2, text_y + 2),
                                    (0, 0, 0),
                                    -1)
                        
                        # Dibujar texto
                        cv2.putText(frame, text, (text_x, text_y),
                                  font, font_scale, (255, 255, 255), thickness)
                        
                except Exception as e:
                    logger.error(f"Error detallado al procesar marcador {ids[i][0]}: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
                    continue

        # Comprimir la imagen con calidad media para balance entre calidad y velocidad
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
        if not ret:
            logger.error("No se pudo codificar el frame procesado")
            return 'Error encoding processed frame', 500
            
        return Response(buffer.tobytes(), mimetype='image/jpeg')

    except Exception as e:
        logger.error(f"Error processing frame: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return f'Error processing frame: {str(e)}', 500

@app.route('/check_overlay')
def check_overlay():
    """Ruta de diagnóstico para verificar la imagen de superposición"""
    image_path = os.path.join('static', 'images', 'overlay.jpg')
    exists = os.path.exists(image_path)
    if exists:
        img = cv2.imread(image_path)
        if img is not None:
            return f"Imagen encontrada y cargada correctamente. Dimensiones: {img.shape}"
    return f"Error: Imagen no encontrada o no se puede cargar desde {image_path}"

if __name__ == '__main__':
    # Verificar la estructura de directorios y archivos necesarios
    logger.info("Iniciando verificación de archivos y directorios...")
    
    # Verificar directorio static/images
    if not os.path.exists(UPLOAD_FOLDER):
        logger.warning(f"Creando directorio: {UPLOAD_FOLDER}")
        os.makedirs(UPLOAD_FOLDER)
    
    # Verificar overlay.jpg
    overlay_path = os.path.join(UPLOAD_FOLDER, 'overlay.jpg')
    if not os.path.exists(overlay_path):
        logger.warning(f"Advertencia: overlay.jpg no encontrado en {overlay_path}")
    else:
        logger.info(f"overlay.jpg encontrado en {overlay_path}")
    
    # Verificar directorio templates
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    if not os.path.exists(templates_dir):
        logger.warning(f"Creando directorio templates: {templates_dir}")
        os.makedirs(templates_dir)
    
    # Verificar index.html
    index_path = os.path.join(templates_dir, 'index.html')
    if not os.path.exists(index_path):
        logger.warning(f"Advertencia: index.html no encontrado en {index_path}")
    else:
        logger.info(f"index.html encontrado en {index_path}")
    
    logger.info("Iniciando servidor Flask...")
    
    # Configuración para producción
    port = int(os.environ.get('PORT', 10000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    app.run(host='0.0.0.0', port=port, debug=debug)