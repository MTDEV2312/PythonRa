from flask import Flask, render_template, Response, request
import cv2
import numpy as np
import cv2.aruco as aruco
import requests
import time
from threading import Thread
from queue import Queue
from functools import lru_cache

app = Flask(__name__)

class BlynkReader:
    def __init__(self, token, pin):
        self.token = token
        self.pin = pin
        self.url = f'https://blynk.cloud/external/api/get?token={token}&{pin}'
        self.latest_value = "0"
        self.running = True
        self._last_stable_value = "0"  # Valor estable
        
    def start(self):
        Thread(target=self._read_blynk, daemon=True).start()
        
    def _read_blynk(self):
        while self.running:
            try:
                response = requests.get(self.url)
                if response.status_code == 200:
                    new_value = response.text
                    if new_value != self._last_stable_value:  # Solo actualizar si el valor es diferente
                        self._last_stable_value = new_value
                        self.latest_value = new_value
            except:
                pass
            time.sleep(1)
            
    def get_value(self):
        return self.latest_value
    
    def stop(self):
        self.running = False

# Configuraciones globales
token = "Bv4yA2yVVgURhhHGRg5WqCo4OSiE2FlD"
pin_virtual = "V5"
blynk_reader = BlynkReader(token, pin_virtual)
blynk_reader.start()

# Configuración de ArUco con parámetros optimizados
parametros = cv2.aruco.DetectorParameters()
parametros.adaptiveThreshWinSizeMin = 3
parametros.adaptiveThreshWinSizeMax = 23
parametros.adaptiveThreshWinSizeStep = 10
parametros.adaptiveThreshConstant = 7

aruco_diccionario = aruco.getPredefinedDictionary(aruco.DICT_6X6_100)
detector = aruco.ArucoDetector(aruco_diccionario, parametros)

# Cache para la imagen de superposición
@lru_cache(maxsize=None)
def get_overlay_image():
    img = cv2.imread("static/images/overlay.jpg")
    if img is not None:
        # Redimensionar la imagen a un tamaño más pequeño
        return cv2.resize(img, (320, 240))
    return None

nueva_imagen1 = get_overlay_image()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_frame', methods=['POST'])
def process_frame():
    if 'frame' not in request.files:
        return 'No frame received', 400

    try:
        # Leer y reducir el tamaño del frame
        filestr = request.files['frame'].read()
        npimg = np.frombuffer(filestr, np.uint8)
        frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
        
        # Reducir el tamaño del frame para procesamiento más rápido
        frame = cv2.resize(frame, (640, 480))

        # Procesar el frame con ArUco
        cuadro_gris = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        esquinas, identificador, _ = detector.detectMarkers(cuadro_gris)

        if len(esquinas) > 0:
            aruco.drawDetectedMarkers(frame, esquinas, identificador)
            valor = blynk_reader.get_value()

            for i in range(len(identificador)):
                marker_corners = esquinas[i][0]
                marker_id = identificador[i][0]

                if marker_id == 1:
                    x, y, w, h = cv2.boundingRect(marker_corners)

                    try:
                        if nueva_imagen1 is not None:
                            nueva_imagen1_resized = cv2.resize(nueva_imagen1, (w, h))
                            if y+h <= frame.shape[0] and x+w <= frame.shape[1]:
                                # Usar máscara para una superposición más suave
                                mask = np.ones(nueva_imagen1_resized.shape[:2], dtype=np.uint8) * 255
                                frame[y:y+h, x:x+w] = cv2.addWeighted(
                                    frame[y:y+h, x:x+w], 0.1,
                                    nueva_imagen1_resized, 0.9,
                                    0
                                )
                            
                        # Renderizar el texto con fondo negro
                        text = f"SensorLuz: {valor}"
                        font = cv2.FONT_HERSHEY_SIMPLEX
                        font_scale = 0.6
                        thickness = 1
                        
                        # Calcular el tamaño del texto
                        (text_width, text_height), _ = cv2.getTextSize(text, font, font_scale, thickness)
                        
                        # Definir coordenadas del texto
                        text_x = x
                        text_y = y + h + 20
                        
                        # Dibujar rectángulo negro como fondo
                        padding = 5
                        cv2.rectangle(frame,
                                    (text_x - padding, text_y - text_height - padding),
                                    (text_x + text_width + padding, text_y + padding),
                                    (0, 0, 0),
                                    -1)
                        
                        # Dibujar el texto blanco sobre el fondo negro
                        cv2.putText(frame, text, (text_x, text_y),
                                  font, font_scale, (255, 255, 255), thickness)
                        
                    except Exception as e:
                        print(f"Error al superponer imagen: {e}")

        # Comprimir la imagen con menor calidad para transmisión más rápida
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        return Response(buffer.tobytes(), mimetype='image/jpeg')

    except Exception as e:
        print(f"Error processing frame: {str(e)}")
        return f'Error processing frame: {str(e)}', 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)  # Desactivar debug mode para producción