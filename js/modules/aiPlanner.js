// AI Event Planner interactive engine & modal logic
import { mockVendors } from '../data/mockVendors.js';

export function initializeAIPlanner(currentLang = 'en') {
  const plannerBtn = document.getElementById('launch-ai-planner-btn');
  const heroPlannerBtn = document.getElementById('hero-ai-planner-btn');
  const modal = document.getElementById('ai-planner-modal');
  const closeModal = document.getElementById('close-ai-planner-modal');
  const form = document.getElementById('ai-planner-form');
  const resultsContainer = document.getElementById('ai-planner-results');

  if (!modal) return;

  const openModal = () => {
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    document.body.classList.add('overflow-hidden');
  };

  const hideModal = () => {
    modal.classList.add('hidden');
    modal.classList.remove('flex');
    document.body.classList.remove('overflow-hidden');
  };

  if (plannerBtn) plannerBtn.addEventListener('click', openModal);
  if (heroPlannerBtn) heroPlannerBtn.addEventListener('click', openModal);
  if (closeModal) closeModal.addEventListener('click', hideModal);

  modal.addEventListener('click', (e) => {
    if (e.target === modal) hideModal();
  });

  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const eventType = document.getElementById('planner-event-type').value;
      const guests = parseInt(document.getElementById('planner-guests').value, 10) || 150;
      const city = document.getElementById('planner-city').value;
      const budgetTier = document.getElementById('planner-budget').value;

      generateEventPlan({ eventType, guests, city, budgetTier, lang: window.currentLanguage || 'en' });
    });
  }
}

export function generateEventPlan({ eventType, guests, city, budgetTier, lang = 'en' }) {
  const resultsContainer = document.getElementById('ai-planner-results');
  if (!resultsContainer) return;

  resultsContainer.classList.remove('hidden');
  resultsContainer.innerHTML = `
    <div class="p-6 bg-amber-50/80 rounded-2xl border border-amber-200 animate-pulse text-center">
      <div class="inline-block p-3 rounded-full bg-amber-100 text-amber-700 mb-2">
        <svg class="w-6 h-6 animate-spin inline" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path></svg>
      </div>
      <p class="font-semibold text-amber-900">${lang === 'te' ? 'వేడుక ఏఐ మీ ఈవెంట్ ప్లాన్‌ను సిద్ధం చేస్తోంది...' : lang === 'hi' ? 'उत्सव एआई आपकी विस्तृत योजना तैयार कर रहा है...' : 'Veduka AI is architecting your custom event blueprint...'}</p>
      <p class="text-xs text-amber-700 mt-1">${lang === 'te' ? 'ధరల విశ్లేషణ మరియు ఉత్తమ స్థానిక వెండర్ల ఎంపిక జరుగుతోంది...' : 'Calculating itemized costs and matching verified local vendors...'}</p>
    </div>
  `;

  setTimeout(() => {
    renderGeneratedPlan({ eventType, guests, city, budgetTier, lang });
  }, 900);
}

function renderGeneratedPlan({ eventType, guests, city, budgetTier, lang }) {
  const resultsContainer = document.getElementById('ai-planner-results');
  if (!resultsContainer) return;

  // Budget calculations
  let baseBudget = 350000;
  if (budgetTier === 'budget') baseBudget = guests * 1200;
  if (budgetTier === 'premium') baseBudget = guests * 2500;
  if (budgetTier === 'luxury') baseBudget = guests * 4500;

  const cateringBudget = Math.round(baseBudget * 0.40);
  const venueBudget = Math.round(baseBudget * 0.25);
  const decorBudget = Math.round(baseBudget * 0.15);
  const photoBudget = Math.round(baseBudget * 0.12);
  const musicBudget = Math.round(baseBudget * 0.08);

  const themeName = {
    en: budgetTier === 'luxury' ? 'Royal Nizam & Marigold Symphony' : 'Temple Jasmine & Contemporary Pastel Glow',
    te: budgetTier === 'luxury' ? 'రాయల్ నిజాం & కెంపు బంగారు థీమ్' : 'సాంప్రదాయ మల్లెల పరిమళం & పాస్టెల్ వెలుగులు',
    hi: budgetTier === 'luxury' ? 'शाही निजाम एवं स्वर्णिम गेंदा सिम्फनी' : 'पारंपरिक चमेली एवं आधुनिक पेस्टल छटा'
  }[lang] || 'Temple Jasmine & Contemporary Pastel Glow';

  const matchingVendors = mockVendors.slice(0, 3);

  resultsContainer.innerHTML = `
    <div class="mt-6 p-6 bg-white rounded-2xl border-2 border-rose-100 shadow-xl space-y-6">
      <div class="flex items-start justify-between border-b pb-4">
        <div>
          <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-100 text-rose-800 mb-1">
            ✨ ${lang === 'te' ? 'AI ఈవెంట్ బ్లూప్రింట్' : lang === 'hi' ? 'AI इवेंट ब्लूप्रिंट' : 'AI Event Blueprint Ready'}
          </span>
          <h4 class="text-xl font-bold text-gray-900">${themeName}</h4>
          <p class="text-xs text-gray-500 mt-0.5">
            ${city} • ${guests} ${lang === 'te' ? 'అతిథులు' : lang === 'hi' ? 'मेहमान' : 'Guests'} • ₹${baseBudget.toLocaleString('en-IN')} ${lang === 'te' ? 'అంచనా బడ్జెట్' : 'Est. Budget'}
          </p>
        </div>
        <span class="text-xs px-2.5 py-1 bg-emerald-50 text-emerald-700 font-semibold rounded-lg border border-emerald-200">
          98% Match
        </span>
      </div>

      <!-- Itemized Budget Breakdown -->
      <div>
        <h5 class="text-sm font-bold text-gray-800 mb-3 flex items-center justify-between">
          <span>${lang === 'te' ? 'పారదర్శక బడ్జెట్ బ్రేకప్' : lang === 'hi' ? 'पारदर्शी बजट विवरण' : 'Transparent Itemized Budget Breakdown'}</span>
          <span class="text-xs font-normal text-gray-500">${lang === 'te' ? 'మొత్తం' : 'Total'}: ₹${baseBudget.toLocaleString('en-IN')}</span>
        </h5>
        <div class="grid grid-cols-2 sm:grid-cols-3 gap-2.5 text-xs">
          <div class="p-3 bg-amber-50 rounded-xl border border-amber-200">
            <span class="text-gray-600 block">🍲 ${lang === 'te' ? 'క్యాటరింగ్ (40%)' : 'Catering (40%)'}</span>
            <span class="font-bold text-gray-900 text-sm">₹${cateringBudget.toLocaleString('en-IN')}</span>
            <span class="text-[10px] text-gray-500 block">₹${Math.round(cateringBudget / guests)}/plate</span>
          </div>
          <div class="p-3 bg-purple-50 rounded-xl border border-purple-200">
            <span class="text-gray-600 block">🏛️ ${lang === 'te' ? 'వేదిక / హాల్ (25%)' : 'Venue (25%)'}</span>
            <span class="font-bold text-gray-900 text-sm">₹${venueBudget.toLocaleString('en-IN')}</span>
            <span class="text-[10px] text-gray-500 block">AC Hall + Power</span>
          </div>
          <div class="p-3 bg-rose-50 rounded-xl border border-rose-200">
            <span class="text-gray-600 block">🌸 ${lang === 'te' ? 'డెకరేషన్ (15%)' : 'Decor (15%)'}</span>
            <span class="font-bold text-gray-900 text-sm">₹${decorBudget.toLocaleString('en-IN')}</span>
            <span class="text-[10px] text-gray-500 block">Mandap + Floral Arch</span>
          </div>
          <div class="p-3 bg-blue-50 rounded-xl border border-blue-200">
            <span class="text-gray-600 block">📸 ${lang === 'te' ? 'ఫోటోగ్రఫీ (12%)' : 'Photography (12%)'}</span>
            <span class="font-bold text-gray-900 text-sm">₹${photoBudget.toLocaleString('en-IN')}</span>
            <span class="text-[10px] text-gray-500 block">Candid + Drone + Album</span>
          </div>
          <div class="p-3 bg-teal-50 rounded-xl border border-teal-200">
            <span class="text-gray-600 block">🎵 ${lang === 'te' ? 'సంగీతం & లైటింగ్ (8%)' : 'Music & Lights (8%)'}</span>
            <span class="font-bold text-gray-900 text-sm">₹${musicBudget.toLocaleString('en-IN')}</span>
            <span class="text-[10px] text-gray-500 block">JBL Sound + DJ</span>
          </div>
        </div>
      </div>

      <!-- Suggested Bundled Providers -->
      <div>
        <h5 class="text-sm font-bold text-gray-800 mb-2">
          ${lang === 'te' ? 'సిఫార్సు చేయబడిన స్థానిక వెండర్ల బండిల్' : lang === 'hi' ? 'सुझाए गए स्थानीय वेंडर बंडल' : 'Recommended Local Vendor Bundle'}
        </h5>
        <div class="space-y-2">
          ${matchingVendors.map(v => `
            <div class="flex items-center justify-between p-2.5 rounded-xl border border-gray-100 hover:bg-rose-50/50 transition">
              <div class="flex items-center gap-3">
                <img src="${v.image}" class="w-12 h-12 rounded-lg object-cover" alt="${v.name}" />
                <div>
                  <h6 class="font-bold text-xs text-gray-900">${v.name}</h6>
                  <p class="text-[11px] text-gray-500">${v.city} • ★ ${v.rating} (${v.reviewCount})</p>
                </div>
              </div>
              <div class="text-right">
                <span class="text-xs font-bold text-rose-700">${v.basePriceDisplay}</span>
                <span class="text-[10px] text-gray-500 block">${v.priceUnit}</span>
              </div>
            </div>
          `).join('')}
        </div>
      </div>

      <div class="pt-2 flex flex-col sm:flex-row gap-2">
        <button id="ai-add-all-cart-btn" class="flex-1 py-3 px-4 bg-gradient-to-r from-rose-600 to-amber-600 text-white font-semibold rounded-xl text-xs shadow-md hover:opacity-95 transition">
          🛒 ${lang === 'te' ? 'ఈ బండిల్‌ను ఈవెంట్ కార్ట్‌కు జోడించండి' : lang === 'hi' ? 'इस बंडल को कार्ट में जोड़ें' : 'Add Multi-Vendor Bundle to Event Cart'}
        </button>
        <button onclick="document.getElementById('ai-planner-modal').classList.add('hidden')" class="py-3 px-4 bg-gray-100 text-gray-700 font-semibold rounded-xl text-xs hover:bg-gray-200 transition">
          ${lang === 'te' ? 'మార్పులు చేయండి' : 'Modify'}
        </button>
      </div>
    </div>
  `;

  const addCartBtn = document.getElementById('ai-add-all-cart-btn');
  if (addCartBtn) {
    addCartBtn.addEventListener('click', () => {
      alert(lang === 'te' ? '3 వెండర్ల ప్యాకేజీలు మీ ఈవెంట్ కార్ట్‌కు విజయవంతంగా చేర్చబడ్డాయి! (డెమో)' : 'Multi-vendor bundle added to your Master Event Cart! (Demo simulation)');
    });
  }
}
