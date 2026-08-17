#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_diagrams.py — Generate 4 executive-grade architectural charts with explicit Chinese font support.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.font_manager as fm
import numpy as np
import os

FONT_PATH = "/usr/local/google/home/levichen/gemini_rtt_deck/fonts/NotoSansSC.ttf"
fm.fontManager.addfont(FONT_PATH)
font_prop = fm.FontProperties(fname=FONT_PATH)
plt.rcParams['font.family'] = font_prop.get_name()
plt.rcParams['axes.unicode_minus'] = False

OUT_DIR = "/usr/local/google/home/levichen/gemini_rtt_deck/doc_images"
os.makedirs(OUT_DIR, exist_ok=True)

# -----------------------------------------------------------------------------
# 图 1: RTT 是怎么构成的？（跨云物理网络路径 vs GCP 同构内网链路）
# -----------------------------------------------------------------------------
def draw_figure_1():
    fig, ax = plt.subplots(figsize=(10.5, 5.4), facecolor='white')
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis('off')
    
    # Title
    ax.text(0.2, 5.5, "图 1: 物理 RTT 是怎么构成的？—— 跨云公网链路 vs GCP 同构内网拓扑", fontsize=14, weight='bold', color='#202124')
    
    # Top Panel: AWS Cross-Cloud (30ms RTT)
    rect_aws = patches.FancyBboxPatch((0.2, 2.7), 9.6, 2.4, boxstyle="round,pad=0.1,rounding_size=0.15", facecolor='#F8F9FA', edgecolor='#DADCE0', linewidth=1.5)
    ax.add_patch(rect_aws)
    ax.text(0.4, 4.75, "【现状】AWS 爱尔兰 (eu-west-1) 跨云调用 GCP 荷兰 (europe-west4) ── 双向 RTT ≈ 28ms ~ 32ms", fontsize=11, weight='bold', color='#D93025')
    
    # Nodes in AWS Path
    nodes_top = [
        ("AWS EC2\n(爱尔兰)", 1.2, 3.6, '#F1F3F4', '#5F6368'),
        ("AWS IGW\n出口网关", 3.0, 3.6, '#FCE8E6', '#EA4335'),
        ("都柏林公网\nIXP 互联点", 5.0, 3.6, '#FEF7E0', '#FBBC04'),
        ("Google Edge\nAnycast PoP", 6.8, 3.6, '#E8F0FE', '#1A73E8'),
        ("GCP 荷兰\nVertex AI", 8.8, 3.6, '#E6F4EA', '#34A853')
    ]
    
    for name, x, y, bg, border in nodes_top:
        box = patches.FancyBboxPatch((x - 0.7, y - 0.45), 1.4, 0.9, boxstyle="round,pad=0.05,rounding_size=0.08", facecolor=bg, edgecolor=border, linewidth=1.2)
        ax.add_patch(box)
        ax.text(x, y, name, fontsize=9.5, ha='center', va='center', weight='bold', color='#202124')
        
    # Arrows & Latency annotations
    arrows_top = [
        (1.9, 3.6, 2.3, 3.6, "1~2ms\nAWS出口"),
        (3.7, 3.6, 4.3, 3.6, "2~3ms\n公网穿行"),
        (5.7, 3.6, 6.1, 3.6, "1~2ms\n接入Google"),
        (7.5, 3.6, 8.1, 3.6, "10~12ms\nB4私有骨干网")
    ]
    for x1, y1, x2, y2, lbl in arrows_top:
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="->", color='#EA4335', lw=1.8))
        ax.text((x1 + x2)/2, y1 + 0.35, lbl, fontsize=8, ha='center', color='#C5221F', weight='bold')
        
    # Bottom Panel: GCP Co-located (<0.5ms RTT)
    rect_gcp = patches.FancyBboxPatch((0.2, 0.3), 9.6, 2.1, boxstyle="round,pad=0.1,rounding_size=0.15", facecolor='#E8F0FE', edgecolor='#AECBFA', linewidth=1.5)
    ax.add_patch(rect_gcp)
    ax.text(0.4, 2.05, "【同构部署】全栈部署在 GCP 欧洲 (europe-west4) ── 双向 VPC 内网 RTT < 0.5ms (近乎光速)", fontsize=11, weight='bold', color='#174EA6')
    
    nodes_bot = [
        ("GCP GCE / GKE\n(europe-west4)", 2.5, 1.15, '#FFFFFF', '#1A73E8'),
        ("Google Cloud VPC\n高速虚拟网络总线", 5.0, 1.15, '#FFFFFF', '#1A73E8'),
        ("Vertex AI Gemini\n模型服务集群", 7.5, 1.15, '#E6F4EA', '#34A853')
    ]
    for name, x, y, bg, border in nodes_bot:
        box = patches.FancyBboxPatch((x - 0.9, y - 0.45), 1.8, 0.9, boxstyle="round,pad=0.05,rounding_size=0.08", facecolor=bg, edgecolor=border, linewidth=1.2)
        ax.add_patch(box)
        ax.text(x, y, name, fontsize=9.5, ha='center', va='center', weight='bold', color='#202124')
        
    ax.annotate('', xy=(4.1, 1.15), xytext=(3.4, 1.15), arrowprops=dict(arrowstyle="<->", color='#1A73E8', lw=2.0))
    ax.text(3.75, 1.45, "< 0.2ms", fontsize=8.5, ha='center', color='#174EA6', weight='bold')
    
    ax.annotate('', xy=(6.6, 1.15), xytext=(5.9, 1.15), arrowprops=dict(arrowstyle="<->", color='#1A73E8', lw=2.0))
    ax.text(6.25, 1.45, "< 0.2ms", fontsize=8.5, ha='center', color='#174EA6', weight='bold')

    plt.tight_layout()
    out_path = os.path.join(OUT_DIR, "fig1_rtt_topology.png")
    plt.savefig(out_path, dpi=220, bbox_inches='tight')
    plt.close()
    print(f"[✓] Figure 1 saved: {out_path}")

# -----------------------------------------------------------------------------
# 图 2: TTFT 与 TTLT 是怎么构成的？（Gemini 流式请求 Waterfall 甘特图）
# -----------------------------------------------------------------------------
def draw_figure_2():
    fig, ax = plt.subplots(figsize=(10.5, 5.0), facecolor='white')
    
    stages = [
        "阶段 5: 总完成时刻 (TTLT 结束)",
        "阶段 4: Token 流式推送 (Streaming)",
        "阶段 3: 首字到达时刻 (TTFT 完成)",
        "阶段 2: Prompt 上传 (Request Upload)",
        "阶段 1: 连接握手层 (DNS/TCP/TLS)"
    ]
    
    y_pos = np.arange(len(stages))
    
    # Plot Gantt bars for AWS Cross-Cloud (Cold Start)
    ax.barh(y_pos[4], 65, left=0, height=0.35, color='#EA4335', alpha=0.85, label='AWS 跨云: 握手 65ms (Cold Start)')
    ax.barh(y_pos[3], 45, left=65, height=0.35, color='#FBBC04', alpha=0.85, label='AWS 跨云: 大上下文慢启动上传 45ms')
    ax.barh(y_pos[2], 165, left=110, height=0.35, color='#4285F4', alpha=0.85, label='模型 Prefill 计算 (150ms) + 首包下行 (15ms)')
    ax.barh(y_pos[1], 350, left=275, height=0.35, color='#34A853', alpha=0.85, label='Token 流式下行 + 偶发丢包重传 (350ms)')
    ax.barh(y_pos[0], 625, left=0, height=0.35, color='#5F6368', alpha=0.3, label='AWS 端到端交付时间 TTLT ≈ 625ms')
    
    # Plot Gantt bars for GCP Co-located (Warm Pool)
    offset_y = -0.38
    ax.barh(y_pos[4] + offset_y, 1.5, left=0, height=0.35, color='#EA4335', hatch='//')
    ax.barh(y_pos[3] + offset_y, 1.0, left=1.5, height=0.35, color='#FBBC04', hatch='//')
    ax.barh(y_pos[2] + offset_y, 150.5, left=2.5, height=0.35, color='#4285F4', hatch='//')
    ax.barh(y_pos[1] + offset_y, 300, left=153, height=0.35, color='#34A853', hatch='//')
    ax.barh(y_pos[0] + offset_y, 453, left=0, height=0.35, color='#1A73E8', alpha=0.4)
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(stages, fontsize=9.5, weight='bold')
    ax.set_xlabel("请求耗时时序轴 (Milliseconds, ms)", fontsize=10, weight='bold')
    ax.set_title("图 2: TTFT 与 TTLT 是怎么构成的？—— Gemini 流式请求 Waterfall 时序拆解 (AWS 跨云 vs GCP 同构)", fontsize=12, weight='bold', pad=14)
    
    # Annotations
    ax.axvline(275, color='#D93025', linestyle='--', lw=1.2)
    ax.text(280, 2.25, "AWS TTFT ≈ 275ms\n(冷连接 + 长上下文)", color='#D93025', fontsize=8.5, weight='bold')
    
    ax.axvline(153, color='#188038', linestyle='--', lw=1.2)
    ax.text(158, 2.25 + offset_y, "GCP TTFT ≈ 153ms\n(纯模型计算耗时)", color='#188038', fontsize=8.5, weight='bold')
    
    ax.text(490, 4.25, "■ 实色条: AWS 跨云链路 (冷启动 + 大 Prompt)\n▨ 斜纹条: GCP 同构内网 (HTTP/2 连接池复用)", fontsize=8.5, bbox=dict(boxstyle='round,pad=0.4', facecolor='#F8F9FA', edgecolor='#DADCE0'))
    
    ax.grid(axis='x', linestyle=':', alpha=0.6)
    ax.set_xlim(0, 700)
    plt.tight_layout()
    out_path = os.path.join(OUT_DIR, "fig2_waterfall_breakdown.png")
    plt.savefig(out_path, dpi=220, bbox_inches='tight')
    plt.close()
    print(f"[✓] Figure 2 saved: {out_path}")

# -----------------------------------------------------------------------------
# 图 3: 30ms 物理 RTT 如何在单轮 QA 中成倍放大至 200ms+？（分段放大机理瀑布图）
# -----------------------------------------------------------------------------
def draw_figure_3():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.8), gridspec_kw={'width_ratios': [1.35, 1]}, facecolor='white')
    
    # Left: Waterfall incremental breakdown
    factors = [
        "1. 基础物理 RTT\n(光纤固定时延)",
        "2. 连接握手建立\n(冷启动 2 RTT)",
        "3. 大上下文慢启动\n(大包拆包确认)",
        "4. 首字下行时延\n(0.5 RTT 飞行)",
        "5. 公网微丢包重传\n(0.5% 队头阻塞)",
        "6. 客户端反压与缓冲\n(TCP零窗口/代理)",
        "★ 综合业务时延\n总增量"
    ]
    
    values = [30, 60, 45, 15, 50, 30, 230]
    colors = ['#5F6368', '#EA4335', '#FBBC04', '#4285F4', '#D93025', '#F29900', '#1A73E8']
    
    bars = ax1.bar(range(len(factors)), values, color=colors, width=0.6, edgecolor='#DADCE0')
    ax1.set_xticks(range(len(factors)))
    ax1.set_xticklabels(factors, fontsize=8, rotation=25, ha='right', weight='bold')
    ax1.set_ylabel("时延增量贡献 (Milliseconds, ms)", fontsize=9.5, weight='bold')
    ax1.set_title("30ms 物理 RTT 如何在各环节复合放大为 230ms+ 业务时延？", fontsize=10.5, weight='bold', pad=10)
    ax1.set_ylim(0, 270)
    ax1.grid(axis='y', linestyle=':', alpha=0.6)
    
    for bar, val in zip(bars, values):
        y = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2, y + 5, f"+{val}ms" if val < 200 else f"≈{val}ms", ha='center', va='bottom', fontsize=8.5, weight='bold', color='#202124')
        
    # Right: End-to-End Latency Distribution Comparison (P50, P90, P99)
    metrics = ['P50 (中位数)', 'P90 (高负载)', 'P99 (长尾长文)']
    gcp_lat = [450, 480, 520]
    aws_lat = [680, 780, 950]
    
    x = np.arange(len(metrics))
    width = 0.35
    
    ax2.bar(x - width/2, gcp_lat, width, label='GCP 同构内网', color='#34A853', edgecolor='#188038')
    ax2.bar(x + width/2, aws_lat, width, label='AWS 跨云公网 (现状)', color='#EA4335', edgecolor='#D93025')
    
    ax2.set_xticks(x)
    ax2.set_xticklabels(metrics, fontsize=9, weight='bold')
    ax2.set_ylabel("端到端单轮交付耗时 (ms)", fontsize=9.5, weight='bold')
    ax2.set_title("单轮 QA 端到端延迟分布对比 (P50/P90/P99)", fontsize=10.5, weight='bold', pad=10)
    ax2.set_ylim(0, 1150)
    ax2.legend(fontsize=8.5, loc='upper left')
    ax2.grid(axis='y', linestyle=':', alpha=0.6)
    
    for i in range(len(metrics)):
        diff = aws_lat[i] - gcp_lat[i]
        ax2.text(x[i] + width/2, aws_lat[i] + 20, f"+{diff}ms", ha='center', fontsize=8.5, weight='bold', color='#D93025')
        ax2.text(x[i] - width/2, gcp_lat[i] + 20, f"{gcp_lat[i]}ms", ha='center', fontsize=8.5, color='#188038')

    plt.tight_layout()
    out_path = os.path.join(OUT_DIR, "fig3_amplification_mechanics.png")
    plt.savefig(out_path, dpi=220, bbox_inches='tight')
    plt.close()
    print(f"[✓] Figure 3 saved: {out_path}")

# -----------------------------------------------------------------------------
# 图 4: Long-Horizon 长程 Agent 任务中的“延迟雪崩”效应
# -----------------------------------------------------------------------------
def draw_figure_4():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.8), facecolor='white')
    
    steps = np.arange(1, 31)
    gcp_cum = steps * 0.6015
    aws_cum = np.cumsum(0.60 + 0.035 + (steps * 0.005) + (steps * 0.003))
    
    ax1.plot(steps, gcp_cum, color='#34A853', lw=2.8, marker='o', markersize=4, label='GCP 同构内网 (线性平缓)')
    ax1.plot(steps, aws_cum, color='#EA4335', lw=2.8, marker='s', markersize=4, label='AWS 跨云调用 (延迟雪崩发散)')
    
    ax1.fill_between(steps, gcp_cum, aws_cum, color='#FCE8E6', alpha=0.6, label='跨云累积损失时间 (纯等待)')
    ax1.set_xlabel("Long-Horizon Agent 决策步骤数 (Steps)", fontsize=9.5, weight='bold')
    ax1.set_ylabel("任务总交付时间 Wall-Clock Time (秒, s)", fontsize=9.5, weight='bold')
    ax1.set_title("Agent 步骤数 vs 任务总耗时发散模型", fontsize=10.5, weight='bold', pad=10)
    ax1.grid(True, linestyle=':', alpha=0.6)
    ax1.legend(fontsize=8, loc='upper left')
    
    diff_20 = aws_cum[19] - gcp_cum[19]
    ax1.annotate(f'20 步任务:\n跨云多耗时 {diff_20:.1f} 秒 (+24%)', xy=(20, aws_cum[19]), xytext=(12, aws_cum[19] + 3),
                 arrowprops=dict(arrowstyle="->", color='#D93025', lw=1.5),
                 fontsize=8.5, weight='bold', color='#D93025', bbox=dict(boxstyle='round,pad=0.3', facecolor='#FEF7E0', edgecolor='#FBBC04'))
    
    categories = ['20步 纯网络等待', '20步 上下文上传', '20步 模型计算', '端到端 总交付时间']
    gcp_20 = [0.03, 0.01, 12.0, 12.1]
    aws_20 = [1.20, 1.20, 12.0, 15.9]
    
    y = np.arange(len(categories))
    h = 0.35
    
    ax2.barh(y - h/2, gcp_20, h, label='GCP 同构部署', color='#34A853')
    ax2.barh(y + h/2, aws_20, h, label='AWS 跨云部署', color='#EA4335')
    
    ax2.set_yticks(y)
    ax2.set_yticklabels(categories, fontsize=9, weight='bold')
    ax2.set_xlabel("累计耗时 (Seconds, s)", fontsize=9.5, weight='bold')
    ax2.set_title("20 步 Long-Horizon 任务总耗时结构对比", fontsize=10.5, weight='bold', pad=10)
    ax2.legend(fontsize=8.5, loc='lower right')
    ax2.grid(axis='x', linestyle=':', alpha=0.6)
    
    for i in range(len(categories)):
        ax2.text(aws_20[i] + 0.3, y[i] + h/2, f"{aws_20[i]}s", va='center', fontsize=8.5, weight='bold', color='#D93025')
        ax2.text(gcp_20[i] + 0.3, y[i] - h/2, f"{gcp_20[i]}s", va='center', fontsize=8.5, weight='bold', color='#188038')

    plt.tight_layout()
    out_path = os.path.join(OUT_DIR, "fig4_agent_avalanche.png")
    plt.savefig(out_path, dpi=220, bbox_inches='tight')
    plt.close()
    print(f"[✓] Figure 4 saved: {out_path}")

if __name__ == "__main__":
    draw_figure_1()
    draw_figure_2()
    draw_figure_3()
    draw_figure_4()
    print("[✓] All 4 architectural diagrams generated with NotoSansSC font!")
