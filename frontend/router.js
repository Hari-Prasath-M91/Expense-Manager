/* ============================================================
   Simple SPA Router — History API + surgical updates
   ============================================================ */

const router = {
    _routes: {},
    _current: null,
    _fromPopState: false, // flag to avoid double-pushing on browser back

    register(name, renderFn) {
        this._routes[name] = renderFn;
    },

    navigate(name, opts = {}) {
        const prev = this._current;
        const container = document.getElementById('app');

        // SURGICAL UPDATE: If we're already on this screen, just update the data
        if (prev === name) {
            console.log(`[Router] Surgical update for: ${name}`);
            const updateFnName = 'update' + name.split('-').map(s => s.charAt(0).toUpperCase() + s.slice(1)).join('') + 'Surgical';
            if (window[updateFnName]) {
                window[updateFnName]();
                return;
            }
            // Fallback: no surgical fn found, fall through to full re-render
        }

        this._current = name;
        store.set('currentScreen', name);

        // Push to browser history (unless we got here FROM the browser back/fwd button)
        if (!this._fromPopState && !opts.replace) {
            history.pushState({ screen: name }, '', '#' + name);
        } else if (opts.replace) {
            history.replaceState({ screen: name }, '', '#' + name);
        }
        this._fromPopState = false;

        // Animate out previous screen
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

    back() {
        history.back();
    },

    getCurrentScreen() {
        return this._current;
    },
};

// Listen for browser back/forward button presses
window.addEventListener('popstate', (e) => {
    const screen = e.state?.screen;
    if (screen && router._routes[screen]) {
        router._fromPopState = true;
        router.navigate(screen);
    } else {
        // No state (e.g. very first entry) — go to dashboard if logged in
        const userId = localStorage.getItem('user_id');
        if (userId) {
            router._fromPopState = true;
            router.navigate('dashboard');
        }
    }
});
