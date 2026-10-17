// Voice Assistant module with Web Speech API (STT & TTS) supporting Telugu, Hindi, and English
import { translations } from '../i18n/translations.js';

export function initializeVoiceAssistant() {
  const triggerBtns = [
    document.getElementById('header-voice-btn'),
    document.getElementById('fab-voice-btn'),
    document.getElementById('hero-voice-chip')
  ];
  const modal = document.getElementById('voice-modal');
  const closeModal = document.getElementById('close-voice-modal');
  const micButton = document.getElementById('voice-mic-action-btn');
  const micStatus = document.getElementById('voice-mic-status');
  const transcriptBox = document.getElementById('voice-transcript-output');
  const aiAnswerBox = document.getElementById('voice-ai-answer');
  const sampleChips = document.querySelectorAll('.sample-voice-chip');

  if (!modal) return;

  const openModal = () => {
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    document.body.classList.add('overflow-hidden');
    updateVoiceModalLang();
  };

  const hideModal = () => {
    modal.classList.add('hidden');
    modal.classList.remove('flex');
    document.body.classList.remove('overflow-hidden');
    stopListening();
  };

  triggerBtns.forEach(btn => {
    if (btn) btn.addEventListener('click', openModal);
  });

  if (closeModal) closeModal.addEventListener('click', hideModal);
  modal.addEventListener('click', (e) => {
    if (e.target === modal) hideModal();
  });

  // Speech Recognition setup
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  let recognition = null;
  let isListening = false;

  if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;

    recognition.onstart = () => {
      isListening = true;
      micButton.classList.add('animate-pulse', 'bg-rose-600', 'ring-8', 'ring-rose-200');
      const lang = window.currentLanguage || 'en';
      micStatus.textContent = lang === 'te' 
        ? "శ్రద్ధగా వింటున్నాను... మాట్లాడండి (Listening in Telugu)..." 
        : lang === 'hi' 
        ? "सुन रहा हूँ... बोलिए (Listening in Hindi)..." 
        : "Listening... Speak in English, Telugu, or Hindi...";
    };

    recognition.onresult = (event) => {
      let interimTranscript = '';
      let finalTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          finalTranscript += event.results[i][0].transcript;
        } else {
          interimTranscript += event.results[i][0].transcript;
        }
      }

      const display = finalTranscript || interimTranscript;
      if (transcriptBox) transcriptBox.textContent = `"${display}"`;

      if (finalTranscript) {
        processVoiceCommand(finalTranscript);
      }
    };

    recognition.onerror = (event) => {
      console.warn("Speech recognition error:", event.error);
      micStatus.textContent = `Mic status: ${event.error}. You can also click sample queries below!`;
      stopListening();
    };

    recognition.onend = () => {
      stopListening();
    };
  }

  function startListening() {
    if (!recognition) {
      if (micStatus) micStatus.textContent = "Browser speech recognition not supported in this browser. Try clicking the sample chips below!";
      return;
    }
    const lang = window.currentLanguage || 'en';
    if (lang === 'te') recognition.lang = 'te-IN';
    else if (lang === 'hi') recognition.lang = 'hi-IN';
    else recognition.lang = 'en-IN';

    try {
      recognition.start();
    } catch (e) {
      console.log("Recognition already active", e);
    }
  }

  function stopListening() {
    isListening = false;
    if (micButton) {
      micButton.classList.remove('animate-pulse', 'bg-rose-600', 'ring-8', 'ring-rose-200');
    }
    if (recognition) {
      try { recognition.stop(); } catch(e) {}
    }
  }

  if (micButton) {
    micButton.addEventListener('click', () => {
      if (isListening) stopListening();
      else startListening();
    });
  }

  // Handle sample query clicks
  sampleChips.forEach(chip => {
    chip.addEventListener('click', () => {
      const query = chip.getAttribute('data-query');
      if (transcriptBox) transcriptBox.textContent = `"${query}"`;
      processVoiceCommand(query);
    });
  });

  function processVoiceCommand(text) {
    const lang = window.currentLanguage || 'en';
    let reply = "";
    let actionCategory = "all";

    const lower = text.toLowerCase();

    if (lower.includes('ఫోటో') || lower.includes('photo') || lower.includes('कैमरा') || lower.includes('फ़ोटो')) {
      actionCategory = "photography";
      reply = lang === 'te' 
        ? "హైదరాబాద్ మరియు విజయవాడలోని అగ్రశ్రేణి క్యాండిడ్ ఫోటోగ్రాఫర్లను చూపిస్తున్నాను. పారదర్శక ప్యాకేజీ ధరలు ₹45,000 నుండి ప్రారంభమవుతాయి."
        : lang === 'hi' 
        ? "यहाँ शीर्ष वेडिंग फोटोग्राफर हैं। शुरुआती पैकेज ₹45,000 प्रति दिन से उपलब्ध हैं।"
        : "Displaying verified candid wedding photographers with transparent day packages from ₹45,000.";
    } else if (lower.includes('క్యాటరింగ్') || lower.includes('భోజనం') || lower.includes('cater') || lower.includes('खाना') || lower.includes('केटरिंग')) {
      actionCategory = "catering";
      reply = lang === 'te' 
        ? "అన్నపూర్ణ రాయల్ క్యాటరర్స్ ప్లేట్ ధర ₹480 నుండి లభిస్తుంది. సాంప్రదాయ తెలుగు వంటకాల వివరాలు ఇక్కడ ఉన్నాయి."
        : lang === 'hi' 
        ? "प्रसिद्ध केटरर्स के शुद्ध शाकाहारी पैकेज ₹480 प्रति प्लेट से उपलब्ध हैं।"
        : "Showing authentic Andhra and royal catering providers starting at ₹480 per plate.";
    } else if (lower.includes('డెకరేషన్') || lower.includes('decor') || lower.includes('सजावट') || lower.includes('मंडप') || lower.includes('మండపం')) {
      actionCategory = "decorations";
      reply = lang === 'te' 
        ? "సాంప్రదాయ పూల మండపాలు మరియు ఆధునిక స్టేజ్ డెకరేషన్స్ ప్యాకేజీలు ₹38,000 నుండి సిద్ధంగా ఉన్నాయి."
        : lang === 'hi' 
        ? "पारंपरिक पुष्प मंडप और थीम डेकोरेशन ₹38,000 से उपलब्ध हैं।"
        : "Showing traditional floral mandaps and modern stage decor starting from ₹38,000.";
    } else {
      reply = lang === 'te' 
        ? `"${text}" కోసం సరిపోయే వేడుక సర్వీస్ ప్రొవైడర్లను వెతికాము. వివరాలు స్క్రీన్‌పై ఉన్నాయి.`
        : lang === 'hi' 
        ? `"${text}" के लिए उपयुक्त उत्सव वेंडरों की सूची स्क्रीन पर फ़िल्टर कर दी गई है।`
        : `Matched verified local event providers for "${text}". Filtering catalog below.`;
    }

    if (aiAnswerBox) {
      aiAnswerBox.classList.remove('hidden');
      aiAnswerBox.innerHTML = `
        <div class="p-4 bg-emerald-50 border border-emerald-200 rounded-xl">
          <div class="flex items-center gap-2 mb-1">
            <span class="text-xs font-bold text-emerald-800 uppercase tracking-wider">🤖 Veduka AI Voice Response:</span>
          </div>
          <p class="text-sm text-emerald-950 font-medium leading-relaxed">${reply}</p>
        </div>
      `;
    }

    // Trigger Speech Synthesis (TTS)
    speakResponse(reply, lang);

    // Filter UI category in background
    const categoryBtn = document.querySelector(`[data-category="${actionCategory}"]`);
    if (categoryBtn) categoryBtn.click();
  }

  function speakResponse(text, lang) {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    if (lang === 'te') utterance.lang = 'te-IN';
    else if (lang === 'hi') utterance.lang = 'hi-IN';
    else utterance.lang = 'en-IN';

    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    window.speechSynthesis.speak(utterance);
  }

  function updateVoiceModalLang() {
    const lang = window.currentLanguage || 'en';
    const t = translations[lang] || translations.en;
    const title = document.getElementById('voice-modal-title');
    const prompt = document.getElementById('voice-modal-prompt');
    if (title) title.textContent = t.voiceModalTitle;
    if (prompt) prompt.textContent = t.voiceTapPrompt;
  }
}
