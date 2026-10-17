# Deploying StratumAI

Backend (FastAPI) goes to **Render** and is built from `backend/Dockerfile`.
Frontend (Next.js) goes to **Vercel**.

Do them in this order: you need the Render URL before you set up Vercel.

## Before you start

- The code is pushed to GitHub (`Emon3469/StratumAI`, branch `main`).
- You have at least one LLM key: Groq, OpenAI, Anthropic or Gemini.
- You have a Gemini key for embeddings, plus a Qdrant Cloud cluster URL and API key.
- The knowledge base is indexed in Qdrant. If it isn't yet, run this once from your PC (see README "Running locally"):

  ```bash
  python -m app.ingestion.processor DATA/true_data --recreate
  ```

## Part 1: Backend on Render

1. Go to https://dashboard.render.com and choose **New → Blueprint**.
2. Connect GitHub and select the `StratumAI` repo, branch `main`.
   Render reads `render.yaml` and shows one service, `stratumai-api` (Docker, free plan).
3. Render asks for the secret values (the keys marked `sync: false`). Fill them in:

   | Key | Value |
   | --- | --- |
   | `ALLOWED_ORIGINS` | `http://localhost:3000` for now. You'll replace it in Part 3. |
   | `GROQ_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` | Your keys. Leave a provider empty if you don't use it. |
   | `QDRANT_CLUSTER_ENDPOINT` | e.g. `https://xxxx.cloud.qdrant.io:6333` |
   | `QDRANT_API_KEY` | Your Qdrant key |
   | `LOGFIRE_TOKEN` | Optional. Leave empty if you don't use it. |

   > Paste the values with no quotes and no spaces around them.
4. Click **Apply**. The first Docker build takes about 5–10 minutes.
5. When the build finishes, copy the service URL, e.g. `https://stratumai-api.onrender.com`.
6. Check that it works by opening `https://stratumai-api.onrender.com/health` in a browser. You should get an OK response.

Notes:
- You don't need to set `PORT`. Render sets it, and the Dockerfile reads it.
- On the free plan the service sleeps after 15 minutes without traffic. The first request after that takes about 30–60 seconds.

## Part 2: Frontend on Vercel

1. Go to https://vercel.com/new and import the `StratumAI` repo.
2. **Root Directory**: click *Edit* and choose `frontend`. **This step is the one people most often miss.**
3. **Framework Preset**: Next.js (Vercel detects it). Leave the build and output settings at their defaults.
4. **Environment Variables**: add one variable:

   | Key | Value |
   | --- | --- |
   | `NEXT_PUBLIC_API_URL` | Your Render URL from Part 1, e.g. `https://stratumai-api.onrender.com` |

   > Don't add a trailing `/` or `/api`. Use the bare `https://...onrender.com`.
5. Click **Deploy**. When it finishes, copy your site URL, e.g. `https://stratumai.vercel.app`.

If you change `NEXT_PUBLIC_API_URL` later, redeploy (Deployments → ⋯ → Redeploy). The value is baked in at build time.

## Part 3: Connect the two (CORS)

1. In Render, open **stratumai-api → Environment**.
2. Set `ALLOWED_ORIGINS` to your Vercel URL, e.g. `https://stratumai.vercel.app` (no trailing `/`).
   For more than one origin, separate them with commas: `https://stratumai.vercel.app,https://my-domain.com`
3. Click **Save, rebuild and deploy**.

`*.vercel.app` preview URLs are already allowed through `ALLOWED_ORIGIN_REGEX`, so you only need this step for your main URL and any custom domain.

## Part 4: Test

1. Open your Vercel URL and ask a question, e.g. "How do I autoscale pods?"
2. You should get a streamed answer with sources.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| Vercel build: "No Next.js version detected" | Root Directory isn't set to `frontend` (Part 2, step 2). |
| Browser console: CORS error | `ALLOWED_ORIGINS` on Render doesn't exactly match your Vercel URL (check `https`, no trailing `/`), or you didn't redeploy after changing it. |
| Frontend calls `localhost:8000` | `NEXT_PUBLIC_API_URL` wasn't set before the build. Set it and redeploy. |
| First answer is very slow | The free Render service was asleep. Wait about a minute. |
| Answers have no sources | Qdrant isn't indexed or the Qdrant keys are wrong. Check `https://<render-url>/api/status`. |
| Render deploy fails the health check | Open Render → Logs. Usually a missing or misspelled env var. |

## Updating later

Push to `main`. Render and Vercel both redeploy automatically.
