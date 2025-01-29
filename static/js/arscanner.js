class ARScanner {
    constructor() {
        // Elementos del DOM
        this.video = document.getElementById('video');
        this.canvas = document.getElementById('canvas');
        this.cameraSelect = document.getElementById('cameraSelect');
        this.statusDiv = document.getElementById('status');
        this.errorContainer = document.getElementById('errorContainer');
        this.fpsCounter = document.getElementById('fpsCounter');
        this.startButton = document.getElementById('startButton');
        this.stopButton = document.getElementById('stopButton');
        this.loadingIndicator = document.getElementById('loadingIndicator');
        this.debugPanel = document.getElementById('debugPanel');
        this.debugInfo = document.getElementById('debugInfo');
        this.debugToggle = document.getElementById('debugToggle');
        
        // Estado de la aplicación
        this.stream = null;
        this.isProcessing = false;
        this.isRunning = false;
        this.backCanvas = document.createElement('canvas');
        this.backContext = this.backCanvas.getContext('2d', { willReadFrequently: true });
        
        // Control de FPS y rendimiento
        this.targetFPS = 10;
        this.frameInterval = 1000 / this.targetFPS;
        this.lastFrameTime = 0;
        this.fpsValues = [];
        this.frameCount = 0;
        this.lastFPSUpdate = 0;
        
        // Control de errores
        this.consecutiveErrors = 0;
        this.maxConsecutiveErrors = 5;
        this.debugMode = false;
        
        // Bind de métodos
        this.processVideo = this.processVideo.bind(this);
        this.startCamera = this.startCamera.bind(this);
        this.stopCamera = this.stopCamera.bind(this);
        this.handleCameraChange = this.handleCameraChange.bind(this);
        this.toggleDebug = this.toggleDebug.bind(this);
        
        // Inicialización
        this.setupEventListeners();
        this.init();
    }

    setupEventListeners() {
        this.startButton.addEventListener('click', () => this.startCamera());
        this.stopButton.addEventListener('click', () => this.stopCamera());
        this.cameraSelect.addEventListener('change', this.handleCameraChange);
        this.debugToggle.addEventListener('click', this.toggleDebug);
    }

    toggleDebug() {
        this.debugMode = !this.debugMode;
        this.debugPanel.classList.toggle('hidden');
        this.debugToggle.textContent = this.debugMode ? 'Ocultar Debug' : 'Mostrar Debug';
    }

    updateDebugInfo(info) {
        if (this.debugMode) {
            this.debugInfo.textContent = JSON.stringify(info, null, 2);
        }
    }

    showError(title, messages) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        
        let html = `<h3>${title}</h3>`;
        if (Array.isArray(messages)) {
            html += '<ul>';
            messages.forEach(msg => {
                html += `<li>${msg}</li>`;
            });
            html += '</ul>';
        } else {
            html += `<p>${messages}</p>`;
        }
        
        this.errorContainer.innerHTML = '';
        this.errorContainer.appendChild(errorDiv);
        errorDiv.innerHTML = html;
    }

    checkConnectionStatus() {
        if (!navigator.onLine) {
            this.showError('Error de Conexión', 'No hay conexión a internet. Verifica tu conexión.');
            return false;
        }
        return true;
    }

    updateFPSCounter() {
        const now = performance.now();
        this.frameCount++;

        if (now - this.lastFPSUpdate >= 1000) {
            const fps = Math.round((this.frameCount * 1000) / (now - this.lastFPSUpdate));
            this.fpsCounter.textContent = `FPS: ${fps}`;
            this.frameCount = 0;
            this.lastFPSUpdate = now;
        }
    }

    async processVideo() {
        if (!this.isRunning) return;

        const now = performance.now();
        const timeSinceLastFrame = now - this.lastFrameTime;
        
        if (timeSinceLastFrame < this.frameInterval) {
            requestAnimationFrame(this.processVideo);
            return;
        }
        
        if (!this.stream || this.isProcessing || !this.checkConnectionStatus()) {
            requestAnimationFrame(this.processVideo);
            return;
        }

        this.isProcessing = true;
        this.loadingIndicator.style.display = 'block';
        this.lastFrameTime = now;
        
        try {
            this.backContext.drawImage(
                this.video, 
                0, 0, 
                this.backCanvas.width, 
                this.backCanvas.height
            );
            
            const blob = await new Promise(resolve => {
                this.backCanvas.toBlob(resolve, 'image/jpeg', 0.8);
            });

            if (!blob) {
                throw new Error('Failed to create blob from canvas');
            }

            const formData = new FormData();
            formData.append('frame', blob);

            const response = await fetch('/process_frame', {
                method: 'POST',
                body: formData,
                headers: {
                    'Accept': 'image/jpeg'
                }
            });
            
            if (response.ok) {
                const processedImageBlob = await response.blob();
                if (processedImageBlob.size === 0) {
                    throw new Error('Received empty image from server');
                }
                
                const imageUrl = URL.createObjectURL(processedImageBlob);
                const img = new Image();
                
                img.onload = () => {
                    const ctx = this.canvas.getContext('2d', { alpha: false });
                    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
                    ctx.drawImage(
                        img, 
                        0, 0, 
                        this.canvas.width, 
                        this.canvas.height
                    );
                    
                    URL.revokeObjectURL(imageUrl);
                    this.isProcessing = false;
                    this.consecutiveErrors = 0;
                    this.updateFPSCounter();
                    this.loadingIndicator.style.display = 'none';
                    
                    if (this.isRunning) {
                        requestAnimationFrame(this.processVideo);
                    }
                };
                
                img.onerror = (e) => {
                    console.error('Error loading processed image:', e);
                    this.handleError('Error al cargar la imagen procesada');
                };
                
                img.src = imageUrl;
            } else {
                const errorText = await response.text();
                this.handleError(`Error del servidor: ${errorText}`);
            }
        } catch (error) {
            this.handleError(`Error en el procesamiento: ${error.message}`);
        }
    }

    handleError(message) {
        console.error(message);
        this.statusDiv.textContent = message;
        this.consecutiveErrors++;
        this.loadingIndicator.style.display = 'none';
        
        if (this.consecutiveErrors >= this.maxConsecutiveErrors) {
            this.showError('Error de Procesamiento', 
                'Demasiados errores consecutivos. Reiniciando la cámara...');
            this.restartCamera();
        } else {
            this.isProcessing = false;
            if (this.isRunning) {
                requestAnimationFrame(this.processVideo);
            }
        }
    }

    async restartCamera() {
        await this.stopCamera();
        this.consecutiveErrors = 0;
        await this.startCamera();
    }

    async startCamera(deviceId = null) {
        try {
            await this.stopCamera();

            const constraints = {
                video: {
                    deviceId: deviceId ? { exact: deviceId } : undefined,
                    width: { ideal: 320 },
                    height: { ideal: 240 },
                    facingMode: 'environment'
                }
            };

            this.stream = await navigator.mediaDevices.getUserMedia(constraints);
            this.video.srcObject = this.stream;
            
            this.video.onloadedmetadata = () => {
                const aspectRatio = this.video.videoWidth / this.video.videoHeight;
                this.canvas.width = 320;
                this.canvas.height = this.canvas.width / aspectRatio;
                
                this.backCanvas.width = this.canvas.width;
                this.backCanvas.height = this.canvas.height;
                
                this.canvas.style.width = '100%';
                this.canvas.style.maxWidth = '640px';
                this.canvas.style.height = 'auto';
                
                this.isRunning = true;
                this.startButton.disabled = true;
                this.stopButton.disabled = false;
                requestAnimationFrame(this.processVideo);
                this.statusDiv.textContent = 'Cámara iniciada, buscando marcadores...';
            };
        } catch (error) {
            console.error('Error accessing camera:', error);
            this.showError('Error de Cámara', 
                'No se pudo acceder a la cámara. Asegúrate de dar permisos de acceso.');
        }
    }

    async stopCamera() {
        this.isRunning = false;
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        this.video.srcObject = null;
        this.startButton.disabled = false;
        this.stopButton.disabled = true;
        this.statusDiv.textContent = 'Cámara detenida';
    }

    handleCameraChange(event) {
        if (event.target.value) {
            this.startCamera(event.target.value);
        }
    }

    async listCameras() {
        try {
            const devices = await navigator.mediaDevices.enumerateDevices();
            const videoDevices = devices.filter(device => device.kind === 'videoinput');
            
            this.cameraSelect.innerHTML = '';
            videoDevices.forEach(device => {
                const option = document.createElement('option');
                option.value = device.deviceId;
                option.text = device.label || `Cámara ${this.cameraSelect.length + 1}`;
                this.cameraSelect.appendChild(option);
            });
        } catch (error) {
            console.error('Error listing cameras:', error);
            this.showError('Error', 'No se pudieron listar las cámaras disponibles');
        }
    }

    async init() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            this.showError('Error de Acceso a la Cámara', [
                'Tu navegador no puede acceder a la cámara por una de estas razones:',
                'No estás usando HTTPS (requerido para acceder a la cámara)',
                'El navegador no soporta acceso a la cámara',
                'Prueba accediendo desde localhost o usando HTTPS'
            ]);
            return;
        }

        try {
            await navigator.mediaDevices.getUserMedia({ video: true });
            await this.listCameras();
        } catch (error) {
            console.error('Error initializing camera:', error);
            this.showError('Error', 
                'No se pudo acceder a la cámara. Verifica los permisos y la conexión HTTPS.');
        }

        // Limpieza al cerrar la página
        window.addEventListener('beforeunload', () => {
            if (this.stream) {
                this.stream.getTracks().forEach(track => track.stop());
            }
        });
    }
}

// Iniciar la aplicación cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    new ARScanner();
});