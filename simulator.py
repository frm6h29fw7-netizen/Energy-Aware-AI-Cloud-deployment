from __future__ import annotations

from energy_model import MODEL_PROFILES, MODES, TECHNIQUES, WORKLOADS, evaluate


def ask(prompt: str, fallback: str) -> str:
    value = input(f"{prompt} [{fallback}]: ").strip()
    return value or fallback


def main() -> None:
    print("Energy-Aware AI Deployment Simulator")
    print("This Python simulator uses indirect cloud metrics for dissertation evidence.")
    print()
    print("Deployment modes:", ", ".join(MODES))
    print("Optimisation techniques:", ", ".join(TECHNIQUES))
    print("AI model profiles:", ", ".join(MODEL_PROFILES))
    print("Workload types:", ", ".join(WORKLOADS))
    print()

    params = {
        "mode": ask("Choose deployment mode", "container"),
        "technique": ask("Choose optimisation technique", "quantisation"),
        "modelProfile": ask("Choose AI model profile", "efficientnet"),
        "workload": ask("Choose workload type", "standard"),
        "requests": ask("Daily requests", "250000"),
        "modelSize": ask("Model size in MB", "88"),
        "optimisation": ask("Optimisation level 0-80", "45"),
        "utilisation": ask("Average utilisation 15-95", "60"),
        "carbonIntensity": ask("Carbon intensity kg CO2e/kWh", "0.193"),
        "slaLatency": ask("Latency target in ms", "140"),
    }

    selected = evaluate(params)
    baseline_params = dict(params)
    baseline_params["mode"] = "vm"
    baseline = evaluate(baseline_params)
    reduction = max(0, (1 - selected["energyKwh"] / baseline["energyKwh"]) * 100)

    print()
    print("Results")
    print(f"Model profile: {selected['modelProfileLabel']}")
    print(f"Workload type: {selected['workloadLabel']}")
    print(f"Energy use: {selected['energyKwh']:.2f} kWh/day")
    print(f"Carbon estimate: {selected['carbonKg']:.2f} kg CO2e/day")
    print(f"Estimated latency: {selected['latencyMs']:.0f} ms")
    print(f"Accuracy retained: {selected['accuracyPercent']:.1f}%")
    print(f"Estimated cost: £{selected['costGbp']:.2f}/day")
    print(f"Throughput: {selected['throughputRps']:.0f} requests/second")
    print(f"CPU utilisation proxy: {selected['cpuPercent']:.0f}%")
    print(f"GPU utilisation proxy: {selected['gpuPercent']:.0f}%")
    print(f"Memory demand proxy: {selected['memoryMb']:.0f} MB")
    print(f"Efficiency score: {selected['efficiencyScore']:.0f}/100")
    print(f"Risk level: {selected['riskLevel']}")
    print(f"Energy reduction compared with VM baseline: {reduction:.0f}%")
    print()
    print(selected["recommendationTitle"])
    print(selected["recommendationMessage"])
    print()
    print("Note: this is a prototype model using indirect metrics, not a physical power meter.")


if __name__ == "__main__":
    main()
