/* ============================================================
   Global State Store — Central app state with event system
   ============================================================ */

const store = {
    /* ---- State ---- */
    _state: {
        user: null,
        userId: null,
        categories: [],
        expenses: [],
        budgets: [],
        summary: null,
        currentScreen: 'splash',
        sidebarOpen: false,
        loading: {},
    },

    _listeners: [],

    /* ---- Getters ---- */
    get(key) {
        return this._state[key];
    },

    getAll() {
        return { ...this._state };
    },

    /* ---- Setters ---- */
    set(key, value) {
        this._state[key] = value;
        this._notify(key);
    },

    update(partial) {
        Object.assign(this._state, partial);
        Object.keys(partial).forEach(k => this._notify(k));
    },

    /* ---- Loading helpers ---- */
    setLoading(key, val) {
        this._state.loading = { ...this._state.loading, [key]: val };
        this._notify('loading');
    },
    isLoading(key) {
        return !!this._state.loading[key];
    },

    /* ---- Subscribe ---- */
    subscribe(fn) {
        this._listeners.push(fn);
        return () => {
            this._listeners = this._listeners.filter(l => l !== fn);
        };
    },

    _notify(key) {
        this._listeners.forEach(fn => fn(key, this._state));
    },

    /* ---- Data actions (async) ---- */
    async initUser() {
        this.setLoading('user', true);
        try {
            // 1. Check URL hash for login_success after Google OAuth redirect
            const hash = window.location.hash;
            if (hash.includes('login_success')) {
                const params = new URLSearchParams(hash.split('?')[1]);
                const userId = params.get('user_id');
                if (userId) {
                    localStorage.setItem('user_id', userId);
                    window.location.hash = ''; // Clear hash
                }
            }

            // 2. Check localStorage for persistent session
            const userId = localStorage.getItem('user_id');
            if (!userId) {
                this.update({ user: null, userId: null });
                return null;
            }

            // 3. Fetch user data from backend
            const user = await api.getUser(userId);
            if (user) {
                this.update({ user, userId: user.user_id });
                if (user.dark_mode) document.body.classList.add('dark-mode');
                else document.body.classList.remove('dark-mode');
                return user;
            } else {
                localStorage.removeItem('user_id');
            }
        } catch (e) {
            console.error('Failed to init user:', e);
            // If user not found (e.g. DB cleared), logout
            if (e.message.includes('404')) localStorage.removeItem('user_id');
        } finally {
            this.setLoading('user', false);
        }
    },

    async updateProfile(updates) {
        const userId = this.get('userId');
        if (!userId) return;
        this.setLoading('user', true);
        try {
            const updatedUser = await api.updateUserProfile(userId, updates);
            this.update({ user: updatedUser });
            if (updatedUser.dark_mode) document.body.classList.add('dark-mode');
            else document.body.classList.remove('dark-mode');
            return updatedUser;
        } catch (e) {
            console.error('Failed to update profile:', e);
            throw e;
        } finally {
            this.setLoading('user', false);
        }
    },

    async loadCategories() {
        this.setLoading('categories', true);
        try {
            const data = await api.listCategories();
            this.set('categories', data.categories || []);
        } catch (e) {
            console.error('Failed to load categories:', e);
        } finally {
            this.setLoading('categories', false);
        }
    },

    async loadExpenses(opts = {}) {
        this.setLoading('expenses', true);
        try {
            const userId = this.get('userId');
            if (!userId) return;
            const data = await api.listExpenses({ userId, limit: 200, ...opts });
            this.set('expenses', data.expenses || []);
        } catch (e) {
            console.error('Failed to load expenses:', e);
        } finally {
            this.setLoading('expenses', false);
        }
    },

    async loadBudgets() {
        this.set('budgets', []); // Clear stale budgets
        this.setLoading('budgets', true);
        try {
            const userId = this.get('userId');
            if (!userId) return;
            const d = new Date();
            const currentMonth = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
            const data = await api.getUserBudgets(userId, currentMonth);
            this.set('budgets', data.budgets || []);
        } catch (e) {
            console.error('Failed to load budgets:', e);
        } finally {
            this.setLoading('budgets', false);
        }
    },

    async loadSummary(startDate, endDate) {
        this.setLoading('summary', true);
        try {
            const userId = this.get('userId');
            if (!userId) return;

            // Default to current month if no dates provided
            if (!startDate && !endDate) {
                const now = new Date();
                const year = now.getFullYear();
                const month = now.getMonth();
                startDate = `${year}-${String(month + 1).padStart(2, '0')}-01`;
                // Get last day of month
                const lastDay = new Date(year, month + 1, 0).getDate();
                endDate = `${year}-${String(month + 1).padStart(2, '0')}-${lastDay}`;
            }

            const data = await api.spendingSummary(userId, startDate, endDate);
            this.set('summary', data);
        } catch (e) {
            console.error('Failed to load summary:', e);
        } finally {
            this.setLoading('summary', false);
        }
    },



    async addExpense(expenseData) {
        this.setLoading('addExpense', true);
        try {
            const userId = this.get('userId');
            const result = await api.createExpense({ user_id: userId, ...expenseData });
            await this.loadExpenses();
            await this.loadSummary();
            return result;
        } catch (e) {
            console.error('Failed to add expense:', e);
            throw e;
        } finally {
            this.setLoading('addExpense', false);
        }
    },

    async deleteExpense(expenseId) {
        this.setLoading('deleteExpense', true);
        try {
            await api.deleteExpense(expenseId);
            await this.loadExpenses();
            await this.loadSummary();
        } catch (e) {
            console.error('Failed to delete expense:', e);
            throw e;
        } finally {
            this.setLoading('deleteExpense', false);
        }
    },

    async addBudget(budgetData) {
        this.setLoading('addBudget', true);
        try {
            const userId = this.get('userId');
            const result = await api.createBudget({ user_id: userId, ...budgetData });
            await this.loadBudgets();
            return result;
        } catch (e) {
            console.error('Failed to add budget:', e);
            throw e;
        } finally {
            this.setLoading('addBudget', false);
        }
    },

    /* Category helpers */
    getCategoryById(id) {
        return this.get('categories').find(c => c.category_id === id);
    },
    getCategoryName(id) {
        const cat = this.getCategoryById(id);
        return cat ? cat.name : 'Uncategorized';
    },
    getCategoryIcon(id) {
        const cat = this.getCategoryById(id);
        return cat ? cat.icon : '📌';
    },
    getCategoryColor(id) {
        const cat = this.getCategoryById(id);
        return cat ? cat.color : '#D5DBDB';
    },

    /* Format helpers */
    getCurrencySymbol() {
        const user = this.get('user');
        const currency = (user && user.preferred_currency) ? user.preferred_currency : 'INR';
        try {
            const parts = new Intl.NumberFormat('en', { style: 'currency', currency }).formatToParts(0);
            const part = parts.find(p => p.type === 'currency');
            return part ? part.value : currency;
        } catch (e) { return currency; }
    },

    formatCurrency(amount, currencyOverride) {
        let currency = currencyOverride;
        if (!currency) {
            const user = this.get('user');
            currency = (user && user.preferred_currency) ? user.preferred_currency : 'INR';
        }
        const abs = Math.abs(amount || 0);
        try {
            return new Intl.NumberFormat('en', { style: 'currency', currency, minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(abs);
        } catch (e) {
            return currency + ' ' + abs.toLocaleString();
        }
    },

    formatDate(dateStr) {
        if (!dateStr) return '';
        // Parse date part only to avoid timezone shifts during comparison
        const d = new Date(dateStr);
        const d_yyyy = d.getFullYear();
        const d_mm = d.getMonth();
        const d_dd = d.getDate();
        const dateKey = `${d_yyyy}-${String(d_mm + 1).padStart(2, '0')}-${String(d_dd).padStart(2, '0')}`;

        const now = new Date();
        const todayStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;

        const yesterday = new Date();
        yesterday.setDate(now.getDate() - 1);
        const yesterdayStr = `${yesterday.getFullYear()}-${String(yesterday.getMonth() + 1).padStart(2, '0')}-${String(yesterday.getDate()).padStart(2, '0')}`;

        if (dateKey === todayStr) return 'Today';
        if (dateKey === yesterdayStr) return 'Yesterday';

        const diffTime = Math.abs(new Date(todayStr) - new Date(dateKey));
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

        if (diffDays < 7) {
            return d.toLocaleDateString('en-US', { weekday: 'long' });
        }
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    },

    formatDateFull(dateStr) {
        if (!dateStr) return '';
        return new Date(dateStr).toLocaleDateString('en-US', {
            year: 'numeric', month: 'long', day: 'numeric'
        });
    },
};
