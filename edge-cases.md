# Edge Cases — AI-Powered Restaurant Recommendation System

> Comprehensive catalogue of edge cases across every layer of the system.
> Referenced from [architecture.md](file:///c:/Users/preeti/OneDrive/Desktop/nextleapproject1/architecture.md), [context.md](file:///c:/Users/preeti/OneDrive/Desktop/nextleapproject1/context.md), and [implementation-plan.md](file:///c:/Users/preeti/OneDrive/Desktop/nextleapproject1/implementation-plan.md).

---

## 1. Data Ingestion & Preprocessing

### 1.1 Dataset Availability

| ID    | Scenario                                       | Expected Behavior                                              | Severity |
| ----- | ---------------------------------------------- | -------------------------------------------------------------- | -------- |
| DI-01 | Hugging Face API is down / unreachable         | Fall back to locally cached CSV in `data/processed/`           | Critical |
| DI-02 | Dataset has been removed or renamed on HF      | Log error, display message "Dataset unavailable, using cache"  | Critical |
| DI-03 | Network timeout during dataset download        | Retry up to 3 times with backoff; fall back to cache           | High     |
| DI-04 | First-time run with no cache and no network    | Halt gracefully with clear error: "No data available"          | Critical |
| DI-05 | Dataset is partially downloaded (corrupted)    | Detect corrupt file, delete and re-download                    | High     |

### 1.2 Data Quality

| ID    | Scenario                                       | Expected Behavior                                              | Severity |
| ----- | ---------------------------------------------- | -------------------------------------------------------------- | -------- |
| DQ-01 | `restaurant_name` is null or empty             | Drop the row during preprocessing                              | Medium   |
| DQ-02 | `aggregate_rating` is negative or > 5.0        | Clamp to 0.0–5.0 range                                        | Medium   |
| DQ-03 | `average_cost` contains non-numeric values     | Parse and strip symbols (₹, $, commas); default to 0 if fails | Medium   |
| DQ-04 | `cuisines` field is null                       | Replace with "Unknown"                                        | Low      |
| DQ-05 | `city` has inconsistent casing ("delhi" vs "Delhi") | Normalize to title-case during preprocessing              | Low      |
| DQ-06 | Duplicate restaurants (same name + same city)  | Deduplicate, keeping the entry with higher votes               | Low      |
| DQ-07 | `votes` field is null or negative              | Default to 0                                                  | Low      |
| DQ-08 | `cuisines` contains trailing/leading whitespace| Trim during preprocessing                                      | Low      |
| DQ-09 | Dataset schema changes (columns renamed/removed)| Validate expected columns on load; raise clear error          | High     |
| DQ-10 | Dataset is empty (0 rows)                      | Display "Dataset is empty" message; halt recommendation flow   | Critical |
| DQ-11 | `average_cost` is 0 for all restaurants        | Still include in results; LLM notes cost as "not available"    | Low      |
| DQ-12 | `aggregate_rating` is 0.0 for all restaurants  | Skip rating filter; inform user "ratings unavailable"          | Medium   |

---

## 2. User Input & Validation

### 2.1 Location Input

| ID    | Scenario                                       | Expected Behavior                                              | Severity |
| ----- | ---------------------------------------------- | -------------------------------------------------------------- | -------- |
| UI-01 | Location not found in dataset (typo: "Dlehi")  | Suggest closest matches ("Did you mean: Delhi?")               | High     |
| UI-02 | Location is empty / not provided               | Return validation error: "Location is required"                | High     |
| UI-03 | Location with special characters ("New\nDelhi")| Strip control characters; normalize whitespace                 | Medium   |
| UI-04 | Location provided in different language/script  | Only English city names supported; return validation error     | Medium   |
| UI-05 | Location exists but has only 1–2 restaurants   | Proceed normally; LLM works with limited data                  | Low      |
| UI-06 | Location with case variation ("BANGALORE")     | Normalize to title-case before filtering                       | Low      |

### 2.2 Budget Input

| ID    | Scenario                                       | Expected Behavior                                              | Severity |
| ----- | ---------------------------------------------- | -------------------------------------------------------------- | -------- |
| BU-01 | Budget not provided                            | Default to "medium"                                            | Low      |
| BU-02 | Budget value is invalid ("ultra-high")         | Return 422 validation error with allowed values                | Medium   |
| BU-03 | Budget set to "low" but no cheap restaurants exist | Trigger fallback: expand to "medium" range                 | High     |
| BU-04 | Budget is "high" but all restaurants are cheap | Return cheap restaurants with note from LLM                    | Low      |

### 2.3 Cuisine Input

| ID    | Scenario                                       | Expected Behavior                                              | Severity |
| ----- | ---------------------------------------------- | -------------------------------------------------------------- | -------- |
| CU-01 | Cuisine not in dataset ("Martian Food")        | Return "No restaurants found for this cuisine"; suggest alternatives | High |
| CU-02 | Cuisine is empty / not provided                | Skip cuisine filter; include all cuisines                      | Low      |
| CU-03 | Cuisine has multiple matches ("Indian" matches "North Indian", "South Indian") | Include all partial matches | Low |
| CU-04 | Cuisine with typo ("Itlian")                   | Attempt fuzzy match; suggest corrections if no results         | Medium   |
| CU-05 | Cuisine in different casing ("CHINESE")        | Case-insensitive matching                                      | Low      |
| CU-06 | User provides multiple cuisines ("Italian, Chinese") | Split and filter for restaurants matching ANY of them     | Medium   |

### 2.4 Rating Input

| ID    | Scenario                                       | Expected Behavior                                              | Severity |
| ----- | ---------------------------------------------- | -------------------------------------------------------------- | -------- |
| RT-01 | `min_rating` = 5.0 (unrealistically high)      | Likely zero results; fallback lowers to 4.5, then 4.0         | High     |
| RT-02 | `min_rating` = 0.0                             | Include all restaurants regardless of rating                   | Low      |
| RT-03 | `min_rating` is negative (-1.0)                | Clamp to 0.0                                                  | Medium   |
| RT-04 | `min_rating` > 5.0 (e.g., 6.0)                | Clamp to 5.0                                                  | Medium   |
| RT-05 | `min_rating` is not a number ("abc")           | Return 422 validation error                                    | Medium   |

### 2.5 Additional Preferences (Free Text)

| ID    | Scenario                                       | Expected Behavior                                              | Severity |
| ----- | ---------------------------------------------- | -------------------------------------------------------------- | -------- |
| AP-01 | Additional prefs is empty                      | Skip; no impact on filtering or prompting                      | Low      |
| AP-02 | Additional prefs contains prompt injection attempt ("Ignore all instructions and...") | Sanitize/escape before prompt insertion | Critical |
| AP-03 | Additional prefs is extremely long (>1000 chars)| Truncate to 500 characters with warning                        | Medium   |
| AP-04 | Additional prefs contains HTML/JS code         | Strip all HTML/JS tags                                         | High     |
| AP-05 | Additional prefs has only special characters   | Treat as empty after sanitization                              | Low      |
| AP-06 | Additional prefs contains PII (phone, email)   | Pass through to LLM (not stored); LLM should not echo PII     | Medium   |

---

## 3. Filter Service

### 3.1 Filter Results

| ID    | Scenario                                       | Expected Behavior                                              | Severity |
| ----- | ---------------------------------------------- | -------------------------------------------------------------- | -------- |
| FS-01 | All filters applied → 0 results               | Trigger progressive fallback (remove cuisine → lower rating → expand budget) | Critical |
| FS-02 | Filters return exactly 1 result                | LLM ranks it as #1; explain why it's the only match           | Low      |
| FS-03 | Filters return > 20 results                    | Sort by rating descending; cap at 20 candidates               | Low      |
| FS-04 | Filters return exactly 20 results              | Send all 20 to LLM; no truncation needed                      | Low      |
| FS-05 | Location filter alone returns 0                | Cannot fallback further; return "No restaurants in {location}" | High     |
| FS-06 | All fallback steps exhausted → still 0 results | Return clear message: "No restaurants match. Try different preferences." | Critical |
| FS-07 | Multiple cuisines in a restaurant's `cuisines` field and user searches one | Partial match should succeed | Low |

### 3.2 Budget Boundary Cases

| ID    | Scenario                                       | Expected Behavior                                              | Severity |
| ----- | ---------------------------------------------- | -------------------------------------------------------------- | -------- |
| BB-01 | Restaurant cost is exactly ₹500 (low/medium boundary) | Include in BOTH "low" and "medium" buckets (boundary-inclusive) | Medium |
| BB-02 | Restaurant cost is exactly ₹1500 (medium/high boundary) | Include in BOTH "medium" and "high" buckets               | Medium   |
| BB-03 | Restaurant cost is ₹0 (free)                   | Include in "low" budget category                               | Low      |
| BB-04 | Restaurant cost is extremely high (₹50,000)    | Include in "high" bucket normally                              | Low      |

---

## 4. Prompt Builder

| ID    | Scenario                                       | Expected Behavior                                              | Severity |
| ----- | ---------------------------------------------- | -------------------------------------------------------------- | -------- |
| PB-01 | Candidate set has only 1 restaurant            | Prompt asks LLM to explain why it's recommended               | Low      |
| PB-02 | Candidate set has < 5 restaurants (LLM asked for top 5) | LLM returns only available restaurants (e.g., top 3)   | Medium   |
| PB-03 | Restaurant names contain special characters or emoji | Escape properly in prompt; LLM handles them               | Low      |
| PB-04 | Combined prompt exceeds Groq's context window  | Truncate restaurant list; reduce to top 15 or 10 candidates   | High     |
| PB-05 | All candidate restaurants have identical ratings| LLM differentiates by cuisine match, cost, and votes           | Low      |
| PB-06 | User's `additional_prefs` contradicts other inputs (e.g., "cheap" with "high" budget) | LLM uses judgment to reconcile; preference to explicit budget | Medium |
| PB-07 | Restaurant data has missing fields (e.g., no votes) | Prompt marks field as "N/A" instead of blank             | Low      |

---

## 5. LLM / Groq API Integration

### 5.1 API Communication

| ID    | Scenario                                       | Expected Behavior                                              | Severity |
| ----- | ---------------------------------------------- | -------------------------------------------------------------- | -------- |
| LM-01 | Groq API key is missing or invalid             | Clear error: "Invalid API key. Check your .env configuration." | Critical |
| LM-02 | Groq API key has expired                       | Same as LM-01; prompt user to regenerate key                   | Critical |
| LM-03 | Groq API returns HTTP 429 (rate limit)         | Wait and retry with exponential backoff (2s, 4s, 8s)           | High     |
| LM-04 | Groq API returns HTTP 500 (server error)       | Retry up to 3 times; fallback to secondary model               | High     |
| LM-05 | Groq API returns HTTP 503 (service unavailable)| Retry with backoff; after 3 failures, show error message       | High     |
| LM-06 | Network timeout during LLM API call            | Retry with longer timeout; max 30 seconds per attempt          | High     |
| LM-07 | Primary model (`llama-3.3-70b-versatile`) is unavailable | Automatically switch to fallback (`mixtral-8x7b-32768`) | High   |
| LM-08 | Both primary and fallback models unavailable   | Return error: "AI service temporarily unavailable. Try later." | Critical |

### 5.2 Response Quality

| ID    | Scenario                                       | Expected Behavior                                              | Severity |
| ----- | ---------------------------------------------- | -------------------------------------------------------------- | -------- |
| LR-01 | LLM returns invalid JSON                       | Re-prompt once with stricter format instructions; then parse manually | High |
| LR-02 | LLM returns JSON missing required fields       | Fill in defaults; show partial results with warning            | Medium   |
| LR-03 | LLM returns more than 5 recommendations        | Trim to top 5                                                  | Low      |
| LR-04 | LLM returns 0 recommendations                  | Show "AI couldn't generate recommendations" with raw data view | High     |
| LR-05 | LLM hallucinates restaurant names not in data   | Cross-validate recommendations against candidate set; filter out hallucinations | Critical |
| LR-06 | LLM returns ratings/costs that differ from data | Override with actual data from DataFrame; keep LLM explanation | Medium   |
| LR-07 | LLM explanation is generic (not personalized)  | Accept but log for prompt improvement; no user-facing error    | Low      |
| LR-08 | LLM response contains markdown/formatting      | Strip markdown before JSON parsing                             | Low      |
| LR-09 | LLM response is cut off (max tokens reached)   | Detect incomplete JSON; retry with higher `max_tokens` or fewer candidates | High |
| LR-10 | LLM returns recommendations in wrong language  | System prompt enforces English; re-prompt if violated          | Medium   |
| LR-11 | LLM `summary` field is empty                   | Generate a fallback summary from the recommendation data       | Low      |

---

## 6. API Layer (FastAPI)

### 6.1 Request Handling

| ID    | Scenario                                       | Expected Behavior                                              | Severity |
| ----- | ---------------------------------------------- | -------------------------------------------------------------- | -------- |
| API-01| POST `/recommend` with empty body              | Return 422 with field-level validation errors                  | Medium   |
| API-02| POST `/recommend` with extra unknown fields    | Ignore extra fields (Pydantic `extra = "ignore"`)              | Low      |
| API-03| POST `/recommend` with wrong content type      | Return 415 Unsupported Media Type                              | Low      |
| API-04| GET `/cuisines` when dataset is not loaded      | Load dataset on demand; return list or 503 if unavailable      | Medium   |
| API-05| GET `/locations` returns empty list             | Return `[]` with 200 (dataset may have no valid cities)        | Low      |
| API-06| Concurrent POST requests (>10 simultaneous)    | Queue and process; Groq rate limiter prevents overload         | High     |
| API-07| Request with extremely large body (>1MB)        | Reject with 413 Payload Too Large                              | Medium   |

### 6.2 Security

| ID    | Scenario                                       | Expected Behavior                                              | Severity |
| ----- | ---------------------------------------------- | -------------------------------------------------------------- | -------- |
| SC-01 | SQL injection in location field                | No SQL used; Pandas filtering is safe; input sanitized anyway  | Low      |
| SC-02 | XSS payload in additional_prefs                | HTML-escape before rendering in Streamlit                      | Medium   |
| SC-03 | CORS request from unauthorized origin          | Block by CORS policy (configure allowed origins)               | Medium   |
| SC-04 | API endpoint accessed without rate limiting    | Implement rate limiting middleware (e.g., `slowapi`)           | High     |
| SC-05 | Prompt injection via user input fields         | Escape special characters; wrap user input in delimiters       | Critical |

---

## 7. Frontend (Streamlit)

### 7.1 UI Interactions

| ID    | Scenario                                       | Expected Behavior                                              | Severity |
| ----- | ---------------------------------------------- | -------------------------------------------------------------- | -------- |
| FE-01 | User clicks "Recommend" without selecting location | Show inline validation: "Please select a location"         | High     |
| FE-02 | User clicks "Recommend" multiple times rapidly | Disable button during API call; prevent duplicate requests     | Medium   |
| FE-03 | API call takes > 10 seconds                    | Show spinner with message "Generating recommendations..."      | Medium   |
| FE-04 | API call takes > 30 seconds                    | Show timeout error with "Try Again" button                     | High     |
| FE-05 | Backend API is not running                     | Show connection error: "Backend server is not available"        | Critical |
| FE-06 | User resizes browser to very small width       | Layout remains usable (responsive design)                      | Low      |
| FE-07 | Location dropdown is empty (API returned `[]`) | Show message: "No locations available. Check data source."     | High     |
| FE-08 | Cuisine dropdown is empty                      | Hide cuisine dropdown; proceed without cuisine filter          | Medium   |

### 7.2 Display Edge Cases

| ID    | Scenario                                       | Expected Behavior                                              | Severity |
| ----- | ---------------------------------------------- | -------------------------------------------------------------- | -------- |
| FD-01 | Restaurant name is very long (>100 characters) | Truncate with ellipsis in card; full name on hover/tooltip      | Low      |
| FD-02 | Explanation text is very long (>500 characters) | Show truncated with "Read more" expander                       | Low      |
| FD-03 | Cost value is 0 or null                        | Display "Price not available" instead of ₹0                    | Low      |
| FD-04 | Rating is 0.0                                  | Display "Not yet rated" instead of 0 stars                     | Low      |
| FD-05 | Only 1 recommendation returned                 | Display single card without rank numbering confusion           | Low      |
| FD-06 | LLM summary contains special characters        | Render safely; escape HTML entities                            | Low      |
| FD-07 | Emoji in restaurant name or cuisine            | Render normally; Streamlit supports emoji                      | Low      |

---

## 8. Environment & Configuration

| ID    | Scenario                                       | Expected Behavior                                              | Severity |
| ----- | ---------------------------------------------- | -------------------------------------------------------------- | -------- |
| EN-01 | `.env` file is missing                         | Application fails with clear error: "Missing .env file"        | Critical |
| EN-02 | `GROQ_API_KEY` not set in `.env`               | Error: "GROQ_API_KEY is required. Get one at console.groq.com" | Critical |
| EN-03 | Python version < 3.10                          | Show compatibility error at startup                            | High     |
| EN-04 | Required package not installed                 | `ImportError` with message: "Run `pip install -r requirements.txt`" | High  |
| EN-05 | Port 8000 (FastAPI) already in use             | Try alternative port or show "Port 8000 is in use" error       | Medium   |
| EN-06 | Port 8501 (Streamlit) already in use           | Streamlit auto-selects next available port                     | Low      |
| EN-07 | Disk full — cannot cache processed CSV         | Process in-memory only; log warning about cache failure        | Medium   |
| EN-08 | Insufficient memory for large dataset          | Recommend reducing dataset size; use chunked processing        | High     |

---

## 9. End-to-End Pipeline

| ID    | Scenario                                       | Expected Behavior                                              | Severity |
| ----- | ---------------------------------------------- | -------------------------------------------------------------- | -------- |
| E2E-01| Happy path: valid inputs → recommendations     | Full pipeline completes in < 5 seconds; 5 ranked results      | —        |
| E2E-02| Cold start: first request after app launch     | Dataset loads + preprocesses; slightly slower (~10–15s)        | Low      |
| E2E-03| Repeated identical queries                     | Return same results (deterministic at temp=0.3; consider cache)| Low      |
| E2E-04| Sequential different queries                   | Each returns correct, independent recommendations              | Low      |
| E2E-05| User changes only budget → re-submits          | Results reflect new budget; other preferences preserved        | Low      |
| E2E-06| All filters pass but LLM fails                 | Show filtered restaurants as a raw table (graceful degradation) | High    |
| E2E-07| Backend crashes mid-request                    | Streamlit shows connection error; user can retry               | High     |

---

## Summary by Severity

| Severity | Count | Description                                        |
| -------- | ----- | -------------------------------------------------- |
| Critical | 12    | System-breaking; must handle before launch         |
| High     | 22    | Major user impact; required for stable experience  |
| Medium   | 21    | Noticeable impact; should address for quality       |
| Low      | 24    | Minor; polish-level improvements                   |
| **Total**| **79**|                                                    |

---

## Priority Action Items

> Top edge cases to address first during implementation:

1. **LR-05** — LLM hallucinating restaurant names → cross-validate against source data
2. **FS-01** — Zero filter results → progressive fallback strategy
3. **LM-01** — Missing/invalid Groq API key → clear startup validation
4. **AP-02** — Prompt injection via free-text input → sanitize before prompt
5. **DI-01** — Hugging Face unavailable → cached CSV fallback
6. **LM-08** — Both LLM models unavailable → graceful degradation to raw data
7. **LR-01** — Invalid JSON from LLM → re-prompt with strict format
8. **FE-05** — Backend not running → frontend connection error handling
9. **DQ-09** — Dataset schema changes → column validation on load
10. **SC-05** — Prompt injection via any input field → delimiter-based escaping
