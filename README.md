# Moomoo Trading Dashboard

A modern web dashboard for visualizing and analyzing your moomoo trading data with interactive charts, tables, and real-time data synchronization.

## Features

- 📊 **Interactive Dashboard** - Overview of trading performance with key metrics
- 📈 **Data Visualizations** - Charts for trading volume, portfolio allocation
- 📋 **Data Tables** - Detailed views of trades, orders, and positions
- 🔄 **Real-time Sync** - Refresh data directly from moomoo API
- 📅 **Date Filtering** - Filter data by custom date ranges
- 🐳 **Docker Support** - Easy deployment with Docker containers

## Prerequisites

- Python 3.9 or higher
- moomoo OpenD running locally (for API access)
- Active moomoo trading account

## Quick Start

### Option 1: Local Development

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your moomoo configuration
   ```

3. **Run the application**:
   ```bash
   python run_local.py
   ```

4. **Access the dashboard**:
   Open http://localhost:5000 in your browser

### Option 2: Docker (Recommended for Production)

1. **Build and run with Docker Compose**:
   ```bash
   docker-compose up --build
   ```

2. **Access the dashboard**:
   Open http://localhost:5000 in your browser

## Configuration

### Environment Variables

Create a `.env` file with the following configuration:

```bash
# Moomoo API Configuration
MOOMOO_HOST=127.0.0.1
MOOMOO_PORT=11111
MOOMOO_SECURITY_FIRM=FUTUSG  # or FUTUHK, FUTUUS
MOOMOO_TRADE_MARKET=US       # or HK, CN

# Database
DATABASE_URL=sqlite:///moomoo_trading.db

# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True
```

### Moomoo OpenD Setup

Make sure moomoo OpenD is running on your system:

1. Download and install moomoo OpenD
2. Start OpenD and ensure it's listening on the configured host/port
3. Verify your trading account is connected

## API Endpoints

The dashboard provides a REST API for accessing your trading data:

- `GET /api/trades` - Get trades with filtering options
- `GET /api/orders` - Get orders with filtering options
- `GET /api/positions` - Get current positions
- `GET /api/dashboard-stats` - Get dashboard statistics
- `POST /api/refresh-data` - Sync fresh data from moomoo API

### Query Parameters

- `start_date` - Filter from date (YYYY-MM-DD)
- `end_date` - Filter to date (YYYY-MM-DD)
- `code` - Filter by stock symbol
- `page` - Page number for pagination
- `per_page` - Items per page (default: 100)

## Database Schema

The application uses SQLite to store:

- **Trades** - Historical trade executions
- **Orders** - Order history and status
- **Positions** - Current portfolio positions

Data is automatically synced from your moomoo account and can be refreshed via the web interface.

## Development

### Project Structure

```
├── app.py              # Flask application
├── models.py           # Database models
├── api_routes.py       # API endpoints
├── data_sync.py        # moomoo API integration
├── run_local.py        # Local development runner
├── static/             # Frontend assets
│   ├── index.html      # Dashboard UI
│   └── dashboard.js    # Frontend JavaScript
├── requirements.txt    # Python dependencies
├── Dockerfile         # Docker configuration
└── docker-compose.yml # Docker Compose setup
```

### Adding New Features

1. **Backend**: Add new API endpoints in `api_routes.py`
2. **Database**: Modify models in `models.py`
3. **Frontend**: Update `static/dashboard.js` and `static/index.html`
4. **Data Sync**: Extend `data_sync.py` for new moomoo API calls

## Deployment

### Cloud Deployment

The application can be deployed to any platform that supports Docker:

- **AWS ECS/Fargate**
- **Google Cloud Run**
- **Azure Container Instances**
- **Digital Ocean App Platform**
- **Heroku** (with Docker stack)

### Environment Setup for Production

1. Set `FLASK_ENV=production`
2. Use a persistent volume for the SQLite database
3. Configure proper networking for moomoo OpenD access
4. Set up SSL/TLS termination if needed

## Troubleshooting

### Common Issues

1. **Can't connect to moomoo API**
   - Ensure OpenD is running and accessible
   - Check host/port configuration in `.env`
   - Verify firewall settings

2. **Database errors**
   - Delete the database file to reset
   - Run database initialization manually

3. **Permission errors**
   - Check file permissions for database directory
   - Ensure Python has write access to app directory

### Logs

- Application logs: Check console output
- Docker logs: `docker-compose logs -f`

## License

This project is for personal use with moomoo trading accounts. Please review moomoo's API terms of service.

## Support

For issues or questions:
1. Check existing Excel exports to verify data format
2. Ensure moomoo OpenD connectivity
3. Review application logs for detailed error messages