# Deployment Plan: AI-Powered Restaurant Recommendation System

This document outlines the step-by-step process to deploy the backend API on **Railway** and the frontend application on **Vercel**.

## 1. Pre-Deployment Preparation

Before deploying, we need to ensure the frontend can dynamically connect to the backend, rather than relying on `localhost`.

### Update Frontend API URL
Currently, `frontend/app.js` hardcodes the backend URL as `http://127.0.0.1:8000`. Once the backend is deployed on Railway, you must update this to the live Railway URL.

**Action Required:**
1. Once Railway gives you a public URL (e.g., `https://my-backend.up.railway.app`), open `frontend/app.js`.
2. Find the lines making API calls (e.g., `fetch('http://127.0.0.1:8000/api/v1/recommend')`).
3. Replace `http://127.0.0.1:8000` with your new Railway URL.

---

## 2. Deploying the Backend on Railway

Railway natively supports Python and will automatically detect the `requirements.txt` file at the root of your repository.

### Step-by-Step Instructions:
1. **Log in to Railway** (https://railway.app/) and click **"New Project"**.
2. Select **"Deploy from GitHub repo"** and choose your repository: `super-duper-bassoon`.
3. Railway will analyze the repository and start building. 
4. **Configure Environment Variables:**
   - Go to your newly created service in the Railway dashboard.
   - Click on the **Variables** tab.
   - Add a new variable: 
     - **Name:** `GROQ_API_KEY`
     - **Value:** *(Paste your Groq API key here)*
5. **Set the Start Command (if not automatically detected):**
   - Go to the **Settings** tab.
   - Scroll down to the "Deploy" section and find the "Start Command".
   - Enter: `python -m uvicorn src.main:app --host 0.0.0.0 --port $PORT`
6. **Generate a Public Domain:**
   - Still in the **Settings** tab, scroll to the "Networking" section.
   - Click **"Generate Domain"**. This is your live backend URL (e.g., `https://super-duper-bassoon-production.up.railway.app`).

> [!IMPORTANT]
> Copy the generated Railway domain. You will need to paste this into your `frontend/app.js` as mentioned in step 1.

---

## 3. Deploying the Frontend on Vercel

Vercel is perfect for static frontends. Since your frontend is located in a specific folder (`frontend`), you just need to tell Vercel which folder to serve.

### Step-by-Step Instructions:
1. **Commit and Push:** Make sure you have updated the backend URL in `frontend/app.js` and pushed those changes to GitHub.
2. **Log in to Vercel** (https://vercel.com/) and click **"Add New..." -> "Project"**.
3. Import your GitHub repository: `super-duper-bassoon`.
4. **Configure the Project:**
   - **Framework Preset:** Leave it as "Other" (since it's Vanilla JS/HTML).
   - **Root Directory:** Click "Edit" and select the `frontend` folder.
   - **Build and Output Settings:** Leave these blank/default, as there is no build step required for static HTML/JS.
5. Click **Deploy**.

Vercel will quickly deploy your frontend and provide you with a live, shareable URL.

---

## 4. Post-Deployment Verification

1. Open your Vercel frontend URL in a browser.
2. Verify that the Location and Cuisine dropdowns are populated correctly (this confirms the frontend is successfully fetching data from the Railway backend).
3. Submit a search query and verify that the AI recommendations are generated and displayed properly with the estimated costs.

> [!TIP]
> If you run into issues with the frontend not fetching data, open the browser's Developer Tools (F12) -> Console / Network tab. Ensure the API requests are being sent to the correct Railway URL and that there are no CORS errors. (CORS is already configured to allow `["*"]` in your FastAPI `main.py`, so it should work smoothly!)
