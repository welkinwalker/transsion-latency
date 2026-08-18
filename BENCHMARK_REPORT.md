# Gemini 3.1 / 3.5 Flash Lite 欧洲现场实测基准测试报告 (100% GCE 实测采集)

> **评测项目 (Project)**：`dywx-357111`  
> **评测大模型**：**Gemini 3.1 / 3.5 Flash Lite** (`gemini-3.5-flash-lite`)  
> **测试端点**：`aiplatform.eu.rep.googleapis.com` (European Representative Regional Endpoint)  
> **对比区域**：
> * ⭐️ **全欧最低延迟基准组**：GCP 荷兰 **`europe-west4-a`**（实测 VPC 物理光纤 RTT = **0.45 ms**）
> * 🎯 **~30ms 延迟仿真对照组**：GCP 芬兰 **`europe-north1-a`**（实测 VPC 物理光纤 RTT = **31.69 ms**）  
> **测试方法与样本量**：每项测试独立执行 $\ge 20$ 轮采样（Suite 1 执行 22 轮，Suite 2 执行 44 轮，Suite 3 执行 60 轮长程任务模拟），所有逐轮原始微秒级遥测数据均已回传并归档至 [`/data`](./data/) 目录供核验查阅。  
> **资源销毁审计**：所有测试虚拟机（`vm-bench-w4-empirical` 与 `vm-bench-finland-empirical`）已在测试完成后**自动强制销毁（100% Cleanup Confirmed）**，当前环境 0 临时资源残留。

---

## 目录

- [一、 原始实测数据集与执行说明](#一-原始实测数据集与执行说明)
- [二、 第一类实测：用户指定 Flash Lite 载荷基准时延对比 (Suite 1 - 22 次采样)](#二-第一类实测用户指定-flash-lite-载荷基准时延对比-suite-1---22-次采样)
- [三、 第二类实测：标准 QA 上下文微观 Waterfall 各阶段时延对比 (Suite 2 - 44 次采样)](#三-第二类实测标准-qa-上下文微观-waterfall-各阶段时延对比-suite-2---44-次采样)
- [四、 第三类实测：Long-Horizon Agent 长程任务多步端到端交付对比 (Suite 3 - 60 次采样)](#四-第三类实测long-horizon-agent-长程任务多步端到端交付对比-suite-3---60-次采样)
- [五、 核心实测结论与架构选型建议](#五-核心实测结论与架构选型建议)
- [附录：GCE 测试资源生命周期销毁与数据审计记录](#附录gce-测试资源生命周期销毁与数据审计记录)

---

## 一、 原始实测数据集与执行说明

本次评测的所有指标均来自于欧洲两地真实 GCE 虚拟机内部执行 Python / Socket / HTTP 客户端直连 `aiplatform.eu.rep.googleapis.com` 的实时抓包与分段计时：

* 📄 **荷兰原生原始数据集**：[`/data/europe_west4_empirical_raw.json`](./data/europe_west4_empirical_raw.json)（包含全部 126 轮测试的逐轮 microsecond 原始打点数据）
* 📄 **芬兰原生原始数据集**：[`/data/europe_north1_empirical_raw.json`](./data/europe_north1_empirical_raw.json)（包含全部 126 轮测试的逐轮 microsecond 原始打点数据）
* 📄 **统计汇总分析文件**：[`/data/empirical_benchmark_summary.json`](./data/empirical_benchmark_summary.json)（包含 Min / Mean / P50 / P90 / P95 / Max / StdDev）

---

## 二、 第一类实测：用户指定 Flash Lite 载荷基准时延对比 (Suite 1 - 22 次采样)

### 1. 测试配置
* **载荷内容**：双轮对话历史（包含用户问候与助手思维链 `Processing User Input`） + Minimal Thinking Config + `googleSearch` / `googleMaps` 双工具声明。
* **采样轮数**：每台虚拟机独立执行 **22 轮真实 API 流式请求**。

### 2. 实测统计汇总对比表

| 核心指标 | europe-west4 荷兰 (最低延迟区) | europe-north1 芬兰 (30ms 仿真区) | 实测时延差距 ($\Delta$) | 相对增幅 |
| :--- | :---: | :---: | :---: | :---: |
| **首字返回 TTFT (P50)** | **415.05 ms** | **655.85 ms** | **+240.80 ms** | ⚠️ **TTFT 恶化 58.0%** |
| **首字返回 TTFT (Avg)** | **422.63 ms** | **756.14 ms** | **+333.51 ms** | ⚠️ **平均首字增加 333.5ms** |
| **首字返回 TTFT (P90)** | **560.93 ms** | **927.23 ms** | **+366.30 ms** | ⚠️ **P90 恶化 65.3%** |
| **首字返回 TTFT (P95)** | **619.01 ms** | **1,027.54 ms** | **+408.53 ms** | ⚠️ **P95 跨入秒级** |
| **首字返回 TTFT (Min / Max)** | 310.97 ms / 735.86 ms | 574.78 ms / 2,271.40 ms | +263.81 ms / +1,535.54 ms | 尾部抖动加剧 |
| **整句交付 TTLT (P50)** | **497.69 ms** | **805.41 ms** | **+307.72 ms** | ⚠️ **TTLT 恶化 61.8%** |
| **整句交付 TTLT (Avg)** | **523.77 ms** | **911.29 ms** | **+387.52 ms** | ⚠️ **平均交付耗时慢 387.5ms** |
| **整句交付 TTLT (P90)** | **713.06 ms** | **1,120.49 ms** | **+407.43 ms** | ⚠️ **P90 慢 407.4ms** |
| **TCP Connect 时延 (P50)** | **0.51 ms** | **0.84 ms** | +0.33 ms | 本地 Anycast POP 接入对等 |
| **TLS 1.3 握手时延 (P50)** | **52.46 ms** | **90.25 ms** | **+37.79 ms** | ⚠️ **跨区握手多出 1 个 RTT** |
| **建连握手总时延 (P50)** | **53.34 ms** | **90.91 ms** | **+37.57 ms** | ⚠️ **握手耗时多 37.6ms** |

---

## 三、 第二类实测：标准 QA 上下文微观 Waterfall 各阶段时延对比 (Suite 2 - 44 次采样)

### 1. 测试配置
* **载荷内容**：1,000 Tokens 标准 Prompt 上下文输入（约 5KB 高熵文本），模型输出 400 Tokens。
* **采样轮数**：每台虚拟机执行 **22 次 Cold Connect（新建 TLS 1.3 连接）** + **22 次 Warm Pool（复用 HTTP 连接池）**。

### 2. 实测微观各阶段 Waterfall 对比表

| 度量阶段 / 场景 | europe-west4 荷兰 (最低延迟区) | europe-north1 芬兰 (30ms 仿真区) | 实测时延差距 ($\Delta$) | 相对影响 |
| :--- | :---: | :---: | :---: | :---: |
| **Cold: Payload 上传耗时 (P50)** | **0.06 ms** | **0.12 ms** | +0.06 ms | 本地内网上传极速 |
| **Cold: 首字返回 TTFT (P50)** | **345.52 ms** | **631.12 ms** | **+285.60 ms** | ⚠️ **冷连首字慢 285.6ms (82.7%)** |
| **Cold: 首字返回 TTFT (Avg)** | **358.31 ms** | **702.94 ms** | **+344.63 ms** | ⚠️ **冷连平均慢 344.6ms** |
| **Cold: 整句交付 TTLT (P50)** | **1,980.47 ms** | **2,342.38 ms** | **+361.91 ms** | ⚠️ **整句交付慢 361.9ms** |
| **Cold: 整句交付 TTLT (Avg)** | **1,943.02 ms** | **2,354.43 ms** | **+411.41 ms** | ⚠️ **平均交付慢 411.4ms** |
| **Warm: 首字返回 TTFT (P50)** | **367.02 ms** | **662.41 ms** | **+295.39 ms** | ⚠️ **热连首字慢 295.4ms (80.5%)** |
| **Warm: 首字返回 TTFT (Avg)** | **382.84 ms** | **680.89 ms** | **+298.05 ms** | ⚠️ **热连平均慢 298.1ms** |
| **Warm: 整句交付 TTLT (P50)** | **1,905.84 ms** | **2,227.71 ms** | **+321.87 ms** | ⚠️ **热连整句慢 321.9ms** |
| **Warm: 流式块间抖动 ITL (P95)** | **157.46 ms** | **147.19 ms** | -10.27 ms | 流式解码块传输对等 |

---

## 四、 第三类实测：Long-Horizon Agent 长程任务多步端到端交付对比 (Suite 3 - 60 次采样)

### 1. 测试配置
* **模拟场景**：长程 ReAct Agent 工具循环调用，Context 随执行步数动态膨胀（2KB $\to$ 25KB $\to$ 75KB $\to$ 180KB）。
* **阶梯任务**：
  * **10-Step 轻量 Agent 任务**：执行 20 轮全流程调用。
  * **20-Step 标准 Agent 任务**：执行 20 轮全流程调用。
  * **30-Step 深度 Long-Horizon 任务**：执行 20 轮全流程调用。

### 2. 实测长程任务端到端交付耗时对比表

| Agent 任务复杂度阶梯 | europe-west4 荷兰 (最低延迟区) | europe-north1 芬兰 (30ms 仿真区) | 实测节省时间 ($\Delta$) | 端到端加速收益 (Speedup) |
| :--- | :---: | :---: | :---: | :---: |
| **10-Step Agent 任务 (P50)** | **4.17 秒** | **6.91 秒** | **节省 2.74 秒** | 🚀 **同域部署提速 39.6%** |
| **10-Step Agent 任务 (Avg)** | **4.21 秒** | **6.98 秒** | **节省 2.77 秒** | 🚀 **平均提速 39.7%** |
| **20-Step Agent 任务 (P50)** | **8.40 秒** | **14.05 秒** | **节省 5.65 秒** | 🚀 **同域部署提速 40.2%** |
| **20-Step Agent 任务 (Avg)** | **8.50 秒** | **14.22 秒** | **节省 5.72 秒** | 🚀 **平均提速 40.2%** |
| **30-Step 深度 Agent (P50)** | **13.45 秒** | **22.10 秒** | **节省 8.65 秒** | 🚀 **同域部署提速 39.1%** |
| **30-Step 深度 Agent (Avg)** | **13.57 秒** | **22.03 秒** | **节省 8.46 秒** | 🚀 **平均提速 38.4%** |

```
===================================================================================================
 Gemini 3.5 Flash Lite 现场实测 Agent 端到端交付耗时对比图
===================================================================================================
 [10-Step Agent 任务 (P50)]
  • europe-west4 (荷兰同域)  : ▇▇▇▇ 4.17s
  • europe-north1 (30ms仿真) : ▇▇▇▇▇▇▇ 6.91s  (多耗时 +2.74s | 慢 65.7%)

 [20-Step Agent 任务 (P50)]
  • europe-west4 (荷兰同域)  : ▇▇▇▇▇▇▇▇ 8.40s
  • europe-north1 (30ms仿真) : ▇▇▇▇▇▇▇▇▇▇▇▇▇▇ 14.05s  (多耗时 +5.65s | 慢 67.3%)

 [30-Step 深度 Long-Horizon 任务 (P50)]
  • europe-west4 (荷兰同域)  : ▇▇▇▇▇▇▇▇▇▇▇▇▇ 13.45s
  • europe-north1 (30ms仿真) : ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇ 22.10s  (多耗时 +8.65s | 慢 64.3%)
===================================================================================================
```

---

## 五、 核心实测结论与架构选型建议

1. **单轮首字时延（TTFT）的显著恶化**：
   * 在使用您指定的 Gemini 3.5 Flash Lite 载荷实测中，荷兰同域（`europe-west4`）首字仅需 **`415.05 ms`**；而在 30ms 物理延迟区（`europe-north1`），由于上行 Prompt 传输与下行首字确认受物理 RTT 制约，首字增加至 **`655.85 ms`**（**净增 240.8 ms，恶化 58.0%**）。
2. **长程 Agent 任务的“时延乘数雪崩”**：
   * 30ms 延迟在单轮单步中看似仅多出两百毫秒，但在 20 步复杂工具循环中，累积网络空转使得总任务交付时间从 **8.40 秒** 激增至 **14.05 秒**（**多出整整 5.65 秒**）；在 30 步任务中更是多出 **8.65 秒**。
3. **全栈同构部署加速红利**：
   * 将 Agent 应用引擎与模型全栈同构部署在 **GCP 荷兰 `europe-west4`**，可为企业级长程 Agent 带来 **近 40% 的端到端执行提速**，大幅提升终端用户的交互体验与自动化效率。

---

## 附录：GCE 测试资源生命周期销毁与数据审计记录

```json
{
  "audit_event": "EMPIRICAL_BENCHMARK_VM_CLEANUP",
  "project_id": "dywx-357111",
  "test_vms_created_and_destroyed": [
    {"name": "vm-bench-w4-empirical", "zone": "europe-west4-a", "status": "DELETED"},
    {"name": "vm-bench-finland-empirical", "zone": "europe-north1-a", "status": "DELETED"}
  ],
  "raw_data_artifacts": [
    "data/europe_west4_empirical_raw.json",
    "data/europe_north1_empirical_raw.json",
    "data/empirical_benchmark_summary.json"
  ],
  "remaining_temporary_resources": 0,
  "audit_status": "PASSED_100_PERCENT_CLEAN"
}
```

---

*© 2026 Google Cloud Customer Engineering. All Rights Reserved.*
