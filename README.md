# Energy-Aware AI Cloud Deployment

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/frm6h29fw7-netizen/Energy-Aware-AI-Cloud-deployment)

A final-year project prototype for evaluating energy-aware AI model deployment choices across cloud execution styles.

The application helps compare deployment options using estimated energy use, carbon impact, latency, cost, accuracy retention, throughput, utilisation, and operational risk. It includes a responsive dashboard, simulator, sign-in flow, optional MongoDB storage, and APX Assistant for project-focused guidance.

## Quick Start

### GitHub Codespaces

1. Click the `Open in GitHub Codespaces` button above.
2. Wait for the container setup to finish.
3. Open the forwarded port named `Energy-Aware AI Dashboard`.

Codespaces installs the Python requirements and starts the backend automatically on port `8080`.

If it does not start automatically, run:

```bash
python3 backend/server.py
```

### Local Development

```bash
python3 -m pip install -r requirements.txt
python3 backend/server.py
```

Then open:

```text
http://localhost:8080
```

## Features

- Responsive web dashboard for energy-aware AI deployment evaluation.
- Python backend API for simulator calculations and saved experiments.
- Sign-in and sign-up flow with password hashing.
- APX Assistant with local fallback responses and optional OpenAI support.
- Optional MongoDB support for users, experiments, assistant chats, simulator reports, and backend events.
- Codespaces configuration for easier tutor review and demonstration.

## Project Structure

```text
.
├── .devcontainer/          GitHub Codespaces configuration
├── backend/                Python server, simulator, and energy model
├── frontend/               HTML, CSS, and JavaScript dashboard UI
├── scripts/                Optional MongoDB import/migration scripts
├── .env.example            Example environment configuration
├── requirements.txt        Python dependencies
└── README.md               Project guide
```

## Optional MongoDB

The project runs without MongoDB by using local JSON/CSV fallback storage. To use MongoDB, set these environment variables before starting the backend:

```bash
MONGODB_URI="mongodb://127.0.0.1:27017"
MONGODB_NAME="energy_aware_ai"
python3 backend/server.py
```

MongoDB collections used by the backend:

- `users`
- `experiments`
- `simulator_reports`
- `assistant_chats`
- `backend_events`

## Optional OpenAI Assistant

APX Assistant works without OpenAI by using the built-in project-focused fallback. To enable OpenAI-backed responses, run:

```bash
OPENAI_API_KEY="your_api_key_here" OPENAI_MODEL="gpt-5.2" OPENAI_ENABLE_WEB="true" python3 backend/server.py
```

Keep API keys on the backend only. Do not place secrets in frontend files.

## Scope

This is a decision-support prototype. It does not directly measure real data-centre electricity consumption and it does not train a new AI model. Instead, it estimates and compares deployment scenarios using energy-aware metrics that are relevant to cloud AI inference workloads.

Local runtime data, report drafts, templates, and evidence files are intentionally ignored by Git so the repository stays focused on the runnable application.
