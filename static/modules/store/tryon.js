/* Óptica Matiz Visión — tryon.js
 * Probador Virtual 2D/3D con MediaPipe FaceMesh (Cámara en vivo + Subida de foto + Modelos demo).
 * Procesamiento 100% en el navegador (Ley N° 21.719 - Privacidad y Resguardo de Biometría).
 */
(function () {
  'use strict';

  var MV = window.MV || {};
  window.MV = MV;

  // Estado del Probador
  var state = {
    isOpen: false,
    mode: 'camera', // 'camera' | 'upload'
    currentProduct: null,
    allProducts: [],
    videoStream: null,
    faceMesh: null,
    cameraAnimId: null,
    isModelLoading: false,
    glassesImageCache: {},
    currentGlassesImg: null,
    scaleFactor: 1.0, // Control manual de calibre (+- 25%)
    offsetY: 0,       // Control manual de altura (+- 30px)
    staticImage: null,
    lastLandmarks: null,
    facingMode: 'user'
  };

  // Suavizado temporal de posición y orientación (evita temblores por ruido de cámara)
  var smoothTracker = {
    x: null,
    y: null,
    width: null,
    angle: null,
    reset: function () {
      this.x = null;
      this.y = null;
      this.width = null;
      this.angle = null;
    }
  };

  var MEDIAPIPE_SCRIPTS = [
    'https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js',
    'https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/face_mesh.js'
  ];

  function loadScript(url) {
    return new Promise(function (resolve, reject) {
      if (document.querySelector('script[src="' + url + '"]')) {
        resolve();
        return;
      }
      var s = document.createElement('script');
      s.src = url;
      s.crossOrigin = 'anonymous';
      s.onload = resolve;
      s.onerror = reject;
      document.head.appendChild(s);
    });
  }

  function ensureMediaPipe() {
    if (window.FaceMesh) return Promise.resolve();
    return Promise.all(MEDIAPIPE_SCRIPTS.map(loadScript));
  }

  // Pre-carga y cache de imágenes de armazones
  function preloadGlasses(url) {
    if (!url) return Promise.resolve(null);
    if (state.glassesImageCache[url]) {
      return Promise.resolve(state.glassesImageCache[url]);
    }
    return new Promise(function (resolve) {
      var img = new Image();
      img.crossOrigin = 'anonymous';
      img.onload = function () {
        state.glassesImageCache[url] = img;
        resolve(img);
      };
      img.onerror = function () {
        resolve(null);
      };
      img.src = url;
    });
  }

  // Creación del Modal del Probador en el DOM
  function createTryonModal() {
    var existing = document.getElementById('mv-tryon-overlay');
    if (existing) return existing;

    var overlay = document.createElement('div');
    overlay.id = 'mv-tryon-overlay';
    overlay.className = 'mv-tryon-overlay';
    overlay.style.display = 'none';

    overlay.innerHTML =
      '<div class="mv-tryon-card">' +
        '<!-- Header -->' +
        '<div class="mv-tryon-header">' +
          '<h3 class="mv-tryon-title"><i class="bi bi-camera-video-fill"></i> Probador Virtual <span>Matizvisión</span></h3>' +
          '<div class="mv-tryon-modes">' +
            '<button type="button" class="mv-tryon-mode-btn active" id="tryon-mode-cam"><i class="bi bi-camera-fill"></i> Cámara en vivo</button>' +
            '<button type="button" class="mv-tryon-mode-btn" id="tryon-mode-pic"><i class="bi bi-image"></i> Subir foto / Modelos</button>' +
          '</div>' +
          '<button type="button" class="mv-tryon-close" id="tryon-btn-close" aria-label="Cerrar"><i class="bi bi-x-lg"></i></button>' +
        '</div>' +

        '<!-- Stage Canvas -->' +
        '<div class="mv-tryon-stage" id="tryon-stage">' +
          '<div class="mv-tryon-loader" id="tryon-loader">' +
            '<div class="mv-tryon-spinner"></div>' +
            '<div id="tryon-loader-text">Iniciando motor de visión artificial…</div>' +
          '</div>' +
          '<canvas id="tryon-canvas"></canvas>' +
          '<video id="tryon-video" class="mv-tryon-video-hidden" playsinline muted></video>' +

          '<!-- Guía visual de rostro -->' +
          '<div class="mv-tryon-face-guide" id="tryon-face-guide"><span>Centra tu rostro aquí</span></div>' +

          '<!-- Floating Controls -->' +
          '<div class="mv-tryon-floating-controls">' +
            '<button type="button" class="mv-tryon-float-btn" id="tryon-btn-tune" title="Ajuste de calibre y altura"><i class="bi bi-sliders"></i></button>' +
            '<button type="button" class="mv-tryon-float-btn" id="tryon-btn-snapshot" title="Tomar foto y descargar"><i class="bi bi-camera"></i></button>' +
            '<button type="button" class="mv-tryon-float-btn" id="tryon-btn-flip" title="Cambiar cámara" style="display:none;"><i class="bi bi-arrow-repeat"></i></button>' +
          '</div>' +

          '<!-- Tuning Box -->' +
          '<div class="mv-tryon-tuning-box" id="tryon-tuning-box">' +
            '<div class="mv-tryon-tuning-title"><span>Micro-ajuste</span> <button type="button" class="btn-close btn-close-white" style="font-size:0.6rem;" id="tryon-close-tune"></button></div>' +
            '<div class="mv-tryon-tune-row">' +
              '<label><span>Tamaño / Calibre</span> <span id="val-scale">100%</span></label>' +
              '<input type="range" id="tune-scale" min="0.70" max="1.35" step="0.02" value="1.00" />' +
            '</div>' +
            '<div class="mv-tryon-tune-row mb-0">' +
              '<label><span>Altura nasal</span> <span id="val-height">0</span></label>' +
              '<input type="range" id="tune-height" min="-40" max="40" step="1" value="0" />' +
            '</div>' +
          '</div>' +

          '<!-- Upload & Demo Prompt -->' +
          '<div class="mv-tryon-upload-prompt" id="tryon-upload-prompt">' +
            '<i class="bi bi-cloud-arrow-up" style="font-size:2.8rem; color:var(--green-primary, #10B981);"></i>' +
            '<h4 style="font-weight:800; margin:0.3rem 0;">Pruébate los lentes con una foto</h4>' +
            '<p style="color:#9ca3af; font-size:0.86rem; max-width:400px; margin-bottom:0.8rem;">Sube tu selfie o usa uno de nuestros modelos de prueba para ver el estilo al instante:</p>' +
            '<label class="mv-tryon-upload-btn">' +
              '<i class="bi bi-file-earmark-image"></i> Subir mi propia foto / selfie' +
              '<input type="file" id="tryon-file-input" accept="image/*" style="display:none;" />' +
            '</label>' +
            '<div class="mv-tryon-demo-row">' +
              '<button type="button" class="mv-tryon-demo-btn" id="btn-demo-mujer"><i class="bi bi-person-heart"></i> Modelo Mujer</button>' +
              '<button type="button" class="mv-tryon-demo-btn" id="btn-demo-hombre"><i class="bi bi-person"></i> Modelo Hombre</button>' +
            '</div>' +
          '</div>' +
        '</div>' +

        '<!-- Footer Shelf -->' +
        '<div class="mv-tryon-footer">' +
          '<div class="mv-tryon-shelf-header">' +
            '<div class="mv-tryon-current-info">' +
              '<span class="mv-tryon-current-name" id="tryon-current-name">—</span>' +
              '<span class="mv-tryon-current-price" id="tryon-current-price">—</span>' +
            '</div>' +
            '<div class="d-flex gap-2">' +
              '<button type="button" class="btn btn-cta btn-sm" id="tryon-btn-action"><i class="bi bi-cart-plus"></i> Elegir este modelo</button>' +
            '</div>' +
          '</div>' +
          '<div class="mv-tryon-shelf-track" id="tryon-shelf-track"></div>' +
          '<div class="mv-tryon-action-bar">' +
            '<div class="mv-tryon-privacy-badge">' +
              '<i class="bi bi-shield-check"></i> 100% Privado: El procesamiento facial corre en tu navegador. Ninguna imagen se sube a internet (Ley N° 21.719).' +
            '</div>' +
          '</div>' +
        '</div>' +
      '</div>';

    document.body.appendChild(overlay);
    bindModalEvents(overlay);
    return overlay;
  }

  function bindModalEvents(overlay) {
    document.getElementById('tryon-btn-close').addEventListener('click', closeTryon);
    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) closeTryon();
    });

    // Modos
    var btnCam = document.getElementById('tryon-mode-cam');
    var btnPic = document.getElementById('tryon-mode-pic');
    btnCam.addEventListener('click', function () {
      if (state.mode === 'camera') return;
      setMode('camera');
    });
    btnPic.addEventListener('click', function () {
      if (state.mode === 'upload') return;
      setMode('upload');
    });

    // Tuning Box
    var btnTune = document.getElementById('tryon-btn-tune');
    var boxTune = document.getElementById('tryon-tuning-box');
    var closeTune = document.getElementById('tryon-close-tune');
    btnTune.addEventListener('click', function () {
      boxTune.classList.toggle('open');
    });
    if (closeTune) {
      closeTune.addEventListener('click', function () {
        boxTune.classList.remove('open');
      });
    }

    var tuneScale = document.getElementById('tune-scale');
    var valScale = document.getElementById('val-scale');
    tuneScale.addEventListener('input', function () {
      state.scaleFactor = parseFloat(tuneScale.value);
      valScale.textContent = Math.round(state.scaleFactor * 100) + '%';
      if (state.mode === 'upload' && state.lastLandmarks) {
        drawFrameStatic(state.lastLandmarks);
      }
    });

    var tuneHeight = document.getElementById('tune-height');
    var valHeight = document.getElementById('val-height');
    tuneHeight.addEventListener('input', function () {
      state.offsetY = parseInt(tuneHeight.value, 10);
      valHeight.textContent = (state.offsetY > 0 ? '+' : '') + state.offsetY + 'px';
      if (state.mode === 'upload' && state.lastLandmarks) {
        drawFrameStatic(state.lastLandmarks);
      }
    });

    // Snapshot
    document.getElementById('tryon-btn-snapshot').addEventListener('click', takeSnapshot);

    // Carga de foto propia
    var fileInput = document.getElementById('tryon-file-input');
    fileInput.addEventListener('change', function (e) {
      var file = e.target.files && e.target.files[0];
      if (!file) return;
      var reader = new FileReader();
      reader.onload = function (evt) {
        var img = new Image();
        img.onload = function () {
          state.staticImage = img;
          document.getElementById('tryon-upload-prompt').classList.remove('active');
          document.getElementById('tryon-canvas').style.display = 'block';
          processStaticImage(img);
        };
        img.src = evt.target.result;
      };
      reader.readAsDataURL(file);
    });

    // Carga de modelos demo
    function loadDemoImage(url) {
      showLoader('Cargando modelo de prueba…');
      var img = new Image();
      img.onload = function () {
        state.staticImage = img;
        document.getElementById('tryon-upload-prompt').classList.remove('active');
        document.getElementById('tryon-canvas').style.display = 'block';
        processStaticImage(img);
      };
      img.onerror = function () {
        hideLoader();
        if (MV.toast) MV.toast('No se pudo cargar el modelo demo.', 'error');
      };
      img.src = url;
    }

    var btnDemoM = document.getElementById('btn-demo-mujer');
    var btnDemoH = document.getElementById('btn-demo-hombre');
    if (btnDemoM) {
      btnDemoM.addEventListener('click', function () {
        loadDemoImage('/media/tryon/modelo_mujer.jpg');
      });
    }
    if (btnDemoH) {
      btnDemoH.addEventListener('click', function () {
        loadDemoImage('/media/tryon/modelo_hombre.jpg');
      });
    }

    // Switch camera (para teléfonos con múltiples cámaras)
    var btnFlip = document.getElementById('tryon-btn-flip');
    if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
      navigator.mediaDevices.enumerateDevices().then(function (devices) {
        var videoInputs = devices.filter(function (d) { return d.kind === 'videoinput'; });
        if (videoInputs.length > 1) {
          btnFlip.style.display = 'flex';
          btnFlip.addEventListener('click', function () {
            state.facingMode = (state.facingMode === 'user') ? 'environment' : 'user';
            stopCamera();
            startCamera();
          });
        }
      });
    }

    // Botón de acción (agregar al carrito / elegir lentes)
    document.getElementById('tryon-btn-action').addEventListener('click', function () {
      if (!state.currentProduct) return;
      var prod = state.currentProduct;
      closeTryon();

      var btnCfg = document.querySelector('.btn-add-config[data-id="' + prod.id + '"]');
      if (btnCfg) {
        btnCfg.click();
        return;
      }
      var btnAdd = document.querySelector('.btn-add[data-id="' + prod.id + '"]');
      if (btnAdd) {
        btnAdd.click();
        return;
      }

      if (MV.api) {
        MV.api.post('/orders/carrito/', { body: { producto: prod.id, cantidad: 1 } }).then(function (r) {
          if (r.ok) {
            if (MV.toast) MV.toast('"' + (prod.nombre || 'Lente') + '" agregado al carrito.', 'success');
            if (window.MV_updateCartSticky) window.MV_updateCartSticky();
            if (MV.refreshCartBadge) MV.refreshCartBadge();
          }
        });
      }
    });
  }

  // Cambio de modo (Cámara vs Subir Foto)
  function setMode(newMode) {
    smoothTracker.reset();
    state.mode = newMode;
    var btnCam = document.getElementById('tryon-mode-cam');
    var btnPic = document.getElementById('tryon-mode-pic');
    var uploadPrompt = document.getElementById('tryon-upload-prompt');
    var canvas = document.getElementById('tryon-canvas');

    if (newMode === 'camera') {
      btnCam.classList.add('active');
      btnPic.classList.remove('active');
      uploadPrompt.classList.remove('active');
      canvas.style.display = 'block';
      startCamera();
    } else {
      btnPic.classList.add('active');
      btnCam.classList.remove('active');
      stopCamera();
      if (!state.staticImage) {
        uploadPrompt.classList.add('active');
        canvas.style.display = 'none';
      } else {
        uploadPrompt.classList.remove('active');
        canvas.style.display = 'block';
        processStaticImage(state.staticImage);
      }
    }
  }

  // Inicializar MediaPipe FaceMesh
  function initFaceMesh() {
    if (state.faceMesh) return Promise.resolve(state.faceMesh);
    state.isModelLoading = true;
    showLoader('Cargando motor de detección facial…');

    return ensureMediaPipe().then(function () {
      var fm = new window.FaceMesh({
        locateFile: function (file) {
          return 'https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/' + file;
        }
      });
      fm.setOptions({
        maxNumFaces: 1,
        refineLandmarks: false, // Optimizado: desactiva sub-red innecesaria de iris para máximo rendimiento
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5
      });
      fm.onResults(onResults);
      state.faceMesh = fm;
      state.isModelLoading = false;
      hideLoader();
      return fm;
    }).catch(function (err) {
      state.isModelLoading = false;
      showLoader('No se pudo cargar el motor facial. Verifica tu conexión.');
      console.error('Error MediaPipe:', err);
    });
  }

  function showLoader(text) {
    var l = document.getElementById('tryon-loader');
    var t = document.getElementById('tryon-loader-text');
    if (l) l.style.display = 'flex';
    if (t) t.textContent = text;
  }
  function hideLoader() {
    var l = document.getElementById('tryon-loader');
    if (l) l.style.display = 'none';
  }

  // Iniciar Cámara en vivo
  function startCamera() {
    var video = document.getElementById('tryon-video');
    var guide = document.getElementById('tryon-face-guide');
    if (guide) guide.classList.remove('hidden');

    showLoader('Accediendo a la cámara…');

    initFaceMesh().then(function (fm) {
      if (!fm) return;
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        showLoader('Tu navegador no soporta acceso a la cámara. Prueba subiendo una foto.');
        return;
      }
      return navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 },
          facingMode: state.facingMode
        },
        audio: false
      }).then(function (stream) {
        state.videoStream = stream;
        video.srcObject = stream;
        video.onloadedmetadata = function () {
          video.play();
          hideLoader();
          loopCamera();
          // Ocultar guía suavemente tras 3.5 segundos
          setTimeout(function () {
            if (guide) guide.classList.add('hidden');
          }, 3500);
        };
      }).catch(function (err) {
        console.warn('Error cámara:', err);
        showLoader('No se pudo acceder a la cámara. Activa los permisos o sube una foto.');
        setTimeout(function () {
          setMode('upload');
        }, 2200);
      });
    });
  }

  function stopCamera() {
    smoothTracker.reset();
    if (state.cameraAnimId) {
      cancelAnimationFrame(state.cameraAnimId);
      state.cameraAnimId = null;
    }
    if (state.videoStream) {
      state.videoStream.getTracks().forEach(function (track) { track.stop(); });
      state.videoStream = null;
    }
    var video = document.getElementById('tryon-video');
    if (video) video.srcObject = null;
    var guide = document.getElementById('tryon-face-guide');
    if (guide) guide.classList.add('hidden');
  }

  // Renderizar fotograma de cámara y superposición de lentes a 60 FPS
  function renderCameraFrame(video) {
    var canvas = document.getElementById('tryon-canvas');
    if (!canvas || !video || video.videoWidth === 0) return;

    var vw = video.videoWidth;
    var vh = video.videoHeight;

    if (canvas.width !== vw || canvas.height !== vh) {
      canvas.width = vw;
      canvas.height = vh;
    }

    var ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Espejo para la cámara en vivo
    ctx.save();
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    ctx.restore();

    // Si ya detectamos el rostro, superponer los lentes de forma fluida
    if (state.lastLandmarks) {
      try {
        renderGlassesOnFace(ctx, canvas, state.lastLandmarks);
      } catch (err) {
        console.error('Error renderGlassesOnFace:', err);
      }
    }
  }

  var isSending = false;
  function loopCamera() {
    var video = document.getElementById('tryon-video');
    if (!state.isOpen || state.mode !== 'camera' || !video || video.paused || video.ended) return;

    // 1. Renderizar video continuo sin bloqueos
    renderCameraFrame(video);

    // 2. Procesar detección facial en segundo plano si MediaPipe está libre
    if (state.faceMesh && !isSending && video.readyState >= 2) {
      isSending = true;
      state.faceMesh.send({ image: video }).then(function () {
        isSending = false;
      }).catch(function (e) {
        isSending = false;
      });
    }
    state.cameraAnimId = requestAnimationFrame(loopCamera);
  }

  // Procesar Foto Estática (Upload o Demo)
  function processStaticImage(img) {
    showLoader('Detectando rostro en la foto…');
    initFaceMesh().then(function (fm) {
      if (!fm) return;
      fm.send({ image: img }).then(function () {
        hideLoader();
      });
    });
  }

  // Manejo de Resultados de Detección Facial
  function onResults(results) {
    var landmarks = (results.multiFaceLandmarks && results.multiFaceLandmarks.length > 0)
      ? results.multiFaceLandmarks[0]
      : null;

    state.lastLandmarks = landmarks;

    // En modo foto estática, refrescar el canvas con la foto y los lentes
    if (state.mode === 'upload') {
      if (!landmarks) {
        // Respaldo de puntos si es foto y no fue detectado por iluminación o ángulo
        landmarks = {
          33: { x: 0.40, y: 0.42 },
          263: { x: 0.60, y: 0.42 },
          168: { x: 0.50, y: 0.42 }
        };
        state.lastLandmarks = landmarks;
      }
      drawFrameStatic(landmarks);
    }
  }

  function drawFrameStatic(landmarks) {
    if (!state.staticImage) return;
    var canvas = document.getElementById('tryon-canvas');
    if (!canvas) return;
    var ctx = canvas.getContext('2d');
    var iw = state.staticImage.naturalWidth || state.staticImage.width;
    var ih = state.staticImage.naturalHeight || state.staticImage.height;
    if (iw && ih && (canvas.width !== iw || canvas.height !== ih)) {
      canvas.width = iw;
      canvas.height = ih;
    }
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(state.staticImage, 0, 0, canvas.width, canvas.height);
    if (landmarks) {
      try {
        renderGlassesOnFace(ctx, canvas, landmarks);
      } catch (e) {
        console.error('Error renderGlassesOnFace static:', e);
      }
    }
  }

  // Superposición del Armazón sobre los Puntos Faciales
  function renderGlassesOnFace(ctx, canvas, landmarks) {
    var glassesImg = state.currentGlassesImg;
    if (!glassesImg || !glassesImg.complete || !glassesImg.naturalWidth) return;

    var isMirror = (state.mode === 'camera');

    // Landmarks anatómicos clave de MediaPipe Face Mesh:
    // 33: esquina exterior del ojo derecho anatómico
    // 263: esquina exterior del ojo izquierdo anatómico
    // 168: puente nasal superior (entre los ojos)
    var lmRightAnat = landmarks[33];
    var lmLeftAnat = landmarks[263];
    var lmNose = landmarks[168] || landmarks[6] || { x: 0.5, y: 0.45 };

    if (!lmRightAnat || !lmLeftAnat) return;

    var screenLeftEye, screenRightEye;

    if (isMirror) {
      // En modo espejo (cámara frontal):
      // El canvas se dibuja con scale(-1, 1).
      // El ojo izquierdo del usuario (lm 263) queda visualmente a la IZQUIERDA de la pantalla (menor X).
      // El ojo derecho del usuario (lm 33) queda visualmente a la DERECHA de la pantalla (mayor X).
      screenLeftEye = {
        x: (1 - lmLeftAnat.x) * canvas.width,
        y: lmLeftAnat.y * canvas.height
      };
      screenRightEye = {
        x: (1 - lmRightAnat.x) * canvas.width,
        y: lmRightAnat.y * canvas.height
      };
    } else {
      // En modo foto estática / modelo demo (sin reflejo de espejo):
      // El ojo derecho del rostro (lm 33) está a la IZQUIERDA de la foto.
      // El ojo izquierdo del rostro (lm 263) está a la DERECHA de la foto.
      screenLeftEye = {
        x: lmRightAnat.x * canvas.width,
        y: lmRightAnat.y * canvas.height
      };
      screenRightEye = {
        x: lmLeftAnat.x * canvas.width,
        y: lmLeftAnat.y * canvas.height
      };
    }

    var ptNoseX = (isMirror ? (1 - lmNose.x) : lmNose.x) * canvas.width;
    var ptNoseY = lmNose.y * canvas.height;

    // Vector siempre de ojo izquierdo en pantalla -> ojo derecho en pantalla:
    // dx es SIEMPRE positivo cuando la cabeza está hacia arriba, evitando que los lentes giren 180° (al revés)
    var dx = screenRightEye.x - screenLeftEye.x;
    var dy = screenRightEye.y - screenLeftEye.y;
    var eyeDistance = Math.sqrt(dx * dx + dy * dy);
    if (!eyeDistance || isNaN(eyeDistance)) return;

    // Ángulo de inclinación natural de la cabeza (-π a +π, centrado en 0 rad)
    var targetAngle = Math.atan2(dy, dx);

    // Escala del armazón (calibre estándar balanceado)
    var baseScale = 1.95;
    var targetWidth = eyeDistance * baseScale * state.scaleFactor;
    var aspectRatio = glassesImg.naturalHeight / glassesImg.naturalWidth;
    var targetHeight = targetWidth * aspectRatio;

    // Posición central en el puente nasal
    var midEyesY = (screenLeftEye.y + screenRightEye.y) / 2;
    var targetX = ptNoseX;
    var targetY = (ptNoseY * 0.65 + midEyesY * 0.35) + state.offsetY;

    // Suavizado en tiempo real (evita vibraciones por ruido del sensor de la cámara)
    var renderX = targetX;
    var renderY = targetY;
    var renderWidth = targetWidth;
    var renderHeight = targetHeight;
    var renderAngle = targetAngle;

    if (state.mode === 'camera') {
      if (smoothTracker.x === null) {
        smoothTracker.x = targetX;
        smoothTracker.y = targetY;
        smoothTracker.width = targetWidth;
        smoothTracker.angle = targetAngle;
      } else {
        var alpha = 0.50;
        smoothTracker.x += (targetX - smoothTracker.x) * alpha;
        smoothTracker.y += (targetY - smoothTracker.y) * alpha;
        smoothTracker.width += (targetWidth - smoothTracker.width) * alpha;

        var dAngle = targetAngle - smoothTracker.angle;
        while (dAngle < -Math.PI) dAngle += Math.PI * 2;
        while (dAngle > Math.PI) dAngle -= Math.PI * 2;
        smoothTracker.angle += dAngle * alpha;
      }
      renderX = smoothTracker.x;
      renderY = smoothTracker.y;
      renderWidth = smoothTracker.width;
      renderHeight = renderWidth * aspectRatio;
      renderAngle = smoothTracker.angle;
    }

    // Renderizar armazón con rotación y escala correcta (derecho)
    ctx.save();
    ctx.translate(renderX, renderY);
    ctx.rotate(renderAngle);
    ctx.drawImage(glassesImg, -renderWidth / 2, -renderHeight / 2, renderWidth, renderHeight);
    ctx.restore();
  }

  // Snapshot (Capturar foto con los lentes puestos)
  function takeSnapshot() {
    var canvas = document.getElementById('tryon-canvas');
    if (!canvas) return;
    try {
      var dataUrl = canvas.toDataURL('image/png');
      var a = document.createElement('a');
      a.href = dataUrl;
      var prodName = (state.currentProduct && state.currentProduct.nombre)
        ? state.currentProduct.nombre.toLowerCase().replace(/\s+/g, '_')
        : 'look';
      a.download = 'matizvision_' + prodName + '.png';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      if (MV.toast) MV.toast('¡Foto guardada con éxito!', 'success');
    } catch (e) {
      console.warn('Error snapshot:', e);
      if (MV.toast) MV.toast('No se pudo guardar la captura.', 'error');
    }
  }

  // Actualizar armazón activo en el probador
  function selectProduct(prod) {
    smoothTracker.reset();
    state.currentProduct = prod;

    // Actualizar labels
    var nameEl = document.getElementById('tryon-current-name');
    var priceEl = document.getElementById('tryon-current-price');
    var btnAction = document.getElementById('tryon-btn-action');
    var fmt = new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 });

    if (nameEl) nameEl.textContent = prod.nombre || 'Lente Óptico';
    if (priceEl) priceEl.textContent = fmt.format(Number(prod.precio) || 0);

    if (btnAction) {
      if (prod.configurable_lente) {
        btnAction.innerHTML = '<i class="bi bi-bullseye"></i> Configurar graduación';
      } else {
        btnAction.innerHTML = '<i class="bi bi-cart-plus"></i> Agregar al carrito';
      }
    }

    // Actualizar miniatura activa en el carrusel
    var thumbs = document.querySelectorAll('.mv-tryon-thumb');
    thumbs.forEach(function (t) {
      t.classList.toggle('active', String(t.dataset.id) === String(prod.id));
    });

    // Cargar imagen de tryon
    var imgUrl = prod.imagen_tryon_url || prod.imagen_url;
    preloadGlasses(imgUrl).then(function (img) {
      state.currentGlassesImg = img;
      if (state.mode === 'upload' && state.lastLandmarks) {
        drawFrameStatic(state.lastLandmarks);
      }
    });
  }

  // Renderizar carrusel inferior de armazones
  function renderShelf(products, currentId) {
    var track = document.getElementById('tryon-shelf-track');
    if (!track) return;

    var candidates = products.filter(function (p) {
      var cat = (p.categoria_nombre || '').toLowerCase();
      return (cat.indexOf('armaz') !== -1 || cat.indexOf('sol') !== -1 || p.imagen_tryon_url || p.configurable_lente);
    });

    if (!candidates.length) candidates = products;

    track.innerHTML = candidates.map(function (p) {
      var activeClass = (String(p.id) === String(currentId)) ? ' active' : '';
      var img = p.imagen_tryon_url || p.imagen_url || '';
      return '<div class="mv-tryon-thumb' + activeClass + '" data-id="' + p.id + '">' +
        (img ? '<img src="' + img + '" alt="' + (p.nombre || '') + '" loading="lazy" />' : '<span>👓</span>') +
        '<span>' + (p.nombre || '') + '</span>' +
      '</div>';
    }).join('');

    track.querySelectorAll('.mv-tryon-thumb').forEach(function (thumb) {
      thumb.addEventListener('click', function () {
        var id = thumb.dataset.id;
        var found = candidates.find(function (x) { return String(x.id) === String(id); });
        if (found) selectProduct(found);
      });
    });
  }

  // Abrir el Probador Virtual
  function openTryon(product, allProducts) {
    createTryonModal();
    var overlay = document.getElementById('mv-tryon-overlay');
    overlay.style.display = 'flex';
    state.isOpen = true;
    state.allProducts = allProducts || [product];

    renderShelf(state.allProducts, product.id);
    selectProduct(product);

    setMode(state.mode || 'camera');
  }

  // Cerrar el Probador
  function closeTryon() {
    smoothTracker.reset();
    var overlay = document.getElementById('mv-tryon-overlay');
    if (overlay) overlay.style.display = 'none';
    state.isOpen = false;
    stopCamera();
    var tuning = document.getElementById('tryon-tuning-box');
    if (tuning) tuning.classList.remove('open');
  }

  // Exportar funciones en window.MV
  MV.openTryon = openTryon;
  MV.closeTryon = closeTryon;
})();
