# Smart Utility (Urja) — AI Electricity Utility Assistant

A polished, production-quality frontend prototype for **Smart Utility** (Urja), an AI-powered electricity utility assistant designed for modern Indian homes and businesses. Smart Utility transforms raw electricity bills into actionable consumption insights, accurate forecasts, weather-impact assessments, and interactive conversational guidance.

---

## Overview

Smart Utility simplifies home energy management by allowing users to upload their monthly electricity bills. The underlying agentic analysis pipeline extracts detailed billing metrics, correlates consumption with local weather data, identifies appliance-level drivers, forecasts future bills, and delivers targeted efficiency recommendations.

---

## Product Concept

Most utility bills are confusing and static documents that hide actionable insights. Smart Utility solves this by offering:
- **Instant Bill Analysis**: Multi-format OCR & AI extraction for Indian electricity utilities (e.g., MSEDCL, TATA Power, BESCOM, BSES, Adani Electricity).
- **Consumption Analytics**: Trend breakdown across appliances and historical billing cycles.
- **Predictive Forecasting**: Weather-adjusted next-month bill ranges and kWh estimations.
- **Weather Impact Correlation**: Live weather context matching high consumption periods with temperature spikes.
- **AI Energy Assistant**: Interactive assistant capable of explaining bill increases, offering custom saving tips, and detailing tariff structures.

---

## Core User Flow

```
Landing Page (Upload / Sample Bill)
        ↓
File Validation & Preparation
        ↓
Animated Processing Pipeline (Multi-stage AI Analysis)
        ↓
Analysis Completion & Metrics Summary
        ↓
Interactive Analytics Dashboard (Insights, Forecasts, Assistant)
```

---

## Technology Stack

- **Framework**: Next.js 15 (App Router, TypeScript)
- **Styling**: Tailwind CSS, PostCSS, Autoprefixer
- **Animations & Motion**: Framer Motion
- **Data Visualization**: Recharts
- **Icons**: Lucide React
- **Type Safety**: TypeScript 5.7+
- **Code Quality**: ESLint, PostCSS

---

## Architecture

```
src/
├── app/                  # Next.js App Router routes & layouts
│   ├── layout.tsx        # Global font, styles, metadata
│   ├── page.tsx          # Main single-page application orchestrator
│   └── globals.css       # Global CSS & Tailwind directives
├── components/           # Reusable UI components by domain
│   ├── brand/            # Logo, branding badges, header markers
│   ├── layout/           # Sidebar, Topbar, Main Shell
│   ├── upload/           # Landing page upload zone & file validation
│   ├── processing/       # Animated AI processing pipeline steps
│   ├── dashboard/        # Dashboard overview, top metric cards, breakdown
│   ├── forecast/         # Predictive forecasting visualization
│   ├── weather/          # Weather impact cards & climate widgets
│   ├── insights/         # AI insights & recommendation cards
│   ├── assistant/        # Conversational AI assistant panel
│   ├── documents/        # Historical bills table & document viewer
│   └── ui/               # Reusable buttons, cards, tooltips, badges
├── services/             # Mock service layer (Future Backend Integration point)
│   ├── analysisService.ts# Bill analysis & extraction service
│   ├── forecastService.ts# Consumption forecasting engine
│   ├── weatherService.ts # Local weather context provider
│   ├── assistantService.ts# Conversational query processor
│   └── documentService.ts# User bill document management
├── types/                # TypeScript interface & type definitions
│   ├── bill.ts           # Bill data model
│   ├── analysis.ts       # Analysis pipeline states
│   ├── forecast.ts       # Forecast models
│   ├── weather.ts        # Weather data structures
│   └── assistant.ts     # Chat message & context models
└── config/               # Design tokens, sample bill constants
```

---

## Mock Services

This prototype utilizes an asynchronous mock service layer designed to emulate real backend APIs:
- `analysisService`: Simulates multi-stage OCR extraction, language detection, tariff calculation, and appliance breakdown.
- `forecastService`: Generates upper/lower bound bill estimates based on season, historic kWh, and temperature trends.
- `weatherService`: Delivers real-time location weather metrics (temperature, humidity, cooling load).
- `assistantService`: Returns contextual responses based on active bill data and energy saving rules.
- `documentService`: Manages local bill records with status indicators (Analysed, Processing, Failed).

---

## Future Backend Integration

When integrating a production backend, mock services can be seamlessly replaced by endpoint contracts:
- `POST /api/v1/bills/upload` → OCR / Vision LLM Pipeline (Tesseract / Claude / GPT-4o Vision)
- `POST /api/v1/bills/analyze` → Multi-agent processing orchestrator
- `GET /api/v1/weather?location={loc}` → Weather API (OpenWeatherMap / Tomorrow.io)
- `POST /api/v1/assistant/chat` → RAG / LangChain agent over user bill history

---

## Development Setup

1. **Clone & Install Dependencies**:
   ```bash
   git clone https://github.com/your-org/smart_utility.git
   cd smart_utility
   npm install
   ```

2. **Start Local Development Server**:
   ```bash
   npm run dev
   ```
   Open [http://localhost:3000](http://localhost:3000) in your browser.

3. **Typecheck & Linting**:
   ```bash
   npm run typecheck
   npm run lint
   ```

---

## Environment Variables

Copy `.env.example` to `.env.local` when integrating real backend APIs:
```env
NEXT_PUBLIC_APP_NAME="Smart Utility"
NEXT_PUBLIC_API_BASE_URL="http://localhost:8000/api/v1"
NEXT_PUBLIC_MOCK_DELAY_MS=1200
```

---

## Roadmap

- [x] Phase 1: Repository initialization & Design system tokens
- [x] Phase 2: Minimal landing page & Drag-and-drop bill uploader
- [x] Phase 3: Multi-stage animated AI processing pipeline
- [x] Phase 4: Analysis completion transition & quick summary cards
- [x] Phase 5: Production Analytics Dashboard shell & metric cards
- [x] Phase 6: Monthly consumption charts & Appliance breakdown donut chart
- [x] Phase 7: Predictive forecast visualization & Weather impact module
- [x] Phase 8: Conversational energy assistant experience
- [x] Phase 9: Document history table & detailed bill view modal
- [ ] Phase 10: Real backend OCR & LLM pipeline integration

---

## Current Status

**Frontend Prototype Complete**: Fully functional UI workflow with realistic mock services, Framer Motion transitions, responsive design, and design system fidelity matching the approved visual reference.
