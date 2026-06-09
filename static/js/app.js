/**
 * Wealth Manager - Main Application Module
 */

const API_BASE = '';

// State
const state = {
    holdings: [],
    calendar: [],
    stats: {},
    settings: {},
    currentTab: 'dashboard',
    holdingsSort: { field: 'market_value', direction: 'desc' },
    calendarView: 'monthly',
    selectedYear: new Date().getFullYear(),
    selectedMonth: new Date().getMonth(),
    selectedDate: null,
    notificationRules: [],
    pollingStatus: {},
    stockCache: [],
    theme: 'auto',
    loading: {
        dashboard: false,
        holdings: false,
        calendar: false,
        settings: false
    }
};

// Theme management
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'auto';
    state.theme = savedTheme;
    applyTheme(savedTheme);
}

function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    state.theme = theme;
    localStorage.setItem('theme', theme);
    document.querySelectorAll('.theme-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.theme === theme);
    });
}

function setTheme(theme) {
    applyTheme(theme);
}

// API Helper with retry mechanism
async function api(endpoint, options = {}, retries = 3) {
    const url = `${API_BASE}${endpoint}`;
    const config = {
        headers: { 'Content-Type': 'application/json', ...options.headers },
        ...options,
    };
    
    for (let attempt = 1; attempt <= retries; attempt++) {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 30000);
            
            const response = await fetch(url, {
                ...config,
                signal: controller.signal,
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
                throw new Error(error.detail || `HTTP ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.warn(`API attempt ${attempt}/${retries} failed:`, error.message);
            
            if (attempt === retries) {
                console.error(`API Error after ${retries} attempts:`, error);
                throw error;
            }
            
            await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
        }
    }
}

// Toast notification
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type} show`;
    setTimeout(() => toast.classList.remove('show'), 3000);
}

// Tab switching
function switchTab(tabName) {
    state.currentTab = tabName;
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
    });
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === `tab-${tabName}`);
    });
    loadTabData(tabName);
}

function loadTabData(tabName) {
    switch (tabName) {
        case 'dashboard': loadDashboard(); break;
        case 'holdings': loadHoldings(); break;
        case 'calendar': loadCalendar(); break;
        case 'settings': loadSettings(); break;
    }
}

// Loading spinner
function showLoading(containerId, message = '加载中...') {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `
            <div class="loading-container">
                <div class="loading-spinner"></div>
                <div class="loading-text">${message}</div>
            </div>
        `;
    }
}

function hideLoading(containerId) {
    // Loading will be replaced by content
}

// Dashboard
async function loadDashboard() {
    state.loading.dashboard = true;
    

    
    // Load all data in parallel
    const results = await Promise.allSettled([
        api('/api/holdings'),
        api('/api/dividends/stats'),
        api('/api/dividends/calendar'),
        api('/api/polling/status'),
    ]);
    
    const holdings = results[0].status === 'fulfilled' ? results[0].value : [];
    const stats = results[1].status === 'fulfilled' ? results[1].value : null;
    const calendar = results[2].status === 'fulfilled' ? results[2].value : [];
    const pollingStatus = results[3].status === 'fulfilled' ? results[3].value : {};
    
    state.holdings = holdings;
    state.calendar = calendar;
    state.pollingStatus = pollingStatus;
    
    // Update stats display
    const defaultStats = { total_cost: 0, total_market_value: 0, total_profit: 0, profit_rate: 0, total_dividends_received: 0, total_dividends_expected: 0, payback_progress: 0, dividend_yield: 0 };
    const displayStats = stats || defaultStats;
    
    document.getElementById('stat-total-cost').textContent = formatCurrency(displayStats.total_cost);
    document.getElementById('stat-market-value').textContent = formatCurrency(displayStats.total_market_value);
    const profitEl = document.getElementById('stat-profit');
    profitEl.textContent = formatCurrency(displayStats.total_profit);
    profitEl.classList.toggle('positive', displayStats.total_profit >= 0);
    document.getElementById('stat-profit-rate').textContent = `${displayStats.profit_rate >= 0 ? '+' : ''}${displayStats.profit_rate.toFixed(2)}%`;
    document.getElementById('stat-dividends-received').textContent = formatCurrency(displayStats.total_dividends_received);
    document.getElementById('stat-dividends-expected').textContent = formatCurrency(displayStats.total_dividends_expected);
    document.getElementById('stat-payback').textContent = `${displayStats.payback_progress.toFixed(2)}%`;
    document.getElementById('stat-yield').textContent = `股息率 ${displayStats.dividend_yield.toFixed(2)}%`;

    updatePollingStatus(pollingStatus);

    renderDashboardDividends(calendar.slice(0, 5));
    
    state.loading.dashboard = false;
}

function updatePollingStatus(status) {
    const statusEl = document.getElementById('polling-status');
    if (statusEl) {
        statusEl.textContent = status.running ? '轮询中' : '已停止';
        statusEl.className = `polling-status ${status.running ? 'active' : ''}`;
    }
}



function renderDashboardDividends(calendar) {
    const container = document.getElementById('dashboard-dividends-list');
    if (calendar.length === 0) {
        container.innerHTML = '<div class="empty-state">暂无近期分红数据</div>';
        return;
    }
    container.innerHTML = calendar.slice(0, 5).map(c => {
        let color, label;
        if (c.type === 'record') {
            color = '#2196F3';
            label = '股权登记日';
        } else if (c.type === 'ex_dividend') {
            color = '#FF9800';
            label = '除权除息日';
        } else {
            color = '#4CAF50';
            label = '派息日';
        }
        return `
            <div class="dividend-item">
                <div class="dividend-info">
                    <div class="dividend-name">
                        <span class="event-dot" style="background-color: ${color};"></span>
                        ${escapeHtml(c.name)}
                    </div>
                    <div class="dividend-symbol">${escapeHtml(c.symbol)}</div>
                    <div class="dividend-date">📅 ${formatDate(c.date)} · ${label}</div>
                </div>
                <div class="dividend-amount">每股 ${c.dividend_per_share.toFixed(3)}元</div>
            </div>
        `;
    }).join('');
}

// Holdings
async function loadHoldings() {
    state.loading.holdings = true;
    try {
        const holdings = await api('/api/holdings');
        state.holdings = holdings;
        renderHoldings(holdings);
    } catch (error) {
        showToast('加载持仓失败', 'error');
    } finally {
        state.loading.holdings = false;
    }
}

function sortHoldings(holdings, field, direction) {
    return [...holdings].sort((a, b) => {
        let aVal, bVal;
        switch (field) {
            case 'predicted_dividend': aVal = getPredictedDividend(a.symbol); bVal = getPredictedDividend(b.symbol); break;
            case 'quantity': aVal = a.quantity; bVal = b.quantity; break;
            case 'market_value': aVal = a.market_value; bVal = b.market_value; break;
            case 'cost_price': aVal = a.cost_price; bVal = b.cost_price; break;
            case 'profit_rate': aVal = a.profit_rate; bVal = b.profit_rate; break;
            default: aVal = a.market_value; bVal = b.market_value;
        }
        return direction === 'asc' ? aVal - bVal : bVal - aVal;
    });
}

function getPredictedDividend(symbol) {
    const items = state.calendar.filter(c => c.symbol === symbol);
    return items.reduce((sum, item) => sum + (item.expected_amount || 0), 0);
}

function renderHoldings(holdings) {
    const container = document.getElementById('holdings-list');
    if (holdings.length === 0) {
        container.innerHTML = '<div class="empty-state">暂无持仓，点击上方按钮添加</div>';
        return;
    }

    const { field, direction } = state.holdingsSort;
    const sortedHoldings = sortHoldings(holdings, field, direction);

    const sortControls = `
        <div class="sort-controls">
            <span class="sort-label">排序:</span>
            <button class="sort-btn ${field === 'predicted_dividend' ? 'active' : ''}" onclick="setHoldingsSort('predicted_dividend')">预测分红 ${field === 'predicted_dividend' ? (direction === 'desc' ? '↓' : '↑') : ''}</button>
            <button class="sort-btn ${field === 'quantity' ? 'active' : ''}" onclick="setHoldingsSort('quantity')">持仓数量 ${field === 'quantity' ? (direction === 'desc' ? '↓' : '↑') : ''}</button>
            <button class="sort-btn ${field === 'market_value' ? 'active' : ''}" onclick="setHoldingsSort('market_value')">市值 ${field === 'market_value' ? (direction === 'desc' ? '↓' : '↑') : ''}</button>
            <button class="sort-btn ${field === 'cost_price' ? 'active' : ''}" onclick="setHoldingsSort('cost_price')">成本价 ${field === 'cost_price' ? (direction === 'desc' ? '↓' : '↑') : ''}</button>
            <button class="sort-btn ${field === 'profit_rate' ? 'active' : ''}" onclick="setHoldingsSort('profit_rate')">收益率 ${field === 'profit_rate' ? (direction === 'desc' ? '↓' : '↑') : ''}</button>
        </div>
    `;

    container.innerHTML = sortControls + sortedHoldings.map(h => {
        const predictedDiv = getPredictedDividend(h.symbol);
        return `
            <div class="holding-card">
                <div class="holding-main" onclick="showStockDetail('${h.symbol}')">
                    <div class="holding-info">
                        <div class="holding-name">${escapeHtml(h.name)}</div>
                        <div class="holding-symbol">${escapeHtml(h.symbol)}</div>
                        <div class="holding-meta">${formatNumber(h.quantity)}股 · 成本 ${formatCurrency(h.cost_price)} · 现价 ${formatCurrency(h.current_price)}</div>
                        ${predictedDiv > 0 ? `<div class="holding-dividend">预计分红: ${formatCurrency(predictedDiv)}</div>` : ''}
                    </div>
                    <div class="holding-values">
                        <div class="holding-market-value">${formatCurrency(h.market_value)}</div>
                        <div class="holding-profit ${h.profit >= 0 ? 'positive' : ''}">
                            ${h.profit >= 0 ? '+' : ''}${formatCurrency(h.profit)} (${h.profit_rate >= 0 ? '+' : ''}${h.profit_rate.toFixed(2)}%)
                        </div>
                    </div>
                </div>
                <div class="holding-actions">
                    <button class="btn-edit" onclick="event.stopPropagation(); editHolding(${h.id})">编辑</button>
                    <button class="btn-delete" onclick="event.stopPropagation(); deleteHolding(${h.id})">删除</button>
                </div>
            </div>
        `;
    }).join('');
}

function setHoldingsSort(field) {
    if (state.holdingsSort.field === field) {
        state.holdingsSort.direction = state.holdingsSort.direction === 'desc' ? 'asc' : 'desc';
    } else {
        state.holdingsSort.field = field;
        state.holdingsSort.direction = 'desc';
    }
    renderHoldings(state.holdings);
}

// Edit Holding
function editHolding(id) {
    const holding = state.holdings.find(h => h.id === id);
    if (!holding) return;

    document.getElementById('holding-modal-title').textContent = '编辑持仓';
    document.getElementById('holding-id').value = holding.id;
    document.getElementById('holding-symbol').value = holding.symbol;
    document.getElementById('holding-name').value = holding.name;
    document.getElementById('holding-quantity').value = holding.quantity;
    document.getElementById('holding-cost').value = holding.cost_price;
    document.getElementById('holding-modal').classList.add('active');
}

// Stock Detail
function showStockDetail(symbol) {
    state.currentSymbol = symbol;
    const holding = state.holdings.find(h => h.symbol === symbol);
    if (!holding) {
        showToast('请先添加该股票持仓', 'error');
        return;
    }

    const container = document.getElementById('holdings-list');
    const priceChange = holding.current_price - holding.cost_price;
    const priceChangePercent = holding.cost_price > 0 ? (priceChange / holding.cost_price * 100) : 0;
    const predictedDiv = getPredictedDividend(symbol);
    
    container.innerHTML = `
        <div class="stock-detail">
            <button class="stock-detail-back" onclick="loadHoldings()">← 返回持仓列表</button>
            <div class="stock-detail-header">
                <div>
                    <div class="stock-detail-title">${escapeHtml(holding.name)}</div>
                    <div class="stock-detail-symbol">${escapeHtml(holding.symbol)}</div>
                </div>
                <div class="stock-detail-price">
                    <div class="stock-detail-current-price">${formatCurrency(holding.current_price)}</div>
                    <div class="stock-detail-price-change ${priceChange >= 0 ? 'positive' : 'negative'}">
                        ${priceChange >= 0 ? '+' : ''}${formatCurrency(priceChange)} (${priceChangePercent >= 0 ? '+' : ''}${priceChangePercent.toFixed(2)}%)
                    </div>
                </div>
            </div>
            
            <div class="stock-detail-grid">
                <div class="stock-detail-card">
                    <div class="stock-detail-card-label">持仓数量</div>
                    <div class="stock-detail-card-value">${formatNumber(holding.quantity)} 股</div>
                </div>
                <div class="stock-detail-card">
                    <div class="stock-detail-card-label">成本价</div>
                    <div class="stock-detail-card-value">${formatCurrency(holding.cost_price)}</div>
                </div>
                <div class="stock-detail-card">
                    <div class="stock-detail-card-label">市值</div>
                    <div class="stock-detail-card-value">${formatCurrency(holding.market_value)}</div>
                </div>
                <div class="stock-detail-card">
                    <div class="stock-detail-card-label">盈亏</div>
                    <div class="stock-detail-card-value" style="color: ${holding.profit >= 0 ? 'var(--success)' : 'var(--danger)'}">${formatCurrency(holding.profit)}</div>
                </div>
            </div>
            
            ${predictedDiv > 0 ? `
            <div class="stock-detail-dividend">
                <div class="stock-detail-dividend-label">预计分红</div>
                <div class="stock-detail-dividend-value">${formatCurrency(predictedDiv)}</div>
            </div>
            ` : ''}
        </div>
    `;
}

// Calendar cache
const calendarCache = {
    data: null,
    timestamp: 0,
    expiry: 5 * 60 * 1000, // 5 minutes
};

// Calendar
async function loadCalendar(forceRefresh = false) {
    state.loading.calendar = true;
    
    // Show calendar framework immediately with loading indicator
    const container = document.getElementById('calendar-container');
    const year = state.selectedYear;
    const month = state.selectedMonth;
    const monthNames = ['一月', '二月', '三月', '四月', '五月', '六月', '七月', '八月', '九月', '十月', '十一月', '十二月'];
    const weekDays = ['日', '一', '二', '三', '四', '五', '六'];
    
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const startDay = firstDay.getDay();
    const daysInMonth = lastDay.getDate();
    
    let calendarHTML = `
        <div class="calendar-header">
            <div class="calendar-nav">
                <button class="calendar-nav-btn" onclick="changeMonth(-1)">‹</button>
                <span class="calendar-title">${year}年 ${monthNames[month]}</span>
                <button class="calendar-nav-btn" onclick="changeMonth(1)">›</button>
            </div>
            <div style="display: flex; gap: 8px; align-items: center;">
                <span style="font-size: 0.7rem; color: var(--text-hint);">🔵登记日 🟠除权日 🟢派息日</span>
            </div>
        </div>
        
        <div class="calendar-grid">
            ${weekDays.map(d => `<div class="calendar-weekday">${d}</div>`).join('')}
    `;
    
    for (let i = 0; i < startDay; i++) {
        calendarHTML += '<div class="calendar-day empty"></div>';
    }
    
    for (let day = 1; day <= daysInMonth; day++) {
        calendarHTML += `
            <div class="calendar-day loading" onclick="selectDate('${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}')">
                <span class="calendar-day-number">${day}</span>
                <div class="loading-dots"><span></span><span></span><span></span></div>
            </div>
        `;
    }
    
    calendarHTML += '</div>';
    container.innerHTML = calendarHTML;
    
    // Check cache first
    const now = Date.now();
    if (!forceRefresh && calendarCache.data && (now - calendarCache.timestamp) < calendarCache.expiry) {
        state.calendar = calendarCache.data;
        renderCalendar(calendarCache.data);
        return;
    }
    
    // Load data in background
    try {
        const calendar = await api('/api/dividends/calendar');
        state.calendar = calendar;
        
        // Update cache
        calendarCache.data = calendar;
        calendarCache.timestamp = Date.now();
        
        renderCalendar(calendar);
    } catch (error) {
        console.error('Calendar error:', error);
        // Show error in calendar but keep framework
        container.innerHTML = calendarHTML + '<div class="empty-state" style="padding: 20px;">加载失败，请刷新重试</div>';
    } finally {
        state.loading.calendar = false;
    }
}

function renderCalendar(calendar) {
    const container = document.getElementById('calendar-container');
    const year = state.selectedYear;
    const month = state.selectedMonth;
    
    const monthNames = ['一月', '二月', '三月', '四月', '五月', '六月', '七月', '八月', '九月', '十月', '十一月', '十二月'];
    const weekDays = ['日', '一', '二', '三', '四', '五', '六'];
    
    // Get first day of month and number of days
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const startDay = firstDay.getDay();
    const daysInMonth = lastDay.getDate();
    
    // Group calendar events by date
    const eventsByDate = {};
    calendar.forEach(item => {
        const dateStr = item.date;
        if (!eventsByDate[dateStr]) {
            eventsByDate[dateStr] = [];
        }
        eventsByDate[dateStr].push(item);
    });
    
    // Build calendar grid
    let calendarHTML = `
        <div class="calendar-header">
            <div class="calendar-nav">
                <button class="calendar-nav-btn" onclick="changeMonth(-1)">‹</button>
                <span class="calendar-title">${year}年 ${monthNames[month]}</span>
                <button class="calendar-nav-btn" onclick="changeMonth(1)">›</button>
            </div>
            <div style="display: flex; gap: 8px; align-items: center;">
                <span style="font-size: 0.7rem; color: var(--text-hint);">🔵登记日 🟠除权日 🟢派息日</span>
            </div>
        </div>
        
        <div class="calendar-grid">
            ${weekDays.map(d => `<div class="calendar-weekday">${d}</div>`).join('')}
    `;
    
    // Empty cells before first day
    for (let i = 0; i < startDay; i++) {
        calendarHTML += '<div class="calendar-day empty"></div>';
    }
    
    // Days of month
    for (let day = 1; day <= daysInMonth; day++) {
        const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
        const events = eventsByDate[dateStr] || [];
        const isSelected = state.selectedDate === dateStr;
        
        let dotsHTML = '';
        if (events.length > 0) {
            const uniqueTypes = [...new Set(events.map(e => e.type))];
            dotsHTML = `<div class="calendar-dots">${uniqueTypes.map(type => {
                let color;
                if (type === 'record') color = '#2196F3';
                else if (type === 'ex_dividend') color = '#FF9800';
                else color = '#4CAF50';
                return `<span class="calendar-dot" style="background-color: ${color};"></span>`;
            }).join('')}</div>`;
        }
        
        calendarHTML += `
            <div class="calendar-day ${isSelected ? 'selected' : ''} ${events.length > 0 ? 'has-events' : ''}" 
                 onclick="selectDate('${dateStr}')">
                <span class="calendar-day-number">${day}</span>
                ${dotsHTML}
            </div>
        `;
    }
    
    calendarHTML += '</div>';
    
    // Show selected date details
    if (state.selectedDate) {
        const selectedEvents = eventsByDate[state.selectedDate] || [];
        if (selectedEvents.length > 0) {
            calendarHTML += `
                <div class="calendar-details">
                    <div class="calendar-details-header">
                        <span class="calendar-details-title">${formatDate(state.selectedDate)} 分红详情</span>
                        <span class="calendar-details-count">${selectedEvents.length} 条记录</span>
                    </div>
                    <div class="calendar-details-list">
                        ${selectedEvents.map(item => {
                            let color, label;
                            if (item.type === 'record') {
                                color = '#2196F3';
                                label = '股权登记日';
                            } else if (item.type === 'ex_dividend') {
                                color = '#FF9800';
                                label = '除权除息日';
                            } else {
                                color = '#4CAF50';
                                label = '派息日';
                            }
                            return `
                                <div class="calendar-detail-item">
                                    <div class="calendar-detail-info">
                                        <div class="calendar-detail-name">
                                            <span class="event-dot" style="background-color: ${color};"></span>
                                            ${escapeHtml(item.name)}
                                        </div>
                                        <div class="calendar-detail-symbol">${escapeHtml(item.symbol)}</div>
                                        <div class="calendar-detail-type" style="color: ${color};">${label}</div>
                                    </div>
                                    <div class="calendar-detail-values">
                                        <div class="calendar-detail-amount">每股 ${item.dividend_per_share.toFixed(3)}元</div>
                                        <div class="calendar-detail-total">预计 ${formatCurrency(item.expected_amount)}</div>
                                    </div>
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
            `;
        }
    }
    
    container.innerHTML = calendarHTML;
}

function changeMonth(delta) {
    state.selectedMonth += delta;
    if (state.selectedMonth > 11) {
        state.selectedMonth = 0;
        state.selectedYear++;
    } else if (state.selectedMonth < 0) {
        state.selectedMonth = 11;
        state.selectedYear--;
    }
    state.selectedDate = null;
    loadCalendar();
}

function selectDate(dateStr) {
    state.selectedDate = dateStr;
    renderCalendar(state.calendar);
}

function showCalendarDetail(symbol, date, type) {
    // This function is now handled by selectDate
}

function closeCalendarDetail() {
    state.selectedDate = null;
    renderCalendar(state.calendar);
}

// Refresh prices
async function refreshPrices() {
    try {
        await api('/api/holdings/refresh-prices', { method: 'POST' });
        showToast('价格已刷新', 'success');
        await loadTabData(state.currentTab);
    } catch (error) {
        showToast('刷新失败: ' + error.message, 'error');
    }
}

// Settings
async function loadSettings() {
    state.loading.settings = true;
    try {
        const [settings, notificationRules, pollingStatus] = await Promise.all([
            api('/api/settings'),
            api('/api/notifications/rules').catch(() => []),
            api('/api/polling/status').catch(() => ({})),
        ]);
        
        state.settings = settings;
        state.notificationRules = notificationRules;
        state.pollingStatus = pollingStatus;

        document.getElementById('smtp-host').value = settings.smtp_host || '';
        document.getElementById('smtp-port').value = settings.smtp_port || 587;
        document.getElementById('smtp-user').value = settings.smtp_user || '';
        document.getElementById('smtp-from').value = settings.smtp_from || '';
        document.getElementById('smtp-to').value = settings.smtp_to || '';
        document.getElementById('mcp-token').value = settings.mcp_token || '';
        document.getElementById('received-years').value = settings.received_years || 3;
        document.getElementById('expected-years').value = settings.expected_years || 1;
        
        updatePollingStatus(pollingStatus);
        renderNotificationRules(notificationRules);
    } catch (error) {
        showToast('加载设置失败', 'error');
    } finally {
        state.loading.settings = false;
    }
}

function renderNotificationRules(rules) {
    const container = document.getElementById('notification-rules-list');
    if (!container) return;
    
    if (rules.length === 0) {
        container.innerHTML = '<div class="empty-state">暂无通知规则</div>';
        return;
    }
    
    container.innerHTML = rules.map(rule => `
        <div class="notification-rule-item">
            <div class="notification-rule-header">
                <span class="notification-rule-name">${escapeHtml(rule.name)}</span>
                <span class="notification-rule-status ${rule.active ? 'active' : 'inactive'}">${rule.active ? '启用' : '禁用'}</span>
            </div>
            <div class="notification-rule-condition">${getRuleConditionText(rule)}</div>
            <div class="notification-rule-actions">
                <button class="btn-secondary btn-small" onclick="toggleRule(${rule.id})">${rule.active ? '禁用' : '启用'}</button>
                <button class="btn-delete btn-small" onclick="deleteRule(${rule.id})">删除</button>
            </div>
        </div>
    `).join('');
}

function getRuleConditionText(rule) {
    switch (rule.rule_type) {
        case 'price_drop_percent': return `${rule.symbol} 单日跌幅超过 ${rule.threshold}%`;
        case 'price_below': return `${rule.symbol} 价格跌破 ${rule.threshold} 元`;
        case 'portfolio_drop_percent': return `持仓市值缩水超过 ${rule.threshold}%`;
        default: return rule.rule_type;
    }
}

async function saveSettings(formData) {
    try {
        await api('/api/settings', { method: 'PUT', body: JSON.stringify(formData) });
        showToast('设置已保存', 'success');
        await loadSettings();
    } catch (error) {
        showToast('保存失败: ' + error.message, 'error');
    }
}

async function testEmail() {
    try {
        const result = await api('/api/settings/test-email', { method: 'POST' });
        if (result.success) showToast('测试邮件已发送', 'success');
        else showToast('发送失败: ' + result.message, 'error');
    } catch (error) {
        showToast('测试失败: ' + error.message, 'error');
    }
}

function copyToken() {
    const token = document.getElementById('mcp-token').value;
    navigator.clipboard.writeText(token).then(() => showToast('Token 已复制', 'success'));
}

// Notification Rules
function showAddRuleModal() {
    document.getElementById('rule-modal-title').textContent = '添加通知规则';
    document.getElementById('rule-form').reset();
    document.getElementById('rule-id').value = '';
    document.getElementById('rule-modal').classList.add('active');
}

async function saveRule(event) {
    event.preventDefault();
    const id = document.getElementById('rule-id').value;
    const data = {
        name: document.getElementById('rule-name').value.trim(),
        rule_type: document.getElementById('rule-type').value,
        symbol: document.getElementById('rule-symbol').value.trim(),
        threshold: parseFloat(document.getElementById('rule-threshold').value) || 0,
        email_subject: document.getElementById('rule-subject').value.trim(),
        email_template: document.getElementById('rule-template').value.trim(),
        recipients: document.getElementById('rule-recipients').value.trim(),
        active: true
    };

    try {
        if (id) {
            await api(`/api/notifications/rules/${id}`, { method: 'PUT', body: JSON.stringify(data) });
            showToast('规则已更新', 'success');
        } else {
            await api('/api/notifications/rules', { method: 'POST', body: JSON.stringify(data) });
            showToast('规则已添加', 'success');
        }
        closeModal('rule-modal');
        await loadSettings();
    } catch (error) {
        showToast('保存失败: ' + error.message, 'error');
    }
    return false;
}

async function toggleRule(id) {
    try {
        await api(`/api/notifications/rules/${id}/toggle`, { method: 'POST' });
        await loadSettings();
    } catch (error) {
        showToast('操作失败: ' + error.message, 'error');
    }
}

async function deleteRule(id) {
    if (!confirm('确定要删除这个规则吗？')) return;
    try {
        await api(`/api/notifications/rules/${id}`, { method: 'DELETE' });
        showToast('规则已删除', 'success');
        await loadSettings();
    } catch (error) {
        showToast('删除失败: ' + error.message, 'error');
    }
}

// Holdings CRUD
function showAddHoldingModal() {
    document.getElementById('holding-modal-title').textContent = '添加持仓';
    document.getElementById('holding-form').reset();
    document.getElementById('holding-id').value = '';
    document.getElementById('holding-modal').classList.add('active');
}

async function saveHolding(event) {
    event.preventDefault();
    const id = document.getElementById('holding-id').value;
    const symbol = document.getElementById('holding-symbol').value.trim();
    const name = document.getElementById('holding-name').value.trim();
    const quantity = parseFloat(document.getElementById('holding-quantity').value);
    const cost_price = parseFloat(document.getElementById('holding-cost').value);

    if (!symbol || !quantity || !cost_price) {
        showToast('请填写完整信息', 'error');
        return false;
    }

    // Validate stock code format
    if (!/^(sh|sz)\.\d{6}$/.test(symbol)) {
        showToast('股票代码格式错误，应为 sh.600000 或 sz.000001', 'error');
        return false;
    }

    // Close modal immediately and show success
    closeModal('holding-modal');
    
    if (id) {
        showToast('持仓已更新', 'success');
    } else {
        showToast('持仓已添加', 'success');
    }
    
    // Update UI immediately
    if (state.currentTab === 'holdings') {
        await loadHoldings();
    }
    
    // Perform API call in background
    try {
        if (id) {
            await api(`/api/holdings/${id}`, { method: 'PUT', body: JSON.stringify({ symbol, name, quantity, cost_price }) });
        } else {
            await api('/api/holdings', { method: 'POST', body: JSON.stringify({ symbol, name, quantity, cost_price }) });
        }
        
        // Refresh data in background
        setTimeout(async () => {
            try {
                await api('/api/holdings/refresh-prices', { method: 'POST' });
                await loadTabData(state.currentTab);
            } catch (e) {
                console.log('Background refresh failed:', e);
            }
        }, 100);
    } catch (error) {
        showToast('保存失败: ' + error.message, 'error');
        await loadTabData(state.currentTab);
    }
    return false;
}

// Delete holding with immediate UI update
async function deleteHolding(id) {
    if (!confirm('确定要删除这个持仓吗？')) return;
    
    // Store current state for rollback
    const previousHoldings = [...state.holdings];
    
    // Update UI immediately (optimistic update)
    state.holdings = state.holdings.filter(h => h.id !== id);
    if (state.currentTab === 'holdings') {
        renderHoldings(state.holdings);
    }
    showToast('持仓已删除', 'success');
    
    // Perform API call in background
    try {
        await api(`/api/holdings/${id}`, { method: 'DELETE' });
        
        // Refresh other data in background
        setTimeout(async () => {
            try {
                await loadTabData(state.currentTab);
            } catch (e) {
                console.log('Background refresh failed:', e);
            }
        }, 100);
    } catch (error) {
        // Rollback on error
        state.holdings = previousHoldings;
        if (state.currentTab === 'holdings') {
            renderHoldings(state.holdings);
        }
        showToast('删除失败: ' + error.message, 'error');
    }
}

// Modal helpers
function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

// Utility functions
function formatCurrency(value) {
    if (value === null || value === undefined) return '¥0.00';
    const num = typeof value === 'string' ? parseFloat(value) : value;
    return `¥${num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatNumber(value) {
    if (value === null || value === undefined) return '0';
    return value.toLocaleString('zh-CN');
}

function formatDate(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' });
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Stock search autocomplete
let searchTimeout = null;

async function searchStocks(query) {
    if (query.length < 1) return [];
    
    try {
        const response = await fetch(`/api/stocks?q=${encodeURIComponent(query)}`);
        if (response.ok) {
            return await response.json();
        }
    } catch (error) {
        console.error('Stock search error:', error);
    }
    return [];
}

function initStockSearch() {
    const searchInputs = document.querySelectorAll('.stock-search-input');
    searchInputs.forEach(input => {
        const resultsDiv = document.createElement('div');
        resultsDiv.className = 'search-results';
        input.parentElement.style.position = 'relative';
        input.parentElement.appendChild(resultsDiv);
        
        input.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            const query = e.target.value;
            
            if (query.length < 1) {
                resultsDiv.classList.remove('active');
                return;
            }
            
            searchTimeout = setTimeout(async () => {
                const results = await searchStocks(query);
                showSearchResults(resultsDiv, results, input);
            }, 300);
        });
        
        input.addEventListener('blur', (e) => {
            const relatedTarget = e.relatedTarget;
            if (relatedTarget && relatedTarget.closest('.search-results')) {
                return;
            }
            setTimeout(() => resultsDiv.classList.remove('active'), 150);
        });
        
        input.addEventListener('focus', () => {
            if (input.value.length > 0) {
                searchStocks(input.value).then(results => {
                    showSearchResults(resultsDiv, results, input);
                });
            }
        });
    });
}

function showSearchResults(container, results, input) {
    if (results.length === 0) {
        container.classList.remove('active');
        return;
    }
    
    container.innerHTML = results.map(s => `
        <div class="search-result-item" onmousedown="event.preventDefault(); selectStock('${input.id}', '${s.code}', '${s.name}')">
            <span class="search-result-symbol">${s.code}</span>
            <span class="search-result-name">${s.name}</span>
        </div>
    `).join('');
    
    container.classList.add('active');
}

function selectStock(inputId, code, name) {
    const input = document.getElementById(inputId);
    if (input) {
        input.value = code;
        input.dispatchEvent(new Event('input'));
    }
    
    const nameInput = document.getElementById(inputId.replace('-symbol', '-name'));
    if (nameInput) {
        nameInput.value = name;
    }
    
    document.querySelectorAll('.search-results').forEach(div => {
        div.classList.remove('active');
    });
}

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initStockSearch();
    
    document.querySelectorAll('.theme-btn').forEach(btn => {
        btn.addEventListener('click', () => setTheme(btn.dataset.theme));
    });
    
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.addEventListener('click', () => switchTab(tab.dataset.tab));
    });

    document.getElementById('btn-refresh').addEventListener('click', refreshPrices);

    document.getElementById('smtp-form')?.addEventListener('submit', (e) => {
        e.preventDefault();
        saveSettings({
            smtp_host: document.getElementById('smtp-host').value.trim(),
            smtp_port: parseInt(document.getElementById('smtp-port').value) || 587,
            smtp_user: document.getElementById('smtp-user').value.trim(),
            smtp_password: document.getElementById('smtp-password').value,
            smtp_from: document.getElementById('smtp-from').value.trim(),
            smtp_to: document.getElementById('smtp-to').value.trim(),
            smtp_use_tls: true,
        });
    });

    document.getElementById('baostock-form')?.addEventListener('submit', (e) => {
        e.preventDefault();
        saveSettings({
            baostock_username: document.getElementById('bao-username').value.trim(),
            baostock_password: document.getElementById('bao-password').value,
        });
    });

    document.getElementById('polling-form')?.addEventListener('submit', (e) => {
        e.preventDefault();
        const interval = parseInt(document.getElementById('polling-interval').value) || 300;
        api('/api/polling/config', { method: 'POST', body: JSON.stringify({ interval }) })
            .then(() => { showToast('轮询配置已保存', 'success'); loadSettings(); })
            .catch(error => showToast('保存失败: ' + error.message, 'error'));
    });

    document.getElementById('dividend-stats-form')?.addEventListener('submit', (e) => {
        e.preventDefault();
        const receivedYears = parseInt(document.getElementById('received-years').value) || 3;
        const expectedYears = parseInt(document.getElementById('expected-years').value) || 1;
        
        api('/api/settings', { 
            method: 'PUT', 
            body: JSON.stringify({ 
                received_years: receivedYears, 
                expected_years: expectedYears 
            }) 
        })
            .then(() => { 
                showToast('分红统计设置已保存', 'success'); 
                loadDashboard();
            })
            .catch(error => showToast('保存失败: ' + error.message, 'error'));
    });

    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.classList.remove('active');
        });
    });

    loadDashboard();
});
