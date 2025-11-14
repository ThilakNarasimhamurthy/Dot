# NYC Lifeguard - Frontend

A modern React-based dashboard for monitoring NYC traffic, transit, air quality, and emergency response metrics in real-time.

## 🚀 Features

- **Real-time Dashboard**: Live monitoring of traffic congestion, air quality, and emergency response times
- **Interactive Maps**: Visual representation of traffic segments, zones, and incidents using Leaflet
- **Borough Filtering**: Filter data by NYC boroughs (Manhattan, Brooklyn, Queens, Bronx, Staten Island)
- **KPI Metrics**: Key performance indicators with trend analysis and sparkline charts
- **AI Insights**: AI-powered insights and predictions for traffic hotspots
- **Emergency Tracking**: Real-time emergency incident tracking with critical delay alerts
- **Mobile Health Camps**: Information about mobile health camps and their locations
- **Responsive Design**: Fully responsive UI that works on desktop, tablet, and mobile devices

## 🛠️ Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Styling
- **Shadcn/ui** - UI component library
- **React Query (TanStack Query)** - Data fetching and caching
- **Leaflet** - Interactive maps
- **Recharts** - Data visualization
- **React Router** - Navigation

## 📋 Prerequisites

- Node.js 18+ or Bun
- npm, yarn, or bun package manager

## 🏃 Getting Started

### Installation

```bash
# Install dependencies
npm install
# or
yarn install
# or
bun install
```

### Environment Variables

Create a `.env` file in the root directory:

```env
VITE_API_BASE_URL=http://localhost:8000
```

For production, set the API base URL to your backend server:

```env
VITE_API_BASE_URL=https://api.yourdomain.com
```

### Development

Start the development server:

```bash
npm run dev
# or
yarn dev
# or
bun dev
```

The application will be available at `http://localhost:8080` (or the port specified in `vite.config.ts`).

### Build

Build for production:

```bash
npm run build
# or
yarn build
# or
bun run build
```

The production build will be in the `dist` directory.

### Preview Production Build

Preview the production build locally:

```bash
npm run preview
# or
yarn preview
# or
bun run preview
```

## 📁 Project Structure

```
frontend/
├── src/
│   ├── components/          # React components
│   │   ├── MetricsGrid.tsx   # KPI metrics dashboard
│   │   ├── InteractiveMap.tsx # Main map component
│   │   ├── EmergencyTracking.tsx # Emergency incidents tracking
│   │   ├── AIInsightsPanel.tsx   # AI insights and predictions
│   │   ├── BoroughDetails.tsx    # Borough-specific details
│   │   ├── BoroughMap.tsx        # Borough map view
│   │   ├── MobileHealthCamps.tsx # Health camps information
│   │   └── ui/                   # Shadcn/ui components
│   ├── lib/
│   │   ├── api.ts            # API client and types
│   │   └── utils.ts          # Utility functions and mock data
│   ├── pages/
│   │   ├── Index.tsx         # Main dashboard page
│   │   └── NotFound.tsx      # 404 page
│   ├── hooks/                # Custom React hooks
│   ├── App.tsx               # Root component
│   └── main.tsx              # Entry point
├── public/                   # Static assets
├── package.json
├── vite.config.ts
└── tailwind.config.ts
```

## 🎨 Components

### MetricsGrid
Displays key performance indicators:
- Emergency Response Time
- Traffic Congestion
- Collision Count
- Air Quality Complaints
- Hourly Speed

### InteractiveMap
Interactive map showing:
- Traffic segments with color-coded congestion levels
- Zone boundaries
- Real-time traffic data

### EmergencyTracking
Tracks emergency incidents:
- Critical delays
- Incident locations
- Response time metrics

### AIInsightsPanel
AI-powered insights:
- Traffic hotspot predictions
- Congestion-air quality correlations
- Actionable recommendations

## 🔌 API Integration

The frontend communicates with the backend API through the `api.ts` client. All API calls are made using React Query for efficient data fetching, caching, and automatic refetching.

### API Endpoints Used

- `/api/segments/current` - Get current traffic segments
- `/api/zones/current` - Get current traffic zones
- `/api/predictions` - Get traffic predictions
- `/api/health` - Health check
- `/api/health/validation` - Validation metrics
- `/api/explain/hotspots` - AI explanations

## 🎯 Key Features

### Borough Filtering
Filter all data by NYC borough:
- All NYC Boroughs
- Manhattan
- Brooklyn
- Queens
- Bronx
- Staten Island

### Real-time Updates
- Automatic data refresh every 30 seconds
- Live updates for emergency incidents
- Real-time map markers

### Mock Data Fallback
When the backend API is unavailable, the application uses mock data to ensure the UI remains functional.

## 🧪 Development

### Linting

```bash
npm run lint
# or
yarn lint
# or
bun run lint
```

### Type Checking

TypeScript type checking is performed automatically by the IDE and during build.

## 📦 Dependencies

### Core
- `react` - UI library
- `react-dom` - React DOM renderer
- `react-router-dom` - Routing
- `@tanstack/react-query` - Data fetching

### UI Components
- `@radix-ui/*` - Headless UI primitives
- `tailwindcss` - Utility-first CSS
- `lucide-react` - Icons

### Maps & Visualization
- `leaflet` - Interactive maps
- `recharts` - Charts and graphs

## 🔒 Security

- No sensitive URLs or API keys are hardcoded
- Environment variables are used for configuration
- `.env` files are gitignored

## 📝 License

See LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📞 Support

For issues and questions, please open an issue on the repository.

