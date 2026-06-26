# Architecture: AI-Powered Restaurant Recommendation System

## 1. System Overview

This document describes the architecture of an AI-powered restaurant recommendation system inspired by Zomato. The system combines structured restaurant data from the [Zomato Hugging Face dataset](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation) with a Large Language Model (LLM) to deliver personalized, explainable restaurant recommendations.

---

## 2. High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CLIENT / FRONTEND                            │
│                      (Streamlit Web App)                            │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────────────────┐  │
│  │ Preference│  │  Results     │  │  AI Explanation              │  │
│  │ Form      │  │  Display     │  │  Panel                       │  │
│  └─────┬─────┘  └──────▲──────┘  └──────────────▲───────────────┘  │
│        │               │                        │                   │
└────────┼───────────────┼────────────────────────┼───────────────────┘
         │               │                        │
         ▼               │                        │
┌─────────────────────────────────────────────────────────────────────┐
│                       BACKEND / API LAYER                           │
│                     (FastAPI Application)                            │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  /recommend   │  │  /cuisines   │  │  /locations              │  │
│  │  endpoint     │  │  endpoint    │  │  endpoint                │  │
│  └──────┬────────┘  └──────┬───────┘  └──────────┬──────────────┘  │
│         │                  │                      │                  │
│         ▼                  ▼                      ▼                  │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                  SERVICE LAYER                                │   │
│  │                                                               │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐  │   │
│  │  │ Filter       │  │ Prompt       │  │ Recommendation     │  │   │
│  │  │ Service      │  │ Builder      │  │ Service            │  │   │
│  │  └──────┬───────┘  └──────┬───────┘  └────────┬───────────┘  │   │
│  │         │                 │                    │               │   │
│  └─────────┼─────────────────┼────────────────────┼──────────────┘   │
│            │                 │                    │                   │
│            ▼                 ▼                    ▼                   │
│  ┌─────────────────┐  ┌──────────────────────────────────────────┐  │
│  │  DATA LAYER     │  │          LLM LAYER                       │  │
│  │  (Pandas /      │  │  (Groq API — Llama 3 / Mixtral)           │  │
│  │   CSV Store)    │  │                                          │  │
│  └─────────────────┘  └──────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Component Architecture

### 3.1 Data Ingestion Module

**Responsibility:** Load, clean, and preprocess the Zomato restaurant dataset.

| Aspect            | Detail                                                                            |
| ----------------- | --------------------------------------------------------------------------------- |
| **Source**         | Hugging Face — `ManikaSaini/zomato-restaurant-recommendation`                     |
| **Format**        | CSV / Parquet (via `datasets` library)                                            |
| **Storage**       | In-memory Pandas DataFrame + local CSV cache                                     |
| **Preprocessing** | Handle missing values, normalize cost/rating fields, standardize cuisine & city   |

**Key Fields Extracted:**

| Field               | Type    | Description                          |
| ------------------- | ------- | ------------------------------------ |
| `restaurant_name`   | string  | Name of the restaurant               |
| `city` / `location` | string  | City or locality                     |
| `cuisines`          | string  | Comma-separated list of cuisines     |
| `average_cost`      | float   | Average cost for two people          |
| `aggregate_rating`  | float   | Overall rating (0.0 – 5.0)          |
| `votes`             | integer | Number of user votes                 |
| `has_online_delivery`| boolean | Whether online delivery is available |
| `has_table_booking` | boolean | Whether table booking is available   |

**Data Pipeline:**

```
Hugging Face API
      │
      ▼
  datasets.load_dataset()
      │
      ▼
  Raw DataFrame
      │
      ▼
  ┌─────────────────────┐
  │  Preprocessing       │
  │  • Drop nulls        │
  │  • Normalize ratings │
  │  • Parse cuisines    │
  │  • Standardize costs │
  │  • Clean city names  │
  └──────────┬───────────┘
             │
             ▼
  Cleaned DataFrame (cached as CSV)
```

---

### 3.2 User Input Module

**Responsibility:** Collect and validate user preferences.

**Input Schema:**

```python
class UserPreferences:
    location: str              # e.g., "Delhi", "Bangalore"
    budget: str                # "low" | "medium" | "high"
    cuisine: str               # e.g., "Italian", "Chinese", "North Indian"
    min_rating: float          # 0.0 – 5.0 (default: 3.5)
    additional_prefs: str      # Free-text e.g., "family-friendly, quick service"
```

**Budget Mapping:**

| Budget Level | Estimated Cost Range (for two) |
| ------------ | ------------------------------ |
| Low          | ₹0 – ₹500                     |
| Medium       | ₹500 – ₹1500                  |
| High         | ₹1500+                        |

**Validation Rules:**
- Location must match an available city in the dataset
- Cuisine is optional but validated against available cuisines
- Rating is clamped between 0.0 and 5.0
- Budget defaults to "medium" if unspecified

---

### 3.3 Filter Service

**Responsibility:** Apply deterministic filters to narrow the dataset before LLM processing.

**Filter Pipeline:**

```
Full Dataset
    │
    ├── Filter by Location ──────► Subset A
    │
    ├── Filter by Budget Range ──► Subset B
    │
    ├── Filter by Cuisine ───────► Subset C
    │
    ├── Filter by Min Rating ────► Subset D
    │
    └── Intersection (A ∩ B ∩ C ∩ D) ──► Candidate Set
                                              │
                                              ▼
                                    Top N candidates
                                   (max 20 restaurants)
```

**Why cap at 20?**
- LLM context windows have token limits
- Sending too many restaurants degrades response quality
- If more than 20 match, sort by rating (descending) and take top 20

---

### 3.4 Prompt Builder

**Responsibility:** Construct a well-structured LLM prompt from user preferences and filtered restaurant data.

**Prompt Template Structure:**

```
┌──────────────────────────────────────────────────┐
│  SYSTEM PROMPT                                    │
│  "You are a restaurant recommendation expert..." │
├──────────────────────────────────────────────────┤
│  USER CONTEXT                                     │
│  • Location: {location}                          │
│  • Budget: {budget}                              │
│  • Cuisine: {cuisine}                            │
│  • Min Rating: {min_rating}                      │
│  • Additional: {additional_prefs}                │
├──────────────────────────────────────────────────┤
│  RESTAURANT DATA                                  │
│  Formatted list of candidate restaurants with     │
│  name, cuisine, cost, rating, votes              │
├──────────────────────────────────────────────────┤
│  INSTRUCTIONS                                     │
│  • Rank top 5 restaurants                        │
│  • Provide reasoning for each                    │
│  • Consider user preferences                     │
│  • Return structured JSON output                 │
└──────────────────────────────────────────────────┘
```

**Output Format Specification (in prompt):**

```json
{
  "recommendations": [
    {
      "rank": 1,
      "restaurant_name": "...",
      "cuisine": "...",
      "rating": 4.5,
      "estimated_cost": 800,
      "explanation": "..."
    }
  ],
  "summary": "Overall summary of recommendations..."
}
```

---

### 3.5 Recommendation Engine (LLM Layer)

**Responsibility:** Interface with the LLM API to generate ranked, explained recommendations.

| Aspect              | Detail                                                  |
| -------------------- | ------------------------------------------------------- |
| **Primary LLM**      | Groq API (`llama-3.3-70b-versatile`)                    |
| **Fallback LLM**     | Groq API (`mixtral-8x7b-32768`) (optional)              |
| **SDK**              | `groq`                                                  |
| **Auth**             | API key via environment variable                         |
| **Temperature**      | 0.3 (low creativity, high consistency)                  |
| **Max Tokens**       | 1024                                                    |
| **Response Format**  | Structured JSON                                          |
| **Error Handling**   | Retry with exponential backoff (max 3 retries)          |

**LLM Interaction Flow:**

```
Prompt Builder Output
        │
        ▼
  ┌──────────────────┐
  │  LLM API Call     │
  │  (Groq API)       │
  └────────┬──────────┘
           │
           ▼
  ┌──────────────────┐
  │  Response Parser  │
  │  • Extract JSON   │
  │  • Validate schema│
  │  • Handle errors  │
  └────────┬──────────┘
           │
           ▼
  Structured Recommendations
```

---

### 3.6 Output / Presentation Layer

**Responsibility:** Render recommendations in a user-friendly web interface.

**Technology:** Streamlit (rapid prototyping, Python-native)

**UI Components:**

| Component              | Description                                             |
| ---------------------- | ------------------------------------------------------- |
| **Sidebar**            | Preference input form (location, budget, cuisine, etc.) |
| **Main Panel**         | Recommendation cards with details                       |
| **Recommendation Card**| Restaurant name, cuisine, rating stars, cost, explanation|
| **Summary Section**    | AI-generated overall summary                            |
| **Loading Indicator**  | Spinner during LLM API calls                            |

**Card Layout:**

```
┌────────────────────────────────────────────┐
│  🏆 #1  Restaurant Name                    │
│  ─────────────────────────────────────────  │
│  🍽️ Cuisine: Italian, Continental          │
│  ⭐ Rating: 4.6 / 5.0  (320 votes)        │
│  💰 Cost for Two: ₹1,200                  │
│  ─────────────────────────────────────────  │
│  🤖 Why this pick:                         │
│  "This restaurant perfectly matches your   │
│   preference for Italian cuisine within    │
│   your medium budget range..."             │
└────────────────────────────────────────────┘
```

---

## 4. Project Directory Structure

```
nextleapproject1/
│
├── context.md                  # Problem statement & context
├── architecture.md             # This architecture document
├── problemstatement.txt        # Original problem statement
├── requirements.txt            # Python dependencies
├── .env                        # API keys (not committed)
├── .gitignore                  # Git ignore rules
│
├── data/
│   ├── raw/                    # Raw dataset files
│   └── processed/              # Cleaned & preprocessed data
│
├── src/
│   ├── __init__.py
│   ├── main.py                 # Application entry point
│   ├── config.py               # Configuration & constants
│   │
│   ├── data/
│   │   ├── __init__.py
│   │   ├── loader.py           # Dataset loading from Hugging Face
│   │   └── preprocessor.py     # Data cleaning & normalization
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py          # Pydantic models (UserPreferences, Restaurant, etc.)
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── filter_service.py   # Deterministic filtering logic
│   │   ├── prompt_builder.py   # LLM prompt construction
│   │   └── recommendation.py   # LLM interaction & response parsing
│   │
│   └── api/
│       ├── __init__.py
│       └── routes.py           # FastAPI route handlers
│
├── app/
│   └── streamlit_app.py        # Streamlit frontend
│
└── tests/
    ├── __init__.py
    ├── test_filter_service.py
    ├── test_prompt_builder.py
    └── test_recommendation.py
```

---

## 5. Technology Stack

| Layer          | Technology                         | Purpose                                |
| -------------- | ---------------------------------- | -------------------------------------- |
| **Frontend**   | Streamlit                          | Interactive web UI                     |
| **Backend**    | FastAPI                            | REST API layer                         |
| **Data**       | Pandas, Hugging Face `datasets`    | Data loading & manipulation            |
| **LLM**       | Groq API (Llama 3 / Mixtral)        | AI-powered recommendations             |
| **Validation** | Pydantic                           | Request/response validation            |
| **Config**     | python-dotenv                      | Environment variable management        |
| **Testing**    | pytest                             | Unit & integration testing             |
| **Language**   | Python 3.10+                       | Core language                          |

---

## 6. Dependencies

```txt
fastapi>=0.104.0
uvicorn>=0.24.0
streamlit>=1.28.0
pandas>=2.1.0
datasets>=2.15.0
groq>=0.4.0
pydantic>=2.5.0
python-dotenv>=1.0.0
requests>=2.31.0
pytest>=7.4.0
```

---

## 7. Data Flow (End-to-End)

```
┌─────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  User    │     │  Filter  │     │  Prompt  │     │  LLM     │     │  Output  │
│  Input   │────►│  Service │────►│  Builder │────►│  Engine  │────►│  Display │
│          │     │          │     │          │     │          │     │          │
│ location │     │ pandas   │     │ template │     │ Groq     │     │ Streamlit│
│ budget   │     │ query    │     │ + data   │     │ API call │     │ cards    │
│ cuisine  │     │ filters  │     │ context  │     │ + parse  │     │ + summary│
│ rating   │     │          │     │          │     │          │     │          │
└─────────┘     └──────────┘     └──────────┘     └──────────┘     └──────────┘
     │                │                │                │                │
     ▼                ▼                ▼                ▼                ▼
 Validate        Candidate Set     Structured      JSON Response    Rendered
 & parse         (≤20 items)       LLM Prompt      with rankings    UI Cards
```

---

## 8. API Endpoints

### `POST /recommend`

**Description:** Generate restaurant recommendations based on user preferences.

**Request Body:**

```json
{
  "location": "Delhi",
  "budget": "medium",
  "cuisine": "Italian",
  "min_rating": 3.5,
  "additional_prefs": "family-friendly"
}
```

**Response:**

```json
{
  "recommendations": [
    {
      "rank": 1,
      "restaurant_name": "Olive Bar & Kitchen",
      "cuisine": "Italian, Continental",
      "rating": 4.6,
      "estimated_cost": 1200,
      "explanation": "Highly rated Italian restaurant within your budget..."
    }
  ],
  "summary": "Based on your preferences for Italian cuisine in Delhi...",
  "total_matches": 15
}
```

### `GET /cuisines`

Returns list of all available cuisines in the dataset.

### `GET /locations`

Returns list of all available cities/locations in the dataset.

---

## 9. Error Handling Strategy

| Error Type             | Handling Approach                                         |
| ---------------------- | --------------------------------------------------------- |
| Dataset not found      | Graceful fallback message; retry download                |
| No matching restaurants| Return message suggesting broader criteria               |
| LLM API failure        | Retry with exponential backoff (3 attempts); fallback msg|
| LLM invalid response   | Re-prompt with stricter format instructions              |
| Invalid user input     | Pydantic validation with descriptive error messages      |
| Rate limiting          | Queue requests; display wait message to user             |

---

## 10. Security Considerations

- **API Keys:** Stored in `.env` file, never committed to version control
- **Input Sanitization:** All user inputs validated and sanitized via Pydantic
- **Rate Limiting:** Applied on API endpoints to prevent abuse
- **CORS:** Configured for frontend origin only
- **Prompt Injection:** User free-text inputs are escaped before insertion into prompts

---

## 11. Future Enhancements

| Enhancement                     | Description                                             |
| ------------------------------- | ------------------------------------------------------- |
| **Vector Search**               | Embed restaurant descriptions for semantic matching     |
| **User History**                | Store past preferences for personalized repeat visits   |
| **Multi-turn Conversations**    | Allow follow-up questions ("Show me cheaper options")   |
| **Map Integration**             | Display restaurant locations on an interactive map      |
| **Reviews Integration**         | Incorporate user reviews for richer LLM context         |
| **Caching**                     | Cache frequent queries to reduce LLM API costs          |
| **A/B Testing**                 | Compare different prompt strategies for quality         |
