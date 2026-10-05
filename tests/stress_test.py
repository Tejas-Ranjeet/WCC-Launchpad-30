import time
import statistics
import concurrent.futures
import requests

PREDICT_URL = "http://127.0.0.1:7860/predict"
AGENT_RUN_URL = "http://127.0.0.1:7860/api/agent/run"

SAMPLE_PREDICT_PAYLOAD = {
    "AQI": 115,
    "PM2.5": 42.0,
    "NO2 level": 28.0,
    "SO2 level": 14.0,
    "CO2 level": 425.0,
    "Temperature": 26.5,
    "Humidity": 68.0,
    "Symptoms_Freq": "1-2 times a month",
    "Night_Diff": "Never",
    "Daily_Activity_Impact": "Occasionally",
    "Inhaler_Frequency": "Rarely",
    "Patient_Name": "Stress Test Subject"
}

def hit_predict(i):
    t0 = time.perf_counter()
    try:
        r = requests.post(PREDICT_URL, json=SAMPLE_PREDICT_PAYLOAD, timeout=10)
        dt = time.perf_counter() - t0
        return {"status": r.status_code, "latency": dt, "error": None}
    except Exception as e:
        dt = time.perf_counter() - t0
        return {"status": 0, "latency": dt, "error": str(e)}

def run_stress_test(num_requests=200, concurrency=25):
    print(f"Executing {num_requests} concurrent requests at {PREDICT_URL} with {concurrency} threads...")
    results = []
    t_start = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(hit_predict, i) for i in range(num_requests)]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())
    t_total = time.perf_counter() - t_start

    statuses = [r["status"] for r in results]
    latencies = [r["latency"] for r in results]
    errors = [r["error"] for r in results if r["error"] or r["status"] != 200]

    latencies_sorted = sorted(latencies)
    p50 = statistics.median(latencies_sorted)
    p95 = latencies_sorted[int(len(latencies_sorted) * 0.95)]
    p99 = latencies_sorted[int(len(latencies_sorted) * 0.99)]

    print(f"\n--- STRESS TEST REPORT ---")
    print(f"Total Requests: {num_requests}")
    print(f"Total Time: {t_total:.2f}s")
    print(f"Throughput: {num_requests / t_total:.1f} req/s")
    print(f"Success Count (200 OK): {statuses.count(200)}")
    print(f"Error Count: {len(errors)}")
    print(f"Latency min: {min(latencies)*1000:.1f}ms")
    print(f"Latency p50: {p50*1000:.1f}ms")
    print(f"Latency p95: {p95*1000:.1f}ms")
    print(f"Latency p99: {p99*1000:.1f}ms")
    print(f"Latency max: {max(latencies)*1000:.1f}ms")

    if errors:
        print("Sample errors:", errors[:5])
    return {
        "total": num_requests,
        "success": statuses.count(200),
        "errors": len(errors),
        "p50_ms": p50 * 1000,
        "p95_ms": p95 * 1000,
        "p99_ms": p99 * 1000,
        "throughput_rps": num_requests / t_total
    }

if __name__ == "__main__":
    report = run_stress_test(200, 25)
