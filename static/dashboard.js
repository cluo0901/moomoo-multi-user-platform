class MoomooDashboard {
    constructor() {
        this.baseURL = window.location.origin;
        this.volumeChart = null;
        this.allocationChart = null;
        this.authToken = localStorage.getItem('auth_token');
        this.userInfo = JSON.parse(localStorage.getItem('user_info') || '{}');
        this.csrfToken = this.extractCSRFFromToken();
        this.init();
    }

    // Extract CSRF token from JWT payload for API calls
    extractCSRFFromToken() {
        try {
            if (!this.authToken) return null;
            const payload = this.authToken.split('.')[1];
            const paddedPayload = payload + '='.repeat((4 - payload.length % 4) % 4);
            const decoded = JSON.parse(atob(paddedPayload));
            return decoded.csrf || null;
        } catch (error) {
            console.error('Error extracting CSRF token:', error);
            return null;
        }
    }

    init() {
        // Check authentication first
        if (!this.authToken) {
            window.location.href = '/static/auth.html';
            return;
        }

        this.setupEventListeners();
        this.setDefaultDates();
        this.setupUserInfo();
        this.loadDashboard();
    }

    setupUserInfo() {
        // Add user info to header if we have it
        if (this.userInfo.username) {
            const header = document.querySelector('h1');
            if (header) {
                header.innerHTML = `
                    <div class="flex items-center justify-between w-full">
                        <span>Moomoo Trading Dashboard</span>
                        <div class="flex items-center space-x-4 text-sm">
                            <span class="text-gray-600">Welcome, ${this.userInfo.username}</span>
                            <button id="userMenu" class="bg-gray-200 hover:bg-gray-300 px-3 py-1 rounded-lg">
                                Account
                            </button>
                            <button id="logoutBtn" class="bg-red-500 hover:bg-red-600 text-white px-3 py-1 rounded-lg">
                                Logout
                            </button>
                        </div>
                    </div>
                `;

                // Add logout functionality
                document.getElementById('logoutBtn').addEventListener('click', () => {
                    this.logout();
                });
            }
        }
    }

    logout() {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user_info');
        window.location.href = '/static/auth.html';
    }

    getAuthHeaders() {
        const headers = {
            'Authorization': `Bearer ${this.authToken}`,
            'Content-Type': 'application/json'
        };

        // Add CSRF token for Flask-JWT-Extended compatibility
        if (this.csrfToken) {
            headers['X-CSRF-TOKEN'] = this.csrfToken;
        }

        return headers;
    }

    setupEventListeners() {
        document.getElementById('refreshBtn').addEventListener('click', () => {
            this.refreshData();
        });

        document.getElementById('filterBtn').addEventListener('click', () => {
            this.loadDashboard();
        });

        document.getElementById('viewAllTrades').addEventListener('click', () => {
            this.showModal('trades');
        });

        document.getElementById('viewAllPositions').addEventListener('click', () => {
            this.showModal('positions');
        });

        document.getElementById('viewAllOrders').addEventListener('click', () => {
            this.showModal('orders');
        });

        // Settings modal events
        document.getElementById('settingsBtn').addEventListener('click', () => {
            this.openSettingsModal();
        });
        document.getElementById('closeSettingsBtn').addEventListener('click', () => {
            this.closeSettingsModal();
        });
        document.getElementById('cancelSettingsBtn').addEventListener('click', () => {
            this.closeSettingsModal();
        });
        document.getElementById('credentialsForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveCredentials();
        });

        // Logout functionality
        document.getElementById('logoutBtn').addEventListener('click', () => {
            this.logout();
        });
    }

    setDefaultDates() {
        const endDate = new Date();
        const startDate = new Date();
        startDate.setDate(endDate.getDate() - 30);

        document.getElementById('endDate').value = endDate.toISOString().split('T')[0];
        document.getElementById('startDate').value = startDate.toISOString().split('T')[0];
    }

    showLoading(show = true) {
        const spinner = document.getElementById('loadingSpinner');
        spinner.classList.toggle('hidden', !show);
    }

    formatCurrency(value) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2
        }).format(value || 0);
    }

    formatNumber(value) {
        return new Intl.NumberFormat('en-US').format(value || 0);
    }

    formatDate(dateString) {
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    getCurrencyFromCode(stockCode) {
        const currencyMap = {
            'US.': 'USD',
            'HK.': 'HKD',
            'SG.': 'SGD',
            'SH.': 'CNY',
            'SZ.': 'CNY',
            'JP.': 'JPY',
            'AU.': 'AUD',
            'CA.': 'CAD',
            'MY.': 'MYR'
        };

        for (const [prefix, currency] of Object.entries(currencyMap)) {
            if (stockCode.startsWith(prefix)) {
                return currency;
            }
        }
        return 'USD'; // Default
    }

    formatCurrencyWithOriginal(value, stockCode, showOriginal = false) {
        const currency = this.getCurrencyFromCode(stockCode);

        if (showOriginal && currency !== 'USD') {
            // Show both original and USD equivalent
            const rates = { USD: 1.0, HKD: 7.8, SGD: 1.35, CNY: 7.2, JPY: 150.0, AUD: 1.5, CAD: 1.35, MYR: 4.7 };
            const rate = rates[currency] || 1.0;
            const originalValue = value * rate;

            return `$${value.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                    <span class="text-xs text-gray-500">(${originalValue.toLocaleString()} ${currency})</span>`;
        }

        return this.formatCurrency(value);
    }

    async refreshData() {
        this.showLoading(true);
        try {
            const response = await fetch(`${this.baseURL}/api/refresh-data`, {
                method: 'POST',
                headers: this.getAuthHeaders()
            });
            const result = await response.json();

            if (result.status === 'success') {
                alert(`Data refreshed successfully! Synced ${result.synced_counts.trades} trades, ${result.synced_counts.orders} orders, ${result.synced_counts.positions} positions.`);
                this.loadDashboard();
            } else {
                if (response.status === 401) {
                    this.logout();
                    return;
                }
                alert(`Error refreshing data: ${result.message || result.error}`);
            }
        } catch (error) {
            console.error('Error refreshing data:', error);
            alert('Error refreshing data. Please try again.');
        } finally {
            this.showLoading(false);
        }
    }

    async loadDashboard() {
        this.showLoading(true);
        try {
            const startDate = document.getElementById('startDate').value;
            const endDate = document.getElementById('endDate').value;

            // Load dashboard stats
            await this.loadDashboardStats(startDate, endDate);

            // Load current positions (moved to top)
            await this.loadCurrentPositions();

            // Load recent trades
            await this.loadRecentTrades(startDate, endDate);

            // Load recent orders
            await this.loadRecentOrders(startDate, endDate);

        } catch (error) {
            console.error('Error loading dashboard:', error);
        } finally {
            this.showLoading(false);
        }
    }

    async loadDashboardStats(startDate, endDate) {
        try {
            const params = new URLSearchParams({ start_date: startDate, end_date: endDate });
            const response = await fetch(`${this.baseURL}/api/dashboard-stats?${params}`, {
                headers: this.getAuthHeaders()
            });
            const data = await response.json();

            // Update stats cards
            document.getElementById('totalTrades').textContent = this.formatNumber(data.trades_stats.total_trades);
            document.getElementById('totalVolume').textContent = this.formatCurrency(data.trades_stats.total_volume);
            document.getElementById('totalPositions').textContent = this.formatNumber(data.positions_stats.total_positions);
            document.getElementById('unrealizedPL').textContent = this.formatCurrency(data.positions_stats.total_unrealized_pl);

            // Update volume chart
            this.updateVolumeChart(data.daily_volumes);

        } catch (error) {
            console.error('Error loading dashboard stats:', error);
        }
    }

    updateVolumeChart(dailyVolumes) {
        const ctx = document.getElementById('volumeChart').getContext('2d');

        if (this.volumeChart) {
            this.volumeChart.destroy();
        }

        this.volumeChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: dailyVolumes.map(d => new Date(d.date).toLocaleDateString()),
                datasets: [{
                    label: 'Trading Volume',
                    data: dailyVolumes.map(d => d.volume),
                    borderColor: 'rgb(59, 130, 246)',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return '$' + value.toLocaleString();
                            }
                        }
                    }
                }
            }
        });
    }

    async loadRecentTrades(startDate, endDate) {
        try {
            const params = new URLSearchParams({
                start_date: startDate,
                end_date: endDate,
                per_page: 10
            });
            const response = await fetch(`${this.baseURL}/api/trades?${params}`, {
                headers: this.getAuthHeaders()
            });
            const data = await response.json();

            const tbody = document.getElementById('tradesTable');
            tbody.innerHTML = '';

            data.trades.forEach(trade => {
                const row = document.createElement('tr');
                row.className = 'border-b hover:bg-gray-50';

                const sideClass = trade.side === 'BUY' ? 'text-green-600' : 'text-red-600';

                row.innerHTML = `
                    <td class="px-4 py-2">${this.formatDate(trade.deal_time)}</td>
                    <td class="px-4 py-2 font-semibold">${trade.code}</td>
                    <td class="px-4 py-2 ${sideClass}">${trade.side}</td>
                    <td class="px-4 py-2 text-right">${this.formatNumber(trade.qty)}</td>
                    <td class="px-4 py-2 text-right">${this.formatCurrency(trade.price)}</td>
                    <td class="px-4 py-2 text-right">${this.formatCurrency(trade.val)}</td>
                `;

                tbody.appendChild(row);
            });

        } catch (error) {
            console.error('Error loading recent trades:', error);
        }
    }

    async loadRecentOrders(startDate, endDate) {
        try {
            const params = new URLSearchParams({
                start_date: startDate,
                end_date: endDate,
                per_page: 10
            });
            const response = await fetch(`${this.baseURL}/api/orders?${params}`, {
                headers: this.getAuthHeaders()
            });
            const data = await response.json();

            const tbody = document.getElementById('ordersTable');
            tbody.innerHTML = '';

            data.orders.forEach(order => {
                const row = document.createElement('tr');
                row.className = 'border-b hover:bg-gray-50';

                const sideClass = order.trd_side === 'BUY' ? 'text-green-600' : 'text-red-600';
                const statusClass = this.getOrderStatusClass(order.order_status);
                const fillPercent = order.qty > 0 ? ((order.dealt_qty || 0) / order.qty * 100).toFixed(1) : 0;

                row.innerHTML = `
                    <td class="px-4 py-2">${this.formatDate(order.create_time)}</td>
                    <td class="px-4 py-2 font-semibold">${order.code}</td>
                    <td class="px-4 py-2 ${sideClass}">${order.trd_side}</td>
                    <td class="px-4 py-2">
                        <span class="px-2 py-1 text-xs rounded-full ${statusClass}">
                            ${order.order_status}
                        </span>
                    </td>
                    <td class="px-4 py-2 text-right">${this.formatNumber(order.qty)}</td>
                    <td class="px-4 py-2 text-right">${order.price ? this.formatCurrency(order.price) : 'Market'}</td>
                    <td class="px-4 py-2 text-right">
                        <span class="text-sm">
                            ${this.formatNumber(order.dealt_qty || 0)} (${fillPercent}%)
                        </span>
                    </td>
                `;

                tbody.appendChild(row);
            });

        } catch (error) {
            console.error('Error loading recent orders:', error);
        }
    }

    getOrderStatusClass(status) {
        const statusClasses = {
            'FILLED_ALL': 'bg-green-100 text-green-800',
            'FILLED_PART': 'bg-yellow-100 text-yellow-800',
            'SUBMITTED': 'bg-blue-100 text-blue-800',
            'WAITING_SUBMIT': 'bg-blue-100 text-blue-800',
            'CANCELLED_ALL': 'bg-red-100 text-red-800',
            'CANCELLED_PART': 'bg-red-100 text-red-800',
            'FAILED': 'bg-red-100 text-red-800',
            'DISABLED': 'bg-gray-100 text-gray-800'
        };
        return statusClasses[status] || 'bg-gray-100 text-gray-800';
    }

    async loadCurrentPositions() {
        try {
            const response = await fetch(`${this.baseURL}/api/positions`, {
                headers: this.getAuthHeaders()
            });
            const data = await response.json();

            const tbody = document.getElementById('positionsTable');
            tbody.innerHTML = '';

            // Prepare data for allocation chart
            const allocationData = data.positions
                .filter(pos => pos.market_val > 0)
                .sort((a, b) => b.market_val - a.market_val)
                .slice(0, 10); // Top 10 positions

            data.positions.forEach(position => {
                const row = document.createElement('tr');
                row.className = 'border-b hover:bg-gray-50';

                const plClass = (position.unrealized_pl || 0) >= 0 ? 'text-green-600' : 'text-red-600';

                row.innerHTML = `
                    <td class="px-4 py-2 font-semibold">${position.code}</td>
                    <td class="px-4 py-2">${position.stock_name || '-'}</td>
                    <td class="px-4 py-2 text-right">${this.formatNumber(position.qty)}</td>
                    <td class="px-4 py-2 text-right">${this.formatCurrency(position.market_val)}</td>
                    <td class="px-4 py-2 text-right ${plClass}">${this.formatCurrency(position.unrealized_pl)}</td>
                    <td class="px-4 py-2 text-right ${plClass}">${((position.unrealized_pl_ratio || 0) * 100).toFixed(2)}%</td>
                `;

                tbody.appendChild(row);
            });

            // Update allocation chart
            this.updateAllocationChart(allocationData);

        } catch (error) {
            console.error('Error loading current positions:', error);
        }
    }

    updateAllocationChart(positions) {
        const ctx = document.getElementById('allocationChart').getContext('2d');

        if (this.allocationChart) {
            this.allocationChart.destroy();
        }

        const colors = [
            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
            '#FF9F40', '#FF6384', '#C9CBCF', '#4BC0C0', '#FF6384'
        ];

        this.allocationChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: positions.map(pos => pos.code),
                datasets: [{
                    data: positions.map(pos => pos.market_val),
                    backgroundColor: colors,
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'right',
                    }
                }
            }
        });
    }

    showModal(type) {
        // This would open a modal with full data table
        // For now, just alert
        alert(`Opening full ${type} view... (Feature to be implemented)`);
    }

    openSettingsModal() {
        const modal = document.getElementById('settingsModal');
        modal.classList.remove('hidden');

        // Reset form and hide status messages
        this.clearSettingsForm();
        this.hideSettingsMessages();
    }

    closeSettingsModal() {
        const modal = document.getElementById('settingsModal');
        modal.classList.add('hidden');

        // Reset form
        this.clearSettingsForm();
        this.hideSettingsMessages();
    }

    clearSettingsForm() {
        // Reset form fields to defaults
        document.getElementById('moomooHost').value = '127.0.0.1';
        document.getElementById('moomooPort').value = '11111';
        document.getElementById('securityFirm').value = 'FUTUSG';
        document.getElementById('tradeMarket').value = 'US';
        document.getElementById('moomooUsername').value = '';
        document.getElementById('moomooPassword').value = '';
    }

    hideSettingsMessages() {
        document.getElementById('credentialsStatus').classList.add('hidden');
        document.getElementById('credentialsSuccess').classList.add('hidden');
        document.getElementById('credentialsError').classList.add('hidden');
    }

    showSettingsSuccess(message) {
        document.getElementById('credentialsStatus').classList.remove('hidden');
        document.getElementById('credentialsSuccess').classList.remove('hidden');
        document.getElementById('credentialsError').classList.add('hidden');
        document.getElementById('successMessage').textContent = message;
    }

    showSettingsError(message) {
        document.getElementById('credentialsStatus').classList.remove('hidden');
        document.getElementById('credentialsError').classList.remove('hidden');
        document.getElementById('credentialsSuccess').classList.add('hidden');
        document.getElementById('errorMessage').textContent = message;
    }

    setCredentialsSaving(saving) {
        const btn = document.getElementById('saveCredentialsBtn');
        const text = document.getElementById('saveBtnText');
        const spinner = document.getElementById('saveBtnSpinner');

        btn.disabled = saving;

        if (saving) {
            text.classList.add('hidden');
            spinner.classList.remove('hidden');
        } else {
            text.classList.remove('hidden');
            spinner.classList.add('hidden');
        }
    }

    async refreshToken() {
        try {
            const response = await fetch(`${this.baseURL}/auth/refresh`, {
                method: 'POST',
                headers: this.getAuthHeaders()
            });

            if (response.ok) {
                const data = await response.json();
                this.authToken = data.access_token;
                localStorage.setItem('auth_token', data.access_token);
                return true;
            }
        } catch (error) {
            console.error('Token refresh failed:', error);
        }
        return false;
    }

    async makeAuthenticatedRequest(url, options = {}) {
        // First attempt
        let response = await fetch(url, {
            ...options,
            headers: {
                ...this.getAuthHeaders(),
                ...options.headers
            }
        });

        // If token expired, try to refresh and retry
        if (response.status === 401) {
            console.log('Token expired, attempting refresh...');

            // Try to login again with saved credentials or redirect to login
            this.showSettingsError('Session expired. Please login again.');
            setTimeout(() => {
                this.logout();
            }, 2000);
            return response;
        }

        return response;
    }

    async saveCredentials() {
        const formData = {
            moomoo_host: document.getElementById('moomooHost').value.trim(),
            moomoo_port: parseInt(document.getElementById('moomooPort').value),
            security_firm: document.getElementById('securityFirm').value,
            trade_market: document.getElementById('tradeMarket').value,
            moomoo_username: document.getElementById('moomooUsername').value.trim(),
            moomoo_password: document.getElementById('moomooPassword').value
        };

        // Validation
        if (!formData.moomoo_host || !formData.moomoo_port) {
            this.showSettingsError('Host and Port are required');
            return;
        }

        if (!formData.moomoo_username || !formData.moomoo_password) {
            this.showSettingsError('Moomoo username and password are required');
            return;
        }

        this.setCredentialsSaving(true);
        this.hideSettingsMessages();

        try {
            const response = await this.makeAuthenticatedRequest(`${this.baseURL}/auth/opend-config`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });

            const data = await response.json();

            if (response.ok) {
                this.showSettingsSuccess('Moomoo credentials configured successfully! Your container is being provisioned...');

                // Refresh user info after successful configuration
                setTimeout(() => {
                    this.closeSettingsModal();
                    this.loadDashboard(); // Refresh the dashboard
                }, 2000);

            } else if (response.status === 401) {
                // Token invalid - handled by makeAuthenticatedRequest
                return;
            } else {
                this.showSettingsError(data.error || 'Failed to configure credentials');
            }

        } catch (error) {
            console.error('Settings save error:', error);
            this.showSettingsError('Network error. Please try again.');
        } finally {
            this.setCredentialsSaving(false);
        }
    }

    logout() {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user_info');
        window.location.href = '/static/auth.html';
    }
}

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', () => {
    new MoomooDashboard();
});