from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import csv


HISTORY_HEADER = [
    "createdAt",
    "username",
    "mode",
    "technique",
    "modelProfile",
    "workload",
    "requests",
    "modelSize",
    "optimisation",
    "utilisation",
    "carbonIntensity",
    "energyKwh",
    "carbonKg",
    "latencyMs",
    "accuracyPercent",
    "costGbp",
    "cpuPercent",
    "gpuPercent",
    "memoryMb",
    "throughputRps",
    "efficiencyScore",
    "riskLevel",
]


@dataclass(frozen=True)
class Mode:
    label: str
    energy_factor: float
    latency_factor: float
    cost_factor: float


@dataclass(frozen=True)
class Technique:
    label: str
    energy_factor: float
    latency_factor: float
    accuracy_penalty: float
    memory_factor: float


@dataclass(frozen=True)
class ModelProfile:
    label: str
    default_size_mb: float
    base_accuracy: float
    compute_factor: float
    base_latency_ms: float
    memory_factor: float


@dataclass(frozen=True)
class Workload:
    label: str
    energy_factor: float
    latency_factor: float
    throughput_factor: float
    accuracy_penalty: float


MODES: Dict[str, Mode] = {
    "vm": Mode("VM baseline", 1.35, 0.92, 1.18),
    "container": Mode("Containers", 0.86, 1.00, 0.88),
    "serverless": Mode("Serverless", 0.74, 1.22, 0.72),
}

TECHNIQUES: Dict[str, Technique] = {
    "none": Technique("No model compression", 1.00, 1.00, 1.00, 1.00),
    "pruning": Technique("Pruning", 0.86, 0.94, 0.85, 0.86),
    "quantisation": Technique("Quantisation", 0.76, 0.87, 1.20, 0.68),
    "distillation": Technique("Knowledge distillation", 0.70, 0.82, 1.45, 0.58),
    "hybrid": Technique("Pruning + quantisation", 0.58, 0.74, 1.85, 0.48),
}

MODEL_PROFILES: Dict[str, ModelProfile] = {
    "mobilenet": ModelProfile("MobileNet image classifier", 32, 94.6, 0.46, 52, 0.52),
    "efficientnet": ModelProfile("EfficientNet vision model", 88, 96.8, 0.74, 68, 0.72),
    "resnet": ModelProfile("ResNet-50 baseline", 98, 96.1, 1.00, 78, 1.00),
    "bert": ModelProfile("BERT text classifier", 420, 95.4, 1.55, 118, 1.36),
}

WORKLOADS: Dict[str, Workload] = {
    "batch": Workload("Batch analytics", 0.82, 0.72, 0.96, 0.0),
    "standard": Workload("Standard API inference", 1.00, 1.00, 1.00, 0.0),
    "realtime": Workload("Real-time inference", 1.18, 1.30, 0.86, 0.2),
    "bursty": Workload("Bursty public traffic", 1.28, 1.44, 0.72, 0.1),
}


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def read_float(value: str | None, fallback: float) -> float:
    try:
        return fallback if value in (None, "") else float(value)
    except ValueError:
        return fallback


def risk_level(accuracy: float, latency: float, sla_latency: float, utilisation: float, cpu: float, gpu: float) -> str:
    if accuracy < 91 or latency > sla_latency or cpu > 88 or gpu > 88:
        return "High"
    if accuracy < 94 or latency > sla_latency * 0.85 or utilisation < 35:
        return "Medium"
    return "Low"


def recommendation(mode_key: str, technique_key: str, model_label: str, workload_label: str, energy: float, latency: float, accuracy: float, sla_latency: float, efficiency: float, risk: str) -> tuple[str, str]:
    if accuracy < 91:
        return "Reduce optimisation pressure", "Accuracy is falling too low. Use lighter optimisation or a larger model for safer deployment."
    if latency > sla_latency:
        return "Latency SLA risk", "The energy saving is useful, but this configuration may breach the response-time target. Reduce model size or move to containers."
    if mode_key == "serverless" and latency > 135:
        return "Use containers for latency-sensitive inference", "Serverless can save idle energy, but this scenario has cold-start and response-time risk."
    if technique_key == "hybrid" and accuracy < 94:
        return "Hybrid compression needs validation", "Combined pruning and quantisation improves efficiency, but the accuracy margin should be tested carefully."
    if efficiency > 70 and energy < 1.5 and latency < 130:
        return "Energy-aware deployment looks suitable", f"{model_label} on {workload_label} gives a strong balance between energy reduction, latency, accuracy retention, and cloud utilisation."
    return "Tune utilisation and model size", f"Risk is {risk.lower()}. Improve the scenario by increasing utilisation, reducing model size, or choosing a lighter optimisation/deployment combination."


def evaluate(params: dict[str, str]) -> dict[str, float | str]:
    mode_key = params.get("mode", "container").lower()
    technique_key = params.get("technique", "quantisation").lower()
    model_key = params.get("modelProfile", "efficientnet").lower()
    workload_key = params.get("workload", "standard").lower()

    mode = MODES.get(mode_key, MODES["container"])
    technique = TECHNIQUES.get(technique_key, TECHNIQUES["quantisation"])
    model = MODEL_PROFILES.get(model_key, MODEL_PROFILES["efficientnet"])
    workload_profile = WORKLOADS.get(workload_key, WORKLOADS["standard"])

    requests = read_float(params.get("requests"), 250000)
    model_size = read_float(params.get("modelSize"), model.default_size_mb)
    optimisation = clamp(read_float(params.get("optimisation"), 45), 0, 80)
    utilisation = clamp(read_float(params.get("utilisation"), 60), 15, 95)
    carbon_intensity = clamp(read_float(params.get("carbonIntensity"), 0.193), 0.02, 0.65)
    sla_latency = clamp(read_float(params.get("slaLatency"), 140), 60, 400)

    workload_units = requests / 100000.0
    size_pressure = model_size / max(20.0, model.default_size_mb)
    optimisation_saving = 1 - optimisation / 125.0
    utilisation_penalty = 1 + max(0, 55 - utilisation) / 95.0

    energy = workload_units * size_pressure * optimisation_saving * utilisation_penalty * mode.energy_factor * technique.energy_factor * model.compute_factor * workload_profile.energy_factor
    carbon = energy * carbon_intensity
    cold_start_penalty = max(0, workload_units - 3.5) * 5.5 if mode_key == "serverless" else 0
    queue_penalty = max(0, workload_units - utilisation / 20.0) * 3.5
    latency = ((model.base_latency_ms + model_size * 0.09 - optimisation * 0.38) * mode.latency_factor * technique.latency_factor * workload_profile.latency_factor) + cold_start_penalty + queue_penalty
    accuracy = max(80, model.base_accuracy - optimisation * 0.08 * technique.accuracy_penalty - workload_profile.accuracy_penalty)
    cost = energy * 0.31 * mode.cost_factor
    cpu = clamp(22 + workload_units * 5.8 + size_pressure * 13 + workload_profile.energy_factor * 6 - utilisation * 0.10 - optimisation * 0.12, 8, 98)
    gpu = clamp(16 + workload_units * 5.0 + size_pressure * 18 + model.compute_factor * 10 - optimisation * 0.18, 6, 96)
    memory = max(96, model_size * technique.memory_factor * model.memory_factor + 128)
    throughput = clamp((1000.0 / max(20.0, latency)) * utilisation * workload_profile.throughput_factor, 1, 5000)
    efficiency = clamp((1 / max(0.12, energy)) * accuracy * min(1.08, sla_latency / max(45, latency)) * min(1.05, throughput / 160.0) * 2.4, 0, 100)
    risk = risk_level(accuracy, latency, sla_latency, utilisation, cpu, gpu)
    rec_title, rec_message = recommendation(mode_key, technique_key, model.label, workload_profile.label, energy, latency, accuracy, sla_latency, efficiency, risk)

    return {
        "mode": mode_key,
        "technique": technique_key,
        "techniqueLabel": technique.label,
        "modelProfile": model_key,
        "modelProfileLabel": model.label,
        "workload": workload_key,
        "workloadLabel": workload_profile.label,
        "requests": round(requests, 4),
        "modelSize": round(model_size, 4),
        "optimisation": round(optimisation, 4),
        "utilisation": round(utilisation, 4),
        "carbonIntensity": round(carbon_intensity, 4),
        "energyKwh": round(energy, 4),
        "carbonKg": round(carbon, 4),
        "latencyMs": round(latency, 4),
        "accuracyPercent": round(accuracy, 4),
        "costGbp": round(cost, 4),
        "cpuPercent": round(cpu, 4),
        "gpuPercent": round(gpu, 4),
        "memoryMb": round(memory, 4),
        "throughputRps": round(throughput, 4),
        "efficiencyScore": round(efficiency, 4),
        "riskLevel": risk,
        "recommendationTitle": rec_title,
        "recommendationMessage": rec_message,
    }


def ensure_history_file(path: Path) -> None:
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        path.write_text(",".join(HISTORY_HEADER) + "\n", encoding="utf-8")
        return

    rows = path.read_text(encoding="utf-8").splitlines()
    if rows and rows[0].split(",") != HISTORY_HEADER:
        old_header = rows[0].split(",")
        migrated_rows = []
        for row in rows[1:]:
            values = row.split(",")
            if old_header and old_header[0] == "createdAt" and "username" not in old_header and len(values) == len(old_header):
                values.insert(1, "guest")
            migrated_rows.append(",".join(values))
        body = "\n".join(migrated_rows)
        path.write_text(",".join(HISTORY_HEADER) + "\n" + body + ("\n" if body else ""), encoding="utf-8")


def save_history(path: Path, result: dict[str, float | str], username: str = "guest") -> None:
    ensure_history_file(path)
    row = {
        "createdAt": datetime.now().isoformat(timespec="seconds"),
        "username": username,
        "mode": result["mode"],
        "technique": result["technique"],
        "modelProfile": result["modelProfile"],
        "workload": result["workload"],
        "requests": result["requests"],
        "modelSize": result["modelSize"],
        "optimisation": result["optimisation"],
        "utilisation": result["utilisation"],
        "carbonIntensity": result["carbonIntensity"],
        "energyKwh": result["energyKwh"],
        "carbonKg": result["carbonKg"],
        "latencyMs": result["latencyMs"],
        "accuracyPercent": result["accuracyPercent"],
        "costGbp": result["costGbp"],
        "cpuPercent": result["cpuPercent"],
        "gpuPercent": result["gpuPercent"],
        "memoryMb": result["memoryMb"],
        "throughputRps": result["throughputRps"],
        "efficiencyScore": result["efficiencyScore"],
        "riskLevel": result["riskLevel"],
    }
    with path.open("a", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=HISTORY_HEADER)
        writer.writerow(row)


def load_history(path: Path, username: str | None = None) -> List[dict[str, str]]:
    ensure_history_file(path)
    with path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    if username:
        return [row for row in rows if row.get("username", "guest") == username]
    return rows
