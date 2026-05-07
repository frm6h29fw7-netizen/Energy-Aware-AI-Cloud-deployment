const tabs = document.querySelectorAll(".tab-button");
const tabPanels = document.querySelectorAll(".tab-panel");
const shortcutButtons = document.querySelectorAll("[data-open-tab]");

const controls = {
  requests: document.querySelector("#requests"),
  modelSize: document.querySelector("#modelSize"),
  optimisation: document.querySelector("#optimisation"),
  utilisation: document.querySelector("#utilisation"),
  carbonIntensity: document.querySelector("#carbonIntensity"),
  slaLatency: document.querySelector("#slaLatency"),
  technique: document.querySelector("#technique"),
  modelProfile: document.querySelector("#modelProfile"),
  workload: document.querySelector("#workload"),
  deploymentMode: document.querySelector("#deploymentMode")
};

const outputs = {
  requests: document.querySelector("#requestsOut"),
  model: document.querySelector("#modelOut"),
  optimisation: document.querySelector("#optimisationOut"),
  utilisation: document.querySelector("#utilisationOut"),
  carbonIntensity: document.querySelector("#carbonIntensityOut"),
  slaLatency: document.querySelector("#slaLatencyOut"),
  energy: document.querySelector("#energyUse"),
  carbon: document.querySelector("#carbonUse"),
  latency: document.querySelector("#latencyUse"),
  accuracy: document.querySelector("#accuracyUse"),
  cost: document.querySelector("#costUse"),
  efficiency: document.querySelector("#efficiencyScoreUse"),
  throughput: document.querySelector("#throughputUse"),
  risk: document.querySelector("#riskUse"),
  cpu: document.querySelector("#cpuUse"),
  gpu: document.querySelector("#gpuUse"),
  memory: document.querySelector("#memoryUse"),
  energyScore: document.querySelector("#energyScore"),
  latencyScore: document.querySelector("#latencyScore"),
  apiStatus: document.querySelector("#apiStatus"),
  recommendationTitle: document.querySelector("#recommendationTitle"),
  recommendationText: document.querySelector("#recommendationText"),
  modelSummaryTitle: document.querySelector("#modelSummaryTitle"),
  modelSummaryText: document.querySelector("#modelSummaryText"),
  historyList: document.querySelector("#historyList"),
  scenarioHealth: document.querySelector("#scenarioHealth"),
  healthTitle: document.querySelector("#healthTitle"),
  healthText: document.querySelector("#healthText"),
  comparisonList: document.querySelector("#comparisonList")
};

const saveScenarioButton = document.querySelector("#saveScenario");
const loginForm = document.querySelector("#loginForm");
const logoutButton = document.querySelector("#logoutButton");
const termsButton = document.querySelector("#termsButton");
const gateTermsButton = document.querySelector("#gateTermsButton");
const closeTermsButton = document.querySelector("#closeTerms");
const termsModal = document.querySelector("#termsModal");
const authGate = document.querySelector("#authGate");
let toastStack = document.querySelector("#toastStack");
const assistantForm = document.querySelector("#assistantForm");
const assistantInput = document.querySelector("#assistantInput");
const assistantMessages = document.querySelector("#assistantMessages");
const quickPromptButtons = document.querySelectorAll("[data-prompt]");
const floatingAssistantButton = document.querySelector("#floatingAssistantButton");
const themeButtons = [
  {
    button: document.querySelector("#themeToggle"),
    icon: document.querySelector("#themeIcon"),
    label: document.querySelector("#themeLabel"),
    darkLabel: "Dark mode",
    lightLabel: "Light mode"
  },
  {
    button: document.querySelector("#authThemeToggle"),
    icon: document.querySelector("#authThemeIcon"),
    label: document.querySelector("#authThemeLabel"),
    darkLabel: "Dark",
    lightLabel: "Light"
  }
];
const authElements = {
  email: document.querySelector("#email"),
  password: document.querySelector("#password"),
  username: document.querySelector("#username"),
  usernameLabel: document.querySelector("#usernameLabel"),
  acceptTerms: document.querySelector("#acceptTerms"),
  accountName: document.querySelector("#accountName"),
  authMessage: document.querySelector("#authMessage"),
  gateMessage: document.querySelector("#gateMessage"),
  authTitle: document.querySelector("#authTitle"),
  authLead: document.querySelector("#authLead"),
  authSubmit: document.querySelector("#authSubmit"),
  showSignin: document.querySelector("#showSignin"),
  showSignup: document.querySelector("#showSignup"),
  authModal: document.querySelector(".auth-modal")
};

let lastScenario = null;
let apiAvailable = false;
let currentUser = null;
let assistantGreetedUser = null;
let authMode = "signin";
let currentTheme = localStorage.getItem("apx-theme") || "light";

const modeFactors = {
  vm: { energy: 1.35, latency: 0.92, cost: 1.18, label: "VM baseline", color: "#c65f45" },
  container: { energy: 0.86, latency: 1.0, cost: 0.88, label: "Containers", color: "#237a57" },
  serverless: { energy: 0.74, latency: 1.22, cost: 0.72, label: "Serverless", color: "#1f7f8a" }
};

const techniqueFactors = {
  none: { energy: 1.0, latency: 1.0, accuracy: 1.0, memory: 1.0, label: "No compression" },
  pruning: { energy: 0.86, latency: 0.94, accuracy: 0.85, memory: 0.86, label: "Pruning" },
  quantisation: { energy: 0.76, latency: 0.87, accuracy: 1.2, memory: 0.68, label: "Quantisation" },
  distillation: { energy: 0.7, latency: 0.82, accuracy: 1.45, memory: 0.58, label: "Knowledge distillation" },
  hybrid: { energy: 0.58, latency: 0.74, accuracy: 1.85, memory: 0.48, label: "Pruning + quantisation" }
};

const modelProfiles = {
  mobilenet: { label: "MobileNet image classifier", size: 32, accuracy: 94.6, compute: 0.46, latency: 52, memory: 0.52 },
  efficientnet: { label: "EfficientNet vision model", size: 88, accuracy: 96.8, compute: 0.74, latency: 68, memory: 0.72 },
  resnet: { label: "ResNet-50 baseline", size: 98, accuracy: 96.1, compute: 1.0, latency: 78, memory: 1.0 },
  bert: { label: "BERT text classifier", size: 420, accuracy: 95.4, compute: 1.55, latency: 118, memory: 1.36 }
};

const workloadProfiles = {
  batch: { label: "Batch analytics", energy: 0.82, latency: 0.72, throughput: 0.96, accuracyPenalty: 0 },
  standard: { label: "Standard API inference", energy: 1.0, latency: 1.0, throughput: 1.0, accuracyPenalty: 0 },
  realtime: { label: "Real-time inference", energy: 1.18, latency: 1.3, throughput: 0.86, accuracyPenalty: 0.2 },
  bursty: { label: "Bursty public traffic", energy: 1.28, latency: 1.44, throughput: 0.72, accuracyPenalty: 0.1 }
};

function activateTab(id) {
  tabs.forEach((button) => button.classList.toggle("active", button.dataset.tab === id));
  tabPanels.forEach((panel) => panel.classList.toggle("active", panel.id === id));
}

tabs.forEach((button) => {
  button.addEventListener("click", () => activateTab(button.dataset.tab));
});

shortcutButtons.forEach((button) => {
  button.addEventListener("click", () => activateTab(button.dataset.openTab));
});

floatingAssistantButton.addEventListener("click", () => {
  if (!currentUser) {
    showToast("Sign in first, then APX AI will open from anywhere.", "error");
    shakeAuthModal();
    return;
  }
  activateTab("assistant");
  assistantInput.focus();
});

Object.values(controls).forEach((control) => {
  control.addEventListener("input", updateSimulation);
});

controls.modelProfile.addEventListener("change", () => {
  const profile = modelProfiles[controls.modelProfile.value];
  controls.modelSize.value = profile.size;
  updateSimulation();
});

saveScenarioButton.addEventListener("click", saveScenario);
loginForm.addEventListener("submit", login);
logoutButton.addEventListener("click", logout);
authElements.showSignin.addEventListener("click", () => setAuthMode("signin"));
authElements.showSignup.addEventListener("click", () => setAuthMode("signup"));
themeButtons.forEach((item) => {
  item.button.addEventListener("click", () => setTheme(currentTheme === "dark" ? "light" : "dark"));
});
termsButton.addEventListener("click", () => termsModal.classList.remove("hidden"));
gateTermsButton.addEventListener("click", () => termsModal.classList.remove("hidden"));
closeTermsButton.addEventListener("click", () => termsModal.classList.add("hidden"));
termsModal.addEventListener("click", (event) => {
  if (event.target === termsModal) {
    termsModal.classList.add("hidden");
  }
});
assistantForm.addEventListener("submit", askAssistant);
quickPromptButtons.forEach((button) => {
  button.addEventListener("click", () => {
    assistantInput.value = button.dataset.prompt;
    assistantForm.requestSubmit();
  });
});

function calculateScenario(modeKey) {
  const requests = Number(controls.requests.value);
  const modelSize = Number(controls.modelSize.value);
  const optimisation = Number(controls.optimisation.value);
  const utilisation = Number(controls.utilisation.value);
  const carbonIntensity = Number(controls.carbonIntensity.value);
  const slaLatency = Number(controls.slaLatency.value);
  const factors = modeFactors[modeKey];
  const techniqueKey = controls.technique.value;
  const technique = techniqueFactors[techniqueKey];
  const modelProfileKey = controls.modelProfile.value;
  const modelProfile = modelProfiles[modelProfileKey];
  const workloadKey = controls.workload.value;
  const workloadProfile = workloadProfiles[workloadKey];

  const workload = requests / 100000;
  const sizePressure = modelSize / Math.max(20, modelProfile.size);
  const optimisationSaving = 1 - optimisation / 125;
  const utilisationPenalty = 1 + Math.max(0, 55 - utilisation) / 95;

  const energy = workload * sizePressure * optimisationSaving * utilisationPenalty * factors.energy * technique.energy * modelProfile.compute * workloadProfile.energy;
  const carbon = energy * carbonIntensity;
  const coldStartPenalty = modeKey === "serverless" ? Math.max(0, workload - 3.5) * 5.5 : 0;
  const queuePenalty = Math.max(0, workload - utilisation / 20) * 3.5;
  const latency = ((modelProfile.latency + modelSize * 0.09 - optimisation * 0.38) * factors.latency * technique.latency * workloadProfile.latency) + coldStartPenalty + queuePenalty;
  const accuracy = Math.max(80, modelProfile.accuracy - optimisation * 0.08 * technique.accuracy - workloadProfile.accuracyPenalty);
  const cost = energy * 0.31 * factors.cost;
  const cpu = clamp(22 + workload * 5.8 + sizePressure * 13 + workloadProfile.energy * 6 - utilisation * 0.1 - optimisation * 0.12, 8, 98);
  const gpu = clamp(16 + workload * 5 + sizePressure * 18 + modelProfile.compute * 10 - optimisation * 0.18, 6, 96);
  const memory = Math.max(96, modelSize * technique.memory * modelProfile.memory + 128);
  const throughput = clamp((1000 / Math.max(20, latency)) * utilisation * workloadProfile.throughput, 1, 5000);
  const efficiency = clamp((1 / Math.max(0.12, energy)) * accuracy * Math.min(1.08, slaLatency / Math.max(45, latency)) * Math.min(1.05, throughput / 160) * 2.4, 0, 100);
  const risk = riskLevel(accuracy, latency, slaLatency, utilisation, cpu, gpu);

  return {
    mode: modeKey,
    technique: techniqueKey,
    techniqueLabel: technique.label,
    modelProfile: modelProfileKey,
    modelProfileLabel: modelProfile.label,
    workload: workloadKey,
    workloadLabel: workloadProfile.label,
    energy,
    carbon,
    latency,
    accuracy,
    cost,
    cpu,
    gpu,
    memory,
    throughput,
    efficiency,
    risk,
    recommendation: recommendationFor(modeKey, techniqueKey, modelProfile.label, workloadProfile.label, energy, latency, accuracy, slaLatency, efficiency, risk)
  };
}

function riskLevel(accuracy, latency, slaLatency, utilisation, cpu, gpu) {
  if (accuracy < 91 || latency > slaLatency || cpu > 88 || gpu > 88) {
    return "High";
  }
  if (accuracy < 94 || latency > slaLatency * 0.85 || utilisation < 35) {
    return "Medium";
  }
  return "Low";
}

function recommendationFor(modeKey, techniqueKey, modelLabel, workloadLabel, energy, latency, accuracy, slaLatency, efficiency, risk) {
  if (accuracy < 91) {
    return {
      title: "Reduce optimisation pressure",
      message: "Accuracy is falling too low. Use lighter optimisation or a larger model for safer deployment."
    };
  }
  if (latency > slaLatency) {
    return {
      title: "Latency SLA risk",
      message: "The energy saving is useful, but this configuration may breach the response-time target. Reduce model size or move to containers."
    };
  }
  if (modeKey === "serverless" && latency > 135) {
    return {
      title: "Use containers for latency-sensitive inference",
      message: "Serverless can save idle energy, but this scenario has cold-start and response-time risk."
    };
  }
  if (techniqueKey === "hybrid" && accuracy < 94) {
    return {
      title: "Hybrid compression needs validation",
      message: "Combined pruning and quantisation improves efficiency, but the accuracy margin should be tested carefully."
    };
  }
  if (efficiency > 70 && energy < 1.5 && latency < 130) {
    return {
      title: "Energy-aware deployment looks suitable",
      message: `${modelLabel} on ${workloadLabel} gives a strong balance between energy reduction, latency, accuracy retention, and cloud utilisation.`
    };
  }
  return {
    title: "Tune utilisation and model size",
    message: `Risk is ${risk.toLowerCase()}. Improve the scenario by increasing utilisation, reducing model size, or choosing a lighter optimisation/deployment combination.`
  };
}

async function updateSimulation() {
  const activeMode = controls.deploymentMode.value;
  const scenario = await evaluateScenario(activeMode, false);
  const baseline = calculateScenario("vm");
  const reduction = Math.max(0, (1 - scenario.energy / baseline.energy) * 100);
  lastScenario = scenario;

  outputs.requests.value = Number(controls.requests.value).toLocaleString("en-GB");
  outputs.model.value = `${controls.modelSize.value} MB`;
  outputs.optimisation.value = `${controls.optimisation.value}%`;
  outputs.utilisation.value = `${controls.utilisation.value}%`;
  outputs.carbonIntensity.value = `${Number(controls.carbonIntensity.value).toFixed(3)} kg/kWh`;
  outputs.slaLatency.value = `${controls.slaLatency.value} ms`;
  outputs.energy.textContent = `${scenario.energy.toFixed(2)} kWh/day`;
  outputs.carbon.textContent = `${scenario.carbon.toFixed(2)} kg/day`;
  outputs.latency.textContent = `${scenario.latency.toFixed(0)} ms`;
  outputs.accuracy.textContent = `${scenario.accuracy.toFixed(1)}%`;
  outputs.cost.textContent = `£${scenario.cost.toFixed(2)}/day`;
  outputs.efficiency.textContent = `${scenario.efficiency.toFixed(0)}/100`;
  outputs.throughput.textContent = `${scenario.throughput.toFixed(0)} rps`;
  outputs.risk.textContent = scenario.risk;
  outputs.cpu.textContent = `${scenario.cpu.toFixed(0)}%`;
  outputs.gpu.textContent = `${scenario.gpu.toFixed(0)}%`;
  outputs.memory.textContent = `${scenario.memory.toFixed(0)} MB`;
  outputs.energyScore.textContent = `${reduction.toFixed(0)}%`;
  outputs.latencyScore.textContent = `${scenario.latency.toFixed(0)}ms`;
  outputs.recommendationTitle.textContent = scenario.recommendation.title;
  outputs.recommendationText.textContent = scenario.recommendation.message;
  outputs.modelSummaryTitle.textContent = `${scenario.modelProfileLabel} - ${scenario.workloadLabel}`;
  outputs.modelSummaryText.textContent = `This run applies ${scenario.techniqueLabel.toLowerCase()} and ${modeFactors[activeMode].label.toLowerCase()} deployment to estimate indirect energy, carbon, latency, accuracy, and utilisation evidence for the dissertation.`;
  updateScenarioHealth(scenario, reduction);
  updateComparison(activeMode);

  drawBarChart(activeMode);
}

function updateScenarioHealth(scenario, reduction) {
  const health = healthForScenario(scenario, reduction);
  outputs.scenarioHealth.className = `scenario-health ${health.className}`;
  outputs.healthTitle.textContent = health.title;
  outputs.healthText.textContent = health.text;
}

function healthForScenario(scenario, reduction) {
  const reasons = [];
  if (scenario.risk === "Low") {
    reasons.push("risk is low");
  } else {
    reasons.push(`${scenario.risk.toLowerCase()} risk needs review`);
  }
  if (scenario.accuracy >= 94) {
    reasons.push("accuracy is strong");
  } else if (scenario.accuracy < 91) {
    reasons.push("accuracy is too low");
  }
  if (scenario.latency < Number(controls.slaLatency.value) * 0.8) {
    reasons.push("latency is comfortably within target");
  } else {
    reasons.push("latency is close to the target");
  }
  if (reduction >= 40) {
    reasons.push(`${reduction.toFixed(0)}% lower energy than VM baseline`);
  }

  if (scenario.risk === "Low" && scenario.efficiency >= 75) {
    return {
      className: "health-good",
      title: "Deployment-ready scenario",
      text: `Good candidate for demonstration: ${sentenceList(reasons)}.`
    };
  }
  if (scenario.risk === "High" || scenario.accuracy < 91 || scenario.latency > Number(controls.slaLatency.value)) {
    return {
      className: "health-risk",
      title: "High attention required",
      text: `Use this as a risk example: ${sentenceList(reasons)}. Tune model size, optimisation, or deployment mode before recommending it.`
    };
  }
  return {
    className: "health-medium",
    title: "Good evidence, needs discussion",
    text: `Useful dissertation scenario: ${sentenceList(reasons)}. Explain the trade-off clearly in your results section.`
  };
}

function sentenceList(items) {
  return items.filter(Boolean).join(", ");
}

function updateComparison(activeMode) {
  const rows = Object.keys(modeFactors).map((mode) => {
    const scenario = calculateScenario(mode);
    return {
      mode,
      label: modeFactors[mode].label,
      energy: scenario.energy,
      latency: scenario.latency,
      cost: scenario.cost,
      risk: scenario.risk,
      active: mode === activeMode,
      bestUse: bestUseForMode(mode)
    };
  });

  outputs.comparisonList.innerHTML = rows.map((row) => `
    <article class="${row.active ? "active" : ""}">
      <div>
        <strong>${row.label}</strong>
        <small>${row.bestUse}</small>
      </div>
      <span>${row.energy.toFixed(2)} kWh</span>
      <span>${row.latency.toFixed(0)} ms</span>
      <span>GBP ${row.cost.toFixed(2)}</span>
      <b>${row.risk}</b>
    </article>
  `).join("");
}

function bestUseForMode(mode) {
  if (mode === "vm") {
    return "Baseline and predictable dedicated workloads";
  }
  if (mode === "serverless") {
    return "Bursty traffic and low idle demand";
  }
  return "Balanced production API deployment";
}

async function evaluateScenario(mode, save) {
  const params = new URLSearchParams({
    mode,
    requests: controls.requests.value,
    modelSize: controls.modelSize.value,
    optimisation: controls.optimisation.value,
    utilisation: controls.utilisation.value,
    carbonIntensity: controls.carbonIntensity.value,
    slaLatency: controls.slaLatency.value,
    technique: controls.technique.value,
    modelProfile: controls.modelProfile.value,
    workload: controls.workload.value,
    save: String(save)
  });

  try {
    const response = await fetch(`/api/evaluate?${params.toString()}`);
    if (!response.ok) {
      throw new Error("API unavailable");
    }
    const data = await response.json();
    apiAvailable = true;
    outputs.apiStatus.textContent = data.storageBackend ? `Python API live - ${data.storageBackend}` : "Python API live";
    outputs.apiStatus.classList.add("live");
    return {
      mode,
      technique: data.technique,
      techniqueLabel: data.techniqueLabel,
      modelProfile: data.modelProfile,
      modelProfileLabel: data.modelProfileLabel,
      workload: data.workload,
      workloadLabel: data.workloadLabel,
      energy: data.energyKwh,
      carbon: data.carbonKg,
      latency: data.latencyMs,
      accuracy: data.accuracyPercent,
      cost: data.costGbp,
      cpu: data.cpuPercent,
      gpu: data.gpuPercent,
      memory: data.memoryMb,
      throughput: data.throughputRps,
      efficiency: data.efficiencyScore,
      risk: data.riskLevel,
      recommendation: {
        title: data.recommendationTitle,
        message: data.recommendationMessage
      }
    };
  } catch (error) {
    apiAvailable = false;
    outputs.apiStatus.textContent = "Browser mode";
    outputs.apiStatus.classList.remove("live");
    return calculateScenario(mode);
  }
}

async function saveScenario() {
  if (!currentUser) {
    outputs.historyList.innerHTML = "<p>Please log in and accept the terms before saving experiments.</p>";
    authElements.authMessage.textContent = "Login is required before saving experiment data.";
    return;
  }
  const scenario = await evaluateScenario(controls.deploymentMode.value, true);
  lastScenario = scenario;
  if (apiAvailable) {
    await loadHistory();
  } else {
    outputs.historyList.innerHTML = `<p>Run the Python web server to save experiments to CSV.</p>`;
  }
}

async function loadHistory() {
  try {
    const response = await fetch("/api/history");
    if (!response.ok) {
      throw new Error("No history");
    }
    const history = await response.json();
    if (!history.length) {
      outputs.historyList.innerHTML = currentUser ? "<p>No saved experiments yet for this user.</p>" : "<p>Log in to view your saved experiments.</p>";
      return;
    }
    outputs.historyList.innerHTML = history.slice(-6).reverse().map((item) => `
      <div class="history-item">
        <strong>${item.modelProfile || "model"} - ${item.mode}</strong>
        <span>${Number(item.energyKwh).toFixed(2)} kWh</span>
        <span>${Number(item.latencyMs).toFixed(0)} ms</span>
        <span>${item.riskLevel || "n/a"}</span>
      </div>
    `).join("");
  } catch (error) {
    outputs.historyList.innerHTML = "<p>No saved experiments yet.</p>";
  }
}

async function loadSession() {
  try {
    const response = await fetch("/api/me");
    const data = await response.json();
    setLoggedIn(data.loggedIn ? data.username : null);
  } catch (error) {
    setLoggedIn(null);
  }
}

async function login(event) {
  event.preventDefault();
  const email = authElements.email.value.trim();
  const password = authElements.password.value;
  const username = authElements.username.value.trim();
  const acceptedTerms = authElements.acceptTerms.checked;
  const endpoint = authMode === "signup" ? "/api/signup" : "/api/login";
  const validationError = validateAuthForm(email, password, username, acceptedTerms);
  if (validationError) {
    authElements.authMessage.textContent = validationError;
    authElements.gateMessage.textContent = validationError;
    showToast(validationError, "error");
    shakeAuthModal();
    return;
  }
  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, username, acceptedTerms })
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Login failed");
    }
    setLoggedIn(data.username);
    authElements.email.value = "";
    authElements.password.value = "";
    authElements.username.value = "";
    authElements.acceptTerms.checked = false;
    authElements.authMessage.textContent = "Signed in. Your saved experiments are now linked to this account.";
    authElements.gateMessage.textContent = "Signed in successfully.";
    showToast(authMode === "signup" ? "Account created and signed in." : "Signed in successfully.", "success");
    await loadHistory();
  } catch (error) {
    authElements.authMessage.textContent = error.message;
    authElements.gateMessage.textContent = error.message;
    showToast(error.message, "error");
    shakeAuthModal();
  }
}

function shakeAuthModal() {
  authElements.authModal.classList.remove("attention");
  void authElements.authModal.offsetWidth;
  authElements.authModal.classList.add("attention");
}

function validateAuthForm(email, password, username, acceptedTerms) {
  if (!email) {
    return "Email address is required.";
  }
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
    return "Enter a valid email address.";
  }
  if (!password) {
    return "Password is required.";
  }
  if (authMode === "signup" && password.length < 6) {
    return "Create a password with at least 6 characters.";
  }
  if (authMode === "signup" && username.length < 3) {
    return "Display name is required for sign up.";
  }
  if (!acceptedTerms) {
    return "Please accept the terms and conditions.";
  }
  return "";
}

function showToast(message, type = "info") {
  if (!toastStack) {
    toastStack = document.createElement("div");
    toastStack.id = "toastStack";
    toastStack.className = "toast-stack";
    toastStack.setAttribute("aria-live", "assertive");
    toastStack.setAttribute("aria-atomic", "true");
    document.body.appendChild(toastStack);
  }
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.setAttribute("role", "alert");
  toast.innerHTML = `
    <strong>${type === "success" ? "Success" : type === "error" ? "Action needed" : "Notice"}</strong>
    <span>${message}</span>
  `;
  toastStack.appendChild(toast);
  window.setTimeout(() => {
    toast.classList.add("leaving");
    window.setTimeout(() => toast.remove(), 220);
  }, 4200);
}

function setAuthMode(mode) {
  authMode = mode;
  const isSignup = mode === "signup";
  authElements.showSignin.classList.toggle("active", !isSignup);
  authElements.showSignup.classList.toggle("active", isSignup);
  authElements.usernameLabel.classList.toggle("hidden", !isSignup);
  authElements.authTitle.textContent = isSignup ? "Sign up" : "Sign in";
  authElements.authLead.textContent = isSignup
    ? "Create a local prototype account. After this, use the same email and password to sign in."
    : "Sign in with the email and password you used during sign up. New users must create an account first.";
  authElements.authSubmit.textContent = isSignup ? "Create account and open dashboard" : "Sign in and open dashboard";
  authElements.gateMessage.textContent = isSignup
    ? "Use a unique demo password. This prototype stores a local password hash, not your real university password."
    : "New email? Choose Sign up first. Existing email? Sign in with the same password.";
}

function setTheme(theme) {
  currentTheme = theme;
  document.body.dataset.theme = theme;
  localStorage.setItem("apx-theme", theme);
  const isDark = theme === "dark";
  themeButtons.forEach((item) => {
    item.button.setAttribute("aria-pressed", String(isDark));
    item.icon.textContent = isDark ? "☾" : "☀";
    item.label.textContent = isDark ? item.darkLabel : item.lightLabel;
  });
  if (lastScenario) {
    updateSimulation();
  }
}

function cssVar(name) {
  return getComputedStyle(document.body).getPropertyValue(name).trim();
}

async function logout() {
  await fetch("/api/logout", { method: "POST" });
  setLoggedIn(null);
  await loadHistory();
}

function setLoggedIn(username) {
  currentUser = username;
  authElements.accountName.textContent = username ? username : "Guest user";
  logoutButton.classList.toggle("hidden", !username);
  authGate.classList.toggle("hidden", Boolean(username));
  document.body.classList.toggle("auth-locked", !username);
  saveScenarioButton.textContent = username ? "Save experiment" : "Log in to save";
  authElements.authMessage.textContent = username ? "Signed in. Experiments save to your local CSV history." : "Sign in is required before using the dashboard.";
  authElements.gateMessage.textContent = username ? "Signed in successfully." : "New users must sign up first, then sign in with the same password.";
  updateAssistantGreeting(username);
}

function updateAssistantGreeting(username) {
  if (assistantGreetedUser === username) {
    return;
  }

  assistantGreetedUser = username;
  assistantMessages.innerHTML = "";
  if (username) {
    appendAssistantMessage(`Hi ${username}, I am APX Assistant. I can explain your current cloud AI deployment result, compare VM, container, and serverless choices, suggest realistic improvements, and help turn the evidence into final-year dissertation wording.`, "bot");
    return;
  }
  appendAssistantMessage("Hi, I am APX Assistant. Sign in and I will greet you by name, explain the current result, suggest improvements, and help you describe this prototype for your dissertation.", "bot");
}

async function askAssistant(event) {
  event.preventDefault();
  const question = assistantInput.value.trim();
  if (!question) {
    return;
  }
  appendAssistantMessage(question, "user");
  assistantInput.value = "";
  const typingMessage = appendAssistantMessage("APX Assistant is analysing the current scenario...", "bot typing");
  try {
    const response = await fetch("/api/assistant", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, username: currentUser, scenario: lastScenario || calculateScenario(controls.deploymentMode.value) })
    });
    const data = await response.json();
    typingMessage.remove();
    appendAssistantMessage(data.answer || "I could not produce an answer for that question.", "bot", data.assistantMode);
  } catch (error) {
    typingMessage.remove();
    appendAssistantMessage("The assistant is available when the Python server is running.", "bot");
  }
}

function appendAssistantMessage(text, role, meta) {
  const message = document.createElement("div");
  message.className = `assistant-message ${role}`;
  renderAssistantText(message, text);
  if (meta && role.includes("bot")) {
    const badge = document.createElement("small");
    badge.className = "assistant-mode";
    badge.textContent = meta;
    message.appendChild(badge);
  }
  assistantMessages.appendChild(message);
  assistantMessages.scrollTop = assistantMessages.scrollHeight;
  return message;
}

function renderAssistantText(container, text) {
  const urlPattern = /(https?:\/\/[^\s)]+)/g;
  const parts = String(text).split(urlPattern);
  parts.forEach((part) => {
    if (urlPattern.test(part)) {
      const link = document.createElement("a");
      link.href = part;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = part;
      container.appendChild(link);
    } else {
      container.appendChild(document.createTextNode(part));
    }
    urlPattern.lastIndex = 0;
  });
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function drawBarChart(activeMode) {
  const canvas = document.querySelector("#barChart");
  const ctx = canvas.getContext("2d");
  const scenarios = Object.keys(modeFactors).map((mode) => ({
    mode,
    ...modeFactors[mode],
    ...calculateScenario(mode)
  }));

  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = cssVar("--soft");
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  const maxEnergy = Math.max(...scenarios.map((item) => item.energy));
  const barWidth = 130;
  const gap = 80;
  const baseX = 92;
  const baseY = 230;

  ctx.strokeStyle = cssVar("--line");
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(50, baseY);
  ctx.lineTo(710, baseY);
  ctx.stroke();

  scenarios.forEach((item, index) => {
    const x = baseX + index * (barWidth + gap);
    const height = Math.max(10, (item.energy / maxEnergy) * 160);
    ctx.fillStyle = item.mode === activeMode ? modeFactors[item.mode].color : cssVar("--line");
    ctx.fillRect(x, baseY - height, barWidth, height);

    ctx.fillStyle = cssVar("--ink");
    ctx.font = "700 16px system-ui";
    ctx.textAlign = "center";
    ctx.fillText(`${item.energy.toFixed(2)} kWh`, x + barWidth / 2, baseY - height - 12);
    ctx.font = "13px system-ui";
    ctx.fillStyle = cssVar("--muted");
    ctx.fillText(item.label, x + barWidth / 2, baseY + 28);
  });
}

function drawFlow() {
  const canvas = document.querySelector("#flowCanvas");
  const ctx = canvas.getContext("2d");
  let frame = 0;

  function render() {
    frame += 1;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = cssVar("--soft");
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const nodes = [
      { x: 108, y: 205, label: "Requests", color: "#c78b1f" },
      { x: 270, y: 126, label: "Model", color: "#237a57" },
      { x: 430, y: 205, label: "Cloud", color: "#1f7f8a" },
      { x: 282, y: 306, label: "Metrics", color: "#c65f45" }
    ];

    ctx.lineWidth = 3;
    nodes.forEach((node, index) => {
      const next = nodes[(index + 1) % nodes.length];
      ctx.strokeStyle = currentTheme === "dark" ? "rgba(98, 192, 143, 0.28)" : "rgba(35, 122, 87, 0.28)";
      ctx.beginPath();
      ctx.moveTo(node.x, node.y);
      ctx.quadraticCurveTo((node.x + next.x) / 2, (node.y + next.y) / 2 - 28, next.x, next.y);
      ctx.stroke();
    });

    for (let i = 0; i < 14; i += 1) {
      const angle = (frame * 0.016 + i / 14) * Math.PI * 2;
      const x = 282 + Math.cos(angle) * 175;
      const y = 214 + Math.sin(angle) * 92;
      ctx.fillStyle = i % 3 === 0 ? "#c78b1f" : i % 3 === 1 ? "#237a57" : "#1f7f8a";
      ctx.beginPath();
      ctx.arc(x, y, 4, 0, Math.PI * 2);
      ctx.fill();
    }

    nodes.forEach((node) => {
      ctx.fillStyle = node.color;
      ctx.beginPath();
      ctx.roundRect(node.x - 58, node.y - 34, 116, 68, 12);
      ctx.fill();
      ctx.fillStyle = "#fff";
      ctx.font = "800 15px system-ui";
      ctx.textAlign = "center";
      ctx.fillText(node.label, node.x, node.y + 5);
    });

    ctx.fillStyle = cssVar("--ink");
    ctx.font = "800 24px system-ui";
    ctx.textAlign = "left";
    ctx.fillText("Inference lifecycle", 38, 48);
    ctx.fillStyle = cssVar("--muted");
    ctx.font = "15px system-ui";
    ctx.fillText("Optimise the model, scale the cloud, measure the trade-off.", 38, 76);

    requestAnimationFrame(render);
  }

  render();
}

if (!CanvasRenderingContext2D.prototype.roundRect) {
  CanvasRenderingContext2D.prototype.roundRect = function roundRect(x, y, width, height, radius) {
    this.beginPath();
    this.moveTo(x + radius, y);
    this.arcTo(x + width, y, x + width, y + height, radius);
    this.arcTo(x + width, y + height, x, y + height, radius);
    this.arcTo(x, y + height, x, y, radius);
    this.arcTo(x, y, x + width, y, radius);
    this.closePath();
    return this;
  };
}

drawFlow();
setTheme(currentTheme);
setAuthMode("signin");
loadSession();
updateSimulation();
loadHistory();
