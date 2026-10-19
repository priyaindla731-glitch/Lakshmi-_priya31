# Lakshmi-_priya31
A multilingual AI-powered event marketplace for planning celebrations and connecting customers with trusted local vendors.

## Run locally

Install the Python dependencies and start the Flask application:

```powershell
python -m pip install -r requirements.txt
python run.py
```

Open http://localhost:3000. Flask serves the frontend in `frontend/` and the API from `backend/`.

## Deploy on Render

1. Push this project to a GitHub repository.
2. In Render, choose **New +** and **Blueprint**.
3. Connect the GitHub repository containing this project. Render reads `render.yaml` and creates the web service.
4. Wait for the deployment to finish, then open the `onrender.com` URL shown on the service page.

The current Blueprint uses Render's free web-service plan. Its SQLite database is on temporary storage, so accounts and other changes can be lost when the service restarts or redeploys. For persistent data, use a paid Render plan with a persistent disk, or move the database to a managed database before relying on it. Demo accounts/data are disabled in production.
