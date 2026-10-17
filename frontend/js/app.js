// Veduka AI - Reactive Single Page Application Controller
import { api } from './api.js';
import { translations } from './i18n.js';

// Application State
const state = {
  user: api.getUser(),
  currentRole: api.getUser() ? api.getUser().role : "customer",
  currentLang: api.getUser() ? api.getUser().preferred_language || "en" : "en",
  highContrast: api.getUser() ? api.getUser().high_contrast === 1 : false,
  speechSpeed: api.getUser() ? api.getUser().speech_speed || 1.0 : 1.0,
  activeView: "home",
  activeEventTab: "budget",
  vendors: [],
  selectedCategory: "all",
  selectedCity: "All Cities",
  searchQuery: "",
  comparisonList: [], // array of vendor IDs
  activeEvent: null,
  activeEventId: 1,
  notifications: []
};

document.addEventListener("DOMContentLoaded", async () => {
  applyTheme();
  setupNavEvents();
  setupLanguageSwitcher();
  setupAuthEvents();
  setupVoiceAssistant();
  setupListenPage();
  setupAccessibilityControls();

  // Load initial data
  await loadNotifications();
  await loadVendors();
  await refreshActiveEvent();
  renderApp();
});

// Theme & Accessibility
function applyTheme() {
  if (state.highContrast) {
    document.body.classList.add("high-contrast");
  } else {
    document.body.classList.remove("high-contrast");
  }
}

// Language Switcher
function setupLanguageSwitcher() {
  document.querySelectorAll(".lang-switch-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const lang = btn.getAttribute("data-lang");
      state.currentLang = lang;
      if (state.user) {
        api.updateSettings({ preferred_language: lang }).catch(() => {});
      }
      renderApp();
    });
  });
}

function t(key) {
  const dict = translations[state.currentLang] || translations.en;
  return dict[key] || translations.en[key] || key;
}

// Navigation Events
function setupNavEvents() {
  document.querySelectorAll("[data-nav-view]").forEach(el => {
    el.addEventListener("click", (e) => {
      e.preventDefault();
      const target = el.getAttribute("data-nav-view");
      navigateTo(target);
    });
  });

  // Entry Point CTAs
  const planBtn = document.getElementById("hero-plan-btn");
  if (planBtn) {
    planBtn.addEventListener("click", () => {
      navigateTo("discover");
    });
  }

  const registerBizBtn = document.getElementById("hero-register-btn");
  if (registerBizBtn) {
    registerBizBtn.addEventListener("click", () => {
      if (!state.user) {
        openAuthModal("register", "vendor");
      } else if (state.currentRole !== "vendor") {
        switchUserRole("vendor");
      } else {
        navigateTo("sellerDashboard");
      }
    });
  }
}

export function navigateTo(viewName) {
  state.activeView = viewName;
  window.scrollTo({ top: 0, behavior: "smooth" });
  renderApp();
}

// Load Vendors from Backend
async function loadVendors() {
  try {
    const res = await api.getVendors({
      category: state.selectedCategory,
      city: state.selectedCity,
      q: state.searchQuery
    });
    state.vendors = res.vendors || [];
  } catch (e) {
    console.error("Failed to load vendors:", e);
  }
}

// Refresh active customer event
async function refreshActiveEvent() {
  try {
    const res = await api.getEvents();
    if (res.events && res.events.length > 0) {
      state.activeEventId = res.events[0].id;
      const details = await api.getEventDetails(state.activeEventId);
      state.activeEvent = details.event;
    }
  } catch (e) {
    console.log("No active events loaded:", e);
  }
}

async function loadNotifications() {
  if (!state.user) return;
  try {
    const res = await api.getNotifications();
    state.notifications = res.notifications || [];
    const countBadge = document.getElementById("notif-count-badge");
    const unread = state.notifications.filter(n => !n.is_read).length;
    if (countBadge) {
      countBadge.textContent = unread > 0 ? unread : "";
      countBadge.style.display = unread > 0 ? "inline-block" : "none";
    }
  } catch (e) {}
}

// Render Core Application Router
function renderApp() {
  updateHeaderAndNav();
  hideAllViews();

  switch (state.activeView) {
    case "home":
      renderHomeView();
      break;
    case "discover":
      renderDiscoverView();
      break;
    case "aiPlanner":
      renderAiPlannerView();
      break;
    case "myEvents":
      renderMyEventsView();
      break;
    case "profile":
      renderProfileView();
      break;
    case "sellerDashboard":
      renderSellerDashboardView();
      break;
    case "sellerInquiries":
      renderSellerInquiriesView();
      break;
    case "sellerInventory":
      renderSellerInventoryView();
      break;
    case "adminPanel":
      renderAdminPanelView();
      break;
    default:
      renderHomeView();
  }
}

function hideAllViews() {
  const views = [
    "view-home", "view-discover", "view-ai-planner", "view-my-events",
    "view-profile", "view-seller-dashboard", "view-seller-inquiries",
    "view-seller-inventory", "view-admin-panel"
  ];
  views.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.classList.add("hidden");
  });
}

function showView(viewId) {
  const el = document.getElementById(viewId);
  if (el) el.classList.remove("hidden");
}

// Header & Navigation updates
function updateHeaderAndNav() {
  // Brand name & tagline
  const brandName = document.getElementById("brand-name");
  const brandTag = document.getElementById("brand-tagline");
  if (brandName) brandName.textContent = t("brandName");
  if (brandTag) brandTag.textContent = t("brandTagline");

  // Language buttons
  document.querySelectorAll(".lang-switch-btn").forEach(btn => {
    if (btn.getAttribute("data-lang") === state.currentLang) {
      btn.classList.add("bg-rose-600", "text-white");
      btn.classList.remove("text-gray-700");
    } else {
      btn.classList.remove("bg-rose-600", "text-white");
      btn.classList.add("text-gray-700");
    }
  });

  // User auth display in header
  const authContainer = document.getElementById("header-auth-container");
  if (authContainer) {
    if (state.user) {
      authContainer.innerHTML = `
        <div class="flex items-center gap-2">
          <div class="text-right hidden sm:block">
            <span class="block text-xs font-bold text-gray-900">${state.user.full_name}</span>
            <span class="block text-[10px] text-rose-600 font-semibold uppercase">${state.currentRole}</span>
          </div>
          <button id="header-user-menu-btn" class="w-9 h-9 rounded-full bg-gradient-to-br from-rose-500 to-amber-500 text-white font-bold text-xs flex items-center justify-center shadow-xs">
            ${state.user.full_name.charAt(0)}
          </button>
        </div>
      `;
      const btn = document.getElementById("header-user-menu-btn");
      if (btn) btn.addEventListener("click", () => navigateTo("profile"));
    } else {
      authContainer.innerHTML = `
        <button id="header-login-btn" class="px-3.5 py-1.5 rounded-full bg-gray-900 hover:bg-gray-800 text-white font-semibold text-xs shadow-xs transition">
          ${t("loginBtn")}
        </button>
      `;
      const btn = document.getElementById("header-login-btn");
      if (btn) btn.addEventListener("click", () => openAuthModal("login"));
    }
  }

  // Navigation Links based on role
  renderNavItems();
}

function renderNavItems() {
  const desktopNav = document.getElementById("desktop-nav-links");
  const mobileNav = document.getElementById("mobile-bottom-nav");
  if (!desktopNav || !mobileNav) return;

  if (state.currentRole === "vendor") {
    desktopNav.innerHTML = `
      <a href="#" data-nav-view="sellerDashboard" class="text-xs font-bold ${state.activeView === 'sellerDashboard' ? 'text-rose-600' : 'text-gray-700 hover:text-rose-600'}">📊 ${t("navSellerDashboard")}</a>
      <a href="#" data-nav-view="sellerInquiries" class="text-xs font-bold ${state.activeView === 'sellerInquiries' ? 'text-rose-600' : 'text-gray-700 hover:text-rose-600'}">💬 ${t("navSellerInquiries")}</a>
      <a href="#" data-nav-view="sellerInventory" class="text-xs font-bold ${state.activeView === 'sellerInventory' ? 'text-rose-600' : 'text-gray-700 hover:text-rose-600'}">📦 ${t("navSellerInventory")}</a>
      <a href="#" data-nav-view="profile" class="text-xs font-bold ${state.activeView === 'profile' ? 'text-rose-600' : 'text-gray-700 hover:text-rose-600'}">⚙️ ${t("navProfile")}</a>
    `;

    mobileNav.innerHTML = `
      <button data-nav-view="sellerDashboard" class="flex flex-col items-center ${state.activeView === 'sellerDashboard' ? 'text-rose-600 font-bold' : 'text-gray-500'}">
        <span class="text-lg">📊</span><span class="text-[10px]">Dashboard</span>
      </button>
      <button data-nav-view="sellerInquiries" class="flex flex-col items-center ${state.activeView === 'sellerInquiries' ? 'text-rose-600 font-bold' : 'text-gray-500'}">
        <span class="text-lg">💬</span><span class="text-[10px]">Quotes</span>
      </button>
      <button data-nav-view="sellerInventory" class="flex flex-col items-center ${state.activeView === 'sellerInventory' ? 'text-rose-600 font-bold' : 'text-gray-500'}">
        <span class="text-lg">📦</span><span class="text-[10px]">Inventory</span>
      </button>
      <button data-nav-view="profile" class="flex flex-col items-center ${state.activeView === 'profile' ? 'text-rose-600 font-bold' : 'text-gray-500'}">
        <span class="text-lg">⚙️</span><span class="text-[10px]">Profile</span>
      </button>
    `;
  } else if (state.currentRole === "admin") {
    desktopNav.innerHTML = `
      <a href="#" data-nav-view="adminPanel" class="text-xs font-bold ${state.activeView === 'adminPanel' ? 'text-rose-600' : 'text-gray-700 hover:text-rose-600'}">🛡️ ${t("navAdminOverview")}</a>
      <a href="#" data-nav-view="discover" class="text-xs font-bold ${state.activeView === 'discover' ? 'text-rose-600' : 'text-gray-700 hover:text-rose-600'}">🔍 ${t("navDiscover")}</a>
      <a href="#" data-nav-view="profile" class="text-xs font-bold ${state.activeView === 'profile' ? 'text-rose-600' : 'text-gray-700 hover:text-rose-600'}">⚙️ ${t("navProfile")}</a>
    `;
    mobileNav.innerHTML = `
      <button data-nav-view="adminPanel" class="flex flex-col items-center ${state.activeView === 'adminPanel' ? 'text-rose-600 font-bold' : 'text-gray-500'}">
        <span class="text-lg">🛡️</span><span class="text-[10px]">Admin</span>
      </button>
      <button data-nav-view="discover" class="flex flex-col items-center ${state.activeView === 'discover' ? 'text-rose-600 font-bold' : 'text-gray-500'}">
        <span class="text-lg">🔍</span><span class="text-[10px]">Catalog</span>
      </button>
      <button data-nav-view="profile" class="flex flex-col items-center ${state.activeView === 'profile' ? 'text-rose-600 font-bold' : 'text-gray-500'}">
        <span class="text-lg">⚙️</span><span class="text-[10px]">Settings</span>
      </button>
    `;
  } else {
    // Customer Nav
    desktopNav.innerHTML = `
      <a href="#" data-nav-view="home" class="text-xs font-bold ${state.activeView === 'home' ? 'text-rose-600' : 'text-gray-700 hover:text-rose-600'}">🏠 ${t("navHome")}</a>
      <a href="#" data-nav-view="discover" class="text-xs font-bold ${state.activeView === 'discover' ? 'text-rose-600' : 'text-gray-700 hover:text-rose-600'}">🔍 ${t("navDiscover")}</a>
      <a href="#" data-nav-view="aiPlanner" class="text-xs font-bold ${state.activeView === 'aiPlanner' ? 'text-rose-600' : 'text-gray-700 hover:text-rose-600'}">🤖 ${t("navAiPlanner")}</a>
      <a href="#" data-nav-view="myEvents" class="text-xs font-bold ${state.activeView === 'myEvents' ? 'text-rose-600' : 'text-gray-700 hover:text-rose-600'}">🎉 ${t("navMyEvents")}</a>
      <a href="#" data-nav-view="profile" class="text-xs font-bold ${state.activeView === 'profile' ? 'text-rose-600' : 'text-gray-700 hover:text-rose-600'}">⚙️ ${t("navProfile")}</a>
    `;

    mobileNav.innerHTML = `
      <button data-nav-view="home" class="flex flex-col items-center ${state.activeView === 'home' ? 'text-rose-600 font-bold' : 'text-gray-500'}">
        <span class="text-lg">🏠</span><span class="text-[10px]">Home</span>
      </button>
      <button data-nav-view="discover" class="flex flex-col items-center ${state.activeView === 'discover' ? 'text-rose-600 font-bold' : 'text-gray-500'}">
        <span class="text-lg">🔍</span><span class="text-[10px]">Discover</span>
      </button>
      <button data-nav-view="aiPlanner" class="flex flex-col items-center ${state.activeView === 'aiPlanner' ? 'text-rose-600 font-bold' : 'text-gray-500'}">
        <span class="text-lg">🤖</span><span class="text-[10px]">AI Plan</span>
      </button>
      <button data-nav-view="myEvents" class="flex flex-col items-center ${state.activeView === 'myEvents' ? 'text-rose-600 font-bold' : 'text-gray-500'}">
        <span class="text-lg">🎉</span><span class="text-[10px]">Events</span>
      </button>
      <button data-nav-view="profile" class="flex flex-col items-center ${state.activeView === 'profile' ? 'text-rose-600 font-bold' : 'text-gray-500'}">
        <span class="text-lg">⚙️</span><span class="text-[10px]">Profile</span>
      </button>
    `;
  }

  // Reattach nav events
  document.querySelectorAll("[data-nav-view]").forEach(el => {
    el.onclick = (e) => {
      e.preventDefault();
      navigateTo(el.getAttribute("data-nav-view"));
    };
  });
}

// -------------------------------------------------------------
// VIEW 1: HOME SCREEN
// -------------------------------------------------------------
function renderHomeView() {
  showView("view-home");

  const heroTitle = document.getElementById("hero-title-text");
  const heroSub = document.getElementById("hero-sub-text");
  if (heroTitle) heroTitle.textContent = t("heroTitle");
  if (heroSub) heroSub.textContent = t("heroSubtitle");

  renderFeaturedVendors();
}

function renderFeaturedVendors() {
  const container = document.getElementById("home-featured-vendors");
  if (!container) return;

  const featured = state.vendors.slice(0, 3);
  container.innerHTML = featured.map(v => renderVendorCardHtml(v)).join("");
  attachVendorCardListeners(container);
}

// -------------------------------------------------------------
// VIEW 2: DISCOVER & CATALOG (ITEMIZED PRICING)
// -------------------------------------------------------------
function renderDiscoverView() {
  showView("view-discover");
  renderCategoriesPills();
  renderVendorCatalog();
}

function renderCategoriesPills() {
  const container = document.getElementById("discover-categories-pills");
  if (!container) return;

  const categories = [
    { id: "all", icon: "✨", label: "All" },
    { id: "photography", icon: "📸", label: "Photography" },
    { id: "decorations", icon: "🌸", label: "Decorations" },
    { id: "catering", icon: "🍲", label: "Catering" },
    { id: "venues", icon: "🏛️", label: "Venues" },
    { id: "makeup", icon: "💄", label: "Makeup & Mehendi" },
    { id: "dj_music", icon: "🎵", label: "DJ & Music" }
  ];

  container.innerHTML = categories.map(c => `
    <button data-cat="${c.id}" class="category-pill-btn px-4 py-2 rounded-full text-xs font-bold transition flex items-center gap-1.5 whitespace-nowrap border ${
      state.selectedCategory === c.id 
        ? 'bg-rose-600 text-white border-rose-600 shadow-sm' 
        : 'bg-white text-gray-700 border-gray-200 hover:border-rose-300'
    }">
      <span>${c.icon}</span>
      <span>${c.label}</span>
    </button>
  `).join("");

  container.querySelectorAll(".category-pill-btn").forEach(btn => {
    btn.onclick = async () => {
      state.selectedCategory = btn.getAttribute("data-cat");
      await loadVendors();
      renderDiscoverView();
    };
  });
}

function renderVendorCatalog() {
  const container = document.getElementById("discover-vendors-grid");
  const countDisplay = document.getElementById("discover-count-text");
  if (!container) return;

  if (countDisplay) {
    countDisplay.textContent = `${state.vendors.length} Verified Local Service Providers Available`;
  }

  if (state.vendors.length === 0) {
    container.innerHTML = `
      <div class="col-span-full py-16 text-center bg-white rounded-3xl border border-gray-100 shadow-sm">
        <span class="text-4xl block mb-2">🔍</span>
        <h4 class="font-bold text-gray-800">No matching service providers found</h4>
        <p class="text-xs text-gray-500 mt-1">Try resetting your filters or changing location.</p>
        <button id="reset-filter-btn" class="mt-4 px-4 py-2 bg-rose-50 text-rose-700 font-bold text-xs rounded-xl">Reset Filters</button>
      </div>
    `;
    const btn = document.getElementById("reset-filter-btn");
    if (btn) btn.onclick = async () => {
      state.selectedCategory = "all";
      state.selectedCity = "All Cities";
      state.searchQuery = "";
      await loadVendors();
      renderDiscoverView();
    };
    return;
  }

  container.innerHTML = state.vendors.map(v => renderVendorCardHtml(v)).join("");
  attachVendorCardListeners(container);
}

function renderVendorCardHtml(v) {
  const desc = state.currentLang === "te" ? v.bio_te || v.bio_en : state.currentLang === "hi" ? v.bio_hi || v.bio_en : v.bio_en;
  const isCompared = state.comparisonList.includes(v.id);

  return `
    <article class="bg-white rounded-3xl overflow-hidden border border-gray-100 shadow-sm hover:shadow-xl transition-all duration-300 flex flex-col group">
      <div class="relative h-48 overflow-hidden bg-gray-100">
        <img src="${v.image_url || 'https://images.unsplash.com/photo-1519741497674-611481863552?auto=format&fit=crop&w=800&q=80'}" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" loading="lazy" />
        <div class="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-black/20"></div>

        <div class="absolute top-3 left-3 right-3 flex items-center justify-between">
          <span class="px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${v.kyc_verified ? 'bg-emerald-600 text-white' : 'bg-gray-800 text-white'} backdrop-blur-md">
            ${v.kyc_verified ? '✓ Verified Pro' : 'Registered Provider'}
          </span>
          <button class="compare-toggle-btn px-2 py-1 rounded-lg text-[10px] font-bold border backdrop-blur-md ${isCompared ? 'bg-rose-600 text-white border-rose-600' : 'bg-white/90 text-gray-800 border-white'}" data-vid="${v.id}">
            ${isCompared ? '✓ Compared' : '+ Compare'}
          </button>
        </div>

        <div class="absolute bottom-3 left-3 right-3 flex items-center justify-between text-white text-xs">
          <span class="flex items-center gap-1 drop-shadow">📍 ${v.cities}</span>
          <span class="text-[10px] opacity-90 drop-shadow">⚡ ${v.response_time || '< 15 mins'}</span>
        </div>
      </div>

      <div class="p-5 flex-1 flex flex-col justify-between">
        <div>
          <div class="flex items-start justify-between gap-2 mb-1.5">
            <h3 class="font-bold text-gray-900 text-base leading-snug group-hover:text-rose-600 transition-colors">${v.business_name}</h3>
            <div class="flex items-center gap-1 bg-amber-50 px-2 py-0.5 rounded-lg border border-amber-200 flex-shrink-0">
              <span class="text-amber-500 text-xs">★</span>
              <span class="font-bold text-gray-900 text-xs">${v.rating_avg}</span>
              <span class="text-[10px] text-gray-500">(${v.review_count})</span>
            </div>
          </div>

          <p class="text-xs text-gray-600 line-clamp-2 leading-relaxed mb-4">${desc}</p>

          <div class="p-3 bg-stone-50 rounded-2xl border border-stone-200 mb-4">
            <div class="flex items-baseline justify-between mb-1">
              <span class="text-[11px] font-semibold text-stone-500 uppercase tracking-wider">${t("fromPrice")}</span>
              <div class="text-right">
                <span class="text-base font-extrabold text-gray-900">₹${Number(v.starting_price || 0).toLocaleString('en-IN')}</span>
                <span class="text-[11px] text-gray-500 font-medium"> / ${v.price_unit || 'event'}</span>
              </div>
            </div>
            <div class="text-[11px] text-gray-600 flex items-center gap-1.5 pt-1 border-t border-stone-200/60">
              <span class="text-emerald-600 font-bold">✓</span>
              <span class="truncate">${v.lead_package_title || 'Itemized rate card available'}</span>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-2 pt-1 border-t border-gray-100">
          <button class="view-vendor-details-btn py-2.5 px-3 rounded-xl border border-gray-200 hover:border-rose-300 hover:bg-rose-50/50 text-gray-700 font-bold text-xs transition" data-vid="${v.id}">
            ${t("itemizedBreakdownBtn")}
          </button>
          <button class="open-quote-request-btn py-2.5 px-3 rounded-xl bg-gradient-to-r from-rose-600 to-amber-600 text-white font-bold text-xs shadow-sm hover:shadow transition" data-vid="${v.id}" data-vname="${v.business_name}" data-vcat="${v.category}">
            ${t("requestQuoteBtn")}
          </button>
        </div>
      </div>
    </article>
  `;
}

function attachVendorCardListeners(container) {
  container.querySelectorAll(".view-vendor-details-btn").forEach(btn => {
    btn.onclick = () => openVendorModal(btn.getAttribute("data-vid"));
  });

  container.querySelectorAll(".open-quote-request-btn").forEach(btn => {
    btn.onclick = () => openRfqModal(btn.getAttribute("data-vid"), btn.getAttribute("data-vname"), btn.getAttribute("data-vcat"));
  });

  container.querySelectorAll(".compare-toggle-btn").forEach(btn => {
    btn.onclick = (e) => {
      e.stopPropagation();
      const vid = parseInt(btn.getAttribute("data-vid"));
      if (state.comparisonList.includes(vid)) {
        state.comparisonList = state.comparisonList.filter(id => id !== vid);
      } else {
        if (state.comparisonList.length >= 4) {
          alert("You can compare up to 4 service providers at a time.");
          return;
        }
        state.comparisonList.push(vid);
      }
      renderCompareBar();
      renderVendorCatalog();
    };
  });
}

function renderCompareBar() {
  const bar = document.getElementById("floating-compare-bar");
  if (!bar) return;

  if (state.comparisonList.length >= 2) {
    bar.classList.remove("hidden");
    const label = document.getElementById("compare-bar-count");
    if (label) label.textContent = `${state.comparisonList.length} Providers Selected`;
    const openBtn = document.getElementById("trigger-compare-modal-btn");
    if (openBtn) openBtn.onclick = () => openComparisonModal();
  } else {
    bar.classList.add("hidden");
  }
}

async function openComparisonModal() {
  const modal = document.getElementById("vendor-comparison-modal");
  const content = document.getElementById("vendor-comparison-content");
  if (!modal || !content) return;

  content.innerHTML = `<div class="p-8 text-center"><div class="inline-block animate-spin text-2xl">⏳</div><p class="text-xs text-gray-500 mt-2">Loading side-by-side comparison matrix...</p></div>`;
  modal.classList.remove("hidden");
  modal.classList.add("flex");

  try {
    const res = await api.compareVendors(state.comparisonList);
    const comps = res.comparison || [];
    content.innerHTML = `
      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs border-collapse">
          <thead>
            <tr class="border-b bg-gray-50">
              <th class="p-3 font-bold text-gray-700">Service Feature</th>
              ${comps.map(c => `
                <th class="p-3 font-bold text-gray-900 border-l min-w-[200px]">
                  <div class="text-sm text-rose-700">${c.business_name}</div>
                  <div class="text-[10px] text-gray-500">${c.category} • ★ ${c.rating_avg}</div>
                </th>
              `).join("")}
            </tr>
          </thead>
          <tbody class="divide-y text-gray-700">
            <tr>
              <td class="p-3 font-semibold bg-gray-50/50">Base Package</td>
              ${comps.map(c => `
                <td class="p-3 border-l font-bold text-gray-900">
                  ${c.packages[0] ? `₹${Number(c.packages[0].base_price).toLocaleString('en-IN')} / ${c.packages[0].unit}` : 'Custom'}
                </td>
              `).join("")}
            </tr>
            <tr>
              <td class="p-3 font-semibold bg-gray-50/50">Top Inclusions</td>
              ${comps.map(c => `
                <td class="p-3 border-l text-[11px]">
                  ${c.packages[0] && c.packages[0].inclusions.length ? c.packages[0].inclusions.slice(0, 3).map(i => `<div>✓ ${i}</div>`).join("") : 'Specified in custom quote'}
                </td>
              `).join("")}
            </tr>
            <tr>
              <td class="p-3 font-semibold bg-gray-50/50">Cancellation Terms</td>
              ${comps.map(c => `
                <td class="p-3 border-l text-[10px] text-gray-600">${c.terms_and_conditions || 'Standard 14-day advance'}</td>
              `).join("")}
            </tr>
            <tr>
              <td class="p-3 font-semibold bg-gray-50/50">Action</td>
              ${comps.map(c => `
                <td class="p-3 border-l">
                  <button class="w-full py-2 bg-rose-600 text-white font-bold rounded-lg text-xs hover:bg-rose-700 transition" onclick="document.getElementById('vendor-comparison-modal').classList.add('hidden'); openRfqModal(${c.id}, '${c.business_name}', '${c.category}');">
                    Request Quote
                  </button>
                </td>
              `).join("")}
            </tr>
          </tbody>
        </table>
      </div>
    `;
  } catch (e) {
    content.innerHTML = `<div class="p-6 text-center text-red-600 text-xs">Failed to load comparison data.</div>`;
  }
}

async function openVendorModal(vendorId) {
  const modal = document.getElementById("vendor-details-modal");
  const content = document.getElementById("vendor-details-modal-content");
  if (!modal || !content) return;

  content.innerHTML = `<div class="p-8 text-center"><div class="inline-block animate-spin text-2xl">⏳</div></div>`;
  modal.classList.remove("hidden");
  modal.classList.add("flex");

  try {
    const res = await api.getVendorDetails(vendorId);
    const v = res.vendor;
    content.innerHTML = `
      <div class="space-y-6">
        <div class="flex items-center gap-4 border-b pb-4">
          <img src="${v.image_url || 'https://images.unsplash.com/photo-1519741497674-611481863552?auto=format&fit=crop&w=800&q=80'}" class="w-20 h-20 rounded-2xl object-cover" />
          <div>
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold uppercase text-rose-600">${v.category}</span>
              ${v.kyc_verified ? '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">✓ KYC Verified</span>' : ''}
            </div>
            <h3 class="text-xl font-bold text-gray-900">${v.business_name}</h3>
            <p class="text-xs text-gray-500">📍 ${v.cities} (Radius: ${v.service_radius_km} km) • ★ ${v.rating_avg} (${v.review_count} verified reviews)</p>
          </div>
        </div>

        <div>
          <h4 class="font-bold text-sm text-gray-900 mb-2">Transparent Itemized Packages</h4>
          <div class="space-y-4">
            ${v.packages.map(p => `
              <div class="p-4 rounded-2xl border border-rose-200 bg-rose-50/20">
                <div class="flex justify-between items-start mb-2">
                  <div>
                    <h5 class="font-bold text-sm text-gray-900">${p.title}</h5>
                    <span class="text-[11px] text-gray-500 font-medium">Pricing Model: ${p.pricing_model} (${p.unit})</span>
                  </div>
                  <span class="font-extrabold text-rose-700 text-base">₹${Number(p.base_price).toLocaleString('en-IN')}</span>
                </div>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs mt-3 pt-3 border-t border-rose-100">
                  <div>
                    <span class="font-bold text-emerald-700 block mb-1">Included in Package:</span>
                    <ul class="space-y-1 text-gray-600">
                      ${p.inclusions.map(inc => `<li class="flex items-center gap-1.5"><span class="text-emerald-600 font-bold">✓</span>${inc}</li>`).join("")}
                    </ul>
                  </div>
                  <div>
                    <span class="font-bold text-rose-700 block mb-1">Excluded (Available as Add-on):</span>
                    <ul class="space-y-1 text-gray-600">
                      ${p.exclusions.map(exc => `<li class="flex items-center gap-1.5"><span class="text-gray-400">✗</span>${exc}</li>`).join("")}
                    </ul>
                  </div>
                </div>
              </div>
            `).join("")}
          </div>
        </div>

        ${v.inventory && v.inventory.length ? `
          <div>
            <h4 class="font-bold text-sm text-gray-900 mb-2">Rental Equipment & Props Inventory</h4>
            <div class="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
              ${v.inventory.map(item => `
                <div class="p-2.5 bg-gray-50 rounded-xl border border-gray-200">
                  <span class="font-bold text-gray-900 block truncate">${item.item_name}</span>
                  <span class="text-[11px] text-rose-600 font-semibold">₹${item.rental_price_per_day}/day</span>
                  <span class="text-[10px] text-gray-500 block">Stock: ${item.available_stock}/${item.total_stock}</span>
                </div>
              `).join("")}
            </div>
          </div>
        ` : ''}

        <div class="p-3 bg-amber-50 rounded-xl border border-amber-200 text-xs text-amber-900">
          <span class="font-bold block">Terms & Cancellation Policy:</span>
          <p class="text-[11px] mt-0.5">${v.terms_and_conditions || 'Standard escrow terms apply. Full refund if cancelled 14 days prior.'}</p>
        </div>

        <div class="pt-4 border-t flex gap-2">
          <button class="flex-1 py-3 bg-gradient-to-r from-rose-600 to-amber-600 text-white font-bold rounded-xl text-xs uppercase tracking-wider" onclick="document.getElementById('vendor-details-modal').classList.add('hidden'); openRfqModal(${v.id}, '${v.business_name}', '${v.category}');">
            Request Custom Quotation
          </button>
          <button class="py-3 px-5 bg-gray-100 text-gray-700 font-bold rounded-xl text-xs" onclick="document.getElementById('vendor-details-modal').classList.add('hidden');">
            Close
          </button>
        </div>
      </div>
    `;
  } catch (e) {
    content.innerHTML = `<div class="p-6 text-center text-red-600 text-xs">Failed to load vendor details.</div>`;
  }
}

function openRfqModal(vendorId, vendorName, category) {
  const modal = document.getElementById("rfq-request-modal");
  if (!modal) return;
  document.getElementById("rfq-target-vendor-name").textContent = vendorName;
  document.getElementById("rfq-vendor-id-input").value = vendorId;
  document.getElementById("rfq-category-input").value = category;

  modal.classList.remove("hidden");
  modal.classList.add("flex");
}

// -------------------------------------------------------------
// VIEW 3: AI EVENT ARCHITECT
// -------------------------------------------------------------
function renderAiPlannerView() {
  showView("view-ai-planner");

  const form = document.getElementById("ai-standalone-planner-form");
  if (form) {
    form.onsubmit = async (e) => {
      e.preventDefault();
      const eventType = document.getElementById("ai-plan-type").value;
      const guests = document.getElementById("ai-plan-guests").value;
      const city = document.getElementById("ai-plan-city").value;
      const budgetTier = document.getElementById("ai-plan-tier").value;

      const resultsDiv = document.getElementById("ai-standalone-results");
      resultsDiv.classList.remove("hidden");
      resultsDiv.innerHTML = `
        <div class="p-8 bg-amber-50 rounded-3xl border border-amber-200 text-center animate-pulse">
          <div class="text-3xl mb-2">🤖</div>
          <h4 class="font-bold text-amber-900 text-base">Veduka AI is analyzing your celebration requirements...</h4>
          <p class="text-xs text-amber-700 mt-1">Calculating itemized budget allocations and checking registered provider availability.</p>
        </div>
      `;

      try {
        const res = await api.planEvent({
          event_type: eventType,
          guests: parseInt(guests),
          city: city,
          budget_tier: budgetTier,
          language: state.currentLang
        });

        const bp = res.blueprint;
        resultsDiv.innerHTML = `
          <div class="p-6 sm:p-8 bg-white rounded-3xl border-2 border-rose-100 shadow-xl space-y-6">
            <div class="flex items-start justify-between border-b pb-4">
              <div>
                <span class="inline-block px-3 py-1 rounded-full text-xs font-bold bg-rose-100 text-rose-800 mb-1">
                  ✨ AI Event Blueprint
                </span>
                <h3 class="text-2xl font-black text-gray-900">${bp.theme.name}</h3>
                <p class="text-xs text-gray-500 mt-1">${bp.city} • ${bp.guests} Guests • Colors: ${bp.theme.colors}</p>
              </div>
              <div class="text-right">
                <span class="text-xs text-gray-500 block">Total Est. Budget</span>
                <span class="text-2xl font-black text-rose-600">₹${Number(bp.total_estimated_budget).toLocaleString('en-IN')}</span>
              </div>
            </div>

            <!-- Itemized Budget Breakdown -->
            <div>
              <h4 class="font-bold text-sm text-gray-900 mb-3">Transparent Itemized Budget Allocation</h4>
              <div class="grid grid-cols-2 sm:grid-cols-5 gap-2.5 text-xs">
                ${Object.entries(bp.itemized_budget).map(([cat, info]) => `
                  <div class="p-3 bg-stone-50 rounded-2xl border border-stone-200">
                    <span class="font-bold uppercase text-[10px] text-gray-500 block">${cat} (${info.percentage}%)</span>
                    <span class="font-black text-gray-900 text-sm block">₹${Number(info.amount).toLocaleString('en-IN')}</span>
                    <span class="text-[10px] text-gray-500">${info.note}</span>
                  </div>
                `).join("")}
              </div>
            </div>

            <!-- 4-Phase Checklist -->
            <div>
              <h4 class="font-bold text-sm text-gray-900 mb-2">Event Preparation Timeline & Checklist</h4>
              <div class="space-y-2">
                ${bp.checklist.map(c => `
                  <div class="flex items-center gap-3 p-3 bg-gray-50 rounded-xl text-xs border border-gray-200">
                    <span class="px-2 py-0.5 rounded-lg bg-rose-600 text-white font-bold text-[10px]">${c.timeline}</span>
                    <span class="text-gray-800 font-medium">${c.task}</span>
                  </div>
                `).join("")}
              </div>
            </div>

            <!-- Matched Local Providers -->
            <div>
              <h4 class="font-bold text-sm text-gray-900 mb-2">Recommended Registered Providers for this Blueprint</h4>
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                ${bp.recommended_vendors.map(v => `
                  <div class="flex items-center justify-between p-3 rounded-2xl border border-gray-200 bg-white">
                    <div class="flex items-center gap-3">
                      <img src="${v.image_url}" class="w-12 h-12 rounded-xl object-cover" />
                      <div>
                        <h5 class="font-bold text-xs text-gray-900">${v.business_name}</h5>
                        <p class="text-[10px] text-gray-500">${v.category} • ★ ${v.rating_avg}</p>
                      </div>
                    </div>
                    <button class="px-3 py-1.5 bg-rose-50 text-rose-700 font-bold text-xs rounded-lg hover:bg-rose-100" onclick="openRfqModal(${v.id}, '${v.business_name}', '${v.category}');">
                      Send RFQ
                    </button>
                  </div>
                `).join("")}
              </div>
            </div>
          </div>
        `;
      } catch (err) {
        resultsDiv.innerHTML = `<div class="p-6 text-center text-red-600 text-xs">Error generating AI blueprint. Please try again.</div>`;
      }
    };
  }
}

// -------------------------------------------------------------
// VIEW 4: MY EVENTS & WORKSPACE
// -------------------------------------------------------------
function renderMyEventsView() {
  showView("view-my-events");

  const tabs = ["budget", "quotations", "tracking", "runsheet", "guests", "collaborators"];
  tabs.forEach(tab => {
    const btn = document.getElementById(`tab-btn-${tab}`);
    const pane = document.getElementById(`tab-pane-${tab}`);
    if (btn && pane) {
      if (state.activeEventTab === tab) {
        btn.classList.add("active");
        pane.classList.remove("hidden");
      } else {
        btn.classList.remove("active");
        pane.classList.add("hidden");
      }
      btn.onclick = () => {
        state.activeEventTab = tab;
        renderMyEventsView();
      };
    }
  });

  if (!state.activeEvent) {
    const titleEl = document.getElementById("event-title-display");
    if (titleEl) titleEl.textContent = "No active event yet. Click 'Create New Event' to start!";
    return;
  }

  // Populate Event Header
  const ev = state.activeEvent;
  const titleEl = document.getElementById("event-title-display");
  const subEl = document.getElementById("event-sub-display");
  if (titleEl) titleEl.textContent = ev.title;
  if (subEl) subEl.textContent = `${ev.event_type.toUpperCase()} • ${ev.event_date} • 📍 ${ev.city} (${ev.venue}) • ${ev.guest_count} Guests`;

  // Render Sub-tabs
  renderEventBudgetTab(ev);
  renderEventQuotationsTab(ev);
  renderEventTrackingTab(ev);
  renderEventRunsheetTab(ev);
  renderEventGuestsTab(ev);
}

function renderEventBudgetTab(ev) {
  const container = document.getElementById("budget-items-container");
  const totalDisplay = document.getElementById("budget-total-display");
  const spentDisplay = document.getElementById("budget-spent-display");
  if (!container) return;

  const total = Number(ev.total_budget || 0);
  let totalSpent = 0;

  container.innerHTML = (ev.budget_breakdown || []).map(b => {
    const spent = Number(b.spent_amount || 0);
    totalSpent += spent;
    const percent = Math.min(100, Math.round((spent / Number(b.allocated_amount)) * 100));

    return `
      <div class="p-4 bg-white rounded-2xl border border-gray-100 shadow-xs space-y-2">
        <div class="flex justify-between items-center text-xs">
          <span class="font-bold text-gray-800 uppercase tracking-wider">${b.category}</span>
          <span class="font-extrabold text-gray-900">₹${spent.toLocaleString('en-IN')} / ₹${Number(b.allocated_amount).toLocaleString('en-IN')}</span>
        </div>
        <div class="w-full h-2.5 bg-gray-100 rounded-full overflow-hidden">
          <div class="h-full bg-gradient-to-r from-rose-500 to-amber-500 rounded-full" style="width: ${percent}%"></div>
        </div>
        <div class="text-[10px] text-gray-500 text-right">${percent}% allocated budget utilized</div>
      </div>
    `;
  }).join("");

  if (totalDisplay) totalDisplay.textContent = `₹${total.toLocaleString('en-IN')}`;
  if (spentDisplay) spentDisplay.textContent = `₹${totalSpent.toLocaleString('en-IN')}`;
}

function renderEventQuotationsTab(ev) {
  const container = document.getElementById("quotations-list-container");
  if (!container) return;

  const quotes = ev.quotations || [];
  if (quotes.length === 0) {
    container.innerHTML = `<div class="p-8 text-center text-gray-500 text-xs">No vendor quotations received yet. Browse providers and click 'Request Custom Quote'!</div>`;
    return;
  }

  container.innerHTML = quotes.map(q => `
    <div class="p-5 bg-white rounded-2xl border border-gray-200 shadow-xs space-y-3">
      <div class="flex items-start justify-between">
        <div class="flex items-center gap-3">
          <img src="${q.image_url}" class="w-12 h-12 rounded-xl object-cover" />
          <div>
            <span class="text-[10px] font-bold uppercase text-rose-600">${q.category}</span>
            <h4 class="font-bold text-sm text-gray-900">${q.business_name}</h4>
            <span class="text-xs text-gray-500">Quotation v${q.version} • Status: <strong class="uppercase text-amber-700">${q.status}</strong></span>
          </div>
        </div>
        <div class="text-right">
          <span class="text-xs text-gray-500 block">Total Quoted</span>
          <span class="text-xl font-extrabold text-rose-700">₹${Number(q.total_amount).toLocaleString('en-IN')}</span>
          <span class="text-[10px] text-gray-500 block">Advance req: ₹${Number(q.advance_required).toLocaleString('en-IN')}</span>
        </div>
      </div>

      <div class="p-3 bg-gray-50 rounded-xl text-xs text-gray-700">
        <span class="font-bold">Vendor Notes:</span> ${q.terms_and_notes || 'Standard terms.'}
      </div>

      <div class="flex items-center justify-end gap-2 pt-2 border-t">
        ${q.status === 'sent' ? `
          <button class="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl shadow-xs accept-quote-btn" data-qid="${q.id}">
            ✓ Accept & Confirm Booking
          </button>
        ` : `<span class="px-3 py-1 bg-emerald-100 text-emerald-800 font-bold text-xs rounded-lg">✓ Accepted Booking</span>`}
      </div>
    </div>
  `).join("");

  container.querySelectorAll(".accept-quote-btn").forEach(btn => {
    btn.onclick = async () => {
      const qid = btn.getAttribute("data-qid");
      try {
        await api.acceptQuotation(qid);
        alert("Quotation accepted! Advance secured in escrow and booking confirmed.");
        await refreshActiveEvent();
        renderMyEventsView();
      } catch (err) {
        alert(err.message);
      }
    };
  });
}

function renderEventTrackingTab(ev) {
  const container = document.getElementById("booking-tracking-container");
  if (!container) return;

  const bookings = ev.bookings || [];
  if (bookings.length === 0) {
    container.innerHTML = `<div class="p-8 text-center text-gray-500 text-xs">No active bookings to track. Accept a quotation to initialize live milestone tracking!</div>`;
    return;
  }

  container.innerHTML = bookings.map(b => `
    <div class="p-6 bg-white rounded-3xl border border-gray-200 shadow-sm space-y-4">
      <div class="flex items-center justify-between border-b pb-3">
        <div>
          <span class="text-xs font-bold uppercase text-rose-600">${b.category}</span>
          <h4 class="text-base font-bold text-gray-900">${b.business_name}</h4>
          <span class="text-xs text-gray-500">Order #VEDUKA-${b.id} • Total: ₹${Number(b.total_amount).toLocaleString('en-IN')}</span>
        </div>
        <span class="px-3 py-1 bg-emerald-50 text-emerald-800 font-bold text-xs rounded-full border border-emerald-200">
          ● Status: ${b.booking_status}
        </span>
      </div>

      <!-- 5-Stage Visual Lifecycle Pipeline -->
      <div class="relative py-2">
        <div class="grid grid-cols-5 gap-1 text-center">
          <div class="p-2 bg-emerald-50 text-emerald-800 rounded-xl border border-emerald-200 text-xs">
            <span class="block font-bold">1. Confirmed</span>
            <span class="text-[9px]">Advance Secured</span>
          </div>
          <div class="p-2 bg-amber-50 text-amber-800 rounded-xl border border-amber-200 text-xs">
            <span class="block font-bold">2. Pre-Event</span>
            <span class="text-[9px]">Moodboard Ready</span>
          </div>
          <div class="p-2 bg-gray-50 text-gray-500 rounded-xl border border-gray-200 text-xs">
            <span class="block font-bold">3. Event Day</span>
            <span class="text-[9px]">Check-in & Live</span>
          </div>
          <div class="p-2 bg-gray-50 text-gray-500 rounded-xl border border-gray-200 text-xs">
            <span class="block font-bold">4. Deliverables</span>
            <span class="text-[9px]">Photo/Setup Handover</span>
          </div>
          <div class="p-2 bg-gray-50 text-gray-500 rounded-xl border border-gray-200 text-xs">
            <span class="block font-bold">5. Review</span>
            <span class="text-[9px]">Settlement</span>
          </div>
        </div>
      </div>
    </div>
  `).join("");
}

function renderEventRunsheetTab(ev) {
  const container = document.getElementById("runsheet-timeline-container");
  if (!container) return;

  const items = ev.runsheet || [];
  container.innerHTML = `
    <div class="space-y-3">
      ${items.map(item => `
        <div class="flex items-center gap-4 p-3.5 bg-white rounded-2xl border border-gray-200 text-xs">
          <span class="px-2.5 py-1 bg-rose-50 text-rose-700 font-bold rounded-lg">${item.time_slot}</span>
          <div class="flex-1">
            <h5 class="font-bold text-gray-900">${item.activity}</h5>
            <span class="text-[10px] text-gray-500">Contact: ${item.contact_name || 'Coordinator'} (${item.contact_phone || 'N/A'})</span>
          </div>
          <span class="text-xs ${item.is_completed ? 'text-emerald-600 font-bold' : 'text-gray-400'}">
            ${item.is_completed ? '✓ Completed' : 'Pending'}
          </span>
        </div>
      `).join("")}
    </div>
  `;
}

function renderEventGuestsTab(ev) {
  const container = document.getElementById("guests-list-container");
  const statsDisplay = document.getElementById("guest-stats-display");
  if (!container) return;

  const guests = ev.guests || [];
  const attending = guests.filter(g => g.rsvp_status === "attending").length;
  const checkedIn = guests.filter(g => g.checked_in === 1).length;

  if (statsDisplay) {
    statsDisplay.textContent = `Total: ${guests.length} | Attending: ${attending} | Checked-in at Venue: ${checkedIn}`;
  }

  container.innerHTML = guests.map(g => `
    <div class="flex items-center justify-between p-3.5 bg-white rounded-2xl border border-gray-200 text-xs">
      <div>
        <h5 class="font-bold text-gray-900">${g.full_name} (${g.guest_count} guests)</h5>
        <p class="text-[10px] text-gray-500">Side: ${g.side.toUpperCase()} • Meal: ${g.dietary.toUpperCase()} • Table: ${g.table_number}</p>
        <span class="inline-block mt-1 font-mono text-[10px] px-2 py-0.5 bg-gray-100 rounded text-gray-700">QR: ${g.qr_code_token}</span>
      </div>
      <div class="text-right">
        <span class="px-2.5 py-1 rounded-full text-[10px] font-bold ${g.checked_in ? 'bg-emerald-100 text-emerald-800' : 'bg-gray-100 text-gray-700'}">
          ${g.checked_in ? '✓ Checked In' : 'Not Checked In'}
        </span>
        <button class="block mt-1 text-[10px] text-rose-600 hover:underline copy-invite-btn" data-token="${g.qr_code_token}">
          Copy Digital Invite
        </button>
      </div>
    </div>
  `).join("");

  container.querySelectorAll(".copy-invite-btn").forEach(btn => {
    btn.onclick = () => {
      const token = btn.getAttribute("data-token");
      navigator.clipboard.writeText(`https://veduka.ai/rsvp/${token}`).catch(() => {});
      alert(`Digital WhatsApp invite link copied for QR pass: ${token}`);
    };
  });
}

// -------------------------------------------------------------
// VIEW 5: SELLER DASHBOARD & INQUIRIES
// -------------------------------------------------------------
async function renderSellerDashboardView() {
  showView("view-seller-dashboard");

  try {
    const res = await api.getSellerDashboard();
    const m = res.metrics;

    document.getElementById("seller-inquiries-kpi").textContent = m.inquiries;
    document.getElementById("seller-bookings-kpi").textContent = m.active_bookings;
    document.getElementById("seller-revenue-kpi").textContent = `₹${Number(m.total_revenue).toLocaleString('en-IN')}`;
    document.getElementById("seller-pending-kpi").textContent = `₹${Number(m.pending_escrow_payout).toLocaleString('en-IN')}`;

    // Render Recent Inquiries
    const inquiriesContainer = document.getElementById("seller-recent-inquiries");
    if (inquiriesContainer) {
      inquiriesContainer.innerHTML = (res.recent_inquiries || []).map(inq => `
        <div class="p-4 bg-white rounded-2xl border border-gray-200 shadow-xs flex items-center justify-between">
          <div>
            <span class="text-[10px] font-bold uppercase text-rose-600">${inq.category}</span>
            <h5 class="font-bold text-sm text-gray-900">${inq.customer_name}</h5>
            <p class="text-xs text-gray-500">${inq.event_title} (${inq.event_date}) • ${inq.guest_count} Guests</p>
            <p class="text-xs text-gray-700 italic mt-1">"${inq.requirements}"</p>
          </div>
          <button class="px-4 py-2 bg-gradient-to-r from-rose-600 to-amber-600 text-white font-bold text-xs rounded-xl shadow-xs" onclick="openQuotationBuilderModal(${inq.id}, ${inq.event_id}, ${inq.customer_id});">
            Build Itemized Quote
          </button>
        </div>
      `).join("");
    }
  } catch (err) {
    console.error("Seller dashboard error:", err);
  }
}

function renderSellerInquiriesView() {
  showView("view-seller-inquiries");
  renderSellerDashboardView();
}

async function renderSellerInventoryView() {
  showView("view-seller-inventory");
  try {
    const res = await api.getSellerDashboard();
    const container = document.getElementById("seller-inventory-table-container");
    if (!container) return;

    container.innerHTML = `
      <div class="p-6 bg-white rounded-3xl border border-gray-200 shadow-sm space-y-4">
        <div class="flex justify-between items-center">
          <h4 class="font-bold text-base text-gray-900">Rental Equipment & Props Stock</h4>
          <button class="px-3 py-1.5 bg-rose-50 text-rose-700 font-bold text-xs rounded-xl" onclick="alert('Add inventory item modal (Demo)');">
            + Add New Asset
          </button>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs border-collapse">
            <thead>
              <tr class="border-b bg-gray-50">
                <th class="p-3 font-bold text-gray-700">Item Name</th>
                <th class="p-3 font-bold text-gray-700">Category</th>
                <th class="p-3 font-bold text-gray-700">Available / Total</th>
                <th class="p-3 font-bold text-gray-700">Rate / Day</th>
                <th class="p-3 font-bold text-gray-700">Deposit</th>
              </tr>
            </thead>
            <tbody class="divide-y text-gray-700">
              ${(res.inventory || []).map(item => `
                <tr>
                  <td class="p-3 font-bold text-gray-900">${item.item_name}</td>
                  <td class="p-3">${item.category}</td>
                  <td class="p-3 font-semibold text-emerald-700">${item.available_stock} / ${item.total_stock}</td>
                  <td class="p-3 font-bold">₹${Number(item.rental_price_per_day).toLocaleString('en-IN')}</td>
                  <td class="p-3">₹${Number(item.security_deposit).toLocaleString('en-IN')}</td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      </div>
    `;
  } catch (e) {}
}

// -------------------------------------------------------------
// VIEW 6: ADMINISTRATOR PANEL
// -------------------------------------------------------------
async function renderAdminPanelView() {
  showView("view-admin-panel");

  try {
    const res = await api.getAdminOverview();
    const m = res.metrics;

    document.getElementById("admin-users-kpi").textContent = m.total_users;
    document.getElementById("admin-vendors-kpi").textContent = m.total_vendors;
    document.getElementById("admin-bookings-kpi").textContent = m.total_bookings;
    document.getElementById("admin-gmv-kpi").textContent = `₹${Number(m.gross_marketplace_volume).toLocaleString('en-IN')}`;

    const vendorContainer = document.getElementById("admin-vendors-list");
    if (vendorContainer) {
      vendorContainer.innerHTML = (res.vendors || []).map(v => `
        <div class="p-4 bg-white rounded-2xl border border-gray-200 flex items-center justify-between text-xs">
          <div>
            <h5 class="font-bold text-gray-900">${v.business_name} (${v.category})</h5>
            <span class="text-gray-500">Contact: ${v.email || v.phone} • Status: ${v.kyc_verified ? 'Verified Pro' : 'Pending Verification'}</span>
          </div>
          <button class="px-3 py-1.5 rounded-xl font-bold ${v.kyc_verified ? 'bg-amber-100 text-amber-800' : 'bg-emerald-600 text-white'} admin-verify-btn" data-vid="${v.id}">
            ${v.kyc_verified ? 'Revoke KYC' : 'Verify Vendor KYC'}
          </button>
        </div>
      `).join("");

      vendorContainer.querySelectorAll(".admin-verify-btn").forEach(btn => {
        btn.onclick = async () => {
          const vid = btn.getAttribute("data-vid");
          await api.verifyVendor(vid);
          await loadVendors();
          renderAdminPanelView();
        };
      });
    }
  } catch (err) {
    console.error("Admin overview error:", err);
  }
}

// -------------------------------------------------------------
// VIEW 7: PROFILE & SETTINGS
// -------------------------------------------------------------
function renderProfileView() {
  showView("view-profile");

  const nameEl = document.getElementById("profile-name-display");
  const emailEl = document.getElementById("profile-email-display");
  const roleEl = document.getElementById("profile-role-display");
  const speedSlider = document.getElementById("speech-speed-slider");
  const contrastCheck = document.getElementById("high-contrast-toggle");

  if (nameEl && state.user) nameEl.textContent = state.user.full_name;
  if (emailEl && state.user) emailEl.textContent = state.user.email || state.user.phone || "No email";
  if (roleEl && state.user) roleEl.textContent = `Active Role: ${state.currentRole.toUpperCase()}`;

  if (speedSlider) {
    speedSlider.value = state.speechSpeed;
    speedSlider.oninput = (e) => {
      state.speechSpeed = parseFloat(e.target.value);
      document.getElementById("speech-speed-val").textContent = `${state.speechSpeed}x`;
      if (state.user) api.updateSettings({ speech_speed: state.speechSpeed }).catch(() => {});
    };
  }

  if (contrastCheck) {
    contrastCheck.checked = state.highContrast;
    contrastCheck.onchange = (e) => {
      state.highContrast = e.target.checked;
      applyTheme();
      if (state.user) api.updateSettings({ high_contrast: state.highContrast }).catch(() => {});
    };
  }
}

// -------------------------------------------------------------
// VOICE ASSISTANT & "LISTEN TO THIS PAGE" (TTS)
// -------------------------------------------------------------
function setupVoiceAssistant() {
  const triggerBtns = [
    document.getElementById("header-voice-btn"),
    document.getElementById("fab-voice-btn"),
    document.getElementById("hero-voice-chip")
  ];
  const modal = document.getElementById("voice-modal");
  const closeBtn = document.getElementById("close-voice-modal");
  const micBtn = document.getElementById("voice-mic-action-btn");
  const statusEl = document.getElementById("voice-mic-status");
  const transcriptEl = document.getElementById("voice-transcript-output");
  const answerEl = document.getElementById("voice-ai-answer");

  if (!modal) return;

  const openModal = () => {
    modal.classList.remove("hidden");
    modal.classList.add("flex");
  };

  const closeModal = () => {
    modal.classList.add("hidden");
    modal.classList.remove("flex");
  };

  triggerBtns.forEach(b => { if (b) b.onclick = openModal; });
  if (closeBtn) closeBtn.onclick = closeModal;

  // Web Speech API
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  let rec = null;
  if (SpeechRecognition) {
    rec = new SpeechRecognition();
    rec.continuous = false;
    rec.onresult = (e) => {
      const text = e.results[0][0].transcript;
      if (transcriptEl) transcriptEl.textContent = `"${text}"`;
      handleVoiceQuery(text);
    };
    rec.onerror = () => {
      if (statusEl) statusEl.textContent = "Mic ready. Click a sample query or speak again.";
    };
  }

  if (micBtn) {
    micBtn.onclick = () => {
      if (!rec) {
        alert("Browser speech recognition not available. Please click a sample query below.");
        return;
      }
      rec.lang = state.currentLang === "te" ? "te-IN" : state.currentLang === "hi" ? "hi-IN" : "en-IN";
      try {
        rec.start();
        if (statusEl) statusEl.textContent = `Listening in ${state.currentLang.toUpperCase()}... Speak now.`;
      } catch (err) {}
    };
  }

  document.querySelectorAll(".sample-voice-chip").forEach(chip => {
    chip.onclick = () => {
      const q = chip.getAttribute("data-query");
      if (transcriptEl) transcriptEl.textContent = `"${q}"`;
      handleVoiceQuery(q);
    };
  });

  function handleVoiceQuery(query) {
    const lower = query.toLowerCase();
    let reply = "";
    let targetCat = "all";

    if (lower.includes("ఫోటో") || lower.includes("photo") || lower.includes("कैमरा")) {
      targetCat = "photography";
      reply = state.currentLang === "te" 
        ? "హైదరాబాద్ మరియు విజయవాడలోని అగ్రశ్రేణి క్యాండిడ్ ఫోటోగ్రాఫర్ల ప్యాకేజీలు ₹45,000 నుండి ప్రారంభమవుతున్నాయి."
        : "Showing top candid wedding photographers with transparent packages from ₹45,000.";
    } else if (lower.includes("క్యాటరింగ్") || lower.includes("cater") || lower.includes("खाना")) {
      targetCat = "catering";
      reply = state.currentLang === "te" 
        ? "అన్నపూర్ణ రాయల్ క్యాటరర్స్ ప్లేట్ ధర ₹480 నుండి లభిస్తుంది. సాంప్రదాయ తెలుగు వంటకాల వివరాలు ఇక్కడ ఉన్నాయి."
        : "Showing authentic Andhra catering providers starting at ₹480 per plate.";
    } else if (lower.includes("డెకరేషన్") || lower.includes("decor") || lower.includes("सजावट")) {
      targetCat = "decorations";
      reply = state.currentLang === "te" 
        ? "సాంప్రదాయ పూల మండపాలు మరియు ఆధునిక స్టేజ్ డెకరేషన్స్ ప్యాకేజీలు ₹38,000 నుండి సిద్ధంగా ఉన్నాయి."
        : "Showing traditional floral mandaps and stage decor starting from ₹38,000.";
    } else {
      reply = `Filtering verified event providers for "${query}".`;
    }

    if (answerEl) {
      answerEl.classList.remove("hidden");
      answerEl.innerHTML = `<div class="p-3 bg-emerald-50 rounded-xl border border-emerald-200 text-xs font-semibold text-emerald-950">${reply}</div>`;
    }

    speakAloud(reply);

    state.selectedCategory = targetCat;
    loadVendors().then(() => {
      navigateTo("discover");
    });
  }
}

function setupListenPage() {
  const listenBtn = document.getElementById("listen-page-btn");
  if (!listenBtn) return;

  listenBtn.onclick = () => {
    let text = "";
    if (state.activeView === "home") {
      text = state.currentLang === "te" 
        ? "వేడుక ఏఐ హోమ్ స్క్రీన్ కు స్వాగతం. ఇక్కడ మీరు నమ్మకమైన స్థానిక ఫోటోగ్రాఫర్స్, క్యాటరింగ్, డెకరేషన్స్ మరియు వేదికలను పారదర్శక ధరలతో నేరుగా బుక్ చేసుకోవచ్చు."
        : "Welcome to Veduka AI. Discover verified local wedding photographers, caterers, stage decorators, and venues with 100% upfront itemized pricing.";
    } else if (state.activeView === "discover") {
      text = state.currentLang === "te" 
        ? `ప్రస్తుతం ${state.vendors.length} సర్వీస్ ప్రొవైడర్లు అందుబాటులో ఉన్నారు. ధరలు మరియు ప్యాకేజీలను పోల్చి చూసేందుకు కంపేర్ బటన్ ను ఉపయోగించండి.`
        : `Showing ${state.vendors.length} verified service providers. Compare rate cards, inclusions, and request custom quotations.`;
    } else if (state.activeView === "myEvents") {
      text = state.currentLang === "te" 
        ? "మీ ఈవెంట్ ప్లానింగ్ వర్క్‌స్పేస్. బడ్జెట్ స్థితి, కొటేషన్లు, మాస్టర్ రన్-షీట్ మరియు క్యూఆర్ చెక్-ఇన్ వివరాలు ఇక్కడ ఉన్నాయి."
        : "Your event workspace. Monitor your budget, approved vendor quotations, event day run-sheet, and guest QR code check-in.";
    } else {
      text = "Veduka AI Event Marketplace. Empowering celebrations with precision, transparent pricing, and regional language assistance.";
    }

    speakAloud(text);
  };
}

function speakAloud(text) {
  if (!("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();

  const u = new SpeechSynthesisUtterance(text);
  u.lang = state.currentLang === "te" ? "te-IN" : state.currentLang === "hi" ? "hi-IN" : "en-IN";
  u.rate = state.speechSpeed || 1.0;
  window.speechSynthesis.speak(u);
}

function setupAccessibilityControls() {
  const contrastToggle = document.getElementById("header-contrast-toggle");
  if (contrastToggle) {
    contrastToggle.onclick = () => {
      state.highContrast = !state.highContrast;
      applyTheme();
      if (state.user) api.updateSettings({ high_contrast: state.highContrast }).catch(() => {});
    };
  }
}

// -------------------------------------------------------------
// AUTH MODAL & QUICK DEMO LOGINS
// -------------------------------------------------------------
function setupAuthEvents() {
  const authModal = document.getElementById("auth-modal");
  const closeAuthBtn = document.getElementById("close-auth-modal");
  const loginForm = document.getElementById("auth-login-form");
  const registerForm = document.getElementById("auth-register-form");

  if (closeAuthBtn && authModal) {
    closeAuthBtn.onclick = () => {
      authModal.classList.add("hidden");
      authModal.classList.remove("flex");
    };
  }

  // Quick Demo Logins
  const demoCustomerBtn = document.getElementById("demo-login-customer");
  const demoVendorBtn = document.getElementById("demo-login-vendor");
  const demoAdminBtn = document.getElementById("demo-login-admin");

  if (demoCustomerBtn) {
    demoCustomerBtn.onclick = async () => {
      await performLogin("customer@veduka.ai", "customer123");
    };
  }
  if (demoVendorBtn) {
    demoVendorBtn.onclick = async () => {
      await performLogin("nirvana@veduka.ai", "vendor123");
    };
  }
  if (demoAdminBtn) {
    demoAdminBtn.onclick = async () => {
      await performLogin("admin@veduka.ai", "admin123");
    };
  }

  if (loginForm) {
    loginForm.onsubmit = async (e) => {
      e.preventDefault();
      const identifier = document.getElementById("auth-login-id").value;
      const pass = document.getElementById("auth-login-pass").value;
      await performLogin(identifier, pass);
    };
  }

  if (registerForm) {
    registerForm.onsubmit = async (e) => {
      e.preventDefault();
      const name = document.getElementById("auth-reg-name").value;
      const email = document.getElementById("auth-reg-email").value;
      const phone = document.getElementById("auth-reg-phone").value;
      const pass = document.getElementById("auth-reg-pass").value;
      const role = document.getElementById("auth-reg-role").value;

      try {
        const res = await api.register({
          full_name: name,
          email: email || undefined,
          phone: phone || undefined,
          password: pass,
          role: role,
          preferred_language: state.currentLang
        });
        api.setToken(res.token);
        api.setUser(res.user);
        state.user = res.user;
        state.currentRole = res.user.role;
        document.getElementById("auth-modal").classList.add("hidden");
        alert("Registration successful! Welcome to Veduka AI.");
        renderApp();
      } catch (err) {
        alert(err.message);
      }
    };
  }

  // Role Switcher buttons
  const switchToCustomerBtn = document.getElementById("switch-role-customer-btn");
  const switchToVendorBtn = document.getElementById("switch-role-vendor-btn");
  if (switchToCustomerBtn) switchToCustomerBtn.onclick = () => switchUserRole("customer");
  if (switchToVendorBtn) switchToVendorBtn.onclick = () => switchUserRole("vendor");

  // Logout
  const logoutBtn = document.getElementById("profile-logout-btn");
  if (logoutBtn) {
    logoutBtn.onclick = () => {
      api.setToken("");
      api.setUser(null);
      state.user = null;
      state.currentRole = "customer";
      navigateTo("home");
    };
  }
}

async function performLogin(identifier, password) {
  try {
    const res = await api.login({ identifier, password });
    api.setToken(res.token);
    api.setUser(res.user);
    state.user = res.user;
    state.currentRole = res.user.role;
    state.currentLang = res.user.preferred_language || "en";
    state.highContrast = res.user.high_contrast === 1;
    applyTheme();

    const authModal = document.getElementById("auth-modal");
    if (authModal) authModal.classList.add("hidden");

    await loadNotifications();
    await refreshActiveEvent();

    if (state.currentRole === "vendor") {
      navigateTo("sellerDashboard");
    } else if (state.currentRole === "admin") {
      navigateTo("adminPanel");
    } else {
      navigateTo("myEvents");
    }
  } catch (err) {
    alert(err.message);
  }
}

async function switchUserRole(newRole) {
  try {
    const res = await api.switchRole(newRole);
    api.setToken(res.token);
    state.currentRole = newRole;
    state.user.role = newRole;
    api.setUser(state.user);
    if (newRole === "vendor") navigateTo("sellerDashboard");
    else if (newRole === "admin") navigateTo("adminPanel");
    else navigateTo("home");
  } catch (err) {
    alert(err.message);
  }
}

function openAuthModal(initialTab = "login", defaultRole = "customer") {
  const modal = document.getElementById("auth-modal");
  if (!modal) return;
  modal.classList.remove("hidden");
  modal.classList.add("flex");

  const loginTab = document.getElementById("auth-tab-login");
  const regTab = document.getElementById("auth-tab-register");
  const loginForm = document.getElementById("auth-login-form");
  const regForm = document.getElementById("auth-register-form");

  if (initialTab === "register") {
    if (regTab) regTab.classList.add("border-rose-600", "text-rose-600");
    if (loginTab) loginTab.classList.remove("border-rose-600", "text-rose-600");
    if (regForm) regForm.classList.remove("hidden");
    if (loginForm) loginForm.classList.add("hidden");
    const roleSelect = document.getElementById("auth-reg-role");
    if (roleSelect) roleSelect.value = defaultRole;
  } else {
    if (loginTab) loginTab.classList.add("border-rose-600", "text-rose-600");
    if (regTab) regTab.classList.remove("border-rose-600", "text-rose-600");
    if (loginForm) loginForm.classList.remove("hidden");
    if (regForm) regForm.classList.add("hidden");
  }
}

// Global functions for inline HTML modal handling
window.openAuthModal = openAuthModal;
window.openVendorModal = openVendorModal;
window.openRfqModal = openRfqModal;
window.openQuotationBuilderModal = openQuotationBuilderModal;
window.switchUserRole = switchUserRole;
window.navigateTo = navigateTo;

function openQuotationBuilderModal(reqId, eventId, customerId) {
  const modal = document.getElementById("seller-quote-builder-modal");
  if (!modal) return;
  document.getElementById("quote-builder-req-id").value = reqId;
  document.getElementById("quote-builder-event-id").value = eventId;
  document.getElementById("quote-builder-customer-id").value = customerId;

  modal.classList.remove("hidden");
  modal.classList.add("flex");
}
