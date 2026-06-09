# Wealth Manager

A comprehensive wealth management application for tracking stock holdings, dividends, and dividend calendar with mobile-friendly UI.

## Features

- 📊 **Portfolio Tracking**: Track holdings with cost, quantity, and real-time market value
- 💰 **Dividend Calendar**: View upcoming dividend payments and expected amounts
- 📈 **Dividend Yield**: Calculate dividend yield for each holding
- 🎯 **Payback Progress**: Track how much of your investment has been recovered through dividends
- 📧 **Email Notifications**: Get notified before dividend payments via SMTP
- 🤖 **MCP API**: RESTful API with authorization header for LLM integration
- 📱 **Mobile-Friendly**: Responsive design optimized for mobile devices

## Tech Stack

- **Backend**: FastAPI + SQLite
- **Frontend**: Modular HTML/CSS/JavaScript (vanilla, no framework)
- **Stock Data**: BaoStock (baostock package)
- **Package Manager**: UV

## Quick Start

### Run with UV

```bash
cd /root/wealth-manager
uv sync
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Run with UVX (from Git)

After pushing to a Git repository:

```bash
uvx --from git+https://github.com/yourusername/wealth-manager.git wealth-manager
```

## Project Structure

```
wealth-manager/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry
│   ├── config.py            # Configuration management
│   ├── database.py          # SQLite database setup
│   ├── models/              # Data models
│   │   ├── __init__.py
│   │   ├── holding.py       # Holding model
│   │   └── dividend.py      # Dividend model
│   ├── services/            # Business logic
│   │   ├── __init__.py
│   │   ├── baostock_service.py  # BaoStock integration
│   │   ├── dividend_service.py  # Dividend calculations
│   │   └── email_service.py     # SMTP notifications
│   ├── api/                 # API routes
│   │   ├── __init__.py
│   │   ├── holdings.py      # Holdings CRUD
│   │   ├── dividends.py     # Dividend endpoints
│   │   ├── mcp.py           # MCP/LLM API
│   │   └── settings.py      # Settings management
│   └── templates/
│       └── index.html       # Main HTML template
├── static/
│   ├── css/
│   │   └── style.css        # Main stylesheet
│   └── js/
│       ├── app.js           # Main app module
│       ├── holdings.js      # Holdings management
│       ├── dividends.js     # Dividend management
│       └── calendar.js      # Calendar component
├── tests/                   # Test suite
├── data/                    # SQLite database
└── pyproject.toml           # Project configuration
```

## API Endpoints

### Holdings
- `GET /api/holdings` - List all holdings
- `POST /api/holdings` - Add a new holding
- `PUT /api/holdings/{id}` - Update a holding
- `DELETE /api/holdings/{id}` - Delete a holding

### Dividends
- `GET /api/dividends` - List all dividends
- `GET /api/dividends/calendar` - Get dividend calendar
- `POST /api/dividends` - Add a dividend record
- `GET /api/dividends/stats` - Dividend statistics

### MCP (LLM Integration)
- `GET /mcp/holdings` - Get holdings (requires Authorization header)
- `GET /mcp/dividends` - Get dividends (requires Authorization header)
- `GET /mcp/calendar` - Get dividend calendar (requires Authorization header)
- `POST /mcp/holdings` - Add/update holding (requires Authorization header)

### Settings
- `GET /api/settings` - Get settings
- `PUT /api/settings` - Update settings
- `POST /api/settings/test-email` - Test email configuration

## Configuration

Settings are stored in the database and can be managed via the API or web UI.

| Key | Description | Default |
|-----|-------------|---------|
| `mcp_token` | Authorization token for MCP API | (generated on first run) |
| `smtp_host` | SMTP server host | (empty) |
| `smtp_port` | SMTP server port | 587 |
| `smtp_user` | SMTP username | (empty) |
| `smtp_password` | SMTP password | (empty) |
| `smtp_from` | From email address | (empty) |
| `smtp_to` | To email address | (empty) |

## License

MIT
