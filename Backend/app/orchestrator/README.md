# MCP Orchestrator Server

## Overview

The MCP Orchestrator Server is the central control unit for the multi-agent Smart City Dashboard system. It coordinates the execution of three specialized agents that work together to ingest, process, and predict traffic congestion data.

## Architecture

```
                    MCP Orchestrator Server
                           (Central Hub)
                                |
        +-----------------------+-----------------------+
        |                       |                       |
        |                       |                       |
    Schedule/            Run After              Run Forecast
    Run Cycles          Ingestion                  Jobs
        |                       |                       |
        v                       v                       v
   Agent 1:              Agent 2:              Agent 3:
   Ingestion        Cleaning & Correlation    Prediction Engine
        |                       |                       |
        |                       |                       |
   Store Raw              Store Processed        Store Predictions
   Records                Segments/Zones
```

## Components

### MCP Orchestrator Server (`mcp_server.py`)

The central orchestrator that manages:
- **Agent Scheduling**: Coordinates when each agent runs
- **Agent Lifecycle**: Manages agent execution state and prevents overlapping runs
- **Data Flow**: Ensures proper sequencing (Ingestion → Cleaning → Prediction)
- **Explanation Requests**: Handles AI-powered explanation requests

### Agent 1: Data Ingestion

**Function**: Pulls live feeds from multiple sources
- 511NY Traffic API
- NYC DOT Open Data
- MTA GTFS-RT (Vehicle Positions, Trip Updates, Alerts)

**Trigger**: Scheduled cycles (default: every 30 seconds)
**Output**: Stores raw records in MongoDB collections

### Agent 2: Cleaning & Correlation

**Function**: Converts fragmented raw data into usable structures
- Data Quality Checks
- Fusion (Traffic + Transit data)
- Correlation with Air Quality

**Trigger**: 
- Automatically after Agent 1 completes ingestion
- Also runs on independent schedule (every 2 minutes)

**Output**: Creates `segments_state` and `zones_state` collections

### Agent 3: Prediction Engine

**Function**: Generates congestion forecasts
- 15-minute forecast window
- 30-minute forecast window
- ML-powered predictions using gradient boosting models

**Trigger**: Scheduled forecast jobs (default: every 5 minutes)
**Output**: Stores predictions in `predicted_segments` collection

## API Endpoints

### GET `/api/orchestrator/status`
Get current status of MCP Orchestrator and all agents

**Response**:
```json
{
  "orchestrator": "MCP Orchestrator Server",
  "status": "running",
  "agents": {
    "agent1_ingestion": {
      "name": "Agent 1: Data Ingestion",
      "sources": ["511NY Traffic API", "NYC DOT Open Data", "MTA GTFS-RT"],
      "last_run": "2025-01-XX...",
      "in_progress": false
    },
    "agent2_cleaning": {
      "name": "Agent 2: Cleaning & Correlation",
      "functions": ["Data Quality Checks", "Fusion (Traffic + Transit)"],
      "last_run": "2025-01-XX...",
      "in_progress": false
    },
    "agent3_prediction": {
      "name": "Agent 3: Prediction Engine",
      "forecast": "15-30 min Congestion Forecast",
      "last_run": "2025-01-XX...",
      "in_progress": false
    }
  }
}
```

### POST `/api/orchestrator/orchestrate`
Manually trigger a complete orchestration cycle (all agents)

### POST `/api/orchestrator/ingestion`
Manually trigger Agent 1: Ingestion

### POST `/api/orchestrator/cleaning`
Manually trigger Agent 2: Cleaning & Correlation

### POST `/api/orchestrator/forecast`
Manually trigger Agent 3: Forecast Jobs

## Scheduling

The orchestrator sets up scheduled cycles:

1. **Agent 1 (Ingestion)**: Runs every `INGESTION_INTERVAL_TRAFFIC` seconds (default: 30s)
2. **Agent 2 (Cleaning)**: Runs every 2 minutes (also triggered after ingestion)
3. **Agent 3 (Prediction)**: Runs every 5 minutes

## Data Flow

1. **Ingestion Cycle** → Agent 1 fetches data from APIs
2. **After Ingestion** → Agent 2 processes raw data (triggered automatically)
3. **Forecast Jobs** → Agent 3 generates predictions (runs independently)

## State Management

The orchestrator tracks:
- Last execution time for each agent
- Whether each agent is currently running (prevents overlapping executions)
- Execution results and status

## Error Handling

- Each agent execution is wrapped in try-catch blocks
- Errors are logged but don't stop the orchestrator
- Failed agent runs are reported in status responses
- The orchestrator continues operating even if individual agents fail

## Usage

The MCP Orchestrator Server is automatically initialized when the FastAPI application starts:

```python
# In app/main.py lifespan
mcp_orchestrator = MCPOrchestratorServer(scheduler)
mcp_orchestrator.setup_scheduled_cycles()
scheduler.start()
```

## Configuration

Scheduling intervals can be configured via environment variables:
- `INGESTION_INTERVAL_TRAFFIC`: Interval for Agent 1 (seconds)
- `INGESTION_INTERVAL_TRANSIT`: Interval for transit data (seconds)
- `INGESTION_INTERVAL_AIR_QUALITY`: Interval for air quality data (seconds)

## Monitoring

Check orchestrator status:
```bash
curl http://localhost:8000/api/orchestrator/status
```

Trigger manual orchestration:
```bash
curl -X POST http://localhost:8000/api/orchestrator/orchestrate
```

