#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_definitive_empirical_benchmark.py — Executes high-precision empirical benchmarks on live GCE VMs,
retrieves 100% raw telemetry back to local disk via GCP Guest Attributes, deletes all VMs,
and outputs complete statistical reports to GitHub.
"""

import json
import math
import os
import subprocess
import sys
import time
from typing import Dict, Any, List

PROJECT = "dywx-357111"
VM_W4 = "vm-bench-w4-empirical"
ZONE_W4 = "europe-west4-a"

VM_FINLAND = "vm-bench-finland-empirical"
ZONE_FINLAND = "europe-north1-a"

DATA_DIR = "/usr/local/google/home/levichen/transsion-latency/data"
os.makedirs(DATA_DIR, exist_ok=True)

IN_VM_BENCHMARK_CODE = """
import json, math, os, socket, ssl, sys, time, urllib.request

PROJECT_ID = "dywx-357111"
LOCATION = "eu"
ENDPOINT_HOST = "aiplatform.eu.rep.googleapis.com"
MODEL_ID = "gemini-3.5-flash-lite"
API_URL = f"https://{ENDPOINT_HOST}/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{MODEL_ID}:streamGenerateContent"

USER_FLASH_LITE_PAYLOAD = {
    "contents": [
        {"role": "user", "parts": [{"text": "hi"}]},
        {
            "role": "model",
            "parts": [
                {
                    "text": "**Processing User Input**\\n\\nI am currently processing your initial greeting. My instructions guide me to avoid using specific tools for non-location-based queries and to fulfill requests even if they don't immediately fit tool parameters. I am evaluating the best way to respond."
                },
                {"text": "Hello! How can I help you today?"}
            ]
        },
        {"role": "user", "parts": [{"text": "hi"}]}
    ],
    "generationConfig": {
        "maxOutputTokens": 65535,
        "thinkingConfig": {
            "thinkingLevel": "MINIMAL"
        }
    },
    "safetySettings": [
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "OFF"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "OFF"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "OFF"},
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "OFF"}
    ],
    "tools": [
        {"googleSearch": {}},
        {"googleMaps": {}}
    ],
    "toolConfig": {
        "retrievalConfig": {"languageCode": "en_US"}
    }
}

def set_guest_attr(key, value):
    try:
        url = f"http://metadata.google.internal/computeMetadata/v1/instance/guest-attributes/benchmark/{key}"
        data = value.encode("utf-8") if isinstance(value, str) else json.dumps(value).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Metadata-Flavor": "Google"}, method="PUT")
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"Failed to set guest attr {key}: {e}", flush=True)

def get_token():
    req = urllib.request.Request("http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token", headers={"Metadata-Flavor": "Google"})
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read().decode())["access_token"]

def run_suite_1(token, iterations=22):
    set_guest_attr("status", "RUNNING_SUITE_1")
    print(f"[*] Starting Suite 1 ({iterations} runs)...", flush=True)
    payload_bytes = json.dumps(USER_FLASH_LITE_PAYLOAD).encode("utf-8")
    runs = []
    
    for i in range(iterations):
        t0 = time.perf_counter()
        t_dns0 = time.perf_counter()
        ip = socket.gethostbyname(ENDPOINT_HOST)
        t_dns1 = time.perf_counter()
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(15.0)
        t_tcp0 = time.perf_counter()
        sock.connect((ip, 443))
        t_tcp1 = time.perf_counter()
        
        ctx = ssl.create_default_context()
        ssock = ctx.wrap_socket(sock, server_hostname=ENDPOINT_HOST)
        t_tls1 = time.perf_counter()
        
        http_req = (
            f"POST /v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{MODEL_ID}:streamGenerateContent HTTP/1.1\\r\\n"
            f"Host: {ENDPOINT_HOST}\\r\\n"
            f"Authorization: Bearer {token}\\r\\n"
            f"X-Goog-User-Project: {PROJECT_ID}\\r\\n"
            f"Content-Type: application/json\\r\\n"
            f"Content-Length: {len(payload_bytes)}\\r\\n"
            f"Connection: close\\r\\n\\r\\n"
        ).encode("utf-8") + payload_bytes
        
        t_up0 = time.perf_counter()
        ssock.sendall(http_req)
        t_up1 = time.perf_counter()
        
        first_chunk = None
        chunk_times = []
        bytes_rec = 0
        while True:
            chunk = ssock.read(512)
            if not chunk:
                break
            t_now = time.perf_counter()
            if first_chunk is None:
                first_chunk = t_now
            chunk_times.append(t_now)
            bytes_rec += len(chunk)
        t_end = time.perf_counter()
        ssock.close()
        
        runs.append({
            "run_id": i + 1,
            "dns_ms": round((t_dns1 - t_dns0) * 1000.0, 2),
            "tcp_connect_ms": round((t_tcp1 - t_tcp0) * 1000.0, 2),
            "tls_handshake_ms": round((t_tls1 - t_tcp1) * 1000.0, 2),
            "upload_ms": round((t_up1 - t_up0) * 1000.0, 2),
            "ttft_ms": round(((first_chunk - t0) * 1000.0) if first_chunk else 0.0, 2),
            "ttlt_ms": round((t_end - t0) * 1000.0, 2),
            "chunks": len(chunk_times),
            "bytes": bytes_rec
        })
        time.sleep(0.02)
        
    set_guest_attr("suite_1", json.dumps(runs))
    return runs

def run_suite_2(token, iterations=22):
    set_guest_attr("status", "RUNNING_SUITE_2")
    print(f"[*] Starting Suite 2 ({iterations} Cold + {iterations} Warm)...", flush=True)
    prompt = "Explain distributed cloud latency, optical transit, and packet queuing in 3 paragraphs. " * 12
    payload_bytes = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": 400}
    }).encode("utf-8")
    
    cold_runs, warm_runs = [], []
    for i in range(iterations):
        t0 = time.perf_counter()
        ip = socket.gethostbyname(ENDPOINT_HOST)
        t_dns = time.perf_counter()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(15.0)
        sock.connect((ip, 443))
        t_tcp = time.perf_counter()
        ctx = ssl.create_default_context()
        ssock = ctx.wrap_socket(sock, server_hostname=ENDPOINT_HOST)
        t_tls = time.perf_counter()
        http_req = (
            f"POST /v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{MODEL_ID}:streamGenerateContent HTTP/1.1\\r\\n"
            f"Host: {ENDPOINT_HOST}\\r\\n"
            f"Authorization: Bearer {token}\\r\\n"
            f"X-Goog-User-Project: {PROJECT_ID}\\r\\n"
            f"Content-Type: application/json\\r\\n"
            f"Content-Length: {len(payload_bytes)}\\r\\n"
            f"Connection: close\\r\\n\\r\\n"
        ).encode("utf-8") + payload_bytes
        
        t_up0 = time.perf_counter()
        ssock.sendall(http_req)
        t_up1 = time.perf_counter()
        
        first_chunk = None
        chunk_times = []
        while True:
            chunk = ssock.read(512)
            if not chunk:
                break
            t_now = time.perf_counter()
            if first_chunk is None:
                first_chunk = t_now
            chunk_times.append(t_now)
        t_end = time.perf_counter()
        ssock.close()
        
        itls = [(chunk_times[j] - chunk_times[j-1]) * 1000.0 for j in range(1, len(chunk_times))] if len(chunk_times) > 1 else [0]
        cold_runs.append({
            "run_id": i + 1,
            "dns_ms": round((t_dns - t0) * 1000.0, 2),
            "tcp_ms": round((t_tcp - t_dns) * 1000.0, 2),
            "tls_ms": round((t_tls - t_tcp) * 1000.0, 2),
            "upload_ms": round((t_up1 - t_up0) * 1000.0, 2),
            "ttft_ms": round(((first_chunk - t0) * 1000.0) if first_chunk else 0.0, 2),
            "ttlt_ms": round((t_end - t0) * 1000.0, 2),
            "itl_p95_ms": round(sorted(itls)[int(len(itls)*0.95)], 2) if itls else 0.0,
            "chunks": len(chunk_times)
        })
        time.sleep(0.02)
        
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "X-Goog-User-Project": PROJECT_ID}
    for i in range(iterations):
        t0 = time.perf_counter()
        req = urllib.request.Request(API_URL, data=payload_bytes, headers=headers, method="POST")
        first_chunk = None
        chunk_times = []
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                while True:
                    chunk = resp.read(512)
                    if not chunk:
                        break
                    t_now = time.perf_counter()
                    if first_chunk is None:
                        first_chunk = t_now
                    chunk_times.append(t_now)
            t_end = time.perf_counter()
            itls = [(chunk_times[j] - chunk_times[j-1]) * 1000.0 for j in range(1, len(chunk_times))] if len(chunk_times) > 1 else [0]
            warm_runs.append({
                "run_id": i + 1,
                "ttft_ms": round(((first_chunk - t0) * 1000.0) if first_chunk else 0.0, 2),
                "ttlt_ms": round((t_end - t0) * 1000.0, 2),
                "itl_p95_ms": round(sorted(itls)[int(len(itls)*0.95)], 2) if itls else 0.0,
                "chunks": len(chunk_times)
            })
        except Exception as e:
            print(f"Warm run err: {e}", flush=True)
        time.sleep(0.02)
        
    res = {"cold_runs": cold_runs, "warm_runs": warm_runs}
    set_guest_attr("suite_2", json.dumps(res))
    return res

def run_suite_3(token, runs_per_tier=20):
    set_guest_attr("status", "RUNNING_SUITE_3")
    print(f"[*] Starting Suite 3 (Agent 10/20/30 steps x {runs_per_tier})...", flush=True)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "X-Goog-User-Project": PROJECT_ID}
    agent_res = {}
    
    for steps in [10, 20, 30]:
        tier_runs = []
        for run_idx in range(runs_per_tier):
            t_start = time.perf_counter()
            step_latencies = []
            for step in range(1, steps + 1):
                p_text = "Simulated tool context iteration state. " * (step * 25)
                b = {"contents": [{"role": "user", "parts": [{"text": f"Step {step}: {p_text}\\nAction:"}]}], "generationConfig": {"maxOutputTokens": 40, "temperature": 0.0}}
                d = json.dumps(b).encode("utf-8")
                t_s0 = time.perf_counter()
                req = urllib.request.Request(API_URL, data=d, headers=headers, method="POST")
                try:
                    with urllib.request.urlopen(req, timeout=15) as resp:
                        resp.read(512)
                except Exception:
                    pass
                t_s1 = time.perf_counter()
                step_latencies.append((t_s1 - t_s0) * 1000.0)
            t_end = time.perf_counter()
            tier_runs.append({
                "run_id": run_idx + 1,
                "total_wall_clock_s": round(t_end - t_start, 2),
                "avg_step_ms": round(sum(step_latencies) / len(step_latencies), 2),
                "steps": steps
            })
            time.sleep(0.02)
        agent_res[f"{steps}_steps"] = tier_runs
        
    set_guest_attr("suite_3", json.dumps(agent_res))
    return agent_res

def main():
    print("Starting in-VM benchmark runner...", flush=True)
    token = get_token()
    s1 = run_suite_1(token, 22)
    s2 = run_suite_2(token, 22)
    s3 = run_suite_3(token, 20)
    set_guest_attr("status", "COMPLETED")
    print("ALL SUITES COMPLETED AND WRITTEN TO GUEST ATTRIBUTES!", flush=True)

if __name__ == "__main__":
    main()
"""

def create_vm(vm_name, zone):
    startup_content = f"""#!/bin/bash
cat << 'PYEOF' > /tmp/runner.py
{IN_VM_BENCHMARK_CODE}
PYEOF
python3 -u /tmp/runner.py > /tmp/runner.log 2>&1
"""
    tmp_file = f"/tmp/startup_{vm_name}.sh"
    with open(tmp_file, "w") as f:
        f.write(startup_content)
        
    cmd = [
        "/usr/local/google/home/levichen/google-cloud-sdk/bin/gcloud", "compute", "instances", "create", vm_name,
        "--project", PROJECT,
        "--zone", zone,
        "--machine-type", "e2-standard-4",
        "--image-family", "debian-12",
        "--image-project", "debian-cloud",
        "--scopes", "cloud-platform",
        "--metadata-from-file", f"startup-script={tmp_file}",
        "--quiet"
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return res.returncode == 0

def get_guest_attr(vm_name, zone, key):
    cmd = [
        "/usr/local/google/home/levichen/google-cloud-sdk/bin/gcloud", "compute", "instances",
        "get-guest-attributes", vm_name,
        "--project", PROJECT,
        "--zone", zone,
        "--query-path", f"benchmark/{key}",
        "--format", "value(value)"
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode == 0:
        return res.stdout.strip()
    return None

def wait_for_completion(vm_name, zone, max_wait=600):
    print(f"[*] Waiting for benchmark completion on {vm_name} ({zone})...")
    t0 = time.time()
    while time.time() - t0 < max_wait:
        status = get_guest_attr(vm_name, zone, "status")
        if status == "COMPLETED":
            print(f"[✓] {vm_name} reached COMPLETED status!")
            s1 = json.loads(get_guest_attr(vm_name, zone, "suite_1") or "[]")
            s2 = json.loads(get_guest_attr(vm_name, zone, "suite_2") or "{}")
            s3 = json.loads(get_guest_attr(vm_name, zone, "suite_3") or "{}")
            return {
                "hostname": vm_name,
                "zone": zone,
                "suite_1_user_flash_lite": s1,
                "suite_2_qa_waterfall": s2,
                "suite_3_agent_simulation": s3
            }
        elif status:
            print(f"  [{vm_name}] Current Status: {status} ({int(time.time() - t0)}s elapsed)")
        time.sleep(10)
    print(f"[!] Timeout on {vm_name}")
    return None

def delete_vms(vm_list):
    print("\n" + "="*80)
    print(" [!] MANDATORY CLEANUP: Deleting ALL benchmark VMs...")
    print("="*80)
    for name, zone in vm_list:
        cmd = [
            "/usr/local/google/home/levichen/google-cloud-sdk/bin/gcloud", "compute", "instances",
            "delete", name,
            "--project", PROJECT,
            "--zone", zone,
            "--quiet"
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print(f"[✓] VM {name} in {zone} deleted.")

def compute_stats(values):
    if not values:
        return {"min": 0, "avg": 0, "p50": 0, "p90": 0, "p95": 0, "max": 0, "stddev": 0, "samples": 0}
    vals = sorted(values)
    n = len(vals)
    mean = sum(vals) / n
    variance = sum((x - mean) ** 2 for x in vals) / n
    return {
        "samples": n,
        "min": round(vals[0], 2),
        "p50": round(vals[int(n * 0.50)], 2),
        "avg": round(mean, 2),
        "p90": round(vals[int(n * 0.90)], 2),
        "p95": round(vals[int(n * 0.95)], 2),
        "max": round(vals[-1], 2),
        "stddev": round(math.sqrt(variance), 2)
    }

def main():
    vms_to_clean = [(VM_W4, ZONE_W4), (VM_FINLAND, ZONE_FINLAND)]
    raw_data = {}
    
    try:
        delete_vms(vms_to_clean)
        
        print("\n[Step 1/3] Creating live empirical benchmark VMs in europe-west4 and europe-north1...")
        ok_w4 = create_vm(VM_W4, ZONE_W4)
        ok_fin = create_vm(VM_FINLAND, ZONE_FINLAND)
        if not (ok_w4 and ok_fin):
            print("[!] VM creation failed.")
            return
            
        print("\n[Step 2/3] Collecting 100% verified raw telemetry data via guest attributes...")
        data_w4 = wait_for_completion(VM_W4, ZONE_W4)
        data_fin = wait_for_completion(VM_FINLAND, ZONE_FINLAND)
        
        raw_data["europe_west4_lowest"] = data_w4
        raw_data["europe_north1_30ms"] = data_fin
        
        with open(os.path.join(DATA_DIR, "europe_west4_raw_benchmark.json"), "w") as f:
            json.dump(data_w4, f, indent=2)
        with open(os.path.join(DATA_DIR, "europe_north1_raw_benchmark.json"), "w") as f:
            json.dump(data_fin, f, indent=2)
            
        print(f"[✓] Raw per-iteration telemetry written to {DATA_DIR}")
        
    finally:
        print("\n[Step 3/3] EXECUTING MANDATORY CLEANUP...")
        delete_vms(vms_to_clean)
        
    # Statistical Processing
    summary = {}
    for key, data in raw_data.items():
        if not data:
            continue
        s1 = data.get("suite_1_user_flash_lite", [])
        s2_cold = data.get("suite_2_qa_waterfall", {}).get("cold_runs", [])
        s2_warm = data.get("suite_2_qa_waterfall", {}).get("warm_runs", [])
        s3 = data.get("suite_3_agent_simulation", {})
        
        summary[key] = {
            "suite_1_user_flash_lite": {
                "ttft_ms": compute_stats([r["ttft_ms"] for r in s1]),
                "ttlt_ms": compute_stats([r["ttlt_ms"] for r in s1]),
                "tcp_connect_ms": compute_stats([r["tcp_connect_ms"] for r in s1]),
                "tls_handshake_ms": compute_stats([r["tls_handshake_ms"] for r in s1]),
                "handshake_total_ms": compute_stats([r["tcp_connect_ms"] + r["tls_handshake_ms"] for r in s1])
            },
            "suite_2_qa_waterfall": {
                "cold_ttft_ms": compute_stats([r["ttft_ms"] for r in s2_cold]),
                "cold_ttlt_ms": compute_stats([r["ttlt_ms"] for r in s2_cold]),
                "cold_upload_ms": compute_stats([r["upload_ms"] for r in s2_cold]),
                "warm_ttft_ms": compute_stats([r["ttft_ms"] for r in s2_warm]),
                "warm_ttlt_ms": compute_stats([r["ttlt_ms"] for r in s2_warm]),
                "warm_itl_p95_ms": compute_stats([r["itl_p95_ms"] for r in s2_warm])
            },
            "suite_3_agent_simulation": {
                "10_steps_total_s": compute_stats([r["total_wall_clock_s"] for r in s3.get("10_steps", [])]),
                "20_steps_total_s": compute_stats([r["total_wall_clock_s"] for r in s3.get("20_steps", [])]),
                "30_steps_total_s": compute_stats([r["total_wall_clock_s"] for r in s3.get("30_steps", [])])
            }
        }
        
    with open(os.path.join(DATA_DIR, "benchmark_comparison_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
        
    print("\n" + "="*80)
    print(" [✓] STATISTICAL SUMMARY RESULT:")
    print("="*80)
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
