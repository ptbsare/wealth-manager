# Wealth Manager

A comprehensive wealth management application for tracking stock holdings, dividends, and dividend calendar with mobile-friendly UI.

## Features

- 📊 **Portfolio Tracking**: Track holdings with cost, quantity, and real-time market value
- 💰 **Dividend Calendar**: View upcoming dividend payments with color-coded dates (🔵Record, 🟠Ex-dividend, 🟢Pay)
- 📈 **Dividend Yield**: Calculate dividend yield for each holding
- 🎯 **Payback Progress**: Track how much of your investment has been recovered through dividends
- 📧 **Email Notifications**: Get notified before dividend payments via SMTP
- 🤖 **MCP API**: RESTful API with authorization header for LLM integration
- 📱 **Mobile-Friendly**: Responsive design optimized for mobile devices
- 🌓 **Theme Support**: Light, dark, and auto themes
- ⚡ **Caching**: Dividend data cached for 24 hours for fast loading

## Tech Stack

- **Backend**: FastAPI + SQLite
- **Frontend**: Modular HTML/CSS/JavaScript (vanilla, no framework)
- **Stock Data**: BaoStock (baostock package)
- **Package Manager**: UV

## Quick Start

### Run with UV

```bash
git clone https://github.com/ptbsare/wealth-manager.git
cd wealth-manager
uv sync --extra dev
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then open http://localhost:8000 in your browser.

## Project Structure

```
wealth-manager/
├── app/                    # Application code
│   ├── api/               # API routes
│   ├── models/            # Data models
│   ├── services/          # Business logic
│   └── templates/         # HTML templates
├── static/                # Static files
│   ├── css/style.css
│   ├── js/app.js
│   └── manifest.json
├── tests/                 # Test suite (54 tests)
├── data/cache/            # Cached dividend data
├── pyproject.toml         # UV project configuration
├── LICENSE                # GPLv3 License
└── README.md              # This file
```

## API Endpoints

### Holdings
- `GET /api/holdings` - List all holdings
- `POST /api/holdings` - Add a new holding
- `PUT /api/holdings/{id}` - Update a holding
- `DELETE /api/holdings/{id}` - Delete a holding

### Dividends
- `GET /api/dividends/calendar` - Get dividend calendar
- `POST /api/dividends/fetch-from-baostock` - Auto-fetch dividends

### Settings
- `GET /api/settings` - Get settings
- `PUT /api/settings` - Update settings

### MCP (LLM Integration)
- `GET /mcp/holdings` - Get holdings (requires Authorization header)
- `GET /mcp/dividends` - Get dividends
- `GET /mcp/calendar` - Get dividend calendar

## License

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

See [LICENSE](LICENSE) for the full license text.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Disclaimer

This software is for educational and research purposes only. 
Stock data is provided by BaoStock. Always verify data independently 
before making investment decisions.
