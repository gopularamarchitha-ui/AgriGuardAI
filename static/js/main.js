let selectedCrop = 'Tomato';
let selectedFile = null;
let currentLanguage = 'Telugu';
let cameraStream = null;
let cameraFacingMode = 'environment'; // Default rear camera on mobile
let tempCapturedBlob = null;
let speechRecognizer = null;
let isListening = false;

// 1. MULTI-PAGE NAVIGATION
function navTo(pageId) {
  document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.bnav-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.page-view').forEach(view => view.classList.remove('active'));

  const activeHeaderBtn = document.querySelector(`.nav-btn[data-target="${pageId}"]`);
  if (activeHeaderBtn) activeHeaderBtn.classList.add('active');

  const activeBottomBtn = document.querySelector(`.bnav-btn[data-target="${pageId}"]`);
  if (activeBottomBtn) activeBottomBtn.classList.add('active');

  const page = document.getElementById(`page-${pageId}`);
  if (page) page.classList.add('active');

  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function selectCrop(cropName) {
  selectedCrop = cropName;
  document.querySelectorAll('.crop-chip').forEach(chip => {
    chip.classList.remove('active');
    if (chip.getAttribute('data-crop') === cropName) {
      chip.classList.add('active');
    }
  });
}

function onLanguageChange() {
  const langSelect = document.getElementById('langSelect');
  if (langSelect) {
    currentLanguage = langSelect.value;
  }
}

// 2. REAL BROWSER CAMERA CAPTURE (MOBILE & DESKTOP WEBCAM)
function triggerCameraCapture() {
  const modal = document.getElementById('cameraModal');
  if (modal) modal.classList.remove('hidden');

  // Reset Camera UI state
  document.getElementById('cameraErrorBox').classList.add('hidden');
  document.getElementById('cameraViewportContainer').classList.remove('hidden');
  document.getElementById('liveStreamView').classList.remove('hidden');
  document.getElementById('capturedPreviewView').classList.add('hidden');
  document.getElementById('liveControls').classList.remove('hidden');
  document.getElementById('capturedControls').classList.add('hidden');
  tempCapturedBlob = null;

  startCameraStream();
}

function closeCameraModal() {
  const modal = document.getElementById('cameraModal');
  if (modal) modal.classList.add('hidden');
  stopCameraStream();
}

async function startCameraStream() {
  stopCameraStream();

  const errBox = document.getElementById('cameraErrorBox');
  const errText = document.getElementById('cameraErrorMessage');
  const viewport = document.getElementById('cameraViewportContainer');
  const liveCtrls = document.getElementById('liveControls');

  // Requirement 10: Graceful fallback check for browser support
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    if (viewport) viewport.classList.add('hidden');
    if (liveCtrls) liveCtrls.classList.add('hidden');
    if (errBox) errBox.classList.remove('hidden');
    if (errText) {
      errText.textContent = "Your browser does not support direct camera capture. Please use Upload Leaf Image instead.";
    }
    return;
  }

  try {
    const constraints = {
      video: {
        facingMode: { ideal: cameraFacingMode },
        width: { ideal: 1280 },
        height: { ideal: 720 }
      }
    };

    cameraStream = await navigator.mediaDevices.getUserMedia(constraints);
    const video = document.getElementById('cameraVideo');
    if (video) {
      video.srcObject = cameraStream;
      await video.play().catch(e => console.log('Video play error:', e));
    }

    // Check if multiple camera devices exist to show flip button
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoDevices = devices.filter(d => d.kind === 'videoinput');
      const flipBtn = document.getElementById('toggleCameraBtn');
      if (flipBtn) {
        if (videoDevices.length > 1) {
          flipBtn.classList.remove('hidden');
        } else {
          flipBtn.classList.add('hidden');
        }
      }
    } catch (e) {
      console.log('Error enumerating video devices:', e);
    }

  } catch (err) {
    console.error('Camera stream access error:', err);
    if (viewport) viewport.classList.add('hidden');
    if (liveCtrls) liveCtrls.classList.add('hidden');
    if (errBox) errBox.classList.remove('hidden');

    // Requirement 4: Camera Permission Denied Error Handling
    if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
      if (errText) {
        errText.innerHTML = "📷 <strong>Camera access is blocked.</strong><br>Please allow camera permission in your browser settings and try again.";
      }
    } else {
      if (errText) {
        errText.textContent = `Unable to access device camera (${err.message || 'Camera Error'}). Please use Upload Leaf Image instead.`;
      }
    }
  }
}

function stopCameraStream() {
  if (cameraStream) {
    cameraStream.getTracks().forEach(track => track.stop());
    cameraStream = null;
  }
}

function switchCameraFacing() {
  cameraFacingMode = cameraFacingMode === 'environment' ? 'user' : 'environment';
  startCameraStream();
}

// Requirement 6 & 7: Live camera capture & Preview with "Is this leaf image clear?"
function takeCameraPhoto() {
  const video = document.getElementById('cameraVideo');
  const canvas = document.getElementById('cameraCanvas');
  if (!video || !canvas) return;

  const width = video.videoWidth || 640;
  const height = video.videoHeight || 480;
  canvas.width = width;
  canvas.height = height;

  const ctx = canvas.getContext('2d');
  ctx.drawImage(video, 0, 0, width, height);

  canvas.toBlob((blob) => {
    tempCapturedBlob = blob;
    const capturedImg = document.getElementById('cameraCapturedImg');
    if (capturedImg) capturedImg.src = URL.createObjectURL(blob);

    // Switch UI to captured photo preview mode
    document.getElementById('liveStreamView').classList.add('hidden');
    document.getElementById('capturedPreviewView').classList.remove('hidden');
    document.getElementById('liveControls').classList.add('hidden');
    document.getElementById('capturedControls').classList.remove('hidden');
  }, 'image/jpeg', 0.92);
}

function retakeCameraPhoto() {
  tempCapturedBlob = null;
  document.getElementById('capturedPreviewView').classList.add('hidden');
  document.getElementById('liveStreamView').classList.remove('hidden');
  document.getElementById('capturedControls').classList.add('hidden');
  document.getElementById('liveControls').classList.remove('hidden');
}

function useCapturedPhoto() {
  if (!tempCapturedBlob) return;

  // Set captured blob as active selectedFile
  selectedFile = new File([tempCapturedBlob], "captured_leaf.jpg", { type: "image/jpeg" });

  const previewImg = document.getElementById('leafPreviewImg');
  const placeholder = document.getElementById('noImagePlaceholder');
  const previewBox = document.getElementById('imagePreviewBox');

  if (previewImg) previewImg.src = URL.createObjectURL(tempCapturedBlob);
  if (placeholder) placeholder.classList.add('hidden');
  if (previewBox) previewBox.classList.remove('hidden');

  closeCameraModal();
  navTo('diagnose');
}

// 3. FILE UPLOAD HANDLING
function triggerFileUpload() {
  const input = document.getElementById('fileUploadInput');
  if (input) input.click();
}

function handleFilePicked(event) {
  const files = event.target.files;
  if (files && files[0]) {
    selectedFile = files[0];
    const reader = new FileReader();
    reader.onload = function (e) {
      const img = document.getElementById('leafPreviewImg');
      const placeholder = document.getElementById('noImagePlaceholder');
      const box = document.getElementById('imagePreviewBox');

      if (img) img.src = e.target.result;
      if (placeholder) placeholder.classList.add('hidden');
      if (box) box.classList.remove('hidden');

      navTo('diagnose');
    };
    reader.readAsDataURL(selectedFile);
  }
}

// 4. FARMER VOICE INPUT (WEB SPEECH RECOGNITION API)
function toggleSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  if (!SpeechRecognition) {
    alert('మరొక బ్రౌజర్ ప్రయత్నించండి: మీ బ్రౌజర్‌లో మైక్రోఫోన్ వాయిస్ గుర్తింపు సపోర్ట్ లేదు. దయచేసి క్రింద ఉన్న బాక్స్‌లో ప్రశ్నను టైప్ చేయండి.\n(Web Speech Recognition is not supported in this browser. Please type your question below.)');
    return;
  }

  if (isListening) {
    stopSpeechRecognition();
    return;
  }

  try {
    speechRecognizer = new SpeechRecognition();
    speechRecognizer.continuous = false;
    speechRecognizer.interimResults = false;

    // Set speech language based on selection or Telugu default
    speechRecognizer.lang = currentLanguage === 'Telugu' ? 'te-IN' : 'en-US';

    speechRecognizer.onstart = function () {
      isListening = true;
      document.getElementById('listeningIndicator').classList.remove('hidden');
      document.getElementById('micBtnText').textContent = '🔴 వింటున్నాము... (Stop)';
      document.getElementById('micBtn').classList.add('recording');
    };

    speechRecognizer.onresult = function (event) {
      const transcript = event.results[0][0].transcript;
      console.log('Recognized speech:', transcript);

      document.getElementById('transcriptText').textContent = transcript;
      document.getElementById('transcriptBox').classList.remove('hidden');
      document.getElementById('voiceQueryInput').value = transcript;

      // Auto submit voice query
      submitVoiceTextQuery(transcript);
    };

    speechRecognizer.onerror = function (event) {
      console.error('Speech recognition error:', event.error);
      stopSpeechRecognition();
      if (event.error === 'not-allowed') {
        alert('📷 మైక్రోఫోన్ అనుమతి తిరస్కరించబడింది. దయచేసి బ్రౌజర్ సెట్టింగ్స్‌లో మైక్రోఫోన్ అనుమతి ఇవ్వండి.\n(Microphone access blocked. Please allow permission.)');
      }
    };

    speechRecognizer.onend = function () {
      stopSpeechRecognition();
    };

    speechRecognizer.start();

  } catch (err) {
    console.error('Speech recognition exception:', err);
    stopSpeechRecognition();
  }
}

function stopSpeechRecognition() {
  isListening = false;
  if (speechRecognizer) {
    try { speechRecognizer.stop(); } catch (e) { }
    speechRecognizer = null;
  }
  const ind = document.getElementById('listeningIndicator');
  if (ind) ind.classList.add('hidden');

  const btnText = document.getElementById('micBtnText');
  if (btnText) btnText.textContent = '🎙️ నొక్కి మాట్లాడండి (Tap to Speak)';

  const btn = document.getElementById('micBtn');
  if (btn) btn.classList.remove('recording');
}

async function submitVoiceTextQuery(providedQuery) {
  const queryInput = document.getElementById('voiceQueryInput');
  const question = providedQuery || (queryInput ? queryInput.value.trim() : '');

  if (!question) {
    alert('దయచేసి మీ ప్రశ్నను మాట్లాడండి లేదా టైప్ చేయండి.\n(Please speak or type your question first.)');
    return;
  }

  const city = document.getElementById('citySelect') ? document.getElementById('citySelect').value : 'Hyderabad';
  const lang = currentLanguage;

  const resultCard = document.getElementById('voiceResultCard');
  const ansSummary = document.getElementById('voiceAnswerSummary');

  if (ansSummary) ansSummary.textContent = 'AgriGuard AI సమాధానం సేకరిస్తోంది... (Processing answer...)';
  if (resultCard) resultCard.classList.remove('hidden');

  try {
    const response = await fetch('/voice_query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: question, city: city, language: lang, crop: selectedCrop })
    });

    const data = await response.json();

    if (data.status === 'ERROR') {
      alert('Error: ' + data.message);
      return;
    }

    renderVoiceResponse(data);
    saveVoiceToHistory(data);

  } catch (err) {
    console.error('Voice query execution error:', err);
    alert('నెట్‌వర్క్ లోపం జరిగింది. దయచేసి మళ్లీ ప్రయత్నించండి.\n(Network error. Please try again.)');
  }
}

function renderVoiceResponse(data) {
  const adv = data.telugu_advisory || data.advisory || {};
  const audioPath = data.audio_path;

  document.getElementById('voiceAnswerSummary').textContent = adv.summary || 'సమాధాన సిద్ధంగా ఉంది.';

  const actionsList = document.getElementById('voiceActionsList');
  actionsList.innerHTML = '';
  (adv.actions || []).forEach(act => {
    const li = document.createElement('li');
    li.textContent = act;
    actionsList.appendChild(li);
  });

  const treatText = document.getElementById('voiceTreatmentText');
  if (treatText) {
    treatText.textContent = adv.treatment || 'ఈ వ్యాధికి నిర్దిష్ట పురుగుమందు సూచన ఇవ్వడానికి ధృవీకరించిన సమాచారం అందుబాటులో లేదు. స్థానిక వ్యవసాయ అధికారిని సంప్రదించండి.';
  }

  // Audio handling
  const voiceAudio = document.getElementById('voiceAudio');
  if (voiceAudio && audioPath) {
    voiceAudio.src = `/${audioPath}`;
    const autoPlayChk = document.getElementById('voiceAutoplayChk');
    if (autoPlayChk && autoPlayChk.checked) {
      voiceAudio.play().catch(e => console.log('Autoplay blocked by browser policy:', e));
    }
  }
}

// 5. CROP LEAF ANALYSIS EXECUTION
async function startAnalysis() {
  if (!selectedFile) {
    alert('దయచేసి ఆకు ఫోటోను ఎంచుకోండి లేదా కెమెరాతో తీయండి.\n(Please capture or upload a leaf photo first.)');
    return;
  }

  const overlay = document.getElementById('analysisProgressOverlay');
  if (overlay) overlay.classList.remove('hidden');

  animateWorkflowSteps();

  const city = document.getElementById('citySelect').value;
  const language = currentLanguage;

  const formData = new FormData();
  formData.append('image', selectedFile);
  formData.append('city', city);
  formData.append('language', language);

  try {
    const response = await fetch('/analyze', {
      method: 'POST',
      body: formData
    });

    const data = await response.json();
    if (overlay) overlay.classList.add('hidden');

    if (data.status === 'ERROR') {
      alert('Analysis Error: ' + data.message);
      return;
    }

    renderResultPage(data);
    saveToHistory(data);
    navTo('result');

  } catch (err) {
    console.error('Analysis execution error:', err);
    if (overlay) overlay.classList.add('hidden');
    alert('An unexpected network error occurred. Please try again.');
  }
}

function animateWorkflowSteps() {
  const steps = [1, 2, 3, 4, 5, 6, 7];
  steps.forEach((s, idx) => {
    setTimeout(() => {
      const stepElem = document.getElementById(`wf-step-${s}`);
      if (stepElem) stepElem.classList.add('active');
    }, idx * 350);
  });
}

function translateEnglishActionToTelugu(text) {
  if (!text) return "";
  if (text.includes("Scout leaves")) return "ఆకుల అడుగు భాగాన్ని మరియు కాండాన్ని నిశితంగా పరిశీలించండి.";
  if (text.includes("Ensure adequate drainage")) return "పొలంలో నీరు నిల్వ ఉండకుండా తగినంత డ్రైనేజీ ఏర్పాటు చేయండి.";
  if (text.includes("Take additional photos")) return "మంచి వెలుతురు ఉన్న సమయంలో ఆకు ఫోటోను స్పష్టంగా తీసి మళ్లీ విశ్లేషించండి.";
  if (text.includes("Inspect lower")) return "కింది మరియు మధ్య ఆకులపై వ్యాధి మచ్చల వ్యాప్తిని పరిశీలించండి.";
  if (text.includes("Ensure drip irrigation")) return "సాయంత్రం వేళల్లో ఆకులపై తేమ నిల్వ ఉండకుండా ఉదయపు వేళల్లో మాత్రమే నీరు పారించండి.";
  if (text.includes("Maintain adequate plant spacing")) return "మొక్కల మధ్య తగినంత గాలి వెలుతురు ప్రసరించేలా ప్లాంట్ స్పేసింగ్ నిర్వహించండి.";
  if (text.includes("Consult local extension")) return "అధీకృత రసాయన మందుల కోసం స్థానిక వ్యవసాయ విస్తరణ అధికారిని సంప్రదించండి.";
  if (text.includes("Avoid overhead sprinkler")) return "అధిక తేమ ఉన్న సమయాల్లో పైనుండి నీరు చిలకరించడం నివారించండి.";
  if (text.includes("Do not apply unverified")) return "స్థానిక ఉత్పత్తి లేబుల్స్ పరిశీలించకుండా ధృవీకరించని రసాయనాలను స్ప్రే చేయకండి.";
  return text;
}

function renderResultPage(data) {
  const pred = data.prediction_info || {};
  const telugu = data.telugu_advisory;
  const adv = (currentLanguage === 'Telugu' && telugu) ? telugu : (data.advisory || {});
  const weather = data.weather || {};
  const audioPath = data.audio_path;

  // Update Section Sub-headings & Safety Banner dynamically by selected language
  const introElem = document.getElementById('advisoryIntroText');
  if (introElem) {
    introElem.textContent = (currentLanguage === 'Telugu')
      ? 'పొలం యాజమాన్యం మరియు సేంద్రీయ/రసాయనేతర ముందస్తు జాగ్రత్తలు:'
      : 'Practical field management and preventive non-chemical steps:';
  }

  const safetyElem = document.getElementById('safetyNoticeText');
  if (safetyElem) {
    safetyElem.innerHTML = (currentLanguage === 'Telugu')
      ? '<strong>ముఖ్యమైన భద్రతా హెచ్చరిక:</strong> ధృవీకరించని రసాయన మందులను స్ప్రే చేయకండి. స్థానిక వ్యవసాయ నిపుణుల సలహా మేరకు మాత్రమే మందులను వాడండి.'
      : '<strong>Mandatory Safety Notice:</strong> Never apply unverified chemical sprays. Only use formulations supported by approved product labels and regional agricultural authority guidance.';
  }

  // 1. Low confidence alert check (<60%)
  const lowConfAlert = document.getElementById('lowConfidenceAlert');
  if (data.status === 'LOW_CONFIDENCE' || pred.status === 'LOW_CONFIDENCE' || (pred.confidence && pred.confidence < 60.0)) {
    lowConfAlert.classList.remove('hidden');
  } else {
    lowConfAlert.classList.add('hidden');
  }

  // 2. Metrics
  document.getElementById('resCropName').textContent = `${pred.crop || selectedCrop}`;
  document.getElementById('resConditionName').textContent = `${pred.disease || 'Uncertain'}`;

  const confVal = pred.confidence || 0;
  document.getElementById('resConfidenceScore').textContent = `${confVal}%`;
  document.getElementById('resConfidenceBar').style.width = `${confVal}%`;

  // 3. What it means
  let summaryText = adv.summary || `ఏఐ విశ్లేషణలో ${pred.crop || ''} ఆకుపై ${pred.disease || ''} సంకేతాలు గుర్తించబడ్డాయి.`;
  if (currentLanguage === 'Telugu' && /^[A-Za-z\s.,]+$/.test(summaryText)) {
    summaryText = "పంట ఆకు ఆరోగ్య పరిశీలన మరియు విశ్లేషణ నివేదిక సిద్ధంగా ఉంది.";
  }
  document.getElementById('resWhatItMeans').textContent = summaryText;

  // 4. Actions & Prevention
  const preventionList = document.getElementById('preventionActionsList');
  preventionList.innerHTML = '';
  let actions = adv.actions || [
    "పొలంలో ఆకుల పరిస్థితిని మరియు వ్యాధి వ్యాప్తిని రోజూ గమనించండి.",
    "మొక్కల మధ్య తగినంత గాలి వెలుతురు ప్రసరించేలా చూడండి.",
    "సూర్యోదయ సమయంలో నీరు పారించండి, ఆకులపై నీరు నిల్వ ఉండకుండా చూడండి."
  ];

  if (currentLanguage === 'Telugu') {
    actions = actions.map(act => translateEnglishActionToTelugu(act));
  }

  actions.forEach(act => {
    const li = document.createElement('li');
    li.textContent = act;
    preventionList.appendChild(li);
  });

  // 5. Treatment advice (with strict safety check)
  const chemText = document.getElementById('chemicalAdviceText');
  if (chemText) {
    let treatVal = adv.treatment || 'ఈ వ్యాధికి నిర్దిష్ట పురుగుమందు సూచన ఇవ్వడానికి ధృవీకరించిన సమాచారం అందుబాటులో లేదు. స్థానిక వ్యవసాయ అధికారి లేదా అధీకృత వ్యవసాయ నిపుణుడిని సంప్రదించండి.';
    if (currentLanguage === 'Telugu' && /^[A-Za-z\s.,]+$/.test(treatVal)) {
      treatVal = 'ఈ వ్యాధికి నిర్దిష్ట పురుగుమందు సూచన ఇవ్వడానికి ధృవీకరించిన సమాచారం అందుబాటులో లేదు. స్థానిక వ్యవసాయ అధికారి లేదా అధీకృత వ్యవసాయ నిపుణుడిని సంప్రదించండి.';
    }
    chemText.textContent = treatVal;
  }

  // 6. Weather context
  document.getElementById('wCity').textContent = weather.city || 'Local';
  document.getElementById('wTemp').textContent = `${weather.temperature_c || 'N/A'}°C`;
  document.getElementById('wHumidity').textContent = `${weather.humidity_percent || 'N/A'}%`;
  document.getElementById('wRain').textContent = `${weather.precipitation_mm || '0'} mm`;

  let weatherNote = adv.weather_context || 'వాతావరణంలో తేమ శాతం ఎక్కువగా ఉన్నప్పుడు వ్యాధుల తీవ్రత పెరుగుతుంది.';
  if (currentLanguage === 'Telugu' && /^[A-Za-z\s.,]+$/.test(weatherNote)) {
    weatherNote = 'వాతావరణంలో తేమ శాతం ఎక్కువగా ఉన్నప్పుడు వ్యాధుల తీవ్రత పెరుగుతుంది.';
  }
  document.getElementById('wImpactNote').textContent = weatherNote;

  // 7. Telugu Audio Player
  const audioPlayer = document.getElementById('teluguAudio');
  if (audioPlayer && audioPath) {
    audioPlayer.src = `/${audioPath}`;
    const autoPlayChk = document.getElementById('teluguAutoplayChk');
    if (autoPlayChk && autoPlayChk.checked) {
      audioPlayer.play().catch(e => console.log('Autoplay blocked by browser policy:', e));
    }
  }
}

// AUDIO CONTROLS
function playTeluguAudio(audioId) {
  const audio = document.getElementById(audioId);
  if (audio && audio.src) {
    audio.play().catch(e => console.log('Audio play error:', e));
  }
}

function pauseTeluguAudio(audioId) {
  const audio = document.getElementById(audioId);
  if (audio) {
    audio.pause();
  }
}

function replayTeluguAudio(audioId) {
  const audio = document.getElementById(audioId);
  if (audio && audio.src) {
    audio.currentTime = 0;
    audio.play().catch(e => console.log('Audio replay error:', e));
  }
}

// LOCAL STORAGE HISTORY
function saveToHistory(data) {
  try {
    const pred = data.prediction_info || {};
    const item = {
      type: 'diagnosis',
      date: new Date().toLocaleDateString(),
      crop: pred.crop || selectedCrop,
      disease: pred.disease || 'Uncertain',
      confidence: pred.confidence || 0,
      summary: data.telugu_advisory?.summary || data.advisory?.summary || ''
    };

    let history = JSON.parse(localStorage.getItem('agriguard_history') || '[]');
    history.unshift(item);
    history = history.slice(0, 10);
    localStorage.setItem('agriguard_history', JSON.stringify(history));

    renderHistory();
  } catch (e) {
    console.error('Failed to save history to localStorage:', e);
  }
}

function saveVoiceToHistory(data) {
  try {
    const item = {
      type: 'voice_query',
      date: new Date().toLocaleDateString(),
      question: data.question || '',
      summary: data.telugu_advisory?.summary || data.advisory?.summary || ''
    };

    let history = JSON.parse(localStorage.getItem('agriguard_history') || '[]');
    history.unshift(item);
    history = history.slice(0, 10);
    localStorage.setItem('agriguard_history', JSON.stringify(history));

    renderHistory();
  } catch (e) {
    console.error('Failed to save voice history to localStorage:', e);
  }
}

function renderHistory() {
  const container = document.getElementById('historyListContainer');
  const emptyNotice = document.getElementById('emptyHistoryNotice');
  if (!container) return;

  try {
    const history = JSON.parse(localStorage.getItem('agriguard_history') || '[]');
    if (history.length === 0) {
      if (emptyNotice) emptyNotice.classList.remove('hidden');
      return;
    }

    if (emptyNotice) emptyNotice.classList.add('hidden');
    container.innerHTML = '';

    history.forEach(item => {
      const div = document.createElement('div');
      div.className = 'history-item-card';
      if (item.type === 'voice_query') {
        div.innerHTML = `
          <div style="font-size:0.75rem; color:#64748b; font-weight:700;">🎙️ ${item.date} (Voice Question)</div>
          <h4 style="font-size:0.95rem; color:#064e3b; margin:4px 0;">"${item.question}"</h4>
          <p style="font-size:0.85rem; color:#475569; margin-top:4px;">${item.summary}</p>
        `;
      } else {
        div.innerHTML = `
          <div style="font-size:0.75rem; color:#64748b; font-weight:700;">🌱 ${item.date}</div>
          <h4 style="font-size:1rem; color:#064e3b; margin:4px 0;">${item.crop} — ${item.disease}</h4>
          <div style="font-size:0.85rem; color:#059669; font-weight:700;">Confidence: ${item.confidence}%</div>
          <p style="font-size:0.82rem; color:#475569; margin-top:4px;">${item.summary}</p>
        `;
      }
      container.appendChild(div);
    });
  } catch (e) {
    console.error('Failed to render history:', e);
  }
}

// Initialize history on page load
document.addEventListener('DOMContentLoaded', () => {
  renderHistory();
});
