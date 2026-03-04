/* ============================================================
   API Service — Simplified for college project
   4 tables: users, categories, expenses, budgets
   ============================================================ */

const API_BASE = (() => {
    // Auto-detect environment:
    // If running on local server (localhost, 127.0.0.1) or via file:// protocol
    const hn = window.location.hostname;
    if (hn === 'localhost' || hn === '127.0.0.1' || !hn) {
        return 'http://localhost:10000'; // Target local FastAPI backend
    }
    // Production on Render — same origin, no CORS needed
    return '';
})();

const api = {
    getBaseUrl() { return API_BASE; },
    async _fetch(path, opts = {}) {
        const url = `${API_BASE}${path}`;
        const config = {
            headers: { 'Content-Type': 'application/json', ...opts.headers },
            ...opts,
        };
        try {
            const res = await fetch(url, config);
            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: res.statusText }));
                throw new Error(err.detail || `HTTP ${res.status}`);
            }
            return res.json();
        } catch (e) {
            if (e.name === 'TypeError' && e.message.includes('Failed to fetch')) {
                console.warn(`API cold start? Retrying [${path}] in 3s...`);
                await new Promise(r => setTimeout(r, 3000));
                const res2 = await fetch(url, config);
                if (!res2.ok) throw new Error(`HTTP ${res2.status}`);
                return res2.json();
            }
            throw e;
        }
    },

    get(path) { return this._fetch(path); },
    post(path, body) { return this._fetch(path, { method: 'POST', body: JSON.stringify(body) }); },
    put(path, body) { return this._fetch(path, { method: 'PUT', body: JSON.stringify(body) }); },
    del(path) { return this._fetch(path, { method: 'DELETE' }); },

    // System
    health() { return this.get('/health'); },

    // Users
    listUsers(limit = 50) { return this.get(`/users?limit=${limit}`); },
    getUser(id) { return this.get(`/users/${id}`); },
    createUser(data) { return this.post('/users', data); },
    updateUserProfile(id, data) { return this.put(`/users/${id}/profile`, data); },

    // Categories
    listCategories() { return this.get('/categories'); },

    // Expenses
    listExpenses({ userId, categoryId, limit = 50, offset = 0 } = {}) {
        const p = new URLSearchParams();
        if (userId) p.set('user_id', userId);
        if (categoryId) p.set('category_id', categoryId);
        p.set('limit', limit);
        p.set('offset', offset);
        return this.get(`/expenses?${p}`);
    },
    createExpense(data) { return this.post('/expenses', data); },
    deleteExpense(id) { return this.del(`/expenses/${id}`); },

    // Budgets
    createBudget(data) { return this.post('/budgets', data); },
    getUserBudgets(userId, month) {
        const q = month ? `?month=${month}` : '';
        return this.get(`/budgets/${userId}${q}`);
    },

    // Analytics
    spendingSummary(userId, startDate, endDate) {
        let q = '';
        if (startDate || endDate) {
            const p = new URLSearchParams();
            if (startDate) p.set('start_date', startDate);
            if (endDate) p.set('end_date', endDate);
            q = '?' + p.toString();
        }
        return this.get(`/analytics/summary/${userId}${q}`);
    },
    aiRecommendations(userId) {
        return this.get(`/analytics/recommendations/${userId}`);
    },

    // Gmail Sync
    previewGmailSync(userId) {
        return this.get(`/sync/gmail/preview?user_id=${userId}`);
    },
    confirmGmailSync(userId, expenses) {
        return this.post(`/sync/gmail/confirm?user_id=${userId}`, expenses);
    },

    // OCR
    async uploadInvoice(file) {
        const formData = new FormData();
        formData.append('file', file);
        const url = `${API_BASE}/ocr/upload`;
        const res = await fetch(url, { method: 'POST', body: formData });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail || `HTTP ${res.status}`);
        }
        return res.json();
    },
    saveOCRItems(data) {
        return this.post('/ocr/save', data);
    },
};
