# Energy-Aware AI Cloud Deployment

This is a final-year project prototype for evaluating **energy-aware AI model deployment in cloud environments**.

## What The Project Does

- Shows a professional website dashboard.
- Runs a Python backend server.
- Provides an API for energy, carbon, latency, accuracy, cost, throughput, and risk calculations.
- Requires sign-in and terms acceptance before using the dashboard.
- Saves experiments under the signed-in username.
- Supports optional MongoDB storage for user accounts, experiment history, simulator reports, APX Assistant chats, and backend events.
- Includes APX Assistant, which can use OpenAI when `OPENAI_API_KEY` is configured and falls back to a local rule-based advisor when it is not.
- Gives deployment recommendations.
- Saves experiment history into `experiment-history.csv`.
- Includes a simple Python console simulator for VS Code evidence.

## Best Way To Run It

1. Open this folder in VS Code.

2. Run the backend:

   ```bash
   python3 server.py
   ```

3. Open this in your browser:

   `http://localhost:8080`

4. Sign in, accept the terms and conditions, use the simulator, and click `Save experiment`.

## Optional MongoDB Setup

The project works without MongoDB by using `user-accounts.json`, `experiment-history.csv`, and local JSON evidence files.
For extra full-stack evidence, install `pymongo` and run MongoDB locally:

```bash
python3 -m pip install -r requirements.txt
```

Then start MongoDB and run the server. By default it uses:

```text
mongodb://127.0.0.1:27017
```

You can override this with:

```bash
MONGODB_URI="mongodb://127.0.0.1:27017" MONGODB_NAME="energy_aware_ai" python3 server.py
```

MongoDB collections used by the backend:

- `users`: sign-up account records with hashed passwords
- `experiments`: saved simulator experiment values
- `simulator_reports`: dissertation-style summaries for saved scenarios
- `assistant_chats`: APX Assistant questions, answers, and scenario snapshots
- `backend_events`: sign-up, login, logout, assistant, and save events

## Optional OpenAI Assistant Setup

APX Assistant works without OpenAI by using the local rule-based project advisor.
To make it behave more like a real AI chatbot, set an OpenAI API key on the backend:

```bash
OPENAI_API_KEY="your_api_key_here" OPENAI_MODEL="gpt-5.2" OPENAI_ENABLE_WEB="true" python3 server.py
```

Keep the API key on the backend only. Do not put it in `app.js` or expose it in browser code.
The assistant is intentionally scoped to this website and project, so it should answer only about simulator results, deployment trade-offs, backend/MongoDB evidence, limitations, screenshots, and project explanation.
When `OPENAI_ENABLE_WEB` is `true`, OpenAI can use web search for current project-related information and the UI displays source URLs as clickable links.

## Project Scope

This is not a basic static website. It is a prototype web application with a Python backend. The system evaluates deployment scenarios for AI inference workloads and compares virtual machine, container, and serverless deployments using indirect energy-aware metrics.

The project does not train a new deep learning model because that would require more data, hardware, and time. Instead, it focuses on deployment evaluation, which matches the literature review topic. The prototype demonstrates how cloud AI deployments can be assessed using energy, carbon, latency, accuracy retention, utilisation, and cost.

The system should be described as a simulator and decision-support prototype. It does not directly measure physical data-centre electricity usage.

## Main Files

- `index.html`: website structure
- `styles.css`: dashboard design
- `app.js`: frontend logic and charts
- `server.py`: Python backend and API
- `energy_model.py`: Python energy-aware deployment model
- `simulator.py`: Python console simulator
- `requirements.txt`: optional Python package list for MongoDB support

Local runtime files such as account records, assistant chat history, backend events, simulator reports, and experiment CSV exports are ignored by Git to avoid uploading private data.
