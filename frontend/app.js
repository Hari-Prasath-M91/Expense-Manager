/* ============================================================
   🚀 App Logic — Final Version (Clean Architecture)
   ============================================================ */

/* ---- Splash ---- */
function renderSplash() {
    return el('div', { class: 'screen splash-screen', id: 'splash-screen' },
        el('div', { class: 'splash-circles' },
            el('div', { class: 'splash-circle' }),
            el('div', { class: 'splash-circle' }),
            el('div', { class: 'splash-circle' }),
        ),
        el('div', { class: 'splash-icon' }, svg(icons.money, 120, 120)),
        el('div', { class: 'splash-title' }, 'Personal Expense Manager'),
        el('div', { class: 'splash-subtitle' }, 'Track Smart, Save Better'),
        el('button', {
            class: 'google-btn',
            id: 'google-login-btn',
            onClick: () => {
                const btn = document.getElementById('google-login-btn');
                btn.innerHTML = '<span>Connecting...</span>';
                btn.disabled = true;
                // Use absolute URL to backend to avoid path issues
                window.location.href = api.getBaseUrl() + '/auth/google';
            }
        },
            svg(icons.google, 20, 20),
            el('span', {}, 'Continue with Google')
        ),
    );
}

/* ---- Dashboard ---- */
function renderDashboard() {
    const screen = el('div', { class: 'screen', id: 'dashboard-screen' },
        DashboardHeader(),
        el('div', { class: 'px-page' },
            el('div', { id: 'ai-insight-section' }),
            BalanceCard(),
            el('div', { id: 'recent-txn-section' }),
            el('div', { id: 'spending-chart-section' }),
            el('div', { id: 'trend-chart-section' }),
        ),
    );

    // Transparent loading overlay to see the dashboard behind it
    const loadingOverlay = el('div', { class: 'loading-overlay' }, LoadingSpinner('Crafting your dashboard...'));
    screen.appendChild(loadingOverlay);

    // Ensure sidebar exists
    if (!document.getElementById('sidebar-root')) {
        document.getElementById('app').appendChild(Sidebar());
    }

    setTimeout(async () => {
        try {
            await Promise.all([
                store.loadExpenses(),
                store.loadSummary(),
                store.loadCategories(),
                store.loadBudgets(),
                store.loadRecommendations()
            ]);
        } finally {
            loadingOverlay.classList.add('slide-out-left');
            setTimeout(() => loadingOverlay.remove(), 400);
        }

        renderSpendingChart();
        renderTrendChart();
        renderAIInsight();
        renderRecentTransactions();
        // Re-render BalanceCard since it depends on budgets
        const balanceNode = document.querySelector('.balance-card');
        if (balanceNode) {
            const newNode = BalanceCard();
            balanceNode.replaceWith(newNode);
        }
    }, 100);

    return screen;
}

function renderSpendingChart() {
    const section = document.getElementById('spending-chart-section');
    if (!section) return;
    const summary = store.get('summary');
    const byCat = summary?.by_category || [];

    if (byCat.length === 0) {
        section.innerHTML = '';
        section.appendChild(el('div', { class: 'chart-card slide-up' },
            el('div', { class: 'chart-card-title' }, 'Spending by Category'),
            EmptyState('📊', 'No data yet', 'Add expenses to see your spending breakdown'),
        ));
        return;
    }

    const figmaColors = ['#fbc04f', '#62aade', '#ed61ae', '#69ba6c', '#ec6258', '#D5DBDB'];
    const totalAll = byCat.reduce((s, c) => s + (c.total || 0), 0) || 1;
    const top6 = byCat.slice(0, 6);
    const labels = top6.map(c => c.category);
    const data = top6.map(c => c.total);
    const colors = top6.map((c, i) => c.color || figmaColors[i % figmaColors.length]);

    const card = el('div', { class: 'chart-card slide-up' },
        el('div', { class: 'chart-card-title' }, 'Spending by Category'),
        el('div', { class: 'chart-content' },
            el('div', { class: 'chart-canvas-wrap' }, el('canvas', { id: 'pie-chart' })),
            el('div', { class: 'chart-legend' },
                ...top6.map((c, i) => {
                    const pct = Math.round((c.total / totalAll) * 100);
                    return el('div', { class: 'legend-item' },
                        el('div', { class: 'legend-dot', style: { background: colors[i] } }),
                        el('span', { style: 'white-space: nowrap; font-size: 12px;' }, `${c.icon || ''} ${c.category} - ${pct}%`)
                    );
                })
            ),
        ),
    );
    section.innerHTML = '';
    section.appendChild(card);

    const ctx = document.getElementById('pie-chart');
    if (ctx && data.length > 0) {
        new Chart(ctx, {
            type: 'doughnut',
            data: { labels, datasets: [{ data, backgroundColor: colors, borderColor: '#fff', borderWidth: 2 }] },
            options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { display: false } }, cutout: '0%' },
        });
    }
}

function renderTrendChart() {
    const section = document.getElementById('trend-chart-section');
    if (!section) return;
    const summary = store.get('summary');
    const trend = summary?.daily_trend || [];

    if (trend.length === 0) {
        section.innerHTML = '';
        section.appendChild(el('div', { class: 'trend-card slide-up' },
            el('div', { class: 'trend-card-title' }, 'Monthly Expense Trend'),
            EmptyState('📈', 'No trend data', 'Add expenses over time to see trends'),
        ));
        return;
    }

    // Reverse so oldest entries are on right, most recent on left (away from the FAB)
    const reversedTrend = [...trend].reverse();
    const labels = reversedTrend.map(d => {
        const dt = new Date(d.expense_date);
        return dt.toLocaleDateString('en-US', { weekday: 'short' });
    });
    const data = reversedTrend.map(d => d.daily_total);

    const card = el('div', { class: 'trend-card slide-up' },
        el('div', { class: 'trend-card-title' }, 'Monthly Expense Trend'),
        el('div', { class: 'trend-chart-wrap' }, el('canvas', { id: 'bar-chart' })),
    );
    section.innerHTML = '';
    section.appendChild(card);

    const ctx = document.getElementById('bar-chart');
    if (ctx) {
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    data,
                    backgroundColor: (ctx2) => {
                        const chart = ctx2.chart;
                        const { ctx: c, chartArea } = chart;
                        if (!chartArea) return '#817af3';
                        const g = c.createLinearGradient(0, chartArea.bottom, 0, chartArea.top);
                        g.addColorStop(0, '#79d0f1'); g.addColorStop(0.5, '#74b0fa'); g.addColorStop(1, '#817af3');
                        return g;
                    },
                    borderRadius: 20, barThickness: 10,
                }],
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { display: false }, ticks: { font: { family: 'Inter', size: 11 } } },
                    y: { grid: { color: 'rgba(0,0,0,.04)' }, ticks: { font: { family: 'Inter', size: 11 } } },
                },
            },
        });
    }
}

function renderAIInsight() {
    const section = document.getElementById('ai-insight-section');
    if (!section) return;

    const recommendations = store.get('recommendations');
    const isLoading = store.isLoading('recommendations');

    if (isLoading) {
        section.innerHTML = '';
        section.appendChild(el('div', { class: 'ai-summary-card loading-skeleton' }));
        return;
    }

    let score = 0;
    if (recommendations && !recommendations.error) {
        score = recommendations.healthScore || 0;
    }

    section.innerHTML = '';
    section.appendChild(el('div', {
        class: 'ai-summary-card slide-up',
        onClick: () => router.navigate('ai-analysis')
    },
        el('div', { class: 'ai-summary-left' },
            el('div', { class: 'ai-summary-icon' }, '🤖'),
            el('div', { class: 'ai-summary-info' },
                el('div', { class: 'ai-summary-title' }, 'AI Financial Analysis'),
                el('div', { class: 'ai-summary-score' }, `Health Score: ${score}/100`)
            )
        ),
        el('div', { class: 'ai-summary-link' }, 'View Analysis →')
    ));
}

function renderAIAnalysisPage() {
    const recommendations = store.get('recommendations');

    // If we land here directly (e.g. refresh) and haven't loaded recs yet, load them!
    if (!recommendations && !window._loadingRecs) {
        window._loadingRecs = true;
        store.loadRecommendations().finally(() => window._loadingRecs = false);
    }

    const recs = (recommendations && recommendations.recommendations) ? recommendations.recommendations : [];
    const score = (recommendations && recommendations.healthScore) ? recommendations.healthScore : 0;

    const screen = el('div', { class: 'screen ai-analysis-screen', id: 'ai-analysis-screen' },
        SubHeader('AI Analysis', 'dashboard'),
        el('div', { class: 'px-page' },
            el('div', { class: 'ai-analysis-hero slide-up' },
                el('div', { class: 'ai-analysis-score-wrap' },
                    el('svg', { class: 'score-circle', viewBox: '0 0 100 100' },
                        el('circle', { class: 'score-circle-bg', cx: '50', cy: '50', r: '45' }),
                        el('circle', {
                            id: 'ai-score-progress',
                            class: 'score-circle-progress',
                            cx: '50', cy: '50', r: '45',
                            style: { strokeDashoffset: `${283 - (283 * score / 100)}` }
                        })
                    ),
                    el('div', { class: 'score-value', id: 'ai-score-value' }, score)
                ),
                el('div', { class: 'ai-analysis-hero-text' },
                    el('div', { class: 'hero-title' }, 'Financial Health'),
                    el('div', { class: 'hero-desc', id: 'ai-hero-desc' }, getHealthStatusText(score))
                )
            ),

            el('div', { class: 'rec-list-header', style: 'display: flex; justify-content: space-between; align-items: center;' },
                el('span', {}, 'Key Recommendations'),
                el('button', {
                    class: 'refresh-btn',
                    onClick: async (e) => {
                        const btn = e.currentTarget;
                        const originalHtml = btn.innerHTML;
                        btn.disabled = true;
                        btn.innerHTML = 'Refining...';

                        try {
                            await store.loadRecommendations(true);
                            const updated = store.get('recommendations');
                            const newRecs = updated.recommendations || [];
                            const newScore = updated.healthScore || 0;

                            // Update Score surgically
                            const progress = document.getElementById('ai-score-progress');
                            const scoreVal = document.getElementById('ai-score-value');
                            const heroDesc = document.getElementById('ai-hero-desc');

                            if (progress) progress.style.strokeDashoffset = `${283 - (283 * newScore / 100)}`;
                            if (scoreVal) scoreVal.textContent = newScore;
                            if (heroDesc) heroDesc.textContent = getHealthStatusText(newScore);

                            // Update List surgically
                            const list = document.getElementById('ai-recommendations-list');
                            if (list) {
                                list.innerHTML = '';
                                const cards = renderRecommendationCards(newRecs);
                                cards.forEach(c => list.appendChild(c));
                            }

                            // Also sync dashboard card
                            renderAIInsight();

                            toast.success('Analysis updated!');
                        } catch (err) {
                            console.error('Refresh failed:', err);
                            toast.error('AI Service is busy, try again in a moment');
                        } finally {
                            btn.disabled = false;
                            btn.innerHTML = originalHtml;
                        }
                    }
                },
                    el('span', { style: 'font-size: 14px;' }, '🔄'),
                    el('span', {}, 'Refresh')
                )
            ),
            el('div', { class: 'rec-full-list stagger-children', id: 'ai-recommendations-list' },
                ...(recs.length > 0 ? renderRecommendationCards(recs) : [EmptyState('🤖', 'No recommendations yet', 'Keep tracking your expenses to get personalized insights.')])
            )
        )
    );

    return screen;
}

function renderRecommendationCards(recs) {
    return recs.map(rec => {
        const hasValidAction = isValidRecommendationAction(rec.action);
        return el('div', { class: 'rec-full-card slide-up' },
            el('div', { class: `rec-full-type rec-type-${rec.type}` }, rec.type),
            el('div', { class: 'rec-full-title' }, rec.title),
            el('div', { class: 'rec-full-body' }, rec.body),
            (rec.action && hasValidAction) ? el('button', {
                class: 'rec-full-action',
                onClick: () => handleRecommendationAction(rec.action)
            }, formatActionText(rec.action)) : null
        );
    });
}

function getHealthStatusText(score) {
    if (score >= 80) return 'Excellent! You are managing your finances like a pro.';
    if (score >= 60) return 'Good job! There are a few areas to optimize.';
    if (score >= 40) return 'Noticeable spending. Consider reviewing your budgets.';
    return 'Action required. Your financial health needs attention.';
}

function handleRecommendationAction(action) {
    if (!action) return;
    const act = action.toLowerCase();
    if (act.includes('budget')) router.navigate('budget');
    else if (act.includes('add')) router.navigate('add-expense');
    else if (act.includes('transaction') || act.includes('expense')) router.navigate('transactions');
}

function isValidRecommendationAction(action) {
    if (!action) return false;
    const act = action.toLowerCase();
    return act.includes('budget') ||
        act.includes('add') ||
        act.includes('transaction') ||
        act.includes('expense');
}

function formatActionText(text) {
    if (!text) return '';
    // If it has spaces already, just return it
    if (text.includes(' ')) return text;

    // Split PascalCase or camelCase by adding spaces before uppercase letters
    // "ReviewShoppingBudget" -> "Review Shopping Budget"
    let result = text.replace(/([A-Z])/g, ' $1').trim();

    // If it's still one big word (lowercase), try to split common financial terms
    if (!result.includes(' ')) {
        const terms = ['budget', 'expense', 'transaction', 'profile', 'add', 'view', 'review', 'shopping', 'saving'];
        terms.forEach(term => {
            const regex = new RegExp(`(${term})`, 'gi');
            result = result.replace(regex, ' $1');
        });
        result = result.trim();
    }

    return result;
}

function renderRecentTransactions() {
    const section = document.getElementById('recent-txn-section');
    if (!section) return;
    const allExpenses = store.get('expenses');
    const expenses = allExpenses.slice(0, 5);
    const hasMore = allExpenses.length > 5;
    section.innerHTML = '';
    section.appendChild(el('div', { class: 'section-header' },
        el('span', { class: 'section-title' }, 'Recent Transactions'),
        hasMore ? el('button', {
            class: 'section-link', onClick: () => router.navigate('transactions')
        }, 'View All') : null,
    ));
    if (expenses.length === 0) {
        section.appendChild(EmptyState('📊', 'No transactions yet', 'Tap the menu to add your first expense!'));
    } else {
        section.appendChild(el('div', { class: 'transaction-list stagger-children' }, ...expenses.map(TransactionItem)));
    }
}

/* ---- Add Expense (Expense/Invoice Tabs) ---- */
let _addTab = 'expense';
let _pendingExpenses = [];
let _draftExpense = null;
let _invoiceFile = null;
let _invoicePreview = null;
let _gmailDrafts = [];
let _gmailScannedIds = [];

/* ---- OCR State ---- */
let _ocrItems = [];        // [{description, amount, tax, category_id}]
let _ocrMerchant = '';
let _ocrDate = '';
let _ocrTotalTax = 0;
let _ocrTips = 0;
let _ocrProcessing = false;

/* ---- Split State ---- */
let _splitItems = [];      // items to split
let _splitPeople = ['Me']; // people involved, always starts with 'Me'
let _splitAssignments = {}; // { itemIdx: [personNames...] }
let _splitOpenDropdownIdx = null; // Tracks which dropdown is currently open

function handleInvoiceSelection(file) {
    if (!file || !file.type.startsWith('image/')) {
        toast.error('Please select an image file');
        return;
    }
    _invoiceFile = file;
    const reader = new FileReader();
    reader.onload = (e) => {
        _invoicePreview = e.target.result;
        router.navigate('add-expense');
    };
    reader.readAsDataURL(file);
}

function renderAddExpense() {
    const categories = store.get('categories');

    // Tab Headers
    const tabs = el('div', { class: 'add-tabs-wrap' },
        el('div', { class: 'add-tabs' },
            el('button', {
                class: 'add-tab-btn' + (_addTab === 'expense' ? ' active' : ''),
                onClick: () => {
                    if (_addTab !== 'expense') {
                        _pendingExpenses = [];
                        _draftExpense = null;
                        _invoiceFile = null;
                        _invoicePreview = null;
                        _addTab = 'expense';
                        router.navigate('add-expense');
                    }
                }
            }, 'Expense'),
            el('button', {
                class: 'add-tab-btn' + (_addTab === 'invoice' ? ' active' : ''),
                onClick: () => {
                    if (_addTab !== 'invoice') {
                        _pendingExpenses = [];
                        _draftExpense = null;
                        _invoiceFile = null;
                        _invoicePreview = null;
                        _addTab = 'invoice';
                        router.navigate('add-expense');
                    }
                }
            }, 'Invoice'),
            el('button', {
                class: 'add-tab-btn' + (_addTab === 'gmail' ? ' active' : ''),
                onClick: () => {
                    if (_addTab !== 'gmail') {
                        _pendingExpenses = [];
                        _draftExpense = null;
                        _invoiceFile = null;
                        _invoicePreview = null;
                        _addTab = 'gmail';
                        router.navigate('add-expense');
                    }
                }
            }, 'Gmail')
        )
    );

    let formContent;
    const _d = new Date();
    const todayStr = `${_d.getFullYear()}-${String(_d.getMonth() + 1).padStart(2, '0')}-${String(_d.getDate()).padStart(2, '0')}`;

    if (_addTab === 'expense') {
        const pendingList = el('div', { class: 'pending-expenses-container', style: 'margin-bottom: 20px;' });
        if (_pendingExpenses.length > 0) {
            // Group by date
            const groups = {};
            _pendingExpenses.forEach((exp, idx) => {
                const key = exp.expense_date;
                if (!groups[key]) groups[key] = [];
                groups[key].push({ ...exp, originalIdx: idx });
            });

            const lastAddedDate = _pendingExpenses.length > 0 ? _pendingExpenses[_pendingExpenses.length - 1].expense_date : null;

            // Iterate sorted dates
            Object.keys(groups).sort((a, b) => b.localeCompare(a)).forEach((dateKey, groupIdx) => {
                const dt = new Date(dateKey + 'T00:00:00');
                // Target full format: "Mon, Mar 1, 2026"
                const fullDateLabel = dt.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });

                const groupOpen = dateKey === lastAddedDate;

                const groupEl = el('div', { class: 'txn-date-group minimal' + (groupOpen ? ' open' : ''), style: 'margin-bottom: 5px;' },
                    el('div', {
                        class: 'txn-date-header',
                        onClick: (e) => e.currentTarget.parentElement.classList.toggle('open')
                    },
                        el('div', { class: 'txn-date-header-left' },
                            el('div', { class: 'txn-date-arrow' }, svg(icons.arrowDown, 14, 14)),
                            el('span', { class: 'txn-date-label', style: 'text-transform: none; font-size: 11px;' }, fullDateLabel),
                        )
                    ),
                    el('div', { class: 'transaction-list-collapsible' },
                        el('div', { class: 'transaction-list', style: 'padding: 0 4px 4px 18px;' },
                            ...groups[dateKey].map(exp => {
                                const cat = categories.find(c => c.category_id === exp.category_id);
                                return el('div', {
                                    style: 'display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid var(--border-light); font-size: 12px; color: var(--text-dark);'
                                },
                                    el('div', { style: 'display: flex; align-items: center; gap: 6px;' },
                                        el('span', { style: 'font-size: 13px;' }, cat ? cat.icon : '📌'),
                                        el('span', { style: 'font-weight: 500;' }, cat ? cat.name : 'Unknown')
                                    ),
                                    el('div', { style: 'display: flex; align-items: center; gap: 8px;' },
                                        el('span', { style: 'font-weight: 700;' }, store.formatCurrency(exp.amount)),
                                        el('div', { style: 'display: flex; gap: 4px;' },
                                            el('button', {
                                                style: 'color: var(--blue-link); border: none; background: #eef2ff; padding: 4px 8px; border-radius: 4px; font-size: 10px; font-weight: 700; cursor: pointer;',
                                                onClick: (e) => {
                                                    e.stopPropagation();
                                                    _draftExpense = _pendingExpenses[exp.originalIdx];
                                                    _pendingExpenses.splice(exp.originalIdx, 1);
                                                    router.navigate('add-expense');
                                                }
                                            }, 'EDIT'),
                                            el('button', {
                                                style: 'color: #fd3c4a; border: none; background: #fff5f5; width: 22px; height: 22px; display: flex; align-items:center; justify-content:center; border-radius: 4px; font-size: 12px; cursor: pointer;',
                                                onClick: (e) => {
                                                    e.stopPropagation();
                                                    _pendingExpenses.splice(exp.originalIdx, 1);
                                                    router.navigate('add-expense');
                                                }
                                            }, '✕')
                                        )
                                    )
                                );
                            })
                        )
                    )
                );
                pendingList.appendChild(groupEl);
            });
        }

        const actionBtns = el('div', { class: 'form-actions', style: 'display: flex; flex-direction: column; gap: 10px; margin-top: 20px;' });

        actionBtns.appendChild(el('button', {
            class: 'submit-btn',
            type: 'submit',
            id: 'submit-expense-btn',
            style: 'background: var(--blue-link); font-size: 14px; padding: 12px;'
        }, 'Add More'));

        actionBtns.appendChild(el('button', {
            class: 'submit-btn',
            type: 'button',
            style: 'background: var(--green-accent); box-shadow: 0 4px 15px rgba(70, 163, 108, 0.3);',
            onClick: handleSaveAllPending
        }, 'Save Expenses'));

        const initialCat = _draftExpense ? categories.find(c => c.category_id === _draftExpense.category_id) : null;

        formContent = el('form', { class: 'expense-form add-slide-in', id: 'add-expense-form', onSubmit: handleAddToList },
            pendingList,
            el('div', { class: 'form-group' },
                el('label', { class: 'form-label' }, 'CATEGORY'),
                CategoryDropdown(categories, null, initialCat)
            ),
            el('div', { class: 'form-group' },
                el('label', { class: 'form-label' }, 'DESCRIPTION'),
                el('input', { class: 'form-input', id: 'expense-description', type: 'text', placeholder: 'What was this expense for?', value: _draftExpense ? (_draftExpense.description || '') : '' }),
            ),
            el('div', { class: 'form-group' },
                el('label', { class: 'form-label' }, 'AMOUNT'),
                el('input', { class: 'form-input', id: 'expense-amount', type: 'number', placeholder: 'Enter Amount', required: 'true', step: '0.01', min: '0.01', value: _draftExpense ? _draftExpense.amount : '' }),
            ),
            el('div', { class: 'form-group' },
                el('label', { class: 'form-label' }, 'DATE'),
                DatePicker({ id: 'expense-date', value: _draftExpense ? _draftExpense.expense_date : todayStr, allowFuture: false })
            ),
            actionBtns
        );
    } else if (_addTab === 'gmail') {
        let gmailContent;

        if (_gmailDrafts && _gmailDrafts.length > 0) {
            gmailContent = el('div', { class: 'gmail-preview-container' },
                el('div', { class: 'preview-header' },
                    el('span', {}, `Found ${_gmailDrafts.length} expenses`),
                    el('button', { class: 'clear-drafts-btn', onClick: () => { _gmailDrafts = []; router.navigate('add-expense'); } }, 'Clear All')
                ),
                el('div', { class: 'gmail-draft-list' },
                    ..._gmailDrafts.map((draft, idx) => el('div', { class: 'gmail-draft-card' },
                        el('div', { class: 'card-header' },
                            el('div', { class: 'sender-info' },
                                el('i', { class: 'source-icon' }, '📧'),
                                el('span', { class: 'sender-addr' }, draft.sender || 'Unknown')
                            ),
                            el('button', {
                                class: 'card-remove',
                                onClick: () => { _gmailDrafts.splice(idx, 1); router.navigate('add-expense'); }
                            }, '✕')
                        ),
                        el('div', { class: 'card-body' },
                            el('div', { class: 'main-inputs' },
                                el('input', {
                                    class: 'draft-desc-input',
                                    value: draft.description || '',
                                    onChange: (e) => draft.description = e.target.value,
                                    placeholder: 'Description'
                                }),
                                el('div', { class: 'amount-pill' },
                                    el('span', { class: 'curr-symbol' }, store.getCurrencySymbol()),
                                    el('input', {
                                        class: 'amount-input',
                                        type: 'number',
                                        value: draft.amount,
                                        step: '0.01',
                                        onChange: (e) => draft.amount = parseFloat(e.target.value) || 0
                                    })
                                )
                            ),
                            el('div', { class: 'meta-row' },
                                el('div', { class: 'date-box' },
                                    el('i', {}, '📅'),
                                    el('span', {}, draft.expense_date)
                                ),
                                el('div', { class: 'cat-box' },
                                    el('select', {
                                        class: 'card-cat-select',
                                        onChange: (e) => draft.category = e.target.value
                                    },
                                        ...categories.map(c => el('option', { value: c.name, selected: c.name === draft.category }, `${c.icon} ${c.name}`))
                                    )
                                ),
                                draft.converted ? el('div', { class: 'conv-badge' }, `⚡ ${draft.original_currency}`) : null
                            ),
                            el('div', { class: 'email-snippet' },
                                el('div', { class: 'snippet-label' }, 'Email Content:'),
                                el('div', { class: 'snippet-text' }, draft.body ? draft.body.substring(0, 150) + '...' : '...')
                            )
                        )
                    ))
                ),
                el('button', {
                    class: 'submit-btn gmail-btn-confirm',
                    id: 'gmail-confirm-btn',
                    onClick: async () => {
                        const btn = document.getElementById('gmail-confirm-btn');
                        const userId = store.get('userId');
                        btn.disabled = true;
                        btn.innerHTML = '<span>Saving...</span>';
                        try {
                            const res = await api.confirmGmailSync(userId, {
                                expenses: _gmailDrafts,
                                scanned_ids: _gmailScannedIds
                            });
                            if (res.status === 'ok') {
                                // 🎉 Confetti Explosion!
                                confetti({
                                    particleCount: 150,
                                    spread: 70,
                                    origin: { y: 0.6 },
                                    colors: ['#b1cca1', '#45B7D1', '#FF6B6B', '#96CEB4']
                                });

                                toast.success(res.message);
                                _gmailDrafts = [];
                                _gmailScannedIds = [];
                                await store.loadExpenses();
                                await store.loadSummary();
                                router.navigate('dashboard');
                            }
                        } catch (e) {
                            toast.error(e.message);
                        } finally {
                            btn.disabled = false;
                        }
                    }
                }, 'Save to Expenses')
            );
        } else {
            gmailContent = el('div', { class: 'gmail-sync-card' },
                el('div', { class: 'gmail-icon-large' }, svg(icons.google, 60, 60)),
                el('div', { class: 'gmail-sync-title' }, 'Sync with Gmail'),
                el('div', { class: 'gmail-sync-desc' }, 'Automatically scan your recent emails for receipts and invoices using AI.'),
                el('button', {
                    class: 'submit-btn gmail-btn-sync',
                    id: 'gmail-sync-btn',
                    onClick: async () => {
                        const btn = document.getElementById('gmail-sync-btn');
                        btn.disabled = true;
                        btn.innerHTML = '<span>Scanning Emails...</span>';
                        try {
                            const userId = store.get('userId');
                            const res = await api.previewGmailSync(userId);
                            if (res.status === 'ok') {
                                _gmailDrafts = res.expenses || [];
                                _gmailScannedIds = res.scanned_ids || [];
                                if (_gmailDrafts.length === 0) {
                                    toast.info('No expenses found in recent emails');
                                }
                                router.navigate('add-expense');
                            }
                        } catch (e) {
                            toast.error(e.message || 'Gmail Sync failed');
                        } finally {
                            btn.disabled = false;
                            btn.innerHTML = '<span>Start Sync</span>';
                        }
                    }
                }, 'Start Sync')
            );
        }

        formContent = el('div', { class: 'gmail-sync-container add-slide-in' }, gmailContent);
    } else {
        // === INVOICE TAB: Upload → Process → Results Table ===
        if (_ocrItems.length > 0) {
            // --- RESULTS TABLE ---
            formContent = renderOCRResults(categories, todayStr);
        } else {
            // --- UPLOAD ZONE ---
            const uploadZone = _invoicePreview
                ? el('div', { class: 'invoice-preview-container' },
                    el('img', { src: _invoicePreview, class: 'invoice-preview-img' }),
                    el('button', {
                        class: 'invoice-remove-btn',
                        type: 'button',
                        onClick: (e) => {
                            e.preventDefault();
                            _invoiceFile = null;
                            _invoicePreview = null;
                            router.navigate('add-expense');
                        }
                    }, svg(icons.close || '✕', 20, 20))
                )
                : el('div', {
                    class: 'invoice-upload-zone',
                    onClick: () => document.getElementById('invoice-file-input').click(),
                    onDragOver: (e) => { e.preventDefault(); e.currentTarget.classList.add('drag-over'); },
                    onDragLeave: (e) => { e.preventDefault(); e.currentTarget.classList.remove('drag-over'); },
                    onDrop: (e) => {
                        e.preventDefault();
                        e.currentTarget.classList.remove('drag-over');
                        const file = e.dataTransfer.files[0];
                        if (file) handleInvoiceSelection(file);
                    }
                },
                    el('div', { class: 'upload-zone-icon' }, svg(icons.invoice, 48, 48)),
                    el('div', { class: 'upload-zone-text' }, 'Choose an invoice or drag it here'),
                    el('div', { class: 'upload-zone-subtext' }, 'JPG, PNG up to 10MB'),
                    el('input', {
                        type: 'file',
                        id: 'invoice-file-input',
                        style: 'display: none;',
                        accept: 'image/*',
                        onChange: (e) => {
                            const file = e.target.files[0];
                            if (file) handleInvoiceSelection(file);
                        }
                    })
                );

            formContent = el('div', { class: 'expense-form add-slide-in', id: 'add-invoice-form' },
                el('div', { class: 'form-group' },
                    el('label', { class: 'form-label' }, 'SCAN RECEIPT'),
                    uploadZone
                ),
                el('button', {
                    class: 'submit-btn' + (_invoiceFile ? ' submit-btn-vibrant' : ''),
                    type: 'button',
                    id: 'ocr-process-btn',
                    disabled: (!_invoiceFile || _ocrProcessing) ? true : null,
                    style: _invoiceFile ? '' : 'opacity: 0.6; cursor: not-allowed; height: 50px;',
                    onClick: async () => {
                        if (!_invoiceFile) return toast.error('Please upload an invoice first');
                        const btn = document.getElementById('ocr-process-btn');
                        btn.disabled = true;
                        btn.textContent = 'Processing...';
                        _ocrProcessing = true;
                        try {
                            const res = await api.uploadInvoice(_invoiceFile);
                            if (res.status === 'ok' && res.items && res.items.length > 0) {
                                _ocrItems = res.items.map(it => ({
                                    description: it.description || '',
                                    amount: it.amount || 0,
                                    tax: 0,
                                    category_id: null,
                                }));
                                // Distribute taxes proportionally
                                const totalTax = (res.cgst || 0) + (res.sgst || 0) + (res.additional_charge || 0);
                                _ocrTotalTax = totalTax;
                                if (totalTax > 0) {
                                    const preTaxTotal = _ocrItems.reduce((s, i) => s + i.amount, 0) || 1;
                                    const taxPercent = (totalTax / preTaxTotal) * 100; // total Tax amt / pre tax total * 100 = tax %

                                    _ocrItems.forEach(it => {
                                        // Item amt * tax% = final tax for the item
                                        const finalTax = it.amount * (taxPercent / 100);
                                        it.tax = Math.round(finalTax * 100) / 100; // round to 2 decimal places
                                    });
                                }
                                _ocrMerchant = res.merchant || '';
                                _ocrDate = '';
                                // Parse date from DD/MM/YYYY to YYYY-MM-DD
                                if (res.date) {
                                    const dp = res.date.split('/');
                                    if (dp.length === 3) {
                                        const yr = dp[2].length === 4 ? dp[2] : '20' + dp[2];
                                        _ocrDate = `${yr}-${dp[1].padStart(2, '0')}-${dp[0].padStart(2, '0')}`;
                                    }
                                }
                                if (!_ocrDate) _ocrDate = todayStr;
                                toast.success(`Found ${_ocrItems.length} items!`);
                            } else {
                                toast.error('No items found in the receipt. Try a clearer image.');
                            }
                        } catch (err) {
                            toast.error('OCR failed: ' + err.message);
                        } finally {
                            _ocrProcessing = false;
                            router.navigate('add-expense');
                        }
                    }
                }, _ocrProcessing ? 'Processing...' : (_invoiceFile ? 'Process Invoice' : 'Select a File')),
            );
        }
    }

    return el('div', { class: 'screen add-expense-bg', id: 'add-expense-screen' },
        SubHeader('Add Expense'),
        el('div', { class: 'px-page add-expense-card' },
            tabs,
            formContent
        ),
    );
}

async function handleAddToList(e) {
    e.preventDefault();
    const catId = parseInt(document.getElementById('expense-category').value);
    const amount = parseFloat(document.getElementById('expense-amount').value);
    const date = document.getElementById('expense-date').value;
    const descEl = document.getElementById('expense-description');
    const description = descEl ? descEl.value.trim() : '';

    if (!catId) {
        toast.error('Please select a category');
        return;
    }

    _pendingExpenses.push({
        user_id: store.get('userId'),
        amount,
        category_id: catId,
        description: description || null,
        expense_date: date
    });

    _draftExpense = null;
    router.navigate('add-expense');
}

async function handleSaveAllPending(e) {
    const btn = e.target;
    const catId = parseInt(document.getElementById('expense-category').value);
    const amountStr = document.getElementById('expense-amount').value;
    const amount = parseFloat(amountStr);
    const date = document.getElementById('expense-date').value;
    const descEl = document.getElementById('expense-description');
    const description = descEl ? descEl.value.trim() : '';

    // Check if current form can be added as a last item
    const currentList = [..._pendingExpenses];
    if (amount > 0 && catId) {
        currentList.push({
            user_id: store.get('userId'),
            amount,
            category_id: catId,
            description: description || null,
            expense_date: date
        });
    }

    if (currentList.length === 0) {
        toast.error('No expenses to save');
        return;
    }

    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = 'Saving...';

    try {
        const promises = currentList.map(exp => api.createExpense(exp));
        await Promise.all(promises);

        const count = currentList.length;
        confetti({ particleCount: 150, spread: 70, origin: { y: 0.6 }, colors: ['#b1cca1', '#45B7D1', '#FF6B6B', '#96CEB4'] });
        toast.success(count === 1 ? '1 expense saved!' : `${count} expenses saved!`);
        _pendingExpenses = [];
        _draftExpense = null;

        await Promise.all([store.loadExpenses(), store.loadSummary()]);
        router.navigate('dashboard');
    } catch (err) {
        toast.error('Failed to save: ' + err.message);
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

/* ---- OCR Results Table ---- */
function renderOCRResults(categories, todayStr) {
    const dateVal = _ocrDate || todayStr;

    const tableRows = _ocrItems.map((item, idx) => {
        return el('tr', { class: 'ocr-table-row' },
            el('td', { class: 'ocr-cell' },
                el('input', {
                    class: 'ocr-cell-input', type: 'text', value: item.description,
                    onInput: (e) => { _ocrItems[idx].description = e.target.value; }
                })
            ),
            el('td', { class: 'ocr-cell ocr-cell-num' },
                el('input', {
                    class: 'ocr-cell-input num', type: 'number', step: '0.01', value: item.tax,
                    readonly: true,
                    style: 'opacity: 0.6; cursor: not-allowed; background: transparent;'
                })
            ),
            el('td', { class: 'ocr-cell ocr-cell-num' },
                el('input', {
                    class: 'ocr-cell-input num', type: 'number', step: '0.01', value: item.amount,
                    onChange: (e) => {
                        _ocrItems[idx].amount = parseFloat(e.target.value) || 0;
                        updateOCRSurgical();
                    }
                })
            ),
            el('td', { class: 'ocr-cell' },
                el('select', {
                    class: 'ocr-cell-select',
                    onChange: (e) => { _ocrItems[idx].category_id = parseInt(e.target.value) || null; }
                },
                    el('option', { value: '' }, 'Select'),
                    ...categories.map(c => el('option', {
                        value: c.category_id,
                        selected: item.category_id === c.category_id ? 'selected' : null
                    }, `${c.icon} ${c.name}`))
                )
            ),
            el('td', { class: 'ocr-cell ocr-cell-action' },
                el('button', {
                    class: 'ocr-remove-btn', type: 'button',
                    onClick: () => { _ocrItems.splice(idx, 1); router.navigate('add-expense'); }
                }, '✕')
            )
        );
    });

    const preTaxTotal = _ocrItems.reduce((s, i) => s + i.amount, 0);
    const grandTotal = _ocrItems.reduce((s, i) => s + i.amount + i.tax, 0) + _ocrTips;

    return el('div', { class: 'ocr-results-container add-slide-in' },
        _ocrMerchant ? el('div', { class: 'ocr-merchant-label' }, `📋 ${_ocrMerchant}`) : null,
        el('div', { class: 'ocr-table-wrap' },
            el('table', { class: 'ocr-table' },
                el('thead', {},
                    el('tr', {},
                        el('th', {}, 'Description'),
                        el('th', { class: 'ocr-th-num' }, 'Tax'),
                        el('th', { class: 'ocr-th-num' }, 'Subtotal'),
                        el('th', { class: 'ocr-th-category' },
                            el('select', {
                                class: 'ocr-master-category-select',
                                onChange: (e) => {
                                    const catId = parseInt(e.target.value) || null;
                                    if (catId) {
                                        _ocrItems.forEach((it, i) => {
                                            it.category_id = catId;
                                            const rowSelect = document.querySelectorAll('.ocr-cell-select')[i];
                                            if (rowSelect) rowSelect.value = catId;
                                        });
                                        e.target.value = '';
                                    }
                                }
                            },
                                el('option', { value: '' }, 'Assign All'),
                                ...categories.map(c => el('option', { value: c.category_id }, `${c.icon} ${c.name}`))
                            )
                        ),
                        el('th', { class: 'ocr-th-action' }, ''),
                    )
                ),
                el('tbody', {}, ...tableRows)
            )
        ),

        // --- NEW OCR Totals Card --- 
        el('div', { class: 'ocr-totals-card' },
            el('div', { class: 'ocr-totals-row' },
                el('span', { class: 'ocr-totals-label' }, 'Pre-Tax Total'),
                el('span', { class: 'ocr-totals-val', id: 'ocr-pretax-val' }, store.formatCurrency(preTaxTotal))
            ),
            el('div', { class: 'ocr-totals-row' },
                el('span', { class: 'ocr-totals-label' }, 'Total Tax'),
                el('div', { class: 'ocr-totals-input-wrap' },
                    el('span', { class: 'currency-prefix' }, store.getCurrencySymbol()),
                    el('input', {
                        class: 'ocr-totals-input num', type: 'number', step: '0.01',
                        value: Math.round(_ocrTotalTax * 100) / 100,
                        onChange: (e) => {
                            _ocrTotalTax = parseFloat(e.target.value) || 0;
                            updateOCRSurgical();
                        }
                    })
                )
            ),
            el('div', { class: 'ocr-totals-row' },
                el('span', { class: 'ocr-totals-label' }, 'Tips / Other'),
                el('div', { class: 'ocr-totals-input-wrap' },
                    el('span', { class: 'currency-prefix' }, store.getCurrencySymbol()),
                    el('input', {
                        class: 'ocr-totals-input num', type: 'number', step: '0.01',
                        value: Math.round(_ocrTips * 100) / 100,
                        onChange: (e) => {
                            _ocrTips = parseFloat(e.target.value) || 0;
                            updateOCRSurgical();
                        }
                    })
                )
            ),
            el('div', { class: 'ocr-grand-total-wrap' },
                el('span', { class: 'ocr-grand-total-label' }, 'Grand Total'),
                el('span', { class: 'ocr-grand-total-val', id: 'ocr-grandtotal-val' }, store.formatCurrency(grandTotal))
            )
        ),

        el('div', { class: 'ocr-date-row' },
            el('label', { class: 'form-label' }, 'DATE'),
            DatePicker({ id: 'ocr-date', value: dateVal, allowFuture: false, onChange: (v) => { _ocrDate = v; } }),
        ),
        el('div', { class: 'ocr-action-btns' },
            el('button', {
                class: 'submit-btn', type: 'button', id: 'ocr-save-btn',
                style: 'background: var(--green-accent);',
                onClick: handleOCRSave,
            }, 'Save Expense'),
            el('button', {
                class: 'submit-btn', type: 'button', id: 'ocr-split-btn',
                style: 'background: var(--blue-link);',
                onClick: () => {
                    // Regular items get only amount + tax
                    _splitItems = _ocrItems.map(i => ({
                        ...i,
                        subtotal: Math.round((i.amount + i.tax) * 100) / 100
                    }));

                    // Tips as a separate item
                    if (_ocrTips > 0) {
                        _splitItems.push({
                            description: 'Tips / Other',
                            amount: _ocrTips,
                            tax: 0,
                            subtotal: _ocrTips,
                            category_id: null,
                            isTip: true
                        });
                    }

                    _splitPeople = ['Me'];
                    _splitAssignments = {};
                    _splitItems.forEach((item, idx) => {
                        if (item.isTip) {
                            _splitAssignments[idx] = [..._splitPeople];
                        } else {
                            _splitAssignments[idx] = ['Me'];
                        }
                    });
                    router.navigate('split-expense');
                },
            }, 'Split Expense'),
        ),
        el('button', {
            class: 'ocr-clear-btn', type: 'button',
            onClick: () => {
                _ocrItems = []; _ocrMerchant = ''; _ocrDate = '';
                _ocrTotalTax = 0; _ocrTips = 0;
                _invoiceFile = null; _invoicePreview = null;
                router.navigate('add-expense');
            }
        }, 'Clear & Start Over'),
    );
}

function updateOCRSurgical() {
    // Recalculate weights
    const pTotal = _ocrItems.reduce((s, i) => s + i.amount, 0) || 1;
    const tp = (_ocrTotalTax / pTotal) * 100;

    _ocrItems.forEach((it, idx) => {
        const finalTax = it.amount * (tp / 100);
        it.tax = Math.round(finalTax * 100) / 100;

        // Update Tax column in UI
        const taxInput = document.querySelectorAll('.ocr-cell-input.num')[idx * 2]; // 1st is tax, 2nd is subtotal
        if (taxInput) taxInput.value = it.tax;
    });

    const preTaxTotal = _ocrItems.reduce((s, i) => s + i.amount, 0);
    const grandTotal = _ocrItems.reduce((s, i) => s + i.amount + i.tax, 0) + _ocrTips;

    // Update Totals Labels
    const preTaxEl = document.getElementById('ocr-pretax-val');
    const grandEl = document.getElementById('ocr-grandtotal-val');
    if (preTaxEl) preTaxEl.textContent = store.formatCurrency(preTaxTotal);
    if (grandEl) grandEl.textContent = store.formatCurrency(grandTotal);
}

async function handleOCRSave() {
    const btn = document.getElementById('ocr-save-btn');
    if (btn) { btn.disabled = true; btn.textContent = 'Saving...'; }
    const userId = store.get('userId');
    const date = _ocrDate || new Date().toISOString().slice(0, 10);
    try {
        const items = _ocrItems.map(it => ({
            description: it.description,
            amount: it.amount + it.tax,
            category_id: it.category_id || null,
            expense_date: date,
        }));
        const res = await api.saveOCRItems({ user_id: userId, items });
        confetti({ particleCount: 150, spread: 70, origin: { y: 0.6 }, colors: ['#b1cca1', '#45B7D1', '#FF6B6B', '#96CEB4'] });
        toast.success(res.message || 'Expenses saved!');
        _ocrItems = []; _ocrMerchant = ''; _ocrDate = '';
        _invoiceFile = null; _invoicePreview = null;
        await Promise.all([store.loadExpenses(), store.loadSummary()]);
        router.navigate('dashboard');
    } catch (err) {
        toast.error('Save failed: ' + err.message);
        if (btn) { btn.disabled = false; btn.textContent = 'Save Expense'; }
    }
}

/* ---- Split Expense Screen ---- */
function renderSplitExpense() {
    const categories = store.get('categories');

    // Person management
    const peopleSection = el('div', { class: 'split-people-section' },
        el('div', { class: 'split-section-title' }, 'People'),
        el('div', { class: 'split-people-list', id: 'split-people-list' },
            ..._splitPeople.map((name, idx) =>
                el('div', { class: 'split-person-chip' + (name === 'Me' ? ' me' : '') },
                    el('span', {}, name),
                    name !== 'Me' ? el('button', {
                        class: 'split-person-remove',
                        onClick: () => {
                            _splitPeople.splice(idx, 1);
                            // Sync assignments
                            Object.keys(_splitAssignments).forEach(k => {
                                if (_splitItems[k]?.isTip) {
                                    _splitAssignments[k] = [..._splitPeople];
                                } else {
                                    _splitAssignments[k] = _splitAssignments[k].filter(p => p !== name);
                                }
                            });
                            router.navigate('split-expense');
                        }
                    }, '✕') : null
                )
            )
        ),
        el('div', { class: 'split-add-person', id: 'split-add-person-row' },
            el('input', {
                class: 'form-input', id: 'split-new-person', type: 'text', placeholder: 'Add person name...',
                onKeydown: (e) => { if (e.key === 'Enter') { e.preventDefault(); addSplitPerson(); } }
            }),
            el('button', { class: 'split-add-btn', type: 'button', onClick: addSplitPerson }, '+')
        )
    );

    // Item assignment table
    const assignRows = _splitItems.map((item, idx) => {
        const assigned = _splitAssignments[idx] || [];
        const perPerson = assigned.length > 0 ? (item.subtotal / assigned.length) : 0;

        return el('tr', { class: 'split-table-row' },
            el('td', { class: 'split-cell-desc' },
                item.isTip ? el('b', {}, item.description) : (item.description || `Item ${idx + 1}`)
            ),
            el('td', { class: 'split-cell-amt' }, store.formatCurrency(item.subtotal)),
            el('td', { class: 'split-cell-assign' },
                item.isTip ? el('div', { class: 'split-multi-select disabled-tip-select' },
                    el('summary', { class: 'split-multi-summary tip-dropdown-summary', id: 'split-tip-autolabel' }, `Auto-divided (${_splitPeople.length}ppl)`)
                ) :
                    el('details', {
                        class: 'split-multi-select',
                        open: _splitOpenDropdownIdx === idx ? 'open' : null,
                        onToggle: (e) => {
                            if (e.target.open) {
                                _splitOpenDropdownIdx = idx;
                            } else {
                                if (_splitOpenDropdownIdx === idx) _splitOpenDropdownIdx = null;
                                updateSplitSurgicalUI();
                            }
                        }
                    },
                        el('summary', { class: 'split-multi-summary', id: `split-summary-${idx}` },
                            assigned.length === 0 ? '0 persons' : (
                                assigned.length === _splitPeople.length ? 'All selected' :
                                    `${assigned.length} person${assigned.length !== 1 ? 's' : ''}`
                            )
                        ),
                        el('div', { class: 'split-multi-menu' },
                            el('label', { class: 'split-multi-option select-all-option' },
                                el('input', {
                                    type: 'checkbox',
                                    checked: assigned.length === _splitPeople.length ? 'checked' : null,
                                    onChange: (e) => {
                                        const isChecked = e.target.checked;
                                        if (isChecked) {
                                            _splitAssignments[idx] = [..._splitPeople];
                                        } else {
                                            _splitAssignments[idx] = [];
                                        }
                                        // Manually sync other checkboxes in the same menu without a full reload
                                        const container = e.target.closest('.split-multi-menu');
                                        if (container) {
                                            container.querySelectorAll('input[type="checkbox"]').forEach(cb => {
                                                if (cb !== e.target) cb.checked = isChecked;
                                            });
                                        }
                                    }
                                }),
                                el('span', {}, 'Select All')
                            ),
                            ..._splitPeople.map(person => {
                                const isAssigned = assigned.includes(person);
                                return el('label', { class: 'split-multi-option' },
                                    el('input', {
                                        type: 'checkbox',
                                        checked: isAssigned ? 'checked' : null,
                                        onChange: (e) => {
                                            if (e.target.checked) {
                                                if (!_splitAssignments[idx].includes(person)) _splitAssignments[idx].push(person);
                                            } else {
                                                _splitAssignments[idx] = _splitAssignments[idx].filter(p => p !== person);
                                            }
                                        }
                                    }),
                                    el('span', {}, person)
                                );
                            })
                        )
                    ),
                el('div', { class: 'split-per-person', id: `split-per-person-${idx}` },
                    `÷${assigned.length} = ${store.formatCurrency(perPerson)} each`
                )
            )
        );
    });

    // Calculate each person's total
    const personTotals = {};
    _splitPeople.forEach(p => { personTotals[p] = 0; });
    _splitItems.forEach((item, idx) => {
        const assigned = _splitAssignments[idx] || [];
        const share = assigned.length > 0 ? item.subtotal / assigned.length : 0;
        assigned.forEach(p => {
            if (personTotals[p] !== undefined) personTotals[p] += share;
        });
    });

    const totalsSection = el('div', { class: 'split-totals-section' },
        el('div', { class: 'split-section-title' }, 'Split Summary'),
        el('div', { class: 'split-totals-grid', id: 'split-totals-grid' },
            ..._splitPeople.map(person =>
                el('div', { class: 'split-total-card' + (person === 'Me' ? ' me' : '') },
                    el('div', { class: 'split-total-name' }, person),
                    el('div', { class: 'split-total-amount' }, store.formatCurrency(personTotals[person] || 0)),
                )
            )
        )
    );

    return el('div', { class: 'screen add-expense-bg', id: 'split-expense-screen' },
        SubHeader('Split Expense', 'add-expense'),
        el('div', { class: 'px-page add-expense-card' },
            peopleSection,
            el('div', { class: 'split-table-wrap' },
                el('table', { class: 'ocr-table split-table' },
                    el('thead', {},
                        el('tr', {},
                            el('th', {}, 'Item'),
                            el('th', { class: 'ocr-th-num' }, 'Amount'),
                            el('th', {}, 'Assign To'),
                        )
                    ),
                    el('tbody', {}, ...assignRows),
                )
            ),
            totalsSection,
            el('div', { class: 'ocr-action-btns', style: 'margin-top: 20px;' },
                el('button', {
                    class: 'submit-btn', type: 'button', id: 'split-save-btn',
                    style: 'background: var(--green-accent);',
                    onClick: handleSplitSave,
                }, 'Save Expense (My Share)'),
            ),
        ),
    );
}

function updateSplitSurgicalUI() {
    _splitItems.forEach((item, idx) => {
        const assigned = _splitAssignments[idx] || [];
        const perPerson = assigned.length > 0 ? (item.subtotal / assigned.length) : 0;

        // Update Assignment Summary Label
        const summary = document.getElementById(`split-summary-${idx}`);
        if (summary) {
            summary.textContent = assigned.length === 0 ? '0 persons' :
                (assigned.length === _splitPeople.length ? 'All selected' :
                    `${assigned.length} person${assigned.length !== 1 ? 's' : ''}`);
        }

        // Update Per-Person Row Label
        const perPersonEl = document.getElementById(`split-per-person-${idx}`);
        if (perPersonEl) {
            perPersonEl.textContent = `÷${assigned.length} = ${store.formatCurrency(perPerson)} each`;
        }
    });

    // Update Tip labels if they exist
    const tipLabel = document.getElementById('split-tip-autolabel');
    if (tipLabel) tipLabel.textContent = `Auto-divided (${_splitPeople.length}ppl)`;

    // Calculate each person's total
    const personTotals = {};
    _splitPeople.forEach(p => { personTotals[p] = 0; });
    _splitItems.forEach((item, idx) => {
        const assigned = _splitAssignments[idx] || [];
        const share = assigned.length > 0 ? item.subtotal / assigned.length : 0;
        assigned.forEach(p => {
            if (personTotals[p] !== undefined) personTotals[p] += share;
        });
    });

    // Update Totals Cards
    _splitPeople.forEach((person, idx) => {
        const cards = document.querySelectorAll('.split-totals-grid .split-total-amount');
        if (cards[idx]) {
            cards[idx].textContent = store.formatCurrency(personTotals[person] || 0);
        }
    });
}

function addSplitPerson() {
    const input = document.getElementById('split-new-person');
    const name = input ? input.value.trim() : '';
    if (!name) return;
    if (_splitPeople.includes(name)) { toast.error('Person already added'); return; }
    _splitPeople.push(name);
    // Sync Tip assignments to include EVERYONE
    _splitItems.forEach((item, idx) => {
        if (item.isTip) {
            _splitAssignments[idx] = [..._splitPeople];
        }
    });
    router.navigate('split-expense');
}

async function handleSplitSave() {
    const btn = document.getElementById('split-save-btn');
    if (btn) { btn.disabled = true; btn.textContent = 'Saving...'; }

    const userId = store.get('userId');
    const date = _ocrDate || new Date().toISOString().slice(0, 10);

    // Calculate 'Me' share for each item
    const myItems = [];
    _splitItems.forEach((item, idx) => {
        const assigned = _splitAssignments[idx] || [];
        if (assigned.includes('Me')) {
            const share = item.subtotal / assigned.length;
            myItems.push({
                description: item.description,
                amount: Math.round(share * 100) / 100,
                category_id: item.category_id || null,
                expense_date: date,
            });
        }
    });

    if (myItems.length === 0) {
        toast.info('No items assigned to you.');
        if (btn) { btn.disabled = false; btn.textContent = 'Save Expense (My Share)'; }
        return;
    }

    try {
        const res = await api.saveOCRItems({ user_id: userId, items: myItems });
        confetti({ particleCount: 150, spread: 70, origin: { y: 0.6 }, colors: ['#b1cca1', '#45B7D1', '#FF6B6B', '#96CEB4'] });
        toast.success(`Saved your share: ${myItems.length} item(s)!`);
        _ocrItems = []; _ocrMerchant = ''; _ocrDate = '';
        _invoiceFile = null; _invoicePreview = null;
        _splitItems = []; _splitPeople = ['Me']; _splitAssignments = {};
        await Promise.all([store.loadExpenses(), store.loadSummary()]);
        router.navigate('dashboard');
    } catch (err) {
        toast.error('Save failed: ' + err.message);
        if (btn) { btn.disabled = false; btn.textContent = 'Save Expense (My Share)'; }
    }
}



/* ---- Chatbot (calls Python /chatbot endpoint with Cerebras) ---- */
let _chatHistory = [];

function renderChatbot() {
    const msgsContainer = el('div', { class: 'chat-messages', id: 'chat-messages' });

    // Initial welcome if history is empty
    if (_chatHistory.length === 0) {
        msgsContainer.appendChild(el('div', { class: 'chat-bubble bot' }, 'Hi! I\'m your AI expense assistant powered by Cerebras. Ask me anything about your spending, budgets, or financial tips! 🤖'));
    } else {
        _chatHistory.forEach(m => {
            const bubble = el('div', { class: 'chat-bubble ' + (m.role === 'user' ? 'user' : 'bot') });
            bubble.innerHTML = window.marked ? marked.parse(m.content) : m.content;
            msgsContainer.appendChild(bubble);
        });
    }

    const screen = el('div', { class: 'screen', id: 'chatbot-screen' },
        SubHeader('Chatbot'),
        el('div', { class: 'chat-container' },
            msgsContainer,
            el('div', { class: 'chat-input-bar' },
                el('input', { class: 'chat-input', id: 'chat-input', type: 'text', placeholder: 'Ask me anything...', onKeydown: (e) => { if (e.key === 'Enter') handleChatSend(); } }),
                el('button', { class: 'chat-send-btn', id: 'chat-send-btn', onClick: handleChatSend }, svg(icons.send, 22, 22)),
            ),
        ),
    );

    setTimeout(() => { msgsContainer.scrollTop = msgsContainer.scrollHeight; }, 100);
    return screen;
}

async function handleChatSend() {
    const input = document.getElementById('chat-input');
    const msgsContainer = document.getElementById('chat-messages');
    const text = input.value.trim();
    if (!text) return;
    input.value = '';

    // Add user message to UI and history
    msgsContainer.appendChild(el('div', { class: 'chat-bubble user' }, text));
    msgsContainer.scrollTop = msgsContainer.scrollHeight;

    const currentHistory = [..._chatHistory];
    _chatHistory.push({ role: 'user', content: text });

    // Typing indicator
    const typing = el('div', { class: 'chat-bubble bot typing' }, 'Thinking...');
    msgsContainer.appendChild(typing);
    msgsContainer.scrollTop = msgsContainer.scrollHeight;

    try {
        const userId = store.get('userId');
        const data = await api.post('/chatbot', { message: text, user_id: userId, history: currentHistory });
        typing.remove();

        const reply = data.reply;
        _chatHistory.push({ role: 'assistant', content: reply });

        const bubble = el('div', { class: 'chat-bubble bot' });
        bubble.innerHTML = window.marked ? marked.parse(reply) : reply;
        msgsContainer.appendChild(bubble);
    } catch (err) {
        typing.remove();
        // Fallback to local logic if Cerebras is not available
        const expenses = store.get('expenses');
        const total = expenses.reduce((s, e) => s + (e.amount || 0), 0);
        const count = expenses.length;
        let response = '';
        const lw = text.toLowerCase();

        if (lw.includes('total') || lw.includes('spent') || lw.includes('spending')) {
            response = `You've spent ${store.formatCurrency(total)} across ${count} transactions.`;
        } else if (lw.includes('category') || lw.includes('breakdown')) {
            const summary = store.get('summary');
            const byCat = summary?.by_category || [];
            if (byCat.length > 0) {
                response = 'Category breakdown:\n' + byCat.slice(0, 5).map((c, i) => `${i + 1}. ${c.icon} ${c.category}: ${store.formatCurrency(c.total)}`).join('\n');
            } else {
                response = 'No category data available yet. Add some expenses first!';
            }
        } else if (lw.includes('budget') || lw.includes('save') || lw.includes('tip')) {
            response = 'Tips:\n• Set a monthly budget and stick to it\n• Track daily expenses to spot patterns\n• Use the 50/30/20 rule\n• Review subscriptions regularly';
        } else {
            response = `I can help with:\n• "How much did I spend?"\n• "Show category breakdown"\n• "Budget tips"\n\n(Note: Cerebras AI is not connected yet — set CEREBRAS_API_KEY in your backend for full AI responses)`;
        }

        _chatHistory.push({ role: 'assistant', content: response });
        const b = el('div', { class: 'chat-bubble bot' });
        b.innerHTML = window.marked ? marked.parse(response) : response;
        msgsContainer.appendChild(b);
    }
    msgsContainer.scrollTop = msgsContainer.scrollHeight;
}

/* ---- Profile (Settings) ---- */
function renderProfile() {
    const user = store.get('user');
    const name = user ? user.full_name : 'Name';
    const email = user ? user.email : '@email';
    const initial = name.charAt(0).toUpperCase();

    async function editInfo() {
        router.navigate('edit-profile');
    }

    async function changeCurrency() {
        router.navigate('change-currency');
    }

    async function toggleDarkMode() {
        if (!user) return;
        try {
            const newMode = !user.dark_mode;
            await store.updateProfile({ dark_mode: newMode });
            toast.success(newMode ? 'Dark mode enabled' : 'Dark mode disabled');
            router.navigate('profile');
        } catch (e) { toast.error('Failed to toggle dark mode'); }
    }

    const menuItems = [
        { icon: '👤', label: 'Account Info', action: editInfo },
        { icon: '🛡️', label: 'Login and security', action: () => toast.info('Security settings: Manage password and 2FA.') },
        { icon: '🔒', label: 'Data and privacy', action: () => toast.info('Your data is encrypted and securely stored on our servers.') },
    ];

    const isDark = user?.dark_mode;
    const settingsItems = [
        { icon: isDark ? '☀️' : '🌙', label: isDark ? 'Light Mode' : 'Dark Mode', action: toggleDarkMode },
        { icon: '💱', label: `Currency (${store.getCurrencySymbol()} - ${user?.preferred_currency || 'INR'})`, action: changeCurrency },
    ];

    const avatarNode = user?.avatar
        ? el('img', { src: user.avatar, class: 'profile-avatar-img', alt: 'Avatar' })
        : initial;

    return el('div', { class: 'screen profile-screen-bg', id: 'profile-screen' },
        // Custom curved header for profile
        el('div', { class: 'profile-header-curve' },
            el('button', { class: 'profile-back-btn', onClick: () => router.navigate('dashboard') }, svg(icons.back, 24, 24)),
            el('div', { class: 'profile-header-title' }, 'Profile'),
            el('button', { class: 'profile-alert-btn', onClick: () => toast.info('No new notifications.') }, '🔔'),
        ),

        el('div', { class: 'profile-content' },
            el('div', { class: 'profile-avatar-section' },
                el('div', { class: 'profile-avatar' }, avatarNode),
                el('div', { class: 'profile-name' }, name),
                el('div', { class: 'profile-email' }, email),
            ),

            el('div', { class: 'profile-card stagger-children' },
                ...menuItems.map(item =>
                    el('button', { class: 'profile-list-item', onClick: item.action },
                        el('div', { class: 'profile-item-icon' }, item.icon),
                        el('span', { class: 'profile-item-text' }, item.label),
                    )
                ),
            ),

            el('div', { class: 'profile-card' },
                ...settingsItems.map(item =>
                    el('button', { class: 'profile-list-item', onClick: item.action },
                        el('div', { class: 'profile-item-icon' }, item.icon),
                        el('span', { class: 'profile-item-text' }, item.label),
                    )
                ),
            ),

            el('button', {
                class: 'profile-logout-btn',
                onClick: () => {
                    localStorage.removeItem('user_id');
                    store.set('user', null);
                    store.set('userId', null);
                    toast.info('Logged out');
                    router.navigate('splash');
                }
            },
                'Log Out'
            ),
        ),
    );
}

/* ---- Budget ---- */
function renderEditProfile() {
    const user = store.get('user');
    if (!user) {
        setTimeout(() => router.navigate('dashboard'), 0);
        return el('div', { class: 'screen' });
    }

    async function handleSaveProfile(e) {
        e.preventDefault();
        const fd = new FormData(e.target);
        const submitBtn = document.getElementById('save-profile-btn');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = 'Saving...';
        }

        let updates = {};
        const newName = fd.get('full_name');
        const newEmail = fd.get('email');
        const avatarFile = document.getElementById('avatar-upload').files[0];

        if (newName && newName !== user.full_name) updates.full_name = newName;
        if (newEmail && newEmail !== user.email) updates.email = newEmail;

        try {
            if (avatarFile) {
                const reader = new FileReader();
                reader.readAsDataURL(avatarFile);
                reader.onload = async () => {
                    updates.avatar = reader.result;
                    if (Object.keys(updates).length > 0) {
                        await store.updateProfile(updates);
                        toast.success('Profile updated');
                    }
                    router.navigate('profile');
                };
            } else {
                if (Object.keys(updates).length > 0) {
                    await store.updateProfile(updates);
                    toast.success('Profile updated');
                } else {
                    toast.info('No changes made');
                }
                router.navigate('profile');
            }
        } catch (err) {
            toast.error('Failed to update profile');
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Save Profile';
            }
        }
    }

    // Avatar preview logic
    function handlePhotoPreview(e) {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = () => {
                const preview = document.getElementById('avatar-preview-img');
                if (preview) {
                    preview.src = reader.result;
                    preview.style.display = 'block';
                } else {
                    const avatarSection = document.getElementById('avatar-preview-container');
                    if (avatarSection) {
                        avatarSection.innerHTML = '';
                        avatarSection.appendChild(el('img', { src: reader.result, id: 'avatar-preview-img', class: 'profile-avatar-img', alt: 'Preview' }));
                    }
                }
            };
        }
    }

    const currentAvatarNode = user.avatar
        ? el('img', { src: user.avatar, id: 'avatar-preview-img', class: 'profile-avatar-img', alt: 'Avatar' })
        : el('div', { id: 'avatar-preview-img', class: 'profile-avatar', style: 'width: 100%; height: 100%;' }, user.full_name ? user.full_name.charAt(0).toUpperCase() : '');

    const formContent = el('form', { class: 'expense-form add-slide-in', onSubmit: handleSaveProfile },
        el('div', { class: 'form-group', style: 'display: flex; flex-direction: column; align-items: center; margin-bottom: 20px;' },
            el('div', { id: 'avatar-preview-container', class: 'profile-avatar', style: 'cursor: pointer; position: relative;', onClick: () => document.getElementById('avatar-upload').click() },
                currentAvatarNode,
                el('div', { style: 'position: absolute; bottom: 0; right: 0; background: var(--blue-link); border-radius: 50%; padding: 6px; box-shadow: 0 2px 5px rgba(0,0,0,0.2); display: flex; align-items: center; justify-content: center;' },
                    `<svg viewBox="0 0 24 24" width="16" height="16" fill="#fff"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></svg>`
                )
            ),
            el('input', { class: 'form-input', type: 'file', accept: 'image/*', id: 'avatar-upload', style: 'display: none;', onChange: handlePhotoPreview }),
            el('div', { style: 'font-size: 12px; color: #8c9b9d; margin-top: 8px;' }, 'Tap to change photo')
        ),
        el('div', { class: 'form-group' },
            el('label', { class: 'form-label' }, 'FULL NAME'),
            el('input', { class: 'form-input', name: 'full_name', type: 'text', placeholder: 'Enter Full Name', required: 'true', value: user.full_name }),
        ),
        el('div', { class: 'form-group' },
            el('label', { class: 'form-label' }, 'EMAIL'),
            el('input', { class: 'form-input', name: 'email', type: 'email', placeholder: 'Enter Email', required: 'true', value: user.email }),
        ),
        el('button', { class: 'submit-btn', type: 'submit', id: 'save-profile-btn', style: 'margin-top: 10px;' }, 'Save Profile'),
    );

    return el('div', { class: 'screen add-expense-bg', id: 'edit-profile-screen' },
        SubHeader('Edit Profile', 'profile', true),
        el('div', { class: 'px-page add-expense-card' },
            formContent
        ),
    );
}

function renderChangeCurrency() {
    const user = store.get('user');
    if (!user) {
        setTimeout(() => router.navigate('dashboard'), 0);
        return el('div', { class: 'screen' });
    }

    const container = el('div', { class: 'screen add-expense-bg', id: 'change-currency-screen' },
        SubHeader('Currency', 'profile', true),
        el('div', { class: 'px-page add-expense-card', id: 'curr-card' },
            el('div', { style: 'padding: 40px; text-align: center;' }, LoadingSpinner('Loading...'))
        ),
    );

    setTimeout(async () => {
        let currencies = [];
        try {
            const res = await fetch('https://api.exchangerate-api.com/v4/latest/USD');
            const data = await res.json();
            currencies = Object.keys(data.rates);
        } catch (e) {
            try {
                const res2 = await fetch('https://open.er-api.com/v6/latest/USD');
                const data2 = await res2.json();
                currencies = Object.keys(data2.rates);
            } catch (err) {
                currencies = ['USD', 'EUR', 'GBP', 'INR', 'JPY', 'AUD', 'CAD', 'CHF', 'CNY', 'NZD'];
            }
        }

        function CurrencyDropdownUI(currenciesList, initialCurr) {
            let selected = initialCurr || 'INR';

            function getSymbol(code) {
                try {
                    const parts = new Intl.NumberFormat('en', { style: 'currency', currency: code }).formatToParts(0);
                    const part = parts.find(p => p.type === 'currency');
                    return part ? part.value : code;
                } catch (e) { return code; }
            }

            const hiddenInput = el('input', { type: 'hidden', name: 'currency', id: 'currency-select', required: 'true', value: selected });
            const selectedIcon = el('span', { class: 'dropdown-selected-icon' }, getSymbol(selected));
            const selectedText = el('span', { class: 'dropdown-selected-text' }, selected);

            const optionsList = el('div', { class: 'dropdown-options', style: 'max-height: 250px; overflow-y: auto;' },
                ...currenciesList.map(c => {
                    const sym = getSymbol(c);
                    const opt = el('div', { class: 'dropdown-option' },
                        el('span', { class: 'dropdown-option-icon' }, sym),
                        el('span', { class: 'dropdown-option-text' }, c)
                    );
                    opt.onclick = (e) => {
                        e.stopPropagation();
                        selected = c;
                        hiddenInput.value = c;
                        selectedIcon.textContent = sym;
                        selectedText.textContent = c;
                        dropdown.classList.remove('open');
                    };
                    return opt;
                })
            );

            const dropdown = el('div', { class: 'custom-dropdown', id: 'currency-dropdown', style: 'margin-bottom: 20px;' },
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
                document.querySelectorAll('.custom-dropdown').forEach(d => d.classList.remove('open'));
                if (!isOpen) dropdown.classList.add('open');
            };

            window.addEventListener('click', (e) => {
                if (!dropdown.contains(e.target)) dropdown.classList.remove('open');
            }, { once: false });

            return dropdown;
        }

        const currDropdown = CurrencyDropdownUI(currencies, user.preferred_currency);

        async function saveCurrency(e) {
            e.preventDefault();
            const btn = document.getElementById('save-curr-btn');
            if (btn) {
                btn.disabled = true;
                btn.textContent = 'Saving...';
            }
            const selected = document.getElementById('currency-select').value;
            try {
                await store.updateProfile({ preferred_currency: selected });
                toast.success('Currency updated to ' + selected);
                router.navigate('profile');
            } catch (err) {
                toast.error('Failed to update currency');
                if (btn) {
                    btn.disabled = false;
                    btn.textContent = 'Save Currency';
                }
            }
        }

        const formContent = el('form', { class: 'expense-form slide-up', onSubmit: saveCurrency },
            el('div', { class: 'form-group' },
                el('label', { class: 'form-label' }, 'SELECT CURRENCY'),
                currDropdown,
            ),
            el('button', { class: 'submit-btn', type: 'submit', id: 'save-curr-btn' }, 'Save Currency'),
        );

        const currCard = container.querySelector('#curr-card');
        if (currCard) {
            currCard.innerHTML = '';
            currCard.appendChild(formContent);
        }
    }, 100);

    return container;
}

/* ---- Budget ---- */
function renderBudget() {
    const screen = el('div', { class: 'screen', id: 'budget-screen' },
        SubHeader('Budget Planner', 'dashboard'),
        el('div', { class: 'budget-content' },
            el('div', { id: 'budget-main-section' }, LoadingSpinner()),
        ),
    );
    setTimeout(async () => {
        await Promise.all([store.loadBudgets(), store.loadExpenses(), store.loadCategories(), store.loadSummary()]);
        renderBudgetContent();
    }, 100);
    return screen;
}

function handleBudgetSetup(e) {
    e.preventDefault();
    const fd = new FormData(e.target);
    const userId = store.get('userId');
    const d = new Date();
    const dStr = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`; // yyyy-mm
    const promises = [];

    // 1. Save Total Monthly Budget
    const totalAmt = parseFloat(fd.get('total') || 0);
    if (totalAmt > 0) {
        promises.push(api.createBudget({
            user_id: userId,
            category_id: null,
            amount: totalAmt,
            month: dStr
        }));
    }

    // 2. Save Category Budgets
    const cats = store.get('categories');
    cats.forEach(c => {
        const amt = parseFloat(fd.get(`cat_${c.category_id}`) || 0);
        if (amt > 0) {
            promises.push(api.createBudget({
                user_id: userId,
                category_id: c.category_id,
                amount: amt,
                month: dStr
            }));
        }
    });

    const container = document.getElementById('budget-main-section');
    container.innerHTML = '';
    container.appendChild(LoadingSpinner('Saving...'));

    Promise.all(promises).then(() => {
        toast.success('Budgets saved!');
        store.loadBudgets().then(renderBudgetContent);
    }).catch(err => {
        toast.error('Failed to save budgets');
        console.error(err);
        renderBudgetContent();
    });
}

function renderBudgetSetupForm(container, initialBudgets = []) {
    const cats = store.get('categories');
    const totalBudgetObj = initialBudgets.find(b => !b.category_id);
    const totalValue = totalBudgetObj ? totalBudgetObj.amount : '';

    container.appendChild(el('div', { class: 'budget-setup-card slide-up' },
        el('h3', { class: 'budget-setup-title' }, initialBudgets.length > 0 ? 'Edit Your Budgets' : 'Set Your Budgets'),
        el('p', { class: 'budget-setup-subtitle' }, 'Enter your monthly budget and limits for each category.'),
        el('form', { class: 'budget-setup-form', onSubmit: handleBudgetSetup },
            el('div', { class: 'form-group' },
                el('label', { class: 'form-label' }, `Total Monthly Budget (${store.getCurrencySymbol()})`),
                el('input', { class: 'form-input', name: 'total', type: 'number', required: 'true', min: '1', value: totalValue }),
            ),
            el('h4', { style: 'margin-top: 20px; color: #8c9b9d;' }, 'Category Limits'),
            ...cats.map(c => {
                const catBudget = initialBudgets.find(b => b.category_id === c.category_id);
                const catValue = catBudget ? catBudget.amount : '';
                return el('div', { class: 'form-group' },
                    el('label', { class: 'form-label' }, `${c.icon} ${c.name} Limit (${store.getCurrencySymbol()})`),
                    el('input', { class: 'form-input', name: `cat_${c.category_id}`, type: 'number', required: 'true', min: '0', value: catValue }),
                );
            }),
            el('div', { class: 'btn-group' },
                el('button', { class: 'submit-btn flex-1', type: 'submit' }, 'Save Budgets'),
                initialBudgets.length > 0 ? el('button', {
                    class: 'btn-outline btn-danger-outline flex-1',
                    type: 'button',
                    onClick: async () => {
                        if (confirm('Are you sure you want to reset all budgets for this month?')) {
                            const d = new Date();
                            const m = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
                            await store.resetBudgets(m);
                            toast.success('Budgets reset');
                            renderBudgetContent();
                        }
                    }
                }, 'Reset') : null,
                initialBudgets.length > 0 ? el('button', {
                    class: 'btn-outline flex-1',
                    type: 'button',
                    onClick: () => renderBudgetContent()
                }, 'Cancel') : null
            )
        )
    ));
}

function renderBudgetContent() {
    const container = document.getElementById('budget-main-section');
    if (!container) return;
    container.innerHTML = '';

    const summary = store.get('summary');
    const budgets = store.get('budgets') || [];

    // Check if user has budgets for this month. If none, render setup form
    if (budgets.length === 0) {
        renderBudgetSetupForm(container);
        return;
    }

    const totalBudgetObj = budgets.find(b => !b.category_id);
    const totalBudget = totalBudgetObj ? totalBudgetObj.amount : 0;

    const byCat = summary?.by_category || [];
    const totalSpent = summary?.summary?.total_spent || 0;
    const remaining = totalBudget > 0 ? (totalBudget - totalSpent) : 0;
    const pct = totalBudget > 0 ? Math.min(100, (totalSpent / totalBudget) * 100) : 0;
    const daysInMonth = new Date(new Date().getFullYear(), new Date().getMonth() + 1, 0).getDate();
    const daysLeft = daysInMonth - new Date().getDate();
    const dailyAvg = new Date().getDate() > 0 ? Math.round(totalSpent / new Date().getDate()) : 0;

    container.appendChild(el('div', { class: 'budget-title-section slide-up' },
        el('div', { class: 'budget-main-label' }, 'Monthly Budget'),
        el('div', { class: 'budget-main-amount' }, store.formatCurrency(totalBudget)),
        el('div', { class: 'budget-progress-bar' },
            el('div', { class: `budget-progress-fill ${pct > 90 ? 'over' : 'under'}`, style: { width: pct + '%' } }),
        ),
        el('div', { class: 'budget-progress-text' }, `${pct.toFixed(1)}% used`),
    ));

    container.appendChild(el('div', { class: 'budget-stats-row slide-up' },
        el('div', { class: 'budget-stat-card' },
            el('div', { class: 'budget-stat-label' }, 'SPENT'),
            el('div', { class: 'budget-stat-value' }, store.formatCurrency(totalSpent)),
        ),
        el('div', { class: 'budget-stat-card' },
            el('div', { class: 'budget-stat-label' }, 'REMAINING'),
            el('div', { class: `budget-stat-value ${remaining < 0 ? 'danger' : ''}` }, store.formatCurrency(remaining)),
        ),
        el('div', { class: 'budget-stat-card' },
            el('div', { class: 'budget-stat-label' }, 'DAILY AVG'),
            el('div', { class: 'budget-stat-value' }, store.formatCurrency(dailyAvg)),
        ),
        el('div', { class: 'budget-stat-card' },
            el('div', { class: 'budget-stat-label' }, 'DAYS LEFT'),
            el('div', { class: 'budget-stat-value' }, String(daysLeft)),
        ),
    ));

    container.appendChild(el('div', { class: 'budget-section-title' }, 'Category Budget'));

    const cats = store.get('categories');
    const breakdownCard = el('div', { class: 'budget-breakdown-card stagger-children slide-up' });

    cats.forEach(c => {
        // Find spent total from summary
        const summaryCat = byCat.find(bc => bc.category === c.name);
        const spent = summaryCat ? summaryCat.total : 0;

        // Find assigned budget
        const userCatBudget = budgets.find(b => b.category_id === c.category_id);
        const limit = userCatBudget ? userCatBudget.amount : 5000;

        const catPct = Math.min(100, limit > 0 ? (spent / limit) * 100 : 0);

        breakdownCard.appendChild(
            el('div', { class: 'budget-cat-item' },
                el('div', { class: 'budget-cat-header' },
                    el('div', { class: 'budget-cat-name' }, c.name),
                    el('div', { class: 'budget-cat-amts' },
                        store.formatCurrency(spent),
                        el('span', { class: 'budget-cat-limit' }, ` of ${store.formatCurrency(limit)}`)
                    ),
                ),
                el('div', { class: 'budget-cat-bar' },
                    el('div', { class: 'budget-cat-fill', style: { width: catPct + '%', backgroundColor: c.color } })
                )
            )
        );
    });

    container.appendChild(breakdownCard);

    // Add Edit Button
    container.appendChild(el('div', { class: 'px-page slide-up', style: 'margin-top: 24px;' },
        el('button', {
            class: 'submit-btn',
            onClick: () => {
                container.innerHTML = '';
                renderBudgetSetupForm(container, budgets);
            }
        },
            el('span', {}, '✏️'),
            el('span', { style: 'margin-left: 8px;' }, 'Edit Budgets')
        )
    ));
}

/* ---- All Transactions Page ---- */
let _txnFilters = { startDate: '', endDate: '', categoryIds: [], minAmount: '', maxAmount: '' };

function renderAllTransactions() {
    const cats = store.get('categories') || [];

    // Default to current month
    if (!_txnFilters.startDate) {
        const now = new Date();
        const y = now.getFullYear();
        const m = String(now.getMonth() + 1).padStart(2, '0');
        const d = String(now.getDate()).padStart(2, '0');
        _txnFilters.startDate = `${y}-${m}-01`;
        _txnFilters.endDate = `${y}-${m}-${d}`;
    }

    // Date inputs
    const dateRow = el('div', { class: 'txn-filter-row' },
        el('div', { class: 'txn-filter-field' },
            el('label', { class: 'txn-filter-label' }, 'From'),
            DatePicker({ id: 'txn-start-date', value: _txnFilters.startDate, restrictToExpenses: true, onChange: (v) => { _txnFilters.startDate = v; _applyTxnFilters(); } })
        ),
        el('div', { class: 'txn-filter-field' },
            el('label', { class: 'txn-filter-label' }, 'To'),
            DatePicker({ id: 'txn-end-date', value: _txnFilters.endDate, restrictToExpenses: true, onChange: (v) => { _txnFilters.endDate = v; _applyTxnFilters(); } })
        )
    );

    // Category chips
    const catChipsContainer = el('div', { class: 'txn-cat-chips', id: 'txn-cat-chips-container' });

    function updateCatChips() {
        catChipsContainer.innerHTML = '';

        // "All" button
        catChipsContainer.appendChild(
            el('button', {
                class: 'txn-cat-chip' + (_txnFilters.categoryIds.length === 0 ? ' active' : ''),
                onClick: () => {
                    _txnFilters.categoryIds = [];
                    updateCatChips();
                    _applyTxnFilters();
                }
            }, 'All')
        );

        // Individual Category buttons
        cats.forEach(c => {
            const isActive = _txnFilters.categoryIds.includes(Number(c.category_id));
            catChipsContainer.appendChild(
                el('button', {
                    class: 'txn-cat-chip' + (isActive ? ' active' : ''),
                    onClick: () => {
                        const cId = Number(c.category_id);
                        const idx = _txnFilters.categoryIds.indexOf(cId);
                        if (idx >= 0) _txnFilters.categoryIds.splice(idx, 1);
                        else _txnFilters.categoryIds.push(cId);

                        updateCatChips();
                        _applyTxnFilters();
                    }
                }, `${c.icon} ${c.name}`)
            );
        });
    }

    updateCatChips();

    // Amount range
    const amountRow = el('div', { class: 'txn-filter-row' },
        el('div', { class: 'txn-filter-field' },
            el('label', { class: 'txn-filter-label' }, `Min ${store.getCurrencySymbol()}`),
            el('input', {
                class: 'txn-filter-input', type: 'number', placeholder: '0', value: _txnFilters.minAmount,
                onChange: (e) => { _txnFilters.minAmount = e.target.value; _applyTxnFilters(); }
            })
        ),
        el('div', { class: 'txn-filter-field' },
            el('label', { class: 'txn-filter-label' }, `Max ${store.getCurrencySymbol()}`),
            el('input', {
                class: 'txn-filter-input', type: 'number', placeholder: 'Any', value: _txnFilters.maxAmount,
                onChange: (e) => { _txnFilters.maxAmount = e.target.value; _applyTxnFilters(); }
            })
        )
    );

    const screen = el('div', { class: 'screen', id: 'transactions-screen' },
        SubHeader('All Transactions'),
        el('div', { class: 'px-page txn-page-content' },
            el('div', { class: 'txn-filters-card slide-up' },
                dateRow,
                catChipsContainer,
                amountRow,
            ),
            el('div', { class: 'txn-summary-bar slide-up', id: 'txn-summary-bar' }),
            el('div', { id: 'txn-results-section' },
                el('div', { class: 'loading-spinner' }, el('div', { class: 'spinner' }), el('span', { class: 'loading-text' }, 'Loading...'))
            )
        )
    );

    setTimeout(() => {
        store.loadExpenses().then(() => _applyTxnFilters());
    }, 50);

    return screen;
}

function _applyTxnFilters() {
    const allExpenses = store.get('expenses') || [];
    const cats = store.get('categories') || [];
    let filtered = [...allExpenses];

    // Date filter
    if (_txnFilters.startDate) {
        filtered = filtered.filter(e => e.expense_date >= _txnFilters.startDate);
    }
    if (_txnFilters.endDate) {
        filtered = filtered.filter(e => e.expense_date <= _txnFilters.endDate);
    }

    // Category filter
    if (_txnFilters.categoryIds.length > 0) {
        const selectedIds = _txnFilters.categoryIds.map(id => Number(id));
        filtered = filtered.filter(e => selectedIds.includes(Number(e.category_id)));
    }

    // Amount filter
    const minAmt = parseFloat(_txnFilters.minAmount);
    const maxAmt = parseFloat(_txnFilters.maxAmount);
    if (!isNaN(minAmt) && minAmt > 0) {
        filtered = filtered.filter(e => e.amount >= minAmt);
    }
    if (!isNaN(maxAmt) && maxAmt > 0) {
        filtered = filtered.filter(e => e.amount <= maxAmt);
    }

    // Sort by date desc
    filtered.sort((a, b) => b.expense_date.localeCompare(a.expense_date));

    // Summary bar
    const total = filtered.reduce((s, e) => s + e.amount, 0);
    const summaryBar = document.getElementById('txn-summary-bar');
    if (summaryBar) {
        summaryBar.innerHTML = '';
        summaryBar.appendChild(el('span', { class: 'txn-summary-count' }, `${filtered.length} transaction${filtered.length !== 1 ? 's' : ''}`));
        summaryBar.appendChild(el('span', { class: 'txn-summary-total' }, store.formatCurrency(total)));
    }

    // Group by date
    const groups = {};
    filtered.forEach(e => {
        const key = e.expense_date;
        if (!groups[key]) groups[key] = [];
        groups[key].push(e);
    });

    const section = document.getElementById('txn-results-section');
    if (!section) return;
    section.innerHTML = '';

    if (filtered.length === 0) {
        section.appendChild(EmptyState('🔍', 'No transactions found', 'Try adjusting your filters'));
        return;
    }

    Object.keys(groups).sort((a, b) => b.localeCompare(a)).forEach((dateKey, idx) => {
        const dt = new Date(dateKey + 'T00:00:00');
        const label = dt.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
        const dayTotal = groups[dateKey].reduce((s, e) => s + e.amount, 0);

        // Default the first group to open, others closed
        const isOpen = idx === 0;

        const groupEl = el('div', { class: 'txn-date-group slide-up' + (isOpen ? ' open' : '') },
            el('div', {
                class: 'txn-date-header',
                onClick: (e) => {
                    const parent = e.currentTarget.parentElement;
                    parent.classList.toggle('open');
                }
            },
                el('div', { class: 'txn-date-header-left' },
                    el('div', { class: 'txn-date-arrow' }, svg(icons.arrowDown, 16, 16)),
                    el('span', { class: 'txn-date-label' }, label),
                ),
                el('span', { class: 'txn-date-total' }, store.formatCurrency(dayTotal)),
            ),
            el('div', { class: 'transaction-list-collapsible' },
                el('div', { class: 'transaction-list' }, ...groups[dateKey].map(TransactionItem))
            )
        );

        section.appendChild(groupEl);
    });
}

/* ============================================================
   REGISTER ROUTES & BOOTSTRAP
   ============================================================ */
router.register('splash', renderSplash);
router.register('dashboard', renderDashboard);
router.register('add-expense', renderAddExpense);
router.register('split-expense', renderSplitExpense);
router.register('transactions', renderAllTransactions);
router.register('chatbot', renderChatbot);
router.register('profile', renderProfile);
router.register('edit-profile', renderEditProfile);
router.register('change-currency', renderChangeCurrency);
router.register('budget', renderBudget);
router.register('ai-analysis', renderAIAnalysisPage);

function GlobalChatFab() {
    const fab = el('button', {
        class: 'chatbot-fab',
        id: 'global-chat-fab',
        style: { display: 'none' }, // Start hidden
        onClick: () => router.navigate('chatbot')
    }, el('img', {
        src: '/assets/chatbot-icon.png',
        alt: 'Chatbot',
        class: 'chatbot-fab-img'
    }));

    store.subscribe((key) => {
        if (key === 'currentScreen') {
            const screen = store.get('currentScreen');
            // Show ONLY on the dashboard
            const shouldShow = screen === 'dashboard';
            fab.style.display = shouldShow ? 'flex' : 'none';
        }
    });

    return fab;
}

(async function init() {
    try {
        const user = await store.initUser();

        // Add global persistent UI elements to #app
        const appContainer = document.getElementById('app');
        if (appContainer) {
            appContainer.appendChild(GlobalChatFab());
        }

        // --- GLOBAL REACTIVE SUBSCRIBER ---
        // This ensures ANY data change (from store.loadX) triggers a surgical UI update
        // instead of a full router.navigate blink.
        store.subscribe((key) => {
            const current = router.getCurrentScreen();

            // Only trigger updates for data-related keys
            const dataKeys = ['expenses', 'summary', 'budgets', 'recommendations', 'user'];
            if (dataKeys.includes(key)) {
                // router.navigate already handles surgical updates via window.updateXSurgical
                // so we just call it to trigger the logic.
                router.navigate(current);
            }
        });

        await store.loadCategories();

        // Restore from URL hash if present (e.g. user bookmarked a screen or refreshed)
        const hashScreen = window.location.hash.replace('#', '');
        const targetScreen = (hashScreen && router._routes[hashScreen] && user)
            ? hashScreen
            : (user ? 'dashboard' : 'splash');

        router.navigate(targetScreen, { replace: true });
    } catch (e) {
        console.warn('Init failed:', e);
        router.navigate('splash', { replace: true });
    }
})();

/* ============================================================
   SURGICAL UPDATE FUNCTIONS
   These functions allow updating specific screen parts without re-rendering the whole screen.
   The router calls these automatically when navigate is called for the current screen.
   ============================================================ */

window.updateDashboardSurgical = function () {
    console.log('[App] Surgical update: Dashboard');
    renderAIInsight();
    renderRecentTransactions();
    renderSpendingChart();
    renderTrendChart();

    // Update BalanceCard
    const balanceNode = document.querySelector('.balance-card');
    if (balanceNode) {
        const newNode = BalanceCard();
        balanceNode.replaceWith(newNode);
    }
}

window.updateTransactionsSurgical = function () {
    console.log('[App] Surgical update: Transactions');
    if (typeof _applyTxnFilters === 'function') {
        _applyTxnFilters();
    }
}

window.updateAiAnalysisSurgical = function () {
    console.log('[App] Surgical update: AI Analysis');
    const updated = store.get('recommendations');
    if (!updated) return;

    const newRecs = updated.recommendations || [];
    const newScore = updated.healthScore || 0;

    // Update Score surgically
    const progress = document.getElementById('ai-score-progress');
    const scoreVal = document.getElementById('ai-score-value');
    const heroDesc = document.getElementById('ai-hero-desc');

    if (progress) progress.style.strokeDashoffset = `${283 - (283 * newScore / 100)}`;
    if (scoreVal) scoreVal.textContent = newScore;
    if (heroDesc) {
        // Find getHealthStatusText - normally accessible since it's in app.js
        if (typeof getHealthStatusText === 'function') {
            heroDesc.textContent = getHealthStatusText(newScore);
        }
    }

    // Update List surgically
    const list = document.getElementById('ai-recommendations-list');
    if (list) {
        list.innerHTML = '';
        if (newRecs.length > 0) {
            if (typeof renderRecommendationCards === 'function') {
                const cards = renderRecommendationCards(newRecs);
                cards.forEach(c => list.appendChild(c));
            }
        } else {
            list.appendChild(EmptyState('🤖', 'No recommendations yet', 'Keep tracking your expenses to get personalized insights.'));
        }
    }
}

window.updateProfileSurgical = function () {
    console.log('[App] Surgical update: Profile');
    // If we're on profile, a full re-render is usually fast since it's mostly static,
    // but we can at least refresh the name/avatar cards if specific info changed.
    // For now, let's allow it to be handled via the existing Router -> Navigate logic
    // but we define the function to satisfy the router's check.
}

window.updateBudgetSurgical = function () {
    console.log('[App] Surgical update: Budget');
    // Reload budgets list from current DOM or just refresh the whole thing
    // Since budgets are small lists, we usually just re-navigate.
}
