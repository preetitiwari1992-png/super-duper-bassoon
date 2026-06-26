# Backend Implementation Plan — AI-Powered Restaurant Recommendation System

> **Phase-wise roadmap** derived from the architecture and context.

---

## Phase Overview

| Phase | Name                        | Duration  | Key Deliverable                              |
| ----- | --------------------------- | --------- | -------------------------------------------- |
| 0     | Project Setup & Scaffolding | Day 1     | Repository structure, dependencies, config   |
| 1     | Data Ingestion & Preprocessing | Days 2–3  | Clean, cached restaurant dataset             |
| 2     | Filtering & Query Engine    | Days 4–5  | Deterministic filter pipeline                |
| 3     | Prompt Engineering & LLM Integration | Days 6–8  | Groq-powered recommendation engine           |
| 4     | API Layer (FastAPI)         | Days 9–10 | REST endpoints for recommendations           |
| 5     | Testing & Validation        | Days 11–12| Unit tests, integration tests, edge cases    |
| 6     | Polish & Documentation      | Day 13    | Final README, clean code                     |

---

## Phase 0 — Project Setup & Scaffolding

### Objective
Set up the Python project structure, install dependencies, and configure environment variables.

### Tasks
- [ ] Initialize Python virtual environment
- [ ] Create `requirements.txt` with all dependencies
- [ ] Set up `.env` file with Groq API key placeholder
- [ ] Create `src/config.py` with configuration constants
- [ ] Set up directory structure (`src/data/`, `src/models/`, `src/services/`, `src/api/`, `tests/`)

---

## Phase 1 — Data Ingestion & Preprocessing

### Objective
Load the Zomato dataset from Hugging Face, clean it, and cache the processed data locally.

### Tasks
- [ ] Implement `loader.py` — download dataset via `datasets` library
- [ ] Implement `preprocessor.py` — clean & normalize data
- [ ] Cache processed data as CSV in `data/processed/`
- [ ] Create Pydantic `Restaurant` model in `schemas.py`
- [ ] Write exploratory tests to verify data integrity

---

## Phase 2 — Filtering & Query Engine

### Objective
Implement deterministic filters that narrow the dataset based on user preferences before sending to the LLM.

### Tasks
- [ ] Implement `filter_service.py` with chained filters
- [ ] Add budget-range mapping logic
- [ ] Add cuisine partial-match (case-insensitive)
- [ ] Add fallback logic when no results match
- [ ] Write unit tests for filter service

---

## Phase 3 — Prompt Engineering & LLM Integration

### Objective
Build the prompt template and integrate with the Groq API to generate ranked, explained recommendations.

### Tasks
- [ ] Implement `prompt_builder.py` — system + user prompt
- [ ] Define structured JSON output schema in prompt
- [ ] Implement `recommendation.py` — Groq API integration
- [ ] Add response parsing and validation (Pydantic)
- [ ] Add retry logic with exponential backoff and fallback model
- [ ] Write unit tests for prompt builder and recommendation service

---

## Phase 4 — API Layer (FastAPI)

### Objective
Expose the recommendation engine as REST API endpoints.

### Tasks
- [ ] Implement `POST /recommend` endpoint
- [ ] Implement `GET /cuisines` endpoint
- [ ] Implement `GET /locations` endpoint
- [ ] Wire up `main.py` as FastAPI app entry point with CORS
- [ ] Add request validation and error handling middleware

---

## Phase 5 — Testing & Validation

### Objective
Ensure all backend components work correctly individually and together.

### Tasks
- [ ] Unit tests for `filter_service.py`, `prompt_builder.py`, `recommendation.py`
- [ ] Integration test: full pipeline (filter → prompt → LLM → response)
- [ ] API endpoint tests (valid and invalid requests)
- [ ] Edge case testing (e.g. empty results, API failure)

---

## Phase 6 — Polish & Documentation

### Objective
Finalize the backend code with documentation and a clean state.

### Tasks
- [ ] Write backend sections of `README.md`
- [ ] Add inline code comments and docstrings
- [ ] Final code review and refactoring
