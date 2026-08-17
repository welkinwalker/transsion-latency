#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gce_benchmark_agent.py — Production Benchmark Harness for Gemini Latency in GCE VM
Runs on VM in europe-west2 and europe-west4, measures network RTT, TTFT, TTLT, and agent simulation.
"""

import asyncio
import json
import os
import socket
import ssl
import sys
import time
import urllib.request
from typing import Dict, Any, List

PROJECT_ID = "dywx-357111"
LOCATION = "europe-west4"
ENDPOINT_HOST = f"{LOCATION}-aiplatform.googleapis.com"
MODEL_NAME = "gemini-1.5-flash"
API_PATH = f"/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{MODEL_NAME}:streamGenerateContent"

def get_auth_token():
    try:
        req = urllib.request.Request("http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token", headers={"Metadata-Flavor": "Google"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return data["access_token"]
    except Exception as e:
        print(f"[!] Warning: Failed to fetch metadata token: {e}")
        return None

def probe_network_layer(host: str, port: int = 443, iterations: int = 30):
    dns_times = []
    tcp_times = []
    tls_times = []
    
    for _ in range(iterations):
        # 1. DNS
        t0 = time.perf_counter()
        ip = socket.gethostbyname(host)
        t1 = time.perf_counter()
        dns_times.append((t1 - t0) * 1000.0)
        
        # 2. TCP
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        t2 = time.perf_counter()
        sock.connect((ip, port))
        t3 = time.perf_counter()
        tcp_times.append((t3 - t2) * 1000.0)
        
        # 3. TLS
        ctx = ssl.create_default_context()
        ssock = ctx.wrap_socket(sock, server_hostname=host)
        t4 = time.perf_counter()
        tls_times.append((t4 - t3) * 1000.0)
        
        ssock.close()
        time.sleep(0.02)
        
    return {
        "dns_avg_ms": round(sum(dns_times) / len(dns_times), 2),
        "dns_p95_ms": round(sorted(dns_times)[int(len(dns_times)*0.95)], 2),
        "tcp_rtt_avg_ms": round(sum(tcp_times) / len(tcp_times), 2),
        "tcp_rtt_p50_ms": round(sorted(tcp_times)[len(tcp_times)//2], 2),
        "tcp_rtt_p95_ms": round(sorted(tcp_times)[int(len(tcp_times)*0.95)], 2),
        "tls_avg_ms": round(sum(tls_times) / len(tls_times), 2),
        "tls_p95_ms": round(sorted(tls_times)[int(len(tls_times)*0.95)], 2),
        "handshake_total_avg_ms": round((sum(dns_times) + sum(tcp_times) + sum(tls_times)) / len(dns_times), 2)
    }

def run_gemini_api_test(token: str, iterations: int = 15, context_size: str = "1k"):
    # Create request payload
    if context_size == "1k":
        context_text = "Detailed Cloud and Artificial Intelligence infrastructure comparison benchmark. " * 30
    elif context_size == "4k":
        context_text = "Comprehensive Enterprise Agent Architecture and Distributed Systems telemetry log analysis. " * 120
    else:
        context_text = "What is the capital of France and explain why?"
        
    payload = {
        "contents": [{
            "role": "user",
            "parts": [{"text": f"Context: {context_text}\n\nTask: Summarize in 3 bullet points."}]
        }],
        "generationConfig": {
            "temperature": 0.0,
            "seed": 42,
            "maxOutputTokens": 300
        }
    }
    payload_bytes = json.dumps(payload).encode("utf-8")
    
    url = f"https://{ENDPOINT_HOST}{API_PATH}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Host": ENDPOINT_HOST
    }
    
    ttft_list = []
    ttlt_list = []
    chunk_counts = []
    
    for i in range(iterations):
        t0 = time.perf_counter()
        req = urllib.request.Request(url, data=payload_bytes, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                t_first_chunk = None
                chunk_times = []
                chunks = 0
                while True:
                    chunk = resp.read(256)
                    if not chunk:
                        break
                    t_chunk = time.perf_counter()
                    if t_first_chunk is None:
                        t_first_chunk = t_chunk
                    chunk_times.append(t_chunk)
                    chunks += 1
                    
                t_end = time.perf_counter()
                
                if t_first_chunk is not None:
                    ttft_ms = (t_first_chunk - t0) * 1000.0
                    ttlt_ms = (t_end - t0) * 1000.0
                    ttft_list.append(ttft_ms)
                    ttlt_list.append(ttlt_ms)
                    chunk_counts.append(chunks)
        except Exception as e:
            print(f"[!] API call failed on iteration {i}: {e}")
            time.sleep(0.5)
            
        time.sleep(0.1)
        
    if not ttft_list:
        return {"error": "All API calls failed"}
        
    return {
        "samples": len(ttft_list),
        "payload_bytes": len(payload_bytes),
        "ttft_avg_ms": round(sum(ttft_list) / len(ttft_list), 2),
        "ttft_p50_ms": round(sorted(ttft_list)[len(ttft_list)//2], 2),
        "ttft_p95_ms": round(sorted(ttft_list)[int(len(ttft_list)*0.95)], 2),
        "ttlt_avg_ms": round(sum(ttlt_list) / len(ttlt_list), 2),
        "ttlt_p50_ms": round(sorted(ttlt_list)[len(ttlt_list)//2], 2),
        "ttlt_p95_ms": round(sorted(ttlt_list)[int(len(ttlt_list)*0.95)], 2),
        "avg_chunks": round(sum(chunk_counts) / len(chunk_counts), 1)
    }

def main():
    print(f"================================================================")
    print(f" Starting Gemini Network Benchmark on GCE Instance")
    print(f" Target Endpoint: {ENDPOINT_HOST}")
    print(f" Project: {PROJECT_ID}, Location: {LOCATION}")
    print(f"================================================================")
    
    # 1. Network Layer Probe
    print("\n[*] Phase 1: Probing Network Layer (DNS, TCP RTT, TLS 1.3)...")
    net_res = probe_network_layer(ENDPOINT_HOST, iterations=30)
    print(f"  • TCP RTT (P50/Avg/P95) : {net_res['tcp_rtt_p50_ms']}ms / {net_res['tcp_rtt_avg_ms']}ms / {net_res['tcp_rtt_p95_ms']}ms")
    print(f"  • TLS Handshake (Avg)   : {net_res['tls_avg_ms']}ms")
    print(f"  • Total Handshake (Avg) : {net_res['handshake_total_avg_ms']}ms")
    
    # 2. Vertex AI Gemini API Tests
    print("\n[*] Phase 2: Running Real Vertex AI Gemini 1.5 Flash API Benchmark...")
    token = get_auth_token()
    if not token:
        print("[!] Cannot get OAuth token, skipping live API tests.")
        api_1k = {}
        api_4k = {}
    else:
        print("  • Testing 1K Context (~5KB Payload)...")
        api_1k = run_gemini_api_test(token, iterations=12, context_size="1k")
        print(f"    - TTFT (P50/Avg/P95): {api_1k.get('ttft_p50_ms')}ms / {api_1k.get('ttft_avg_ms')}ms / {api_1k.get('ttft_p95_ms')}ms")
        print(f"    - TTLT (P50/Avg/P95): {api_1k.get('ttlt_p50_ms')}ms / {api_1k.get('ttlt_avg_ms')}ms / {api_1k.get('ttlt_p95_ms')}ms")
        
        print("  • Testing 4K Context (~20KB Payload)...")
        api_4k = run_gemini_api_test(token, iterations=10, context_size="4k")
        print(f"    - TTFT (P50/Avg/P95): {api_4k.get('ttft_p50_ms')}ms / {api_4k.get('ttft_avg_ms')}ms / {api_4k.get('ttft_p95_ms')}ms")
        print(f"    - TTLT (P50/Avg/P95): {api_4k.get('ttlt_p50_ms')}ms / {api_4k.get('ttlt_avg_ms')}ms / {api_4k.get('ttlt_p95_ms')}ms")

    # Final JSON Summary
    summary = {
        "timestamp": time.time(),
        "hostname": socket.gethostname(),
        "network_probe": net_res,
        "api_benchmark_1k": api_1k,
        "api_benchmark_4k": api_4k
    }
    
    out_file = "/tmp/benchmark_results.json"
    with open(out_file, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n[✓] Benchmark completed! Results written to {out_file}")

if __name__ == "__main__":
    main()
