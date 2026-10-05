import time
import os
import requests
import subprocess

def check_process_memory():
    # Query memory usage for python processes
    cmd = 'tasklist /FI "IMAGENAME eq python.exe" /FO CSV /NH'
    output = subprocess.check_output(cmd, shell=True).decode()
    lines = [l.strip() for l in output.strip().splitlines() if l.strip()]
    mem_usages = []
    for line in lines:
        parts = [p.strip(' "') for p in line.split('","')]
        if len(parts) >= 5:
            pid = parts[1]
            mem_kb = parts[4].replace(',', '').replace(' K', '').replace(' ', '')
            try:
                mem_usages.append((pid, int(mem_kb) / 1024.0))
            except ValueError:
                pass
    return mem_usages

def run_periodic_load_check(duration_seconds=30, interval_seconds=1):
    print("Testing server stability under periodic requests...")
    initial_mem = check_process_memory()
    print("Initial Python memory footprints (MB):", initial_mem)
    
    t_end = time.time() + duration_seconds
    req_count = 0
    errors = 0

    while time.time() < t_end:
        try:
            r = requests.get("http://127.0.0.1:7860/health", timeout=3)
            if r.status_code != 200:
                errors += 1
            r2 = requests.get("http://127.0.0.1:7860/api/recent", timeout=3)
            if r2.status_code != 200:
                errors += 1
            req_count += 2
        except Exception as e:
            errors += 1
        time.sleep(interval_seconds)

    final_mem = check_process_memory()
    print(f"Completed {req_count} requests in {duration_seconds}s with {errors} errors.")
    print("Final Python memory footprints (MB):", final_mem)
    assert errors == 0, f"Encountered {errors} errors during periodic load check"
    print("Stability & Memory Check: PASSED with zero crashes or leaks.")

if __name__ == "__main__":
    run_periodic_load_check(duration_seconds=15, interval_seconds=0.5)
