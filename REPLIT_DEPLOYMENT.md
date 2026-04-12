# Replit Deployment Guide

## 1. Prepare repository
1. Ensure `.env` is not tracked by git.
2. Keep secrets only in Replit Secrets.
3. Push latest code to GitHub.

## 2. Import into Replit
1. Open Replit and choose **Import from GitHub**.
2. Select this repository.
3. Wait for dependency install.

## 3. Configure Secrets (left sidebar lock icon)
Add keys as needed:
- `GOOGLE_API_KEY`
- `COHERE_API_KEY`
- `TOGETHER_API_KEY`
- `HF_API_KEY`
- `GROQ_API_KEY`
- `GITHUB_MODELS_TOKEN`

## 4. Run app
Click **Run**. Replit will execute:

```bash
streamlit run app.py --server.address 0.0.0.0 --server.port 3000
```

## 5. Verify functionality
1. Upload one PDF.
2. Click `執行 Embedding`.
3. Ask one question and confirm answer quality.
4. Test `清除目前 Embedding 快取（Provider + Model）`.

## 6. Persistence and sleep behavior
- Replit free deployments may sleep.
- Waking may lose local vector cache (`./data/chroma_db_*`).
- If cache is missing after wake-up, re-run embedding.

## 7. Security notes for interview
- Secrets are managed in Replit Secrets, not in repository files.
- Browser localStorage is convenience-only and should not be treated as server secret storage.
- Chroma cache is a rebuildable artifact, not the source of truth.
