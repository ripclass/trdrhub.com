# TRDR Hub - Project Brief

## Overview
TRDR Hub is a trade compliance platform for SME exporters, providing tools to validate LCs, verify commodity prices, screen sanctions, and track shipments.

## Core Tools
1. **LCopilot** - LC validation with UCP600/ISBP rules (4,000+ rulesets, 94% accuracy)
2. **Price Verify** - Commodity price verification for TBML detection
3. **Container/Vessel Tracker** - Shipment tracking with alerts (currently building)
4. **HS Code Lookup** - Tariff classification
5. **Sanctions Screening** - Real-time screening

## Tech Stack
- **Frontend**: React + TypeScript + Vite + Tailwind + shadcn/ui
- **Backend**: FastAPI + SQLAlchemy + PostgreSQL
- **Auth**: Supabase (primary) + JWT
- **Hosting**: Vercel (frontend) + Render (backend)
- **Storage**: S3-compatible

## Key URLs
- Production: https://trdrhub.com
- API: https://trdrhub-api.onrender.com

## Business Model
- API-first rules database (RuleHub)
- SaaS tools for SMEs (TRDR Hub)
- Target markets: Bangladesh, India, Pakistan (localized pricing)

