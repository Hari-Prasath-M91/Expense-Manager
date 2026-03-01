/* ============================================================
   💎 UI Components — Finalized for Clean Architecture
   ============================================================ */

function el(tag, attrs = {}, ...children) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
        if (k === 'class') e.className = v;
        else if (k === 'style' && typeof v === 'object') Object.assign(e.style, v);
        else if (k.startsWith('on') && typeof v === 'function') e.addEventListener(k.slice(2).toLowerCase(), v);
        else if (v !== undefined && v !== null) e.setAttribute(k, v);
    }
    children.flat(Infinity).forEach(c => {
        if (c == null || c === false) return;
        e.appendChild((typeof c === 'string' || typeof c === 'number') ? document.createTextNode(String(c)) : c);
    });
    return e;
}

function svg(html, w = 24, h = 24) {
    const d = document.createElement('div');
    d.innerHTML = (html || '').trim();
    const s = d.firstChild;
    if (s && s.setAttribute && s.nodeType === 1) {
        s.setAttribute('width', w);
        s.setAttribute('height', h);
    }
    return s || d;
}

const icons = {
    menu: `<svg viewBox="0 0 24 24"><path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"/></svg>`,
    profile: `<svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z"/></svg>`,
    back: `<svg viewBox="0 0 24 24"><path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/></svg>`,
    home: `<svg viewBox="0 0 24 24"><path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"/></svg>`,
    wallet: `<svg viewBox="0 0 24 24"><path d="M21 18v1c0 1.1-.9 2-2 2H5c-1.11 0-2-.9-2-2V5c0-1.1.89-2 2-2h14c1.1 0 2 .9 2 2v1h-9c-1.11 0-2 .9-2 2v8c0 1.1.89 2 2 2h9zm-9-2h10V8H12v8zm4-2.5c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5z"/></svg>`,
    add: `<svg viewBox="0 0 24 24"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>`,
    chat: `<svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/></svg>`,
    budget: `<svg viewBox="0 0 24 24"><path d="M11.8 10.9c-2.27-.59-3-1.2-3-2.15 0-1.09 1.01-1.85 2.7-1.85 1.78 0 2.44.85 2.5 2.1h2.21c-.07-1.72-1.12-3.3-3.21-3.81V3h-3v2.16c-1.94.42-3.5 1.68-3.5 3.61 0 2.31 1.91 3.46 4.7 4.13 2.5.6 3 1.48 3 2.41 0 .69-.49 1.79-2.7 1.79-2.06 0-2.87-.92-2.98-2.1h-2.2c.12 2.19 1.76 3.42 3.68 3.83V21h3v-2.15c1.95-.37 3.5-1.5 3.5-3.55 0-2.84-2.43-3.81-4.7-4.4z"/></svg>`,
    settings: `<svg viewBox="0 0 24 24"><path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.07.62-.07.94s.02.64.07.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/></svg>`,
    send: `<svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>`,
    arrowUp: `<svg viewBox="0 0 24 24"><path d="M7 14l5-5 5 5z" fill="#fff"/></svg>`,
    arrowDown: `<svg viewBox="0 0 24 24"><path d="M7 10l5 5 5-5z" fill="#fff"/></svg>`,
    chevronRight: `<svg viewBox="0 0 24 24"><path d="M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z"/></svg>`,
    chevronLeft: `<svg viewBox="0 0 24 24"><path d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z"/></svg>`,
    logout: `<svg viewBox="0 0 24 24"><path d="M17 7l-1.41 1.41L18.17 11H8v2h10.17l-2.58 2.58L17 17l5-5zM4 5h8V3H4c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h8v-2H4V5z"/></svg>`,
    get money() {
        return `<svg viewBox="0 0 48 48" fill="none"><rect x="6" y="14" width="36" height="22" rx="3" fill="#aed581"/><rect x="10" y="18" width="28" height="14" rx="2" fill="#c5e1a5"/><circle cx="24" cy="25" r="5" fill="#558b2f"/><text x="24" y="28" text-anchor="middle" fill="#fff" font-size="8" font-weight="bold">${typeof store !== 'undefined' ? store.getCurrencySymbol() : '₹'}</text></svg>`;
    },
    invoice: `<svg viewBox="0 0 24 24"><path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/></svg>`,
    close: `<svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>`,
};

function DashboardHeader() {
    const user = store.get('user');
    const name = user ? user.full_name : 'User';
    return el('div', { class: 'header-bar' },
        el('div', { class: 'header-bg' }),
        el('div', { class: 'header-circles' },
            el('div', { class: 'header-circle' }),
            el('div', { class: 'header-circle' }),
            el('div', { class: 'header-circle' }),
        ),
        el('div', { class: 'header-top sticky-bar' },
            el('button', { class: 'header-menu-btn', id: 'menu-btn', onClick: () => store.set('sidebarOpen', true) }, svg(icons.menu, 28, 28)),
            el('button', { class: 'header-profile-btn', id: 'profile-btn', onClick: () => router.navigate('profile') }, svg(icons.profile, 36, 36)),
        ),
        el('div', { class: 'header-greeting' },
            el('div', { class: 'header-greeting-label' }, 'Expense Tracker'),
            el('div', { class: 'header-greeting-name' }, `Hello, ${name}`),
        ),
    );
}

function SubHeader(title, backTo = 'dashboard') {
    return el('div', { class: 'sub-header' },
        el('div', { class: 'sub-header-bg' }),
        el('div', { class: 'header-circles' },
            el('div', { class: 'header-circle' }),
            el('div', { class: 'header-circle' }),
            el('div', { class: 'header-circle' }),
        ),
        el('div', { class: 'sub-header-content' },
            el('button', { class: 'sub-header-back', onClick: () => router.navigate(backTo) }, svg(icons.back, 24, 24)),
            el('span', { class: 'sub-header-title' }, title),
        ),
    );
}

function BalanceCard() {
    const summary = store.get('summary');
    const budgets = store.get('budgets') || [];
    const totalSpent = summary ? (summary.summary?.total_spent || 0) : 0;
    const transactionCount = summary?.summary?.transaction_count || 0;

    const totalBudgetObj = budgets.find(b => !b.category_id);
    const totalBudget = totalBudgetObj ? totalBudgetObj.amount : null;
    const budgetLeft = (totalBudget !== null && totalBudget > 0) ? totalBudget - totalSpent : null;

    return el('div', { class: 'balance-card' },
        el('span', { class: 'balance-label' }, 'Total Expenses'),
        el('div', { class: 'balance-amount' }, store.formatCurrency(totalSpent)),
        el('div', { class: 'balance-row' },
            el('div', { class: 'balance-item' },
                el('div', { class: 'balance-item-icon expense' }, svg(icons.wallet, 20, 20)),
                el('div', { class: 'balance-item-info' },
                    el('span', { class: 'balance-item-label' }, 'Budget Left'),
                    el('span', { class: 'balance-item-amount' }, (totalBudget !== null && totalBudget > 0) ? store.formatCurrency(budgetLeft) : 'N/A'),
                ),
            ),
            el('div', { class: 'balance-item' },
                el('div', { class: 'balance-item-icon income' }, svg(icons.arrowDown, 20, 20)),
                el('div', { class: 'balance-item-info' },
                    el('span', { class: 'balance-item-label' }, 'Transactions'),
                    el('span', { class: 'balance-item-amount' }, String(transactionCount)),
                ),
            ),
        ),
    );
}



function TransactionItem(expense) {
    const cats = store.get('categories') || [];
    // Try to find category by ID first, then fallback to name
    const cat = cats.find(c => c.category_id === expense.category_id) ||
        cats.find(c => c.name === expense.category_name);

    const catName = cat ? cat.name : (expense.category_name || 'Uncategorized');
    const catIcon = cat ? cat.icon : '📌';
    const catColor = cat ? cat.color : '#D5DBDB';

    return el('div', { class: 'transaction-item' },
        el('div', { class: 'transaction-icon', style: { background: catColor + '22' } }, catIcon),
        el('div', { class: 'transaction-info' },
            el('div', { class: 'transaction-name' }, catName),
            el('div', { class: 'transaction-category' }, catName),
        ),
        el('div', { class: 'transaction-right' },
            el('div', { class: 'transaction-amount expense' }, '- ' + store.formatCurrency(expense.amount)),
            el('div', { class: 'transaction-date' }, store.formatDate(expense.expense_date)),
        ),
    );
}

function CategoryDropdown(categories, onSelect, initialCat = null) {
    let selected = initialCat;

    const hiddenInput = el('input', { type: 'hidden', name: 'category_id', id: 'expense-category', required: 'true', value: initialCat ? initialCat.category_id : '' });
    const selectedIcon = el('span', { class: 'dropdown-selected-icon' }, initialCat ? initialCat.icon : '📌');
    const selectedText = el('span', { class: 'dropdown-selected-text' }, initialCat ? initialCat.name : 'Select Category');

    const optionsList = el('div', { class: 'dropdown-options custom-scrollbar' },
        ...categories.map(c => {
            const opt = el('div', { class: 'dropdown-option' },
                el('span', { class: 'dropdown-option-icon' }, c.icon || '📌'),
                el('span', { class: 'dropdown-option-text' }, c.name)
            );
            opt.onclick = (e) => {
                e.stopPropagation();
                selected = c;
                hiddenInput.value = c.category_id;
                selectedIcon.textContent = c.icon || '📌';
                selectedText.textContent = c.name;
                dropdown.classList.remove('open');
                if (onSelect) onSelect(c);
            };
            return opt;
        })
    );

    const dropdown = el('div', { class: 'custom-dropdown', id: 'category-dropdown' },
        hiddenInput,
        el('div', { class: 'dropdown-selected' },
            selectedIcon,
            selectedText,
            svg(icons.arrowDown, 12, 8)
        ),
        optionsList
    );

    dropdown.onclick = () => {
        const isOpen = dropdown.classList.contains('open');
        // Close all other dropdowns
        document.querySelectorAll('.custom-dropdown').forEach(d => d.classList.remove('open'));
        if (!isOpen) dropdown.classList.add('open');
    };

    // Close on outside click
    window.addEventListener('click', (e) => {
        if (!dropdown.contains(e.target)) dropdown.classList.remove('open');
    }, { once: false });

    return dropdown;
}

function DatePicker({ id, value, onChange, allowFuture = false, restrictToExpenses = false }) {
    const expenses = store.get('expenses') || [];
    const today = new Date();
    const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;

    // Determine allowed range
    let minDate = '2000-01-01'; // Allow all past dates
    let maxDate = allowFuture ? '2099-12-31' : todayStr;

    if (restrictToExpenses) {
        minDate = todayStr;
        maxDate = todayStr;
        if (expenses.length > 0) {
            const dates = expenses.map(e => e.expense_date).sort();
            minDate = dates[0];
            if (dates[dates.length - 1] > maxDate) maxDate = dates[dates.length - 1];
        }
        if (allowFuture) maxDate = '2099-12-31';
    }

    const selectedDate = value || todayStr;
    const parts = selectedDate.split('-');
    let viewYear = parseInt(parts[0]);
    let viewMonth = parseInt(parts[1]) - 1;

    const hiddenInput = el('input', { type: 'hidden', id, name: id, value: selectedDate });

    const fmtDisplay = (ds) => {
        const d = new Date(ds + 'T00:00:00');
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    };

    const displayText = el('span', { class: 'dp-display-text' }, fmtDisplay(selectedDate));
    const calendarPanel = el('div', { class: 'dp-calendar' });
    calendarPanel.addEventListener('click', (e) => e.stopPropagation());

    function buildCalendar() {
        calendarPanel.innerHTML = '';
        const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
        const dayNames = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];

        function createCustomDropdown(options, currentValue, onSelect, className) {
            const dropdown = el('div', { class: 'dp-header-dropdown ' + className });
            const current = el('div', { class: 'dp-header-dropdown-selected' },
                el('span', {}, String(currentValue)),
                svg(icons.arrowDown, 10, 6)
            );
            const list = el('div', { class: 'dp-header-dropdown-list custom-scrollbar' },
                ...options.map(opt => {
                    const item = el('div', { class: 'dp-header-dropdown-item' + (String(opt) === String(currentValue) ? ' active' : '') }, String(opt));
                    item.onclick = (e) => {
                        e.stopPropagation();
                        onSelect(opt);
                        dropdown.classList.remove('open');
                    };
                    return item;
                })
            );

            dropdown.onclick = (e) => {
                e.stopPropagation();
                const isOpen = dropdown.classList.contains('open');
                document.querySelectorAll('.dp-header-dropdown').forEach(d => d.classList.remove('open'));
                if (!isOpen) {
                    dropdown.classList.add('open');
                    // Scroll active item into view
                    setTimeout(() => {
                        const active = list.querySelector('.dp-header-dropdown-item.active');
                        if (active) active.scrollIntoView({ block: 'center' });
                    }, 0);
                }
            };

            dropdown.appendChild(current);
            dropdown.appendChild(list);
            return dropdown;
        }

        const monthSelect = createCustomDropdown(
            monthNames,
            monthNames[viewMonth],
            (m) => { viewMonth = monthNames.indexOf(m); buildCalendar(); },
            'month-selector'
        );

        const currentYear = new Date().getFullYear();
        const years = [];
        for (let y = currentYear - 50; y <= currentYear + (allowFuture ? 10 : 0); y++) {
            years.push(y);
        }

        const yearSelect = createCustomDropdown(
            years,
            viewYear,
            (y) => { viewYear = parseInt(y); buildCalendar(); },
            'year-selector'
        );

        // Header
        const header = el('div', { class: 'dp-header' },
            el('button', { class: 'dp-nav-btn', type: 'button', onClick: (e) => { e.stopPropagation(); viewMonth--; if (viewMonth < 0) { viewMonth = 11; viewYear--; } buildCalendar(); } }, svg(icons.chevronLeft, 18, 18)),
            el('div', { style: 'display: flex; align-items: center; gap: 6px;' }, monthSelect, yearSelect),
            el('button', { class: 'dp-nav-btn', type: 'button', onClick: (e) => { e.stopPropagation(); viewMonth++; if (viewMonth > 11) { viewMonth = 0; viewYear++; } buildCalendar(); } }, svg(icons.chevronRight, 18, 18)),
        );
        calendarPanel.appendChild(header);

        // Day names
        const dayRow = el('div', { class: 'dp-day-names' }, ...dayNames.map(d => el('div', { class: 'dp-day-name' }, d)));
        calendarPanel.appendChild(dayRow);

        // Days grid
        const firstDay = new Date(viewYear, viewMonth, 1).getDay();
        const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
        const grid = el('div', { class: 'dp-days-grid' });

        for (let i = 0; i < firstDay; i++) {
            grid.appendChild(el('div', { class: 'dp-day empty' }));
        }

        for (let day = 1; day <= daysInMonth; day++) {
            const ds = `${viewYear}-${String(viewMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            const isSelected = ds === hiddenInput.value;
            const isDisabled = ds < minDate || ds > maxDate;
            const isToday = ds === todayStr;

            let cls = 'dp-day';
            if (isSelected) cls += ' selected';
            if (isDisabled) cls += ' disabled';
            if (isToday) cls += ' today';

            const dayEl = el('div', { class: cls }, String(day));
            if (!isDisabled) {
                dayEl.onclick = (e) => {
                    e.stopPropagation();
                    hiddenInput.value = ds;
                    displayText.textContent = fmtDisplay(ds);
                    container.classList.remove('open');
                    if (onChange) onChange(ds);
                };
            }
            grid.appendChild(dayEl);
        }
        calendarPanel.appendChild(grid);
    }

    const container = el('div', { class: 'dp-container', id: id + '-picker' },
        hiddenInput,
        el('div', {
            class: 'dp-trigger', onClick: (e) => {
                e.stopPropagation();
                const isOpen = container.classList.contains('open');
                document.querySelectorAll('.dp-container').forEach(d => d.classList.remove('open'));
                if (!isOpen) { buildCalendar(); container.classList.add('open'); }
            }
        },
            el('span', { class: 'dp-icon' }, '📅'),
            displayText,
        ),
        calendarPanel
    );

    window.addEventListener('click', (e) => {
        if (!container.contains(e.target)) container.classList.remove('open');
    });

    return container;
}

function LoadingSpinner(text = 'Loading...') {
    return el('div', { class: 'loading-spinner' },
        el('div', { class: 'spinner' }),
        el('span', { class: 'loading-text' }, text),
    );
}

function EmptyState(icon, title, text) {
    return el('div', { class: 'empty-state' },
        el('div', { class: 'empty-state-icon' }, icon),
        el('div', { class: 'empty-state-title' }, title),
        el('div', { class: 'empty-state-text' }, text),
    );
}

const toast = {
    _container: null,
    _init() { if (!this._container) { this._container = el('div', { class: 'toast-container' }); document.body.appendChild(this._container); } },
    show(msg, type = 'success', dur = 3000) {
        this._init();
        const t = el('div', { class: `toast ${type}` }, msg);
        this._container.appendChild(t);
        setTimeout(() => { t.classList.add('toast-exit'); setTimeout(() => t.remove(), 300); }, dur);
    },
    success(m) { this.show(m, 'success'); },
    error(m) { this.show(m, 'error'); },
    info(m) { this.show(m, 'info'); },
};

function Sidebar() {
    const navItems = [
        { id: 'dashboard', label: 'Dashboard', icon: icons.home },
        { id: 'add-expense', label: 'Add Expense', icon: icons.add },
        { id: 'transactions', label: 'Transactions', icon: icons.money },
        { id: 'budget', label: 'Budget', icon: icons.budget },
        { id: 'chatbot', label: 'Chatbot', icon: icons.chat },
        { id: 'profile', label: 'Settings', icon: icons.settings },
    ];
    const user = store.get('user');
    const overlay = el('div', { class: 'sidebar-overlay', onClick: () => store.set('sidebarOpen', false) });
    const sidebar = el('div', { class: 'sidebar' },
        el('div', { class: 'sidebar-header' },
            el('div', { class: 'sidebar-app-name' }, 'Expense Tracker'),
            el('div', { class: 'sidebar-user-name' }, user ? user.full_name : 'User'),
        ),
        el('nav', { class: 'sidebar-nav' },
            ...navItems.map(item =>
                el('button', {
                    class: 'sidebar-nav-item' + (store.get('currentScreen') === item.id ? ' active' : ''),
                    onClick: () => router.navigate(item.id),
                }, svg(item.icon, 22, 22), item.label)
            ),
        ),
    );
    const container = el('div', { id: 'sidebar-root' }, overlay, sidebar);
    store.subscribe((key) => {
        if (key === 'sidebarOpen') {
            const isOpen = store.get('sidebarOpen');
            overlay.classList.toggle('open', isOpen);
            sidebar.classList.toggle('open', isOpen);
        }
    });
    if (store.get('sidebarOpen')) { overlay.classList.add('open'); sidebar.classList.add('open'); }
    return container;
}
