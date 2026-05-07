from __future__ import annotations

from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from http.cookies import SimpleCookie
import base64
import hashlib
import hmac
import json
import os
import secrets
import re
import urllib.error
import urllib.request

from energy_model import ensure_history_file, evaluate, load_history, save_history

try:
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError, ServerSelectionTimeoutError
except ImportError:  # MongoDB is optional; the project still runs with JSON/CSV fallback.
    MongoClient = None
    PyMongoError = Exception
    ServerSelectionTimeoutError = Exception

try:
    import certifi
except ImportError:
    certifi = None


PORT = int(os.environ.get("PORT", "8080"))
HOST = os.environ.get("HOST", "0.0.0.0")
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
HISTORY_FILE = PROJECT_ROOT / "experiment-history.csv"
USERS_FILE = PROJECT_ROOT / "user-accounts.json"
ASSISTANT_HISTORY_FILE = PROJECT_ROOT / "assistant-history.json"
REPORTS_FILE = PROJECT_ROOT / "simulator-reports.json"
BACKEND_EVENTS_FILE = PROJECT_ROOT / "backend-events.json"
MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://127.0.0.1:27017")
MONGODB_NAME = os.environ.get("MONGODB_NAME", "energy_aware_ai")
MONGODB_TIMEOUT_MS = int(os.environ.get("MONGODB_TIMEOUT_MS", "10000"))
MONGODB_TLS_ALLOW_INVALID_CERTIFICATES = os.environ.get("MONGODB_TLS_ALLOW_INVALID_CERTIFICATES", "false").lower() == "true"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.2")
OPENAI_ENABLE_WEB = os.environ.get("OPENAI_ENABLE_WEB", "true").lower() == "true"
SESSIONS: dict[str, dict[str, str]] = {}
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MONGO_DB = None
_MONGO_CHECKED = False


class EnergyAwareHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/me":
            session = self.current_session()
            self.send_json({
                "loggedIn": session is not None,
                "username": session.get("username") if session else None,
                "email": session.get("email") if session else None,
                "storage": storage_label(),
            })
            return
        if parsed.path == "/api/evaluate":
            self.handle_evaluate(parsed.query)
            return
        if parsed.path == "/api/history":
            username = self.current_user()
            if not username:
                self.send_json([])
                return
            self.send_json(load_experiment_history(username))
            return
        if parsed.path == "/api/reports":
            username = self.current_user()
            if not username:
                self.send_json([])
                return
            self.send_json(load_simulator_reports(username))
            return
        if parsed.path == "/api/assistant-history":
            username = self.current_user()
            if not username:
                self.send_json([])
                return
            self.send_json(load_assistant_history(username))
            return
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/signup":
            self.handle_signup()
            return
        if parsed.path == "/api/login":
            self.handle_login()
            return
        if parsed.path == "/api/logout":
            self.handle_logout()
            return
        if parsed.path == "/api/assistant":
            self.handle_assistant()
            return
        self.send_json({"error": "Unknown endpoint"}, 404)

    def handle_evaluate(self, raw_query: str) -> None:
        params = {key: values[-1] for key, values in parse_qs(raw_query).items()}
        result = evaluate(params)
        result["storageBackend"] = storage_label()
        if params.get("save", "false").lower() == "true":
            username = self.current_user()
            if not username:
                self.send_json({"error": "Please log in before saving experiments."}, 401)
                return
            save_experiment_history(result, username)
            save_backend_event("experiment_saved", self.current_session(), {"mode": result.get("mode"), "riskLevel": result.get("riskLevel")})
        self.send_json(result)

    def handle_login(self) -> None:
        payload = self.read_json()
        email = normalise_email(payload.get("email"))
        password = str(payload.get("password", ""))
        accepted_terms = bool(payload.get("acceptedTerms"))
        if not EMAIL_PATTERN.match(email):
            self.send_json({"error": "Enter a valid email address."}, 400)
            return
        if not password:
            self.send_json({"error": "Enter your password."}, 400)
            return
        if not accepted_terms:
            self.send_json({"error": "Please accept the terms and conditions."}, 400)
            return
        user = get_user(email)
        if not user:
            self.send_json({"error": "No account found for this email. Please sign up first."}, 404)
            return
        if not verify_password(password, user["passwordHash"]):
            self.send_json({"error": "Incorrect password. Use the same password you created during sign up."}, 401)
            return
        username = str(user.get("username") or email.split("@")[0])
        save_backend_event("user_login", {"email": email, "username": username}, {})
        self.create_session(email, username)

    def handle_signup(self) -> None:
        payload = self.read_json()
        email = normalise_email(payload.get("email"))
        password = str(payload.get("password", ""))
        username = str(payload.get("username", "")).strip()
        accepted_terms = bool(payload.get("acceptedTerms"))
        if not EMAIL_PATTERN.match(email):
            self.send_json({"error": "Enter a valid email address."}, 400)
            return
        if len(password) < 6:
            self.send_json({"error": "Create a password with at least 6 characters."}, 400)
            return
        if len(username) < 3:
            self.send_json({"error": "Enter a display name with at least 3 characters."}, 400)
            return
        if not accepted_terms:
            self.send_json({"error": "Please accept the terms and conditions."}, 400)
            return
        if get_user(email):
            self.send_json({"error": "This email is already signed up. Please sign in with the same password."}, 409)
            return
        save_user({
            "email": email,
            "username": username,
            "passwordHash": hash_password(password),
        })
        save_backend_event("user_signup", {"email": email, "username": username}, {})
        self.create_session(email, username)

    def create_session(self, email: str, username: str) -> None:
        session_id = secrets.token_urlsafe(24)
        SESSIONS[session_id] = {"email": email, "username": username}
        self.send_json(
            {"loggedIn": True, "username": username, "email": email},
            headers={"Set-Cookie": f"ea_session={session_id}; Path=/; SameSite=Lax"},
        )

    def handle_logout(self) -> None:
        session_id = self.session_id()
        if session_id:
            save_backend_event("user_logout", SESSIONS.get(session_id), {})
            SESSIONS.pop(session_id, None)
        self.send_json({"loggedIn": False, "username": None}, headers={"Set-Cookie": "ea_session=; Path=/; Max-Age=0; SameSite=Lax"})

    def handle_assistant(self) -> None:
        payload = self.read_json()
        scenario = payload.get("scenario") or evaluate({})
        question = str(payload.get("question", "")).strip().lower()
        username = str(payload.get("username") or self.current_user() or "student").strip()
        answer, assistant_mode = assistant_response(question, scenario, username)
        session = self.current_session() or {"username": username, "email": ""}
        save_assistant_chat(session, question, answer, scenario)
        save_backend_event("assistant_question", session, {"question": question[:160], "assistantMode": assistant_mode})
        self.send_json({"answer": answer, "assistantMode": assistant_mode, "storageBackend": storage_label()})

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length == 0:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    def session_id(self) -> str | None:
        cookie = SimpleCookie(self.headers.get("Cookie"))
        morsel = cookie.get("ea_session")
        return morsel.value if morsel else None

    def current_session(self) -> dict[str, str] | None:
        session_id = self.session_id()
        return SESSIONS.get(session_id or "")

    def current_user(self) -> str | None:
        session = self.current_session()
        return session.get("username") if session else None

    def send_json(self, payload, status: int = 200, headers: dict[str, str] | None = None) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)


def assistant_response(question: str, scenario: dict, username: str = "student") -> tuple[str, str]:
    if OPENAI_API_KEY:
        answer = openai_assistant_answer(question, scenario, username)
        if answer:
            return answer, "OpenAI"
    return rule_based_assistant_answer(question, scenario, username), "Rule-based fallback"


def openai_assistant_answer(question: str, scenario: dict, username: str) -> str | None:
    instructions = (
        "You are APX Assistant, a helpful dissertation project advisor inside an energy-aware AI cloud deployment dashboard. "
        "Do not greet on every response. Greet only if the user greets you. "
        "If the user says thanks, great, okay, or bye, respond naturally and briefly, then gently point them back to useful project next steps if appropriate. "
        "Give clear, practical, human-sounding answers. Help the user understand ideas, improve scenarios, write report text, "
        "identify limitations, and choose evidence screenshots. Keep answers concise but useful. "
        "Only answer questions related to this website and project: energy-aware AI model deployment, cloud deployment choices, "
        "the simulator metrics, APX Assistant, MongoDB/backend storage, saved evidence, dissertation/report writing, and project limitations. "
        "When web search is available, use it only for project-relevant current information such as cloud AI sustainability, green AI, carbon intensity, cloud deployment, or dissertation evidence. "
        "Do not use web search for unrelated topics. "
        "If the user asks an unrelated question, politely say you can only help with this energy-aware AI deployment project and suggest a relevant project question. "
        "Do not claim the simulator directly measures real data-centre electricity; call it indirect/proxy metric evidence."
    )
    scenario_text = json.dumps(scenario, indent=2)
    payload = {
        "model": OPENAI_MODEL,
        "instructions": instructions,
        "input": (
            f"User name: {username}\n"
            f"Current simulator scenario JSON:\n{scenario_text}\n\n"
            f"User question: {question}"
        ),
    }
    if OPENAI_ENABLE_WEB:
        payload["tools"] = [{"type": "web_search"}]
        payload["tool_choice"] = "auto"
        payload["include"] = ["web_search_call.action.sources"]
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None
    return extract_openai_text(data)


def extract_openai_text(data: dict) -> str | None:
    output_text = data.get("output_text")
    sources = extract_openai_sources(data)
    if isinstance(output_text, str) and output_text.strip():
        return append_sources(output_text.strip(), sources)
    for item in data.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                return append_sources(text.strip(), sources)
    return None


def extract_openai_sources(data: dict) -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    seen = set()
    for item in data.get("output", []):
        action = item.get("action") if isinstance(item, dict) else None
        for source in (action or {}).get("sources", []) if isinstance(action, dict) else []:
            url = source.get("url") if isinstance(source, dict) else None
            title = source.get("title") if isinstance(source, dict) else None
            if url and url not in seen:
                seen.add(url)
                sources.append({"title": title or url, "url": url})
        for content in item.get("content", []) if isinstance(item, dict) else []:
            for annotation in content.get("annotations", []) if isinstance(content, dict) else []:
                url = annotation.get("url") if isinstance(annotation, dict) else None
                title = annotation.get("title") if isinstance(annotation, dict) else None
                if url and url not in seen:
                    seen.add(url)
                    sources.append({"title": title or url, "url": url})
    return sources[:5]


def append_sources(text: str, sources: list[dict[str, str]]) -> str:
    if not sources:
        return text
    source_lines = [f"- {source['title']}: {source['url']}" for source in sources]
    return text + "\n\nSources:\n" + "\n".join(source_lines)


def rule_based_assistant_answer(question: str, scenario: dict, username: str = "student") -> str:
    risk = scenario.get("risk", scenario.get("riskLevel", "Medium"))
    energy = float(scenario.get("energy", scenario.get("energyKwh", 0)))
    carbon = float(scenario.get("carbon", scenario.get("carbonKg", 0)))
    latency = float(scenario.get("latency", scenario.get("latencyMs", 0)))
    accuracy = float(scenario.get("accuracy", scenario.get("accuracyPercent", 0)))
    cost = float(scenario.get("cost", scenario.get("costGbp", 0)))
    throughput = float(scenario.get("throughput", scenario.get("throughputRps", 0)))
    efficiency = float(scenario.get("efficiency", scenario.get("efficiencyScore", 0)))
    mode = scenario.get("mode", "container")
    technique = scenario.get("techniqueLabel", scenario.get("technique", "quantisation"))
    model = scenario.get("modelProfileLabel", scenario.get("modelProfile", "the selected model"))
    workload = scenario.get("workloadLabel", scenario.get("workload", "the selected workload"))

    normalised_question = normalise_question_text(question)
    greeting_words = {"hi", "hii", "hello", "hey", "start"}
    thanks_words = {"thanks", "thank", "you", "thankyou", "thank-you", "thx", "cheers", "great", "good", "nice", "perfect", "ok", "okay"}
    bye_words = {"bye", "goodbye", "see", "later", "done", "finish", "finished"}
    filler_words = {"please", "me", "the", "this", "current", "now", "again", "can", "you", "show", "tell", "give"}
    question_words = set(normalised_question.split())
    intent_words = question_words - filler_words
    allowed_terms = {
        "ai", "apx", "assistant", "backend", "carbon", "chat", "cloud", "cost", "csv", "data",
        "database", "deployment", "dissertation", "energy", "evidence", "experiment", "explain",
        "history", "latency", "limitation", "model", "mongodb", "performance", "python", "report",
        "risk", "save", "scenario", "server", "serverless", "simulator", "throughput", "vm",
        "container", "accuracy", "utilisation", "utilization", "improve", "better", "write",
        "conclusion", "screenshot", "result", "real", "life", "production", "simple", "clear",
        "idea", "method", "architecture", "frontend", "api", "storage", "green", "sustainable"
    }

    if intent_words and intent_words.issubset(greeting_words):
        return f"Hi {username}. I am ready. Your current scenario is {model} on {workload} using {technique} with {mode} deployment. Ask me for an explanation, improvement plan, report wording, limitations, or evidence checklist."
    if intent_words and intent_words.issubset(thanks_words):
        return "You are welcome. The project is in a good shape. The strongest next step is to save a few different simulator scenarios and use them as evidence in your results section."
    if intent_words and intent_words.issubset(bye_words):
        return "Goodbye. Before you finish, remember to save one strong experiment, take screenshots of the simulator and evidence pages, and keep the Python server output for your appendix."
    intent = detect_assistant_intent(normalised_question, intent_words)
    if intent == "unclear":
        return f"I think you are asking about this project, but I need one more clue. Do you want me to explain the current simulator result, improve the scenario, write dissertation wording, list evidence screenshots, or describe the limitations?"
    if intent == "unrelated":
        return "I can help best with this Energy-Aware AI deployment website. Try asking in your own words about the simulator result, risk, energy/carbon impact, MongoDB evidence, backend storage, screenshots, limitations, or report writing."

    if intent == "result":
        return f"Current result: {model} is running for {workload} using {technique} on {mode}. It estimates {energy:.2f} kWh/day energy, {carbon:.2f} kg CO2e/day, {latency:.0f} ms latency, {accuracy:.1f}% retained accuracy, GBP {cost:.2f}/day cost, {throughput:.0f} rps throughput, and {risk} risk. The key point is whether the energy saving is achieved without damaging latency or accuracy. This is a useful scenario for your results section if you compare it against VM and serverless alternatives."
    if intent == "save":
        return "Use Save experiment when you have a scenario worth showing in the dissertation. The backend stores energy, carbon, latency, accuracy, cost, throughput, risk, and recommendation data. It also creates a simulator report record and keeps assistant chat evidence, so you can prove the system is more than a static webpage."
    if intent == "risk":
        return f"The current risk level is {risk}. Treat risk as a deployment warning, not a failure label. Risk rises when accuracy drops, latency approaches the SLA target, or CPU/GPU proxy utilisation becomes too high. For your discussion, explain what caused the risk, then say how you would validate it with load testing, monitoring, and accuracy checks before production."
    if intent == "improve":
        return "A stronger scenario usually has three things: utilisation around 60-80%, latency comfortably below the SLA target, and accuracy that has not been damaged by over-compression. Try containers for a balanced production case, serverless for bursty workloads, and VM as a baseline comparison. If accuracy is weak, reduce optimisation. If latency is weak, reduce model size or avoid serverless cold-start risk."
    if intent == "clear":
        return f"Simple idea: this project helps choose how an AI model should be deployed in the cloud while considering energy and performance together. In this scenario, {model} uses {technique} on {mode}. The key trade-off is {energy:.2f} kWh/day energy, {latency:.0f} ms latency, {accuracy:.1f}% accuracy, and {risk} risk. Your main argument can be: greener deployment is useful only when latency and accuracy remain acceptable."
    if intent == "report":
        return f"Suggested dissertation wording: This prototype evaluates {model} on {workload} using indirect cloud deployment metrics. The selected configuration estimates {energy:.2f} kWh/day, {carbon:.2f} kg CO2e/day, {latency:.0f} ms latency, {accuracy:.1f}% retained accuracy, GBP {cost:.2f}/day estimated cost, {throughput:.0f} rps throughput, and {risk} risk. The result should be presented as decision-support evidence rather than a direct physical data-centre electricity measurement."
    if intent == "real_life":
        return "In real life, the best option depends on workload shape. Containers are usually the safest recommendation for steady API inference because they balance control, scaling, latency, monitoring, and cost. Serverless is attractive for bursty traffic because idle resource use can be lower, but cold starts can hurt latency. VMs are useful as a baseline and for predictable dedicated workloads where control matters more than elasticity."
    if intent == "limitations":
        return "Good limitation to mention: this prototype estimates energy using indirect proxy metrics, not physical data-centre meter readings. It also uses a rule-based assistant, fixed model profiles, and simplified cost assumptions. That is acceptable for a dissertation prototype if you clearly describe it as a decision-support simulator and explain how future work could add live cloud telemetry."
    if intent == "evidence":
        return "Useful evidence screenshots: login/sign-up page, Simulator with Python API status, saved experiment history, APX Assistant answer, Architecture page, Evidence page, MongoDB or local JSON/CSV storage, and the Python terminal running the server. These prove frontend, backend, storage, assistant, and evaluation logic."
    if intent == "conclusion":
        return f"Conclusion idea: the prototype shows that energy-aware AI deployment requires a balance between lower energy use and acceptable service quality. Your current scenario has {energy:.2f} kWh/day energy use, {latency:.0f} ms latency, {accuracy:.1f}% accuracy retention, and {risk} risk. The strongest conclusion is that optimisation and deployment choice should be evaluated together, not separately."
    if intent == "carbon":
        return f"This scenario estimates {carbon:.2f} kg CO2e per day by multiplying estimated energy use by the selected carbon intensity. In the report, call this a carbon proxy calculation. That wording is important because the prototype does not read live electricity meters or cloud-provider carbon telemetry."
    if intent == "cost":
        return f"The estimated running cost is GBP {cost:.2f} per day. Use it for comparison, not as a real invoice. A good discussion point is that the cheapest option is not always best if latency, reliability, or accuracy gets worse."
    if intent == "performance":
        return f"The current performance estimate is {latency:.0f} ms latency and {throughput:.0f} requests per second. If latency is too high, reduce model size, use quantisation, increase capacity, or prefer containers for latency-sensitive inference. If throughput is low, check utilisation and workload type before blaming the model."
    if intent == "explain":
        return f"This scenario runs {model} for {workload} using {technique} on {mode}. It estimates {energy:.2f} kWh/day, {carbon:.2f} kg CO2e/day, {latency:.0f} ms latency, {accuracy:.1f}% retained accuracy, {efficiency:.0f}/100 efficiency, and {risk} risk. The important interpretation is the trade-off: energy saving is only valuable if the service still meets accuracy and latency expectations."
    return "I can help with that, but I need a little more direction. Do you want an explanation of the current result, an improvement plan, dissertation wording, evidence screenshots, or limitations?"


def normalise_question_text(question: str) -> str:
    replacements = {
        "plz": "please",
        "pls": "please",
        "pzz": "please",
        "rslut": "result",
        "reslt": "result",
        "rsult": "result",
        "ans": "answer",
        "anaylse": "analyse",
        "anlyse": "analyse",
        "explan": "explain",
        "explin": "explain",
        "improv": "improve",
        "wht": "what",
        "wat": "what",
        "disertation": "dissertation",
        "diss": "dissertation",
        "repoort": "report",
        "mongdb": "mongodb",
        "mogo": "mongodb",
        "mogoDB": "mongodb",
        "db": "database",
        "ss": "screenshot",
    }
    text = question.lower()
    for wrong, right in replacements.items():
        text = re.sub(rf"\b{re.escape(wrong.lower())}\b", right, text)
    text = re.sub(r"[^a-z0-9£]+", " ", text)
    return " ".join(text.split())


def detect_assistant_intent(question: str, intent_words: set[str]) -> str:
    if not question:
        return "unclear"

    intent_map = [
        ("result", {"result", "results", "output", "analyse", "analyze", "analysis", "answer", "current"}),
        ("save", {"save", "history", "store", "stored", "record", "records"}),
        ("risk", {"risk", "warning", "danger", "safe", "unsafe"}),
        ("improve", {"improve", "better", "fix", "optimise", "optimize", "recommend", "suggest", "tune"}),
        ("clear", {"clear", "idea", "understand", "simple", "confused", "meaning", "explainlike"}),
        ("report", {"report", "dissertation", "write", "writing", "paragraph", "chapter", "methodology", "results"}),
        ("real_life", {"real", "life", "production", "best", "industry", "practical"}),
        ("limitations", {"limit", "limits", "limitation", "limitations", "weakness", "weaknesses", "future"}),
        ("evidence", {"screenshot", "screenshots", "evidence", "proof", "show", "appendix"}),
        ("conclusion", {"conclusion", "summary", "summarise", "summarize", "final"}),
        ("carbon", {"carbon", "co2", "emission", "emissions", "green", "sustainable", "energy"}),
        ("cost", {"cost", "price", "money", "gbp", "cheap", "expensive"}),
        ("performance", {"throughput", "performance", "latency", "speed", "slow", "fast", "sla"}),
        ("explain", {"explain", "what", "why", "how", "describe"}),
    ]

    for intent, terms in intent_map:
        if terms.intersection(intent_words):
            return intent

    project_terms = {
        "ai", "apx", "assistant", "backend", "cloud", "database", "deployment", "model", "mongodb",
        "python", "server", "serverless", "simulator", "vm", "container", "accuracy", "frontend",
        "api", "storage", "website", "project", "dashboard"
    }
    if project_terms.intersection(intent_words):
        return "unclear"
    return "unrelated"


def normalise_email(value) -> str:
    return str(value or "").strip().lower()


def mongo_db():
    global _MONGO_DB, _MONGO_CHECKED
    if _MONGO_CHECKED:
        return _MONGO_DB
    _MONGO_CHECKED = True
    if MongoClient is None:
        return None
    try:
        options = {"serverSelectionTimeoutMS": MONGODB_TIMEOUT_MS}
        if MONGODB_TLS_ALLOW_INVALID_CERTIFICATES:
            options["tlsAllowInvalidCertificates"] = True
        elif certifi is not None and MONGODB_URI.startswith("mongodb+srv://"):
            options["tlsCAFile"] = certifi.where()
        client = MongoClient(MONGODB_URI, **options)
        client.admin.command("ping")
        _MONGO_DB = client[MONGODB_NAME]
    except (PyMongoError, ServerSelectionTimeoutError, OSError):
        _MONGO_DB = None
    return _MONGO_DB


def storage_label() -> str:
    return "MongoDB + CSV" if mongo_db() is not None else "JSON + CSV fallback"


def get_user(email: str) -> dict[str, str] | None:
    db = mongo_db()
    if db is not None:
        try:
            user = db.users.find_one({"email": email}, {"_id": 0})
            return user if isinstance(user, dict) else None
        except PyMongoError:
            pass
    return load_users().get(email)


def save_user(user: dict[str, str]) -> None:
    db = mongo_db()
    if db is not None:
        try:
            db.users.update_one({"email": user["email"]}, {"$set": user}, upsert=True)
            return
        except PyMongoError:
            pass
    users = load_users()
    users[user["email"]] = user
    save_users(users)


def save_experiment_history(result: dict[str, float | str], username: str) -> None:
    save_history(HISTORY_FILE, result, username)
    report = simulator_report_document(result, username)
    append_json_record(REPORTS_FILE, report)
    db = mongo_db()
    if db is None:
        return
    document = {"createdAt": datetime.now().isoformat(timespec="seconds"), "username": username, **result}
    try:
        db.experiments.insert_one(document)
        db.simulator_reports.insert_one(report)
    except PyMongoError:
        return


def load_experiment_history(username: str) -> list[dict[str, str]]:
    db = mongo_db()
    if db is not None:
        try:
            rows = list(db.experiments.find({"username": username}, {"_id": 0}).sort("createdAt", 1))
            if rows:
                return [{key: str(value) for key, value in row.items()} for row in rows]
        except PyMongoError:
            pass
    return load_history(HISTORY_FILE, username)


def simulator_report_document(result: dict[str, float | str], username: str) -> dict:
    return {
        "createdAt": datetime.now().isoformat(timespec="seconds"),
        "username": username,
        "title": f"{result.get('modelProfileLabel', result.get('modelProfile', 'Model'))} deployment report",
        "deploymentMode": result.get("mode"),
        "modelProfile": result.get("modelProfile"),
        "workload": result.get("workload"),
        "technique": result.get("technique"),
        "summary": {
            "energyKwh": result.get("energyKwh"),
            "carbonKg": result.get("carbonKg"),
            "latencyMs": result.get("latencyMs"),
            "accuracyPercent": result.get("accuracyPercent"),
            "costGbp": result.get("costGbp"),
            "throughputRps": result.get("throughputRps"),
            "efficiencyScore": result.get("efficiencyScore"),
            "riskLevel": result.get("riskLevel"),
        },
        "recommendation": {
            "title": result.get("recommendationTitle"),
            "message": result.get("recommendationMessage"),
        },
        "reportUse": "Dissertation evidence for saved simulator scenario.",
        "storageBackend": storage_label(),
    }


def load_simulator_reports(username: str) -> list[dict]:
    db = mongo_db()
    if db is not None:
        try:
            rows = list(db.simulator_reports.find({"username": username}, {"_id": 0}).sort("createdAt", 1))
            if rows:
                return rows
        except PyMongoError:
            pass
    return [row for row in load_json_records(REPORTS_FILE) if row.get("username") == username]


def save_assistant_chat(session: dict[str, str], question: str, answer: str, scenario: dict) -> None:
    username = str(session.get("username") or "student")
    email = str(session.get("email") or "")
    document = {
        "createdAt": datetime.now().isoformat(timespec="seconds"),
        "username": username,
        "email": email,
        "question": question,
        "answer": answer,
        "scenarioSnapshot": scenario,
        "assistantName": "APX Assistant",
        "assistantMode": "OpenAI" if OPENAI_API_KEY else "Rule-based fallback",
        "storageBackend": storage_label(),
    }
    append_json_record(ASSISTANT_HISTORY_FILE, document)
    db = mongo_db()
    if db is not None:
        try:
            db.assistant_chats.insert_one(document)
        except PyMongoError:
            return


def load_assistant_history(username: str) -> list[dict]:
    db = mongo_db()
    if db is not None:
        try:
            rows = list(db.assistant_chats.find({"username": username}, {"_id": 0}).sort("createdAt", 1))
            if rows:
                return rows
        except PyMongoError:
            pass
    return [row for row in load_json_records(ASSISTANT_HISTORY_FILE) if row.get("username") == username]


def save_backend_event(event_type: str, session: dict[str, str] | None, details: dict) -> None:
    document = {
        "createdAt": datetime.now().isoformat(timespec="seconds"),
        "eventType": event_type,
        "username": (session or {}).get("username", ""),
        "email": (session or {}).get("email", ""),
        "details": details,
        "storageBackend": storage_label(),
    }
    append_json_record(BACKEND_EVENTS_FILE, document)
    db = mongo_db()
    if db is not None:
        try:
            db.backend_events.insert_one(document)
        except PyMongoError:
            return


def load_json_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def append_json_record(path: Path, record: dict) -> None:
    records = load_json_records(path)
    records.append(record)
    path.write_text(json.dumps(records, indent=2), encoding="utf-8")


def load_users() -> dict[str, dict[str, str]]:
    if not USERS_FILE.exists():
        return {}
    try:
        data = json.loads(USERS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def save_users(users: dict[str, dict[str, str]]) -> None:
    USERS_FILE.write_text(json.dumps(users, indent=2), encoding="utf-8")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
    return f"pbkdf2_sha256${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, salt_text, digest_text = stored_hash.split("$", 2)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_text)
        expected = base64.b64decode(digest_text)
    except (ValueError, TypeError):
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
    return hmac.compare_digest(actual, expected)


def main() -> None:
    ensure_history_file(HISTORY_FILE)
    server = ThreadingHTTPServer((HOST, PORT), EnergyAwareHandler)
    print("Energy-Aware AI Python project is running.")
    print(f"Open this in your browser: http://localhost:{PORT}")
    print("Press Ctrl+C to stop the server.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
