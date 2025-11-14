# DOT - NYC Smart City Dashboard

A comprehensive Smart City Dashboard system for NYC DOT that integrates real-time traffic, transit, and air quality data with predictive congestion insights and an intuitive web interface.

## 🎯 Overview

DOT addresses NYC DOT's key challenges:
- **Reduce congestion** and improve commute times
- **Coordinate traffic** with transit and waste routes
- **Monitor environmental impact** of traffic
- **Predict future congestion** using ML-powered forecasting
- **Provide actionable insights** through AI-powered analysis

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      DOT System                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐         ┌──────────────────┐        │
│  │   Frontend       │◄────────┤    Backend API   │        │
│  │   (React)        │  HTTP   │   (FastAPI)       │        │
│  │                  │         │                   │        │
│  │  - Dashboard     │         │  - MCP Orchestrator│       │
│  │  - Maps          │         │  - Multi-Agent    │        │
│  │  - KPIs          │         │  - ML Predictions │        │
│  │  - AI Insights   │         │  - Data Ingestion │        │
│  └──────────────────┘         └────────┬──────────┘        │
│                                         │                    │
│                                         ▼                    │
│                              ┌──────────────────┐           │
│                              │    MongoDB       │           │
│                              │   (Data Store)   │           │
│                              └──────────────────┘           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Features

### Frontend Features
- **Real-time Dashboard**: Live monitoring of traffic congestion, air quality, and emergency response times
- **Interactive Maps**: Visual representation of traffic segments, zones, and incidents using Leaflet
- **Borough Filtering**: Filter data by NYC boroughs (Manhattan, Brooklyn, Queens, Bronx, Staten Island)
- **KPI Metrics**: Key performance indicators with trend analysis and sparkline charts
- **AI Insights**: AI-powered insights and predictions for traffic hotspots
- **Emergency Tracking**: Real-time emergency incident tracking with critical delay alerts
- **Mobile Health Camps**: Information about mobile health camps and their locations
- **Responsive Design**: Fully responsive UI that works on desktop, tablet, and mobile devices

### Backend Features
- **MCP Orchestrator Server**: Central hub for coordinating multi-agent workflows
- **Real-time Data Ingestion**: Automated ingestion from NYC DOT OpenData, MTA GTFS-Realtime, and Air Quality APIs
- **Multi-Agent System**: Three specialized agents for ingestion, cleaning, and prediction
- **ML Predictions**: Machine learning models for traffic congestion forecasting (15min and 30min windows)
- **RESTful API**: FastAPI-based REST API with automatic OpenAPI documentation
- **Data Validation**: Automated validation and quality checks
- **AI Explanations**: Hugging Face-powered explanations for traffic hotspots

## 🛠️ Tech Stack

### Frontend
- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Styling
- **Shadcn/ui** - UI component library
- **React Query** - Data fetching and caching
- **Leaflet** - Interactive maps
- **Recharts** - Data visualization

### Backend
- **FastAPI** - Modern Python web framework
- **MongoDB** - NoSQL database (via Motor async driver)
- **APScheduler** - Task scheduling for agents
- **Scikit-learn** - Machine learning models
- **Pandas & NumPy** - Data processing
- **Hugging Face** - AI explanations (optional)
- **Pydantic** - Data validation

## 📋 Prerequisites

### Frontend
- Node.js 18+ or Bun
- npm, yarn, or bun package manager

### Backend
- Python 3.10+
- MongoDB (local or Atlas)
- (Optional) API keys for:
  - MTA GTFS-Realtime
  - 511NY Traffic API
  - AirNow API
  - Hugging Face

## 🏃 Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd NYC-lifegaurd
```

### 2. Backend Setup

```bash
# Navigate to backend directory
cd Backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env  # Or create manually
# Edit .env with your MongoDB URI and API keys

# Start MongoDB (if using local)
# macOS: brew services start mongodb-community
# Linux: sudo systemctl start mongod
# Windows: net start MongoDB

# Run the API server
python -m app.main
# Or: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend API will be available at `http://localhost:8000`

### 3. Frontend Setup

```bash
# Navigate to frontend directory (in a new terminal)
cd frontend

# Install dependencies
npm install
# or
yarn install
# or
bun install

# Create .env file
echo "VITE_API_BASE_URL=http://localhost:8000" > .env

# Start development server
npm run dev
# or
yarn dev
# or
bun dev
```

The frontend will be available at `http://localhost:8080`

### 4. Verify Setup

1. **Backend Health Check**: Visit `http://localhost:8000/api/health`
2. **API Documentation**: Visit `http://localhost:8000/docs` (Swagger UI)
3. **Frontend Dashboard**: Visit `http://localhost:8080`

## 📁 Project Structure

```
NYC-lifegaurd/
├── Backend/                    # Backend API service
│   ├── app/
│   │   ├── agents/            # Multi-agent system
│   │   │   ├── agent1_ingestion.py    # Data ingestion
│   │   │   ├── agent2_cleaning.py     # Data cleaning & correlation
│   │   │   └── agent3_prediction.py   # ML prediction
│   │   ├── orchestrator/      # MCP Orchestrator Server
│   │   │   ├── mcp_server.py  # Central orchestration hub
│   │   │   └── README.md
│   │   ├── api/               # API routes
│   │   │   └── routes/
│   │   │       ├── segments.py
│   │   │       ├── zones.py
│   │   │       ├── predictions.py
│   │   │       ├── health.py
│   │   │       └── explain.py
│   │   ├── clients/           # External API clients
│   │   ├── ml/                # Machine learning
│   │   ├── services/          # Business logic
│   │   ├── models/            # Data models
│   │   ├── config.py          # Configuration
│   │   ├── database.py        # MongoDB connection
│   │   └── main.py            # FastAPI app
│   ├── scripts/               # Utility scripts
│   ├── models/                # Trained ML models
│   ├── requirements.txt
│   └── README.md
│
├── frontend/                   # Frontend React application
│   ├── src/
│   │   ├── components/        # React components
│   │   │   ├── MetricsGrid.tsx      # KPI dashboard
│   │   │   ├── InteractiveMap.tsx   # Map component
│   │   │   ├── EmergencyTracking.tsx
│   │   │   ├── AIInsightsPanel.tsx
│   │   │   └── ui/            # Shadcn/ui components
│   │   ├── lib/
│   │   │   ├── api.ts         # API client
│   │   │   └── utils.ts       # Utilities
│   │   ├── pages/
│   │   │   ├── Index.tsx      # Main dashboard
│   │   │   └── NotFound.tsx
│   │   └── main.tsx           # Entry point
│   ├── package.json
│   ├── vite.config.ts
│   └── README.md
│
└── README.md                   # This file
```

## 🔄 MCP Orchestrator System

The backend uses an **MCP Orchestrator Server** to coordinate a three-agent architecture:

```
                    MCP Orchestrator Server
                           (Central Hub)
                                |
        +-----------------------+-----------------------+
        |                       |                       |
    Schedule/            Run After              Run Forecast
    Run Cycles          Ingestion                  Jobs
        |                       |                       |
        v                       v                       v
   Agent 1:              Agent 2:              Agent 3:
   Ingestion        Cleaning & Correlation    Prediction Engine
   (30s cycle)      (After ingestion)         (5min cycle)
        |                       |                       |
   Store Raw              Store Processed        Store Predictions
   Records                Segments/Zones
```

### Agent 1: Data Ingestion
- Fetches data from external APIs (NYC DOT, MTA, Air Quality)
- Runs every 30 seconds (configurable)
- Sources: 511NY Traffic API, NYC DOT Open Data, MTA GTFS-RT
- Stores raw data in MongoDB

### Agent 2: Cleaning & Correlation
- Cleans and validates ingested data
- Correlates traffic, transit, and air quality data
- Runs automatically after ingestion + every 2 minutes
- Functions: Data Quality Checks, Fusion (Traffic + Transit)
- Creates aggregated zone data

### Agent 3: Prediction Engine
- Generates ML-powered congestion predictions
- 15-minute and 30-minute forecast windows
- Runs every 5 minutes
- Uses trained gradient boosting models

## 📡 API Endpoints

### Data Endpoints
- `GET /api/segments/current` - Get current traffic segments
- `GET /api/zones/current` - Get current traffic zones
- `GET /api/predictions` - Get congestion predictions
- `GET /api/predictions/{segment_id}` - Get predictions for segment

### Health & Monitoring
- `GET /api/health` - API health check
- `GET /api/health/validation` - Data validation metrics
- `POST /api/health/refresh` - Trigger data refresh

### Orchestrator Control
- `GET /api/orchestrator/status` - Get MCP Orchestrator status
- `POST /api/orchestrator/orchestrate` - Trigger full orchestration cycle
- `POST /api/orchestrator/ingestion` - Trigger Agent 1 manually
- `POST /api/orchestrator/cleaning` - Trigger Agent 2 manually
- `POST /api/orchestrator/forecast` - Trigger Agent 3 manually

### AI Explanations
- `GET /api/explain/hotspots` - AI explanations for traffic hotspots

## 🔧 Configuration

### Backend Environment Variables

Create `Backend/.env`:

```env
# MongoDB Configuration
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=smartcity_dashboard

# Environment
ENVIRONMENT=development
USE_MOCKS=True

# CORS Configuration (comma-separated)
CORS_ORIGINS=http://localhost:8080,http://localhost:3000,http://localhost:5173

# Optional API Keys
MTA_API_KEY=your_mta_key_here
NY511_API_KEY=your_511ny_key_here
AIRNOW_API_KEY=your_airnow_key_here
HUGGINGFACE_API_TOKEN=your_hf_token_here

# ML Configuration
ML_MODEL_TYPE=gradient_boosting
ML_MODEL_PATH=models/congestion_models
ML_TRAINING_HISTORY_DAYS=7

# Scheduling Intervals (seconds)
INGESTION_INTERVAL_TRAFFIC=30
INGESTION_INTERVAL_TRANSIT=60
INGESTION_INTERVAL_AIR_QUALITY=900

# Logging
LOG_LEVEL=INFO
DEBUG=False
```

### Frontend Environment Variables

Create `frontend/.env`:

```env
VITE_API_BASE_URL=http://localhost:8000
```

For production, set to your backend URL:
```env
VITE_API_BASE_URL=https://api.yourdomain.com
```

## 🧪 Testing & Development

### Backend Testing

```bash
cd Backend

# Run simulation (populate test data)
python scripts/run_simulation.py

# Test live ingestion
python scripts/test_live_ingestion.py

# Test prediction cycle
python scripts/test_prediction_cycle.py

# Train ML models
python scripts/train_models.py
```

### Frontend Development

```bash
cd frontend

# Run linting
npm run lint

# Build for production
npm run build

# Preview production build
npm run preview
```

## 📊 Data Sources

### NYC DOT OpenData (Public, No API Key Required)
- Traffic Speeds (NBE)
- Traffic Volume Counts
- Motor Vehicle Collisions
- Bus Breakdowns and Delays
- Air Quality Data
- 311 Service Requests

### MTA GTFS-Realtime (Optional API Key)
- Vehicle Positions
- Trip Updates
- Service Alerts

### 511NY Traffic API (Optional API Key)
- Real-time traffic incidents

### AirNow API (Optional API Key)
- Air quality observations

**Note**: The system works with mock data by default (`USE_MOCKS=True`), so API keys are optional for development.

## 🤖 Machine Learning

### Training Models

Train ML models using historical data:

```bash
cd Backend
python scripts/train_models.py
```

### Model Types

- `gradient_boosting` (default) - Gradient Boosting Regressor
- `random_forest` - Random Forest Regressor
- `exponential_smoothing` - Time series forecasting

### Prediction Windows

- 15 minutes
- 30 minutes

## 🚀 Deployment

### Backend Production

```bash
cd Backend

# Set production environment variables
export ENVIRONMENT=production
export USE_MOCKS=False
export MONGODB_URI=mongodb+srv://...
export CORS_ORIGINS=https://yourdomain.com

# Run with multiple workers
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Frontend Production

```bash
cd frontend

# Build for production
npm run build

# The dist/ folder contains production-ready files
# Deploy to your hosting service (Vercel, Netlify, etc.)
```

### Production Checklist

- [ ] Set `ENVIRONMENT=production`
- [ ] Set `USE_MOCKS=False` (if using real APIs)
- [ ] Configure `MONGODB_URI` with production credentials
- [ ] Set `CORS_ORIGINS` to your frontend domain(s)
- [ ] Configure API keys if using external services
- [ ] Set up proper logging and monitoring
- [ ] Use HTTPS in production
- [ ] Configure rate limiting if needed
- [ ] Set up database backups
- [ ] Configure environment variables in hosting platform

## 🔒 Security

- **No hardcoded credentials**: All sensitive data via environment variables
- **CORS configuration**: Configurable allowed origins
- **MongoDB security**: Connection strings via environment variables
- **API keys**: Optional, loaded from environment variables
- **Environment files**: `.env` files are gitignored

## 🐛 Troubleshooting

### Backend Issues

**MongoDB Connection Issues**
1. Check MongoDB is running: `mongosh` or check service status
2. Verify connection string: Check `MONGODB_URI` in `.env`
3. Check network access: For Atlas, ensure IP is whitelisted

**API Not Returning Data**
1. Check agent status: Look at logs for agent execution
2. Verify data ingestion: Check MongoDB collections
3. Check API keys: If using external APIs, verify keys are set
4. Enable mocks: Set `USE_MOCKS=True` for testing

**ML Predictions Not Working**
1. Train models first: Run `python scripts/train_models.py`
2. Check model files: Verify models exist in `models/congestion_models/`
3. Check training data: Ensure sufficient historical data in MongoDB

### Frontend Issues

**API Connection Errors**
1. Verify backend is running: Check `http://localhost:8000/api/health`
2. Check `VITE_API_BASE_URL` in `.env`
3. Check CORS settings in backend

**Build Errors**
1. Clear node_modules: `rm -rf node_modules && npm install`
2. Check Node.js version: Ensure Node.js 18+
3. Check TypeScript errors: Run `npm run lint`

## 📚 Documentation

- **Backend README**: See `Backend/README.md` for detailed backend documentation
- **Frontend README**: See `frontend/README.md` for detailed frontend documentation
- **MCP Orchestrator**: See `Backend/app/orchestrator/README.md` for orchestrator details
- **API Documentation**: Visit `http://localhost:8000/docs` when backend is running

## 📝 License

MIT License - See LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests if applicable
5. Commit your changes (`git commit -m 'Add some amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📞 Support

For issues and questions:
- Open an issue on the repository
- Check the documentation in `Backend/README.md` and `frontend/README.md`
- Review API documentation at `http://localhost:8000/docs`

## 🎯 Roadmap

- [ ] Enhanced ML model accuracy
- [ ] Real-time alerting system
- [ ] Mobile app (React Native)
- [ ] Advanced analytics dashboard
- [ ] Integration with more data sources
- [ ] Performance optimizations
- [ ] Comprehensive test coverage
- [ ] Docker containerization
- [ ] Kubernetes deployment configs

## 👥 Contributors

Built for NYC DOT Smart City Initiative

---

**DOT** - Empowering NYC with data-driven traffic management and predictive insights.

