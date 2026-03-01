/* ============================================================
   Simple SPA Router — Hash-based navigation
   ============================================================ */

const router = {
    _routes: {},
    _current: null,

    register(name, renderFn) {
        this._routes[name] = renderFn;
    },

    navigate(name) {
        const prev = this._current;
        this._current = name;
        store.set('currentScreen', name);

        // Animate out previous screen
        const container = document.getElementById('app');
        const prevScreen = container.querySelector('.screen.active');
        if (prevScreen) {
            prevScreen.classList.add('slide-out-left');
            prevScreen.classList.remove('active');
            setTimeout(() => prevScreen.remove(), 400);
        }

        // Render new screen
        if (this._routes[name]) {
            const screenEl = this._routes[name]();
            if (screenEl) {
                container.appendChild(screenEl);
                // Force reflow then animate in
                requestAnimationFrame(() => {
                    requestAnimationFrame(() => {
                        screenEl.classList.add('active');
                    });
                });
            }
        }

        // Close sidebar on navigation
        store.set('sidebarOpen', false);
    },

    getCurrentScreen() {
        return this._current;
    },
};
