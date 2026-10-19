// Client API Service for Veduka AI Backend
const API_BASE = "";

export const api = {
  getToken() {
    return localStorage.getItem("veduka_token") || "";
  },

  setToken(token) {
    if (token) localStorage.setItem("veduka_token", token);
    else localStorage.removeItem("veduka_token");
  },

  getUser() {
    const raw = localStorage.getItem("veduka_user");
    try {
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  },

  setUser(user) {
    if (user) localStorage.setItem("veduka_user", JSON.stringify(user));
    else localStorage.removeItem("veduka_user");
  },

  async request(endpoint, options = {}) {
    const headers = options.headers || {};
    const token = this.getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    if (options.body && typeof options.body === "object" && !(options.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(options.body);
    }

    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        throw new Error(data.error || `Request failed with status ${res.status}`);
      }
      return data;
    } catch (err) {
      console.error(`API Error [${endpoint}]:`, err);
      throw err;
    }
  },

  // Auth endpoints
  async register(payload) {
    return this.request("/api/auth/register", { method: "POST", body: payload });
  },

  async login(payload) {
    return this.request("/api/auth/login", { method: "POST", body: payload });
  },

  async logout() {
    return this.request("/api/auth/logout", { method: "POST" });
  },

  async getMe() {
    return this.request("/api/auth/me", { method: "GET" });
  },

  async switchRole(role) {
    return this.request("/api/auth/switch-role", { method: "POST", body: { role } });
  },

  async updateSettings(settings) {
    return this.request("/api/auth/update-settings", { method: "POST", body: settings });
  },

  // Vendors
  async getVendors(params = {}) {
    const query = new URLSearchParams(params).toString();
    return this.request(`/api/vendors?${query}`, { method: "GET" });
  },

  async getVendorDetails(id) {
    return this.request(`/api/vendors/${id}`, { method: "GET" });
  },

  async compareVendors(vendorIds) {
    return this.request("/api/vendors/compare", { method: "POST", body: { vendor_ids: vendorIds } });
  },

  // AI Planner
  async planEvent(payload) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 25000);
    try {
      return await this.request("/api/ai/plan", {
        method: "POST",
        body: payload,
        signal: controller.signal
      });
    } catch (error) {
      if (error.name === "AbortError") {
        throw new Error("Plan generation timed out. Check your connection and try again.");
      }
      throw error;
    } finally {
      clearTimeout(timeoutId);
    }
  },

  async sellerAssist(payload) {
    return this.request("/api/ai/seller-assist", { method: "POST", body: payload });
  },

  // Customer Events
  async getEvents() {
    return this.request("/api/events", { method: "GET" });
  },

  async createEvent(payload) {
    return this.request("/api/events", { method: "POST", body: payload });
  },

  async getEventDetails(id) {
    return this.request(`/api/events/${id}`, { method: "GET" });
  },

  // Quotations
  async requestQuotation(payload) {
    return this.request("/api/quotations/request", { method: "POST", body: payload });
  },

  async respondQuotation(quoteId, payload) {
    return this.request(`/api/quotations/${quoteId}/respond`, { method: "POST", body: payload });
  },

  async acceptQuotation(quoteId) {
    return this.request(`/api/quotations/${quoteId}/accept`, { method: "POST" });
  },

  // Bookings & Milestones
  async getBookings() {
    return this.request("/api/bookings", { method: "GET" });
  },

  async getBookingDetails(id) {
    return this.request(`/api/bookings/${id}`, { method: "GET" });
  },

  async updateMilestone(bookingId, stage, payload) {
    return this.request(`/api/bookings/${bookingId}/milestones/${stage}/update`, { method: "POST", body: payload });
  },

  // Guests & QR Check-in
  async getGuests(eventId) {
    return this.request(`/api/events/${eventId}/guests`, { method: "GET" });
  },

  async addGuest(eventId, payload) {
    return this.request(`/api/events/${eventId}/guests`, { method: "POST", body: payload });
  },

  async checkInGuest(token) {
    return this.request("/api/guests/check-in", { method: "POST", body: { qr_code_token: token } });
  },

  // Seller Dashboard
  async getSellerDashboard() {
    return this.request("/api/seller/dashboard", { method: "GET" });
  },

  // Admin
  async getAdminOverview() {
    return this.request("/api/admin/overview", { method: "GET" });
  },

  async verifyVendor(vendorId) {
    return this.request(`/api/admin/verify-vendor/${vendorId}`, { method: "POST" });
  },

  // Notifications & Support
  async getNotifications() {
    return this.request("/api/notifications", { method: "GET" });
  },

  async markNotificationRead(id) {
    return this.request(`/api/notifications/${id}/read`, { method: "POST" });
  },

  async getSupportTickets() {
    return this.request("/api/support", { method: "GET" });
  },

  async createSupportTicket(payload) {
    return this.request("/api/support", { method: "POST", body: payload });
  }
};
