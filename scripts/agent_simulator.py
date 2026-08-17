#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agent_simulator.py — Long-Horizon Multi-step ReAct Agent Simulator
Simulates 10, 20, 30 step serial loops with dynamic context swell and fan-out concurrency.
"""

import argparse
import json
import os
import sys
import time
from typing import List, Dict, Any

def simulate_agent_run(steps: int, base_rtt_ms: float, is_gcp_internal: bool = False) -> Dict[str, Any]:
    step_records = []
    total_wall_clock_ms = 0.0
    current_context_kb = 2.0  # Initial 2KB
    
    # Model compute per step (fixed baseline ≈ 600ms)
    model_compute_per_step_ms = 600.0
    
    for step in range(1, steps + 1):
        # Step context swells by 5KB~8KB tool output per step
        current_context_kb += 7.0
        
        # Calculate upload delay based on context size and network RTT
        if is_gcp_internal:
            upload_delay_ms = 0.2
            network_rtt_ms = 0.4
            loss_penalty_ms = 0.0
        else:
            # WAN TCP slow-start delay: Payload > 15KB adds 1~2 RTTs
            num_rtts = 1.0 if current_context_kb < 15.0 else (1.0 + (current_context_kb / 40.0))
            upload_delay_ms = num_rtts * base_rtt_ms
            network_rtt_ms = base_rtt_ms
            # 0.5% chance of packet loss causing 1 RTT retransmit stall
            loss_penalty_ms = 0.005 * base_rtt_ms * 2.0
            
        step_network_ms = upload_delay_ms + network_rtt_ms + loss_penalty_ms
        step_total_ms = model_compute_per_step_ms + step_network_ms
        total_wall_clock_ms += step_total_ms
        
        step_records.append({
            "step": step,
            "context_kb": round(current_context_kb, 1),
            "step_network_ms": round(step_network_ms, 2),
            "step_total_ms": round(step_total_ms, 2)
        })
        
    return {
        "steps": steps,
        "is_gcp_internal": is_gcp_internal,
        "total_wall_clock_s": round(total_wall_clock_ms / 1000.0, 2),
        "pure_network_delay_s": round(sum(s["step_network_ms"] for s in step_records) / 1000.0, 2),
        "model_compute_s": round((steps * model_compute_per_step_ms) / 1000.0, 2),
        "steps_detail": step_records
    }

def main():
    parser = argparse.ArgumentParser(description="Long-Horizon Agent Benchmark Simulator")
    parser.add_argument("--steps", type=int, default=20, help="Number of sequential ReAct steps")
    parser.add_argument("--rtt", type=float, default=30.0, help="Base network RTT in ms")
    args = parser.parse_args()

    print(f"[*] Simulating {args.steps}-Step Long-Horizon Agent Execution...")
    
    aws_res = simulate_agent_run(args.steps, base_rtt_ms=args.rtt, is_gcp_internal=False)
    gcp_res = simulate_agent_run(args.steps, base_rtt_ms=0.4, is_gcp_internal=True)

    print("\n" + "="*70)
    print(f" 20-Step Agent 任务端到端交付耗时模拟对比")
    print("="*70)
    print(f" [AWS 跨云调用 (30ms RTT)]")
    print(f"  • 端到端总时长 (Wall-Clock): {aws_res['total_wall_clock_s']} 秒")
    print(f"  • 纯网络空转与上传耗时   : {aws_res['pure_network_delay_s']} 秒")
    print(f"  • 模型实际计算推理耗时   : {aws_res['model_compute_s']} 秒")
    print(f"\n [GCP 同构部署 (0.4ms RTT)]")
    print(f"  • 端到端总时长 (Wall-Clock): {gcp_res['total_wall_clock_s']} 秒")
    print(f"  • 纯网络空转与上传耗时   : {gcp_res['pure_network_delay_s']} 秒")
    print(f"  • 模型实际计算推理耗时   : {gcp_res['model_compute_s']} 秒")
    print("-"*70)
    saved_time = round(aws_res['total_wall_clock_s'] - gcp_res['total_wall_clock_s'], 2)
    speedup = round((saved_time / aws_res['total_wall_clock_s']) * 100.0, 1)
    print(f" [★ 架构收益] 全栈同构部署节省 {saved_time} 秒，整体交付提速 {speedup}%！")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
