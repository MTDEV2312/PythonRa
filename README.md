# PythonRa

## Descripción
PythonRa es una aplicación basada en Flask que utiliza visión por computadora para el reconocimiento de marcadores **ArUco** y superposición de imágenes. Además, se integra con **Blynk** para la lectura de sensores en tiempo real.

## Características
- **Detección de marcadores ArUco** usando OpenCV.
- **Superposición de imágenes** sobre los marcadores detectados.
- **Lectura de sensores** mediante integración con **Blynk**.
- **Interfaz web interactiva** para visualizar el procesamiento de imágenes.

## Estructura del Proyecto
```
mtdev2312-pythonra/
├── README.md
├── Procfile
├── app.py
├── gunicorn_config.py
├── requirements.txt
├── static/
│   ├── css/
│   │   └── styles.css
│   ├── images/
│   └── js/
│       └── arscanner.js
└── templates/
    └── index.html
```

## Instalación
### Requisitos previos
- Python 3.8+
- Virtualenv (opcional, recomendado)
- Flask y OpenCV

### Pasos de instalación
1. Clonar el repositorio:
   ```sh
   git clone https://github.com/MTDEV2312/PythonRa.git
   cd PythonRa
   ```

2. Crear un entorno virtual y activarlo (opcional pero recomendado):
   ```sh
   python -m venv venv
   source venv/bin/activate  # En macOS/Linux
   venv\Scripts\activate  # En Windows
   ```

3. Instalar dependencias:
   ```sh
   pip install -r requirements.txt
   ```

4. Configurar variables de entorno (crear `.env` en la raíz del proyecto):
   ```sh
   BLYNK_TOKEN=tu_token_de_blynk
   FLASK_DEBUG=True
   ```

5. Ejecutar la aplicación:
   ```sh
   python app.py
   ```

## Uso
- Accede a `http://localhost:10000/` en tu navegador para ver la interfaz.
- Asegúrate de que la cámara esté habilitada para la detección de marcadores.
- Si usas **Blynk**, asegúrate de configurar correctamente el token de API.


## Tecnologías utilizadas
- **Python** (Flask, OpenCV, Requests)
- **JavaScript** (Control de cámara y procesamiento en frontend)
- **HTML/CSS** (Interfaz de usuario)


