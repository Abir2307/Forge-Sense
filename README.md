# Forge-Sense SafetyTwin
<p align="center">
<b>AI-Powered Industrial Safety Intelligence Platform for Predictive Risk Assessment, Permit Intelligence, Compliance Monitoring, and Emergency Response</b>
</p>

---

## Overview

**Forge-Sense SafetyTwin** is an AI-powered Industrial Safety Intelligence Platform that creates a digital representation of an industrial facility by integrating multiple operational data sources into a unified safety intelligence system.

Unlike conventional safety monitoring systems that evaluate isolated sensor values, Forge-Sense performs **compound risk analysis**, correlating IoT sensor readings, Permit-to-Work (PTW) information, historical incidents, compliance records, and contextual knowledge to provide predictive situational awareness.

The platform assists safety engineers, plant operators, and compliance officers by identifying emerging hazards, recommending preventive actions, and orchestrating emergency responses before incidents escalate.

---

## Key Features

- Real-time Industrial Safety Monitoring
- Compound Risk Detection
- Permit-to-Work Intelligence
- Historical Incident Pattern Analysis
- Compliance Monitoring
- Emergency Response Orchestration
- Interactive Safety Dashboard
- Geospatial Heatmap Visualization
- Knowledge Graph-based Hazard Correlation
- Evaluation Metrics Dashboard
- Modular AI Agent Architecture
- SQLite-backed Operational Database

---

# System Architecture

<p align="center">
<img src="docs/images/System_Architecture.png" width="900">
</p>

Thus, the system follows a layered architecture consisting of a presentation layer, orchestration layer, AI intelligence layer, and persistence layer.
```

---

# Architecture Components

<p align="center">
<img src="docs/images/Dashboard.png" width="900">
</p>

## 1. User Interface Layer

The desktop application is built using **PySide6** and provides a real-time visualization of plant safety conditions.

### Modules

- Main Window
- Safety Dashboard
- Heatmap Widget
- Video Display
- Permit Panel
- Compliance Panel
- Incident Panel

Capabilities include

- Live Risk Score
- Alerts
- Heatmaps
- Recommendations
- Evaluation Metrics
- Incident Summary

---

## 2. Safety Intelligence Worker

The worker continuously executes the monitoring loop without blocking the graphical interface.

Responsibilities include

- Reading sensors
- Collecting permit information
- Running AI assessment
- Updating dashboard
- Emitting Qt signals

Execution Flow

```
Read Sensor Data
        │
        ▼
Read Active Permits
        │
        ▼
Perform Risk Assessment
        │
        ▼
Update Dashboard
        │
        ▼
      Repeat
```
## 3. Safety Intelligence Platform

This is the central orchestration engine responsible for combining outputs from multiple AI agents into a single operational risk assessment.

Responsibilities

- Agent Coordination
- Composite Risk Calculation
- Recommendation Generation
- Emergency Triggering
- Evaluation Metric Generation

---

# AI Intelligence Modules

## Permit Intelligence Agent

Analyzes active permits against operational conditions.

Functions

- Permit Validation
- Simultaneous Operation Detection
- Hazard Correlation
- Permit Risk Classification

Example

```
Hot Work Permit
      +
Gas Sensor Alert
      +
Maintenance Activity

↓

High Compound Risk
```

---

## Incident Pattern Analyzer

Uses historical incidents and near-miss events to estimate future operational risk.

Capabilities

- Pattern Detection
- Historical Hotspots
- Repeat Incident Identification
- Risk Escalation

---

## Compliance Monitor

Performs automated compliance evaluation against industrial regulations.

Current Standards

- Factory Act
- OISD
- DGFASLI

Outputs

- Compliance Status
- Violations
- Corrective Actions

---

## Emergency Response Orchestrator

Coordinates emergency response workflows whenever critical hazards are detected.

Functions

- Emergency Detection
- Evacuation Trigger
- Evidence Preservation
- Incident Reporting

Future Integrations

- SMS
- Email
- MQTT
- Public Address Systems

---

## Safety Knowledge Graph

Maintains relationships among

- Equipment
- Hazards
- Permits
- Locations
- Workers
- Historical Incidents

Graph reasoning improves contextual understanding and compound hazard detection.

---

## Composite Risk Engine

Instead of relying on a single sensor threshold, Forge-Sense combines multiple indicators.

Inputs include

- Gas Concentration
- Temperature
- Humidity
- Permit Status
- Compliance Status
- Incident History
- Knowledge Graph Context

Outputs

- Overall Risk Score
- Risk Category
- Recommendations
- Emergency Actions

---

# Database

SQLite currently stores operational information.

Core Tables

```
work_permits

equipment

incidents

near_miss_events

hazard_logs

compliance_audit
```

The architecture allows migration to PostgreSQL or enterprise databases without major modifications.

---

# Project Structure

```
Forge-Sense/

│
├── safetwin/
│   ├── ui/
│   │     ├── main_window.py
│   │     ├── safety_dashboard.py
│   │     ├── heatmap_widget.py
│   │     └── video_display.py
│   │
│   ├── services/
│   │     ├── safety_intelligence_platform.py
│   │     ├── safety_intelligence_worker.py
│   │     ├── permit_intelligence_agent.py
│   │     ├── incident_pattern_analyzer.py
│   │     ├── compliance_monitor.py
│   │     ├── emergency_orchestrator.py
│   │     ├── knowledge_graph.py
│   │     └── evaluation_metrics.py
│   │
│   ├── database.py
│   └── app.py
│
├── docs/
│   └── images/
│        └── system_architecture.png
│
├── requirements.txt
└── README.md
```

---

# Technology Stack

| Category | Technology |
|-----------|------------|
| Language | Python 3 |
| GUI | PySide6 |
| Database | SQLite |
| AI Modules | Custom Rule Engine |
| Visualization | Qt Graphics |
| Heatmap | Custom Visualization |
| Future CV | YOLO / OpenCV |
| Future ML | PyTorch / Scikit-Learn |

---

# Evaluation Metrics

The platform currently reports

- False Negative Rate
- Lead Time
- Geospatial Quality

Geo Quality supports fallback estimation using permit locations, while False Negative Rate and Lead Time require historical operational data.

---

# Current Status

Implemented

- User Interface
- Dashboard
- Heatmap
- Permit Intelligence
- Incident Analysis
- Compliance Monitoring
- Knowledge Graph
- Composite Risk Assessment
- Emergency Response
- Evaluation Metrics

Pending

- Live SCADA Integration
- CCTV Analytics
- Worker Tracking
- Predictive Machine Learning
- Retrieval-Augmented Generation (RAG)
- Digital Twin Visualization

---

# Future Roadmap

## Short-Term

- Populate historical incident database
- Connect live IoT sensors
- Enhance compound risk rules
- Improve permit lifecycle tracking

## Medium-Term

- Computer Vision Integration
- Predictive Risk Modeling
- Compliance Intelligence using RAG
- Worker Location Tracking

## Long-Term

- Industrial Digital Twin
- Predictive Hazard Forecasting
- Automated Regulatory Reporting
- Closed-loop Emergency Management

---

# Running the Project

Clone the repository

```bash
git clone https://github.com/<username>/Forge-Sense.git
```

Install dependencies

```bash
pip install -r requirements.txt
```

Run the application

```bash
python -m safetwin.app
```

---

# Contributors

**Abir Saha**

B.Tech Computer Science & Engineering

RCC Institute of Information Technology

AI • Computer Vision • Industrial Safety • Digital Twin • Intelligent Systems

---

# License

This project is intended for academic research, industrial safety demonstrations, and educational purposes.

---

## Acknowledgements

Inspired by modern Industrial Digital Twin systems, AI-driven safety intelligence, Industry 4.0 principles, and predictive risk management frameworks aimed at improving workplace safety and operational resilience.
