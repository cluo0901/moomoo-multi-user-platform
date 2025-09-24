class MoomooDashboard {
    constructor() {
        this.baseURL = window.location.origin;
        this.volumeChart = null;
        this.allocationChart = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setDefaultDates();
        this.loadDashboard();
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
                method: 'POST'
            });
            const result = await response.json();

            if (result.status === 'success') {
                alert(`Data refreshed successfully! Synced ${result.synced_counts.trades} trades, ${result.synced_counts.orders} orders, ${result.synced_counts.positions} positions.`);
                this.loadDashboard();
            } else {
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
            const response = await fetch(`${this.baseURL}/api/dashboard-stats?${params}`);
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
            const response = await fetch(`${this.baseURL}/api/trades?${params}`);
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
            const response = await fetch(`${this.baseURL}/api/orders?${params}`);
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
            const response = await fetch(`${this.baseURL}/api/positions`);
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
}

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', () => {
    new MoomooDashboard();
});