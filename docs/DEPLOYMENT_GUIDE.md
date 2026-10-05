# AirGuard Agent — Production Deployment Guide (Render & Vercel)

This guide provides step-by-step instructions to deploy **AirGuard Agent** on **Render** (Recommended for Full-Stack Python & ML) and **Vercel**.

---

## 🚀 Option 1: Deploy on Render (Recommended — Full-Stack Python + ML)

Render is the best platform for AirGuard Agent because it natively supports Python 3.11, persistent memory, Gunicorn WSGI workers, and scikit-learn machine learning ensembles with zero size or timeout restrictions.

### Step-by-Step Instructions:

1. **Sign in to Render**:
   - Go to [https://render.com](https://render.com) and click **Get Started** or **Log In**.
   - Log in using your **GitHub account** (`Tejas-Ranjeet`).

2. **Create New Web Service**:
   - On the Render Dashboard, click the blue **New +** button in the top right.
   - Select **Web Service**.

3. **Connect Your GitHub Repository**:
   - In the repository search box, find and select:  
     `Tejas-Ranjeet/WCC-Launchpad-30`
   - Click **Connect**.

4. **Configure Service Settings**:
   - **Name**: `airguard-agent` (or your preferred name)
   - **Region**: `Oregon (US West)` (or `Frankfurt / Singapore`)
   - **Branch**: `main`
   - **Root Directory**: *(Leave blank)*
   - **Runtime**: `Python 3`
   - **Build Command**:
     ```bash
     pip install -r requirements.txt && python scripts/seed_demo.py
     ```
   - **Start Command**:
     ```bash
     gunicorn app:app --workers 2 --threads 4 --timeout 120 --bind 0.0.0.0:$PORT
     ```
   - **Instance Type**: Select **Free** ($0/month).

5. **Set Environment Variables**:
   Click **Advanced** -> **Add Environment Variable** and add:
   - `PYTHON_VERSION`: `3.11.5`
   - `SECRET_KEY`: *(Click "Generate" or enter a secure random string)*
   - `LLM_PROVIDER`: `MOCK` *(Default resilient clinical engine; set to `GEMINI` if providing an API key)*
   - *(Optional)* `GEMINI_API_KEY`: *(Your Google AI Studio key if using Gemini)*
   - `FLASK_ENV`: `production`

6. **Deploy**:
   - Click the green **Create Web Service** button at the bottom.
   - Render will build the environment, seed the 30-day demo profile (`alex@example.com`), and start the Gunicorn server.
   - In 2–3 minutes, your application will be live at:  
     `https://airguard-agent.onrender.com` (or your chosen service name).

---

## ⚡ Option 2: Deploy on Vercel (Edge CDN + Reverse Proxy)

Vercel functions have a strict 500 MB bundle size limit, whereas heavy ML libraries (XGBoost + CUDA + Scipy + Scikit-Learn) total ~844 MB. 

To achieve optimal speed and reliability, the repository uses **Vercel as an Edge CDN Frontend** that serves the dashboard globally in sub-milliseconds and seamlessly reverse-proxies all `/api/*`, `/predict`, and profile routes to your live Render backend (`https://wcc-launchpad-30.onrender.com`).

### Step-by-Step Instructions:

1. **Sign in to Vercel**:
   - Go to [https://vercel.com](https://vercel.com) and log in with your **GitHub account**.

2. **Import Repository**:
   - Click **Add New...** -> **Project**.
   - Find `Tejas-Ranjeet/WCC-Launchpad-30` in the list and click **Import**.

3. **Configure Project**:
   - **Framework Preset**: `Other`
   - **Root Directory**: `./` *(default)*
   - **Build Command**: *(None needed - static deployment)*
   - **Output Directory**: *(None needed)*

4. **Click Deploy**:
   - Click **Deploy**.
   - Vercel deploys the application in under **10 seconds** with zero function bundle size errors!
   - Your frontend will be live on Vercel's Edge network (e.g. `https://wcc-launchpad-30.vercel.app`), with all real-time ML decisions, diaries, and agent actions powered by your live Render service.

---

## 🛠️ Verification After Deployment

Once deployed (on either Render or Vercel), verify your live deployment:

1. **Health Check**:
   - Open: `https://<YOUR-APP-URL>/health`
   - Should return: `{"success": true, "status": "healthy", "service": "AirGuard Decision Engine", ...}`

2. **Web Dashboard**:
   - Open: `https://<YOUR-APP-URL>/`
   - Confirm the landing page, risk gauge, and AQI forecast load cleanly.
   - Click **Demo Patient** (or sign in with `alex@example.com` / `demo123`) to access the proactive agent co-pilot.

3. **Interactive Agent Test**:
   - Open Chat and ask: *"Can I go for a morning run?"*
   - Test Emergency Red-Flag Interceptor: *"I can't speak in full sentences"* -> Confirm Emergency SOS modal displays 112/108 calling links.
