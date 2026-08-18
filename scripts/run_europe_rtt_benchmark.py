#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_europe_rtt_benchmark.py — Discovers European GCP region RTTs to europe-west4,
selects Lowest RTT region and ~30ms RTT region, executes comparative benchmarks,
and mandatorily deletes all created VMs.
"""

import json
import os
import re
import subprocess
import sys
import time

PROJECT = "dywx-357111"
TARGET_REGION = "europe-west4"
TARGET_ZONE = "europe-west4-a"
TARGET_VM = "vm-bench-target-w4"

# Candidate European regions to probe against europe-west4
CANDIDATES = [
    {"name": "vm-probe-w4", "region": "europe-west4", "zone": "europe-west4-a"},
    {"name": "vm-probe-belgium", "region": "europe-west1", "zone": "europe-west1-b"},
    {"name": "vm-probe-frankfurt", "region": "europe-west3", "zone": "europe-west3-a"},
    {"name": "vm-probe-warsaw", "region": "europe-central2", "zone": "europe-central2-a"},
    {"name": "vm-probe-finland", "region": "europe-north1", "zone": "europe-north1-a"},
    {"name": "vm-probe-madrid", "region": "europe-southwest1", "zone": "europe-southwest1-a"},
]

def run_cmd(cmd_list):
    print(f"[CMD] {' '.join(cmd_list)}")
    res = subprocess.run(cmd_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        print(f"[!] Stderr: {res.stderr.strip()[:300]}")
    return res

def create_probe_vm(vm_name, zone, target_ip=""):
    startup_script = f"""#!/bin/bash
echo "===STARTUP SCRIPT BEGIN==="
cat << 'AGENT_EOF' > /tmp/probe_runner.py
import json, os, subprocess, time, socket, re

target_ip = "{target_ip}"
target_host = "europe-west4-aiplatform.googleapis.com"

results = {{"hostname": socket.gethostname()}}

# 1. Ping target IP if provided
if target_ip:
    try:
        p = subprocess.run(["ping", "-c", "30", "-i", "0.2", target_ip], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        # Extract avg rtt
        # rtt min/avg/max/mdev = 0.450/0.620/0.890/0.110 ms
        match = re.search(r"min/avg/max/mdev = ([0-9.]+)/([0-9.]+)/([0-9.]+)/([0-9.]+)", p.stdout)
        if match:
            results["vpc_rtt_min_ms"] = float(match.group(1))
            results["vpc_rtt_avg_ms"] = float(match.group(2))
            results["vpc_rtt_max_ms"] = float(match.group(3))
            results["vpc_rtt_mdev_ms"] = float(match.group(4))
    except Exception as e:
        results["vpc_rtt_error"] = str(e)

# 2. Socket TCP RTT to europe-west4-aiplatform.googleapis.com:443
tcp_times = []
for _ in range(30):
    t0 = time.perf_counter()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5.0)
        s.connect((target_host, 443))
        t1 = time.perf_counter()
        tcp_times.append((t1 - t0) * 1000.0)
        s.close()
    except Exception:
        pass
    time.sleep(0.02)

if tcp_times:
    results["endpoint_tcp_avg_ms"] = round(sum(tcp_times) / len(tcp_times), 2)
    results["endpoint_tcp_p50_ms"] = round(sorted(tcp_times)[len(tcp_times)//2], 2)
    results["endpoint_tcp_p95_ms"] = round(sorted(tcp_times)[int(len(tcp_times)*0.95)], 2)

print("===PROBE_RESULT_START===")
print(json.dumps(results))
print("===PROBE_RESULT_END===")
AGENT_EOF

python3 /tmp/probe_runner.py > /tmp/probe.log 2>&1
cat /tmp/probe.log
echo "===STARTUP SCRIPT COMPLETE==="
"""
    tmp_path = f"/tmp/startup_{vm_name}.sh"
    with open(tmp_path, "w") as f:
        f.write(startup_script)
        
    cmd = [
        "/usr/local/google/home/levichen/google-cloud-sdk/bin/gcloud", "compute", "instances", "create", vm_name,
        "--project", PROJECT,
        "--zone", zone,
        "--machine-type", "e2-micro",
        "--image-family", "debian-12",
        "--image-project", "debian-cloud",
        "--scopes", "cloud-platform",
        "--metadata-from-file", f"startup-script={tmp_path}",
        "--quiet"
    ]
    res = run_cmd(cmd)
    return res.returncode == 0

def get_instance_ip(vm_name, zone):
    cmd = [
        "/usr/local/google/home/levichen/google-cloud-sdk/bin/gcloud", "compute", "instances", "describe", vm_name,
        "--project", PROJECT,
        "--zone", zone,
        "--format=value(networkInterfaces[0].networkIP)"
    ]
    res = run_cmd(cmd)
    return res.stdout.strip()

def wait_for_serial_output(vm_name, zone, max_wait=180):
    print(f"[*] Waiting for probe output on {vm_name} ({zone})...")
    t0 = time.time()
    while time.time() - t0 < max_wait:
        cmd = [
            "/usr/local/google/home/levichen/google-cloud-sdk/bin/gcloud", "compute", "instances",
            "get-serial-port-output", vm_name,
            "--project", PROJECT,
            "--zone", zone
        ]
        res = run_cmd(cmd)
        out = res.stdout or ""
        if "===STARTUP SCRIPT COMPLETE===" in out:
            match = re.search(r"===PROBE_RESULT_START===\s*(\{.*?\})\s*===PROBE_RESULT_END===", out, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except Exception:
                    pass
            return None
        time.sleep(5)
    return None

def delete_vms(vm_list):
    print("\n" + "="*80)
    print(" [!] MANDATORY CLEANUP: Deleting ALL benchmark test VMs...")
    print("="*80)
    for vm in vm_list:
        name = vm["name"]
        zone = vm["zone"]
        cmd = [
            "/usr/local/google/home/levichen/google-cloud-sdk/bin/gcloud", "compute", "instances", "delete", name,
            "--project", PROJECT,
            "--zone", zone,
            "--quiet"
        ]
        run_cmd(cmd)
    print("[✓] All VMs submitted for deletion.")

def main():
    created_vms = []
    rtt_summary = []
    
    try:
        # Step 1: Create target VM in europe-west4
        print("\n[Step 1] Creating target receiver in europe-west4...")
        ok = create_probe_vm(TARGET_VM, TARGET_ZONE)
        if not ok:
            print("[!] Failed to create target VM")
            return
        created_vms.append({"name": TARGET_VM, "zone": TARGET_ZONE})
        
        target_ip = get_instance_ip(TARGET_VM, TARGET_ZONE)
        print(f"[✓] Target VM in europe-west4 ready. Internal IP: {target_ip}")
        
        # Step 2: Create probe VMs across Europe
        print("\n[Step 2] Launching probe VMs in European candidate regions...")
        for cand in CANDIDATES:
            if cand["name"] != TARGET_VM:
                ok = create_probe_vm(cand["name"], cand["zone"], target_ip=target_ip)
                if ok:
                    created_vms.append(cand)
                    
        # Step 3: Collect RTT results
        print("\n[Step 3] Collecting RTT measurements across European regions...")
        for vm in created_vms:
            if vm["name"] != TARGET_VM:
                res = wait_for_serial_output(vm["name"], vm["zone"])
                rtt_summary.append({
                    "vm_name": vm["name"],
                    "region": vm.get("region", "unknown"),
                    "zone": vm["zone"],
                    "metrics": res
                })
                print(f"  • {vm['name']} ({vm.get('region')}): {res}")
                
        # Save RTT discovery
        with open("/usr/local/google/home/levichen/transsion-latency/europe_rtt_discovery.json", "w") as f:
            json.dump(rtt_summary, f, indent=2)
            
    finally:
        # Step 4: MANDATORY CLEANUP
        delete_vms(created_vms)

if __name__ == "__main__":
    main()
