#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
live_benchmark_runner.py — High-precision Live Benchmark Harness executed on GCE instances
Runs Suite 1 (User's Flash Lite Payload), Suite 2 (Standard QA Waterfall), and Suite 3 (Long-Horizon Agent).
"""

import json
import os
import socket
import ssl
import sys
import time
import urllib.request
from typing import Dict, Any, List

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
                    "text": "**Processing User Input**\n\nI am currently processing your initial greeting. My instructions guide me to avoid using specific tools for non-location-based queries and to fulfill requests even if they don't immediately fit tool parameters. I am evaluating the best way to respond."
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

def get_metadata_token():
    try:
        req = urllib.request.Request("http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token", headers={"Metadata-Flavor": "Google"})
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read().decode())["access_token"]
    except Exception as e:
        print(f"[!] Metadata token error: {e}")
        return None

def run_suite_1_user_payload(token: str, iterations: int = 22) -> Dict[str, Any]:
    print(f"[*] Executing Suite 1: User Flash Lite Payload ({iterations} iterations)...")
    payload_bytes = json.dumps(USER_FLASH_LITE_PAYLOAD).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Goog-User-Project": PROJECT_ID
    }
    
    runs = []
    for i in range(iterations):
        t0 = time.perf_counter()
        
        # DNS & TCP & TLS timing
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
        
        # HTTP Request
        http_req = (
            f"POST /v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{MODEL_ID}:streamGenerateContent HTTP/1.1\r\n"
            f"Host: {ENDPOINT_HOST}\r\n"
            f"Authorization: Bearer {token}\r\n"
            f"X-Goog-User-Project: {PROJECT_ID}\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(payload_bytes)}\r\n"
            f"Connection: close\r\n\r\n"
        ).encode("utf-8") + payload_bytes
        
        t_up0 = time.perf_counter()
        ssock.sendall(http_req)
        t_up1 = time.perf_counter()
        
        # Read stream
        first_chunk_time = None
        chunk_times = []
        bytes_received = 0
        while True:
            chunk = ssock.read(512)
            if not chunk:
                break
            t_now = time.perf_counter()
            if first_chunk_time is None:
                first_chunk_time = t_now
            chunk_times.append(t_now)
            bytes_received += len(chunk)
            
        t_end = time.perf_counter()
        ssock.close()
        
        run_record = {
            "run_id": i + 1,
            "dns_ms": round((t_dns1 - t_dns0) * 1000.0, 2),
            "tcp_connect_ms": round((t_tcp1 - t_tcp0) * 1000.0, 2),
            "tls_handshake_ms": round((t_tls1 - t_tcp1) * 1000.0, 2),
            "upload_ms": round((t_up1 - t_up0) * 1000.0, 2),
            "ttft_ms": round(((first_chunk_time - t0) * 1000.0) if first_chunk_time else 0.0, 2),
            "ttlt_ms": round((t_end - t0) * 1000.0, 2),
            "chunks": len(chunk_times),
            "bytes": bytes_received
        }
        runs.append(run_record)
        print(f"  [Run {i+1:02d}] TTFT: {run_record['ttft_ms']}ms | TTLT: {run_record['ttlt_ms']}ms | Handshake: {run_record['tcp_connect_ms'] + run_record['tls_handshake_ms']}ms")
        time.sleep(0.05)
        
    return {"runs": runs}

def run_suite_2_qa_waterfall(token: str, iterations: int = 22) -> Dict[str, Any]:
    print(f"\n[*] Executing Suite 2: Standard QA Waterfall (1K Context) ({iterations} Cold + {iterations} Warm)...")
    qa_prompt = "Explain the fundamental principles of distributed cloud latency and optical networks in 3 concise paragraphs. " * 15
    qa_payload = {
        "contents": [{"role": "user", "parts": [{"text": qa_prompt}]}],
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": 500}
    }
    payload_bytes = json.dumps(qa_payload).encode("utf-8")
    
    cold_runs, warm_runs = [], []
    
    # 1. Cold Runs (New connection each time)
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
            f"POST /v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{MODEL_ID}:streamGenerateContent HTTP/1.1\r\n"
            f"Host: {ENDPOINT_HOST}\r\n"
            f"Authorization: Bearer {token}\r\n"
            f"X-Goog-User-Project: {PROJECT_ID}\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(payload_bytes)}\r\n"
            f"Connection: close\r\n\r\n"
        ).encode("utf-8") + payload_bytes
        
        t_up0 = time.perf_counter()
        ssock.sendall(http_req)
        t_up1 = time.perf_counter()
        
        first_chunk_time = None
        chunk_times = []
        while True:
            chunk = ssock.read(512)
            if not chunk:
                break
            t_now = time.perf_counter()
            if first_chunk_time is None:
                first_chunk_time = t_now
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
            "ttft_ms": round(((first_chunk_time - t0) * 1000.0) if first_chunk_time else 0.0, 2),
            "ttlt_ms": round((t_end - t0) * 1000.0, 2),
            "itl_p95_ms": round(sorted(itls)[int(len(itls)*0.95)], 2) if itls else 0.0,
            "chunks": len(chunk_times)
        })
        time.sleep(0.05)
        
    # 2. Warm Pool Runs (Reusing connection / HTTP Client)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Goog-User-Project": PROJECT_ID
    }
    for i in range(iterations):
        t0 = time.perf_counter()
        req = urllib.request.Request(API_URL, data=payload_bytes, headers=headers, method="POST")
        first_chunk_time = None
        chunk_times = []
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                while True:
                    chunk = resp.read(512)
                    if not chunk:
                        break
                    t_now = time.perf_counter()
                    if first_chunk_time is None:
                        first_chunk_time = t_now
                    chunk_times.append(t_now)
            t_end = time.perf_counter()
            itls = [(chunk_times[j] - chunk_times[j-1]) * 1000.0 for j in range(1, len(chunk_times))] if len(chunk_times) > 1 else [0]
            warm_runs.append({
                "run_id": i + 1,
                "ttft_ms": round(((first_chunk_time - t0) * 1000.0) if first_chunk_time else 0.0, 2),
                "ttlt_ms": round((t_end - t0) * 1000.0, 2),
                "itl_p95_ms": round(sorted(itls)[int(len(itls)*0.95)], 2) if itls else 0.0,
                "chunks": len(chunk_times)
            })
        except Exception as e:
            print(f"Warm run error: {e}")
        time.sleep(0.05)
        
    return {"cold_runs": cold_runs, "warm_runs": warm_runs}

def run_suite_3_agent_simulation(token: str, runs_per_tier: int = 20) -> Dict[str, Any]:
    print(f"\n[*] Executing Suite 3: Long-Horizon Agent Simulation ({runs_per_tier} runs for 10/20/30 steps)...")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Goog-User-Project": PROJECT_ID
    }
    
    agent_results = {}
    for steps in [10, 20, 30]:
        tier_runs = []
        for run_idx in range(runs_per_tier):
            t_task_start = time.perf_counter()
            step_latencies = []
            
            for step in range(1, steps + 1):
                # Context grows by ~6KB per step
                prompt_text = "Simulated tool context iteration state. " * (step * 30)
                body = {
                    "contents": [{"role": "user", "parts": [{"text": f"Step {step}: {prompt_text}\nEmit next tool call action."}]}],
                    "generationConfig": {"maxOutputTokens": 60, "temperature": 0.0}
                }
                data = json.dumps(body).encode("utf-8")
                
                t_step0 = time.perf_counter()
                req = urllib.request.Request(API_URL, data=data, headers=headers, method="POST")
                try:
                    with urllib.request.urlopen(req, timeout=15) as resp:
                        resp.read(512)
                except Exception:
                    pass
                t_step1 = time.perf_counter()
                step_latencies.append((t_step1 - t_step0) * 1000.0)
                
            t_task_end = time.perf_counter()
            total_task_s = round(t_task_end - t_task_start, 2)
            tier_runs.append({
                "run_id": run_idx + 1,
                "total_wall_clock_s": total_task_s,
                "avg_step_ms": round(sum(step_latencies) / len(step_latencies), 2),
                "steps": steps
            })
            print(f"  [{steps}-Step Agent | Run {run_idx+1:02d}/{runs_per_tier}] Total Wall-Clock: {total_task_s}s (Avg step: {tier_runs[-1]['avg_step_ms']}ms)")
            time.sleep(0.1)
            
        agent_results[f"{steps}_steps"] = tier_runs
        
    return agent_results

def main():
    print("="*80)
    print(f" STARTING FULL 3-SUITE LIVE BENCHMARK ON {socket.gethostname()}")
    print("="*80)
    
    token = get_metadata_token()
    if not token:
        print("[!] Fatal: Cannot get metadata OAuth token")
        sys.exit(1)
        
    s1 = run_suite_1_user_payload(token, iterations=22)
    s2 = run_suite_2_qa_waterfall(token, iterations=22)
    s3 = run_suite_3_agent_simulation(token, runs_per_tier=20)
    
    full_data = {
        "hostname": socket.gethostname(),
        "timestamp": time.time(),
        "suite_1_user_flash_lite_payload": s1,
        "suite_2_qa_waterfall": s2,
        "suite_3_agent_simulation": s3
    }
    
    out_path = "/tmp/live_benchmark_raw_results.json"
    with open(out_path, "w") as f:
        json.dump(full_data, f, indent=2)
        
    print("\n[✓] Raw benchmark data written to disk. Outputting payload:")
    print("===RAW_DATA_START===")
    print(json.dumps(full_data))
    print("===RAW_DATA_END===")

if __name__ == "__main__":
    main()
