// Main application controller for Veduka AI Marketplace
import { mockVendors, eventCategories, citiesList } from './data/mockVendors.js';
import { translations } from './i18n/translations.js';
import { initializeAIPlanner } from './modules/aiPlanner.js';
import { initializeVoiceAssistant } from './modules/voiceAssistant.js';

// Global application state
window.currentLanguage = 'en';
window.selectedCategory = 'all';
window.selectedCity = 'All Cities';
window.searchQuery = '';

document.addEventListener('DOMContentLoaded', () => {
  setupLanguageSwitcher();
  setupCitySelector();
  renderCategories();
  renderVendorCards();
  setupSearchAndFilters();
  setupEntryPoints();
  setupModals();
  initializeAIPlanner(window.currentLanguage);
  initializeVoiceAssistant();
});

// Language Switcher (EN / TE / HI)
function setupLanguageSwitcher() {
  const langButtons = document.querySelectorAll('.lang-btn');
  langButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetLang = btn.getAttribute('data-lang');
      window.currentLanguage = targetLang;

      // Update button styling
      langButtons.forEach(b => {
        b.classList.remove('bg-rose-600', 'text-white', 'shadow-sm');
        b.classList.add('text-gray-700', 'hover:bg-gray-100');
      });
      btn.classList.add('bg-rose-600', 'text-white', 'shadow-sm');
      btn.classList.remove('text-gray-700', 'hover:bg-gray-100');

      applyLanguageTranslations(targetLang);
      renderCategories();
      renderVendorCards();
    });
  });
}

function applyLanguageTranslations(lang) {
  const t = translations[lang] || translations.en;
  
  // Update text content with data-i18n attributes
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    if (t[key]) el.textContent = t[key];
  });

  // Update input placeholders
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    const key = el.getAttribute('data-i18n-placeholder');
    if (t[key]) el.setAttribute('placeholder', t[key]);
  });
}

// City Selector
function setupCitySelector() {
  const citySelect = document.getElementById('city-select');
  if (!citySelect) return;

  citySelect.innerHTML = citiesList.map(city => `
    <option value="${city}">${city}</option>
  `).join('');

  citySelect.addEventListener('change', (e) => {
    window.selectedCity = e.target.value;
    renderVendorCards();
  });
}

// Render Category Filter Pills
function renderCategories() {
  const container = document.getElementById('categories-container');
  if (!container) return;

  const lang = window.currentLanguage;

  container.innerHTML = eventCategories.map(cat => {
    const isSelected = window.selectedCategory === cat.id;
    const label = lang === 'te' ? cat.labelTe : lang === 'hi' ? cat.labelHi : cat.labelEn;
    return `
      <button 
        data-category="${cat.id}"
        class="category-pill flex items-center gap-2 px-4 py-2.5 rounded-full text-xs font-semibold transition-all whitespace-nowrap shadow-sm border ${
          isSelected 
            ? 'bg-gradient-to-r from-rose-600 to-amber-600 text-white border-transparent ring-2 ring-rose-200' 
            : 'bg-white text-gray-700 border-gray-200 hover:border-rose-300 hover:bg-rose-50/50'
        }">
        <span class="text-sm">${cat.icon}</span>
        <span>${label}</span>
      </button>
    `;
  }).join('');

  container.querySelectorAll('.category-pill').forEach(btn => {
    btn.addEventListener('click', () => {
      window.selectedCategory = btn.getAttribute('data-category');
      renderCategories();
      renderVendorCards();
    });
  });
}

// Search and filtering
function setupSearchAndFilters() {
  const searchInput = document.getElementById('search-input');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      window.searchQuery = e.target.value.toLowerCase().trim();
      renderVendorCards();
    });
  }
}

// Render Provider Cards with Itemized Pricing
function renderVendorCards() {
  const grid = document.getElementById('vendors-grid');
  const countDisplay = document.getElementById('vendors-count-display');
  if (!grid) return;

  const lang = window.currentLanguage;
  const t = translations[lang] || translations.en;

  const filtered = mockVendors.filter(v => {
    // Category match
    const categoryMatch = window.selectedCategory === 'all' || v.category === window.selectedCategory;
    // City match
    const cityMatch = window.selectedCity === 'All Cities' || v.city === window.selectedCity;
    // Search query match
    const query = window.searchQuery;
    const queryMatch = !query || 
      v.name.toLowerCase().includes(query) ||
      v.city.toLowerCase().includes(query) ||
      v.areas.toLowerCase().includes(query) ||
      v.category.toLowerCase().includes(query);

    return categoryMatch && cityMatch && queryMatch;
  });

  if (countDisplay) {
    countDisplay.textContent = `${filtered.length} ${t.providerCountSuffix}`;
  }

  if (filtered.length === 0) {
    grid.innerHTML = `
      <div class="col-span-full py-16 text-center bg-white rounded-3xl border border-gray-100 shadow-sm">
        <span class="text-4xl block mb-2">🔍</span>
        <h4 class="text-base font-bold text-gray-800">No matching service providers found</h4>
        <p class="text-xs text-gray-500 mt-1">Try selecting "All Cities" or resetting your search filter.</p>
        <button onclick="window.selectedCategory='all'; window.selectedCity='All Cities'; renderCategories(); renderVendorCards();" 
          class="mt-4 px-4 py-2 bg-rose-50 text-rose-700 font-semibold text-xs rounded-xl hover:bg-rose-100 transition">
          Reset Filters
        </button>
      </div>
    `;
    return;
  }

  grid.innerHTML = filtered.map(v => {
    const desc = v.description[lang] || v.description.en;
    const availabilityBadgeClass = v.availabilityType === 'available' 
      ? 'bg-emerald-50 text-emerald-700 border-emerald-200' 
      : 'bg-amber-50 text-amber-700 border-amber-200';

    return `
      <article class="bg-white rounded-3xl overflow-hidden border border-gray-100 shadow-sm hover:shadow-xl transition-all duration-300 flex flex-col group">
        <!-- Image & Badges -->
        <div class="relative h-48 overflow-hidden bg-gray-100">
          <img 
            src="${v.image}" 
            alt="${v.name}" 
            class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" 
            loading="lazy"
          />
          <div class="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-black/20"></div>

          <!-- Top Badges -->
          <div class="absolute top-3 left-3 right-3 flex items-center justify-between">
            <span class="px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider bg-rose-600/90 text-white backdrop-blur-md shadow-sm">
              ${v.badge}
            </span>
            <span class="px-2 py-0.5 rounded-lg text-[10px] font-bold border backdrop-blur-md ${availabilityBadgeClass}">
              ● ${v.availability}
            </span>
          </div>

          <!-- Location & Response on Image Bottom -->
          <div class="absolute bottom-3 left-3 right-3 flex items-center justify-between text-white text-xs">
            <span class="flex items-center gap-1 drop-shadow">
              📍 ${v.city}
            </span>
            <span class="text-[10px] opacity-90 drop-shadow">
              ⚡ ${v.responseTime}
            </span>
          </div>
        </div>

        <!-- Content -->
        <div class="p-5 flex-1 flex flex-col justify-between">
          <div>
            <div class="flex items-start justify-between gap-2 mb-1.5">
              <h3 class="font-bold text-gray-900 text-base leading-snug group-hover:text-rose-600 transition-colors">
                ${v.name}
              </h3>
              <div class="flex items-center gap-1 bg-amber-50 px-2 py-0.5 rounded-lg border border-amber-200 flex-shrink-0">
                <span class="text-amber-500 text-xs">★</span>
                <span class="font-bold text-gray-900 text-xs">${v.rating}</span>
                <span class="text-[10px] text-gray-500">(${v.reviewCount})</span>
              </div>
            </div>

            <p class="text-xs text-gray-600 line-clamp-2 leading-relaxed mb-4">
              ${desc}
            </p>

            <!-- Transparent Itemized Price Card -->
            <div class="p-3 bg-stone-50 rounded-2xl border border-stone-200 mb-4">
              <div class="flex items-baseline justify-between mb-1">
                <span class="text-[11px] font-semibold text-stone-500 uppercase tracking-wider">
                  ${t.fromPrice}
                </span>
                <div class="text-right">
                  <span class="text-base font-extrabold text-gray-900">${v.basePriceDisplay}</span>
                  <span class="text-[11px] text-gray-500 font-medium"> / ${v.priceUnit}</span>
                </div>
              </div>

              <!-- Top inclusion preview -->
              <div class="text-[11px] text-gray-600 flex items-center gap-1.5 pt-1 border-t border-stone-200/60">
                <span class="text-emerald-600 font-bold">✓</span>
                <span class="truncate">${v.itemizedPackages[0].inclusions[0]}</span>
              </div>
            </div>
          </div>

          <!-- Action Buttons -->
          <div class="grid grid-cols-2 gap-2 pt-1 border-t border-gray-100">
            <button 
              class="view-packages-btn py-2.5 px-3 rounded-xl border border-gray-200 hover:border-rose-300 hover:bg-rose-50/50 text-gray-700 font-semibold text-xs transition"
              data-vendor-id="${v.id}">
              ${t.itemizedBreakdownBtn}
            </button>
            <button 
              class="request-quote-btn py-2.5 px-3 rounded-xl bg-gradient-to-r from-rose-600 to-amber-600 hover:from-rose-700 hover:to-amber-700 text-white font-semibold text-xs shadow-sm hover:shadow transition"
              data-vendor-id="${v.id}">
              ${t.requestQuoteBtn}
            </button>
          </div>
        </div>
      </article>
    `;
  }).join('');

  // Attach button event listeners
  grid.querySelectorAll('.view-packages-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const vendorId = btn.getAttribute('data-vendor-id');
      openVendorPackagesModal(vendorId);
    });
  });

  grid.querySelectorAll('.request-quote-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const vendorId = btn.getAttribute('data-vendor-id');
      openRequestQuoteModal(vendorId);
    });
  });
}

// Open Itemized Packages Modal
function openVendorPackagesModal(vendorId) {
  const vendor = mockVendors.find(v => v.id === vendorId);
  if (!vendor) return;

  const modal = document.getElementById('itemized-packages-modal');
  const modalContent = document.getElementById('itemized-packages-content');
  if (!modal || !modalContent) return;

  const lang = window.currentLanguage;
  const t = translations[lang] || translations.en;

  modalContent.innerHTML = `
    <div class="space-y-6">
      <div class="flex items-center gap-4 border-b pb-4">
        <img src="${vendor.image}" class="w-16 h-16 rounded-2xl object-cover" alt="${vendor.name}" />
        <div>
          <span class="text-[10px] font-bold uppercase tracking-wider text-rose-600">${vendor.category}</span>
          <h3 class="text-lg font-bold text-gray-900">${vendor.name}</h3>
          <p class="text-xs text-gray-500">📍 ${vendor.areas}, ${vendor.city}</p>
        </div>
      </div>

      <!-- Packages List -->
      <div>
        <h4 class="font-bold text-sm text-gray-900 mb-3">${lang === 'te' ? 'పారదర్శక ప్యాకేజీలు & ఇన్-క్లూజన్స్' : 'Transparent Itemized Packages'}</h4>
        <div class="space-y-4">
          ${vendor.itemizedPackages.map(pkg => `
            <div class="p-4 rounded-2xl border border-rose-200 bg-rose-50/30">
              <div class="flex items-start justify-between mb-2">
                <h5 class="font-bold text-sm text-gray-900">${pkg.name}</h5>
                <span class="font-extrabold text-rose-700 text-sm">₹${pkg.price.toLocaleString('en-IN')}</span>
              </div>
              <ul class="space-y-1.5 text-xs text-gray-700">
                ${pkg.inclusions.map(inc => `
                  <li class="flex items-center gap-2">
                    <span class="text-emerald-600 font-bold">✓</span>
                    <span>${inc}</span>
                  </li>
                `).join('')}
              </ul>
            </div>
          `).join('')}
        </div>
      </div>

      <!-- Add-ons -->
      ${vendor.addOns && vendor.addOns.length ? `
        <div>
          <h4 class="font-bold text-sm text-gray-900 mb-2">${lang === 'te' ? 'ఐచ్ఛిక యాడ్-ఆన్స్' : 'Optional Add-ons & Equipment'}</h4>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
            ${vendor.addOns.map(addon => `
              <div class="flex items-center justify-between p-2.5 rounded-xl border border-gray-200 bg-white">
                <span class="text-gray-700">${addon.name}</span>
                <span class="font-bold text-gray-900">+₹${addon.price.toLocaleString('en-IN')}</span>
              </div>
            `).join('')}
          </div>
        </div>
      ` : ''}

      <div class="pt-4 border-t flex gap-2">
        <button 
          onclick="document.getElementById('itemized-packages-modal').classList.add('hidden'); openRequestQuoteModal('${vendor.id}');"
          class="flex-1 py-3 px-4 bg-gradient-to-r from-rose-600 to-amber-600 text-white font-bold rounded-xl text-xs hover:opacity-95 transition shadow-sm">
          ${t.requestQuoteBtn}
        </button>
        <button 
          onclick="document.getElementById('itemized-packages-modal').classList.add('hidden')"
          class="py-3 px-4 bg-gray-100 text-gray-700 font-semibold rounded-xl text-xs hover:bg-gray-200 transition">
          ${t.closeBtn}
        </button>
      </div>
    </div>
  `;

  modal.classList.remove('hidden');
  modal.classList.add('flex');
}

// Request Quote Modal
function openRequestQuoteModal(vendorId) {
  const vendor = mockVendors.find(v => v.id === vendorId);
  const modal = document.getElementById('request-quote-modal');
  const targetVendorName = document.getElementById('quote-target-vendor-name');
  if (!modal) return;

  if (targetVendorName && vendor) {
    targetVendorName.textContent = vendor.name;
  }

  modal.classList.remove('hidden');
  modal.classList.add('flex');
}

// Setup Entry Points (Plan or Book vs Register Business)
function setupEntryPoints() {
  const planBtn = document.getElementById('hero-plan-event-btn');
  const registerBtn = document.getElementById('hero-register-business-btn');
  const navRegisterBtn = document.getElementById('nav-register-business-btn');
  const vendorModal = document.getElementById('vendor-register-modal');

  if (planBtn) {
    planBtn.addEventListener('click', () => {
      document.getElementById('discovery-section').scrollIntoView({ behavior: 'smooth' });
    });
  }

  const openVendorModal = () => {
    if (vendorModal) {
      vendorModal.classList.remove('hidden');
      vendorModal.classList.add('flex');
    }
  };

  if (registerBtn) registerBtn.addEventListener('click', openVendorModal);
  if (navRegisterBtn) navRegisterBtn.addEventListener('click', openVendorModal);
}

// Setup common modal closing logic
function setupModals() {
  const modals = [
    'vendor-register-modal',
    'itemized-packages-modal',
    'request-quote-modal'
  ];

  modals.forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    el.addEventListener('click', (e) => {
      if (e.target === el) {
        el.classList.add('hidden');
        el.classList.remove('flex');
      }
    });

    const closeBtn = el.querySelector('.modal-close-btn');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => {
        el.classList.add('hidden');
        el.classList.remove('flex');
      });
    }
  });

  // Handle Vendor Form Submit (Demo)
  const vendorForm = document.getElementById('vendor-onboarding-form');
  if (vendorForm) {
    vendorForm.addEventListener('submit', (e) => {
      e.preventDefault();
      alert(window.currentLanguage === 'te' 
        ? "మీ వ్యాపార వివరాలు నమోదు చేయబడ్డాయి! మా బృందం 24 గంటల్లో సంప్రదిస్తుంది. (ఫేజ్ 1 డెమో)" 
        : "Vendor details registered successfully! Our onboarding team will verify your catalog within 24 hours. (Phase 1 Demo)");
      document.getElementById('vendor-register-modal').classList.add('hidden');
      vendorForm.reset();
    });
  }

  // Handle Quote Form Submit (Demo)
  const quoteForm = document.getElementById('custom-quote-form');
  if (quoteForm) {
    quoteForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const t = translations[window.currentLanguage] || translations.en;
      alert(t.quickQuoteSuccess);
      document.getElementById('request-quote-modal').classList.add('hidden');
      quoteForm.reset();
    });
  }
}

// Expose functions globally for inline HTML handlers
window.openVendorPackagesModal = openVendorPackagesModal;
window.openRequestQuoteModal = openRequestQuoteModal;
window.renderCategories = renderCategories;
window.renderVendorCards = renderVendorCards;
