# Gemini 3.5 Flash Lite 欧洲现场实测基准测试与网络时延机理报告

> **评测项目 (Project)**：`dywx-357111`  
> **评测大模型**：**Gemini 3.5 Flash Lite** (`gemini-3.5-flash-lite`)  
> **测试端点**：`aiplatform.eu.rep.googleapis.com` (European Regional Representative Endpoint)  
> **在线 Google Slides 演示文稿**：[https://docs.google.com/presentation/d/1kZPUlxv-WqRqlnVFhMALsZInvBBXN3lDBsdCm-YR0ZM/edit](https://docs.google.com/presentation/d/1kZPUlxv-WqRqlnVFhMALsZInvBBXN3lDBsdCm-YR0ZM/edit)  
> **对比区域**：
> * ⭐️ **全欧最低延迟基准组**：GCP 荷兰 **`europe-west4-a`**（实测物理光纤 RTT = **0.45 ms**）
> * 🎯 **~30ms 延迟仿真对照组**：GCP 芬兰 **`europe-north1-a`**（实测物理光纤 RTT = **31.69 ms**）  
> **测试方法与样本量**：每项测试独立执行 $\ge 20$ 轮采样（Suite 1 执行 22 轮，Suite 2 执行 44 轮，Suite 3 执行 60 轮长程任务模拟，共 126 轮全量实测）。  
> **资源销毁审计**：所有测试虚拟机（`vm-bench-w4-empirical` 与 `vm-bench-finland-empirical`）已在测试完成后**自动强制销毁（100% Cleanup Confirmed）**，当前项目 0 临时虚拟机残留。

---

## 目录

- [一、 实测数据出处与测试脚本源码索引](#一-实测数据出处与测试脚本源码索引)
- [二、 核心视觉图表集 (Chart Gallery)](#二-核心视觉图表集-chart-gallery)
- [三、 第一类实测：用户指定 Flash Lite 载荷基准时延对比 (Suite 1 - 22 次采样)](#三-第一类实测用户指定-flash-lite-载荷基准时延对比-suite-1---22-次采样)
- [四、 第二类实测：标准 QA 上下文微观 Waterfall 各阶段时延对比 (Suite 2 - 44 次采样)](#四-第二类实测标准-qa-上下文微观-waterfall-各阶段时延对比-suite-2---44-次采样)
- [五、 第三类实测：Long-Horizon Agent 长程任务多步端到端交付对比 (Suite 3 - 60 次采样)](#五-第三类实测long-horizon-agent-长程任务多步端到端交付对比-suite-3---60-次采样)
- [六、 深度技术机理拆解：为什么不是 +30ms？](#六-深度技术机理拆解为什么不是-30ms)
- [七、 客户解法与推荐全栈同域部署架构](#七-客户解法与推荐全栈同域部署架构)
- [附录：GCE 测试资源生命周期销毁与数据审计记录](#附录gce-测试资源生命周期销毁与数据审计记录)

---

## 一、 实测数据出处与测试脚本源码索引

为保证本报告 100% 的真实性与可复现性，本测试的所有原始数据和执行脚本均已归档于本 GitHub 仓库中，具体位置与出处如下：

### 1. 实测数据原始文件出处
* 📄 **荷兰原生原始数据集**：[`data/europe_west4_empirical_raw.json`](./data/europe_west4_empirical_raw.json)  
  *包含 `europe-west4` 虚拟机内部执行的全部 126 轮测试的微秒级打点数据（包含 DNS 解析、TCP 建连、TLS 握手、Payload 上传、首字 TTFT、整句 TTLT、流式 ITL、Agent 多步耗时）。*
* 📄 **芬兰原生原始数据集**：[`data/europe_north1_empirical_raw.json`](./data/europe_north1_empirical_raw.json)  
  *包含 `europe-north1` 虚拟机内部执行的全部 126 轮测试的微秒级打点数据。*
* 📄 **统计分析汇总文件**：[`data/empirical_benchmark_summary.json`](./data/empirical_benchmark_summary.json)  
  *包含两地实测数据的 Min / Mean / P50 / P90 / P95 / Max / StdDev 完整统计计算结果。*

### 2. 测试脚本在 GitHub 仓库中的位置
* 🛠️ **GCE 虚拟机内执行的压测套件**：[`scripts/live_benchmark_runner.py`](./scripts/live_benchmark_runner.py)  
  *运行在虚拟机内部的 Python 压测套件，通过底层 Socket 与 HTTP 协议栈高精度测量 DNS、TCP、TLS 1.3 协商、首字流式分段与长程 ReAct Agent 工具循环。*
* 🛠️ **本地调度与 Guest Attributes 遥测归档脚本**：[`scripts/run_definitive_empirical_benchmark.py`](./scripts/run_definitive_empirical_benchmark.py)  
  *本地编排脚本，负责自动化创建两地 GCE 虚拟机、通过 GCP Guest Attributes 流水线回传 100% 原始 JSON 遥测、销毁所有 VM 并输出统计摘要。*
* 🛠️ **欧洲全域物理光纤 RTT 探测脚本**：[`scripts/run_europe_rtt_benchmark.py`](./scripts/run_europe_rtt_benchmark.py)  
  *探测 GCP 欧洲 6 大 Region 到荷兰 Gemini 核心算力集群物理 VPC RTT 的基准脚本。*

---

## 二、 核心视觉图表集 (Chart Gallery)

### 1. 单轮 QA 各阶段微观时延瀑布对比图 (Waterfall Chart)
![单轮 QA 瀑布图](./images/fig_qa_waterfall.png)

### 2. 复杂 Agent 多步任务端到端耗时阶梯对比图 (Scaling Bar Chart)
![Agent 多步耗时对比图](./images/fig_agent_scaling.png)

### 3. 大模型代际演进与“阿姆达尔定律”网络瓶颈反转 (Bottleneck Shift)
![阿姆达尔瓶颈转移图](./images/fig_bottleneck_shift.png)

### 4. 欧洲全域 GCP 节点到欧洲 Gemini 核心集群物理时延分布
![欧洲 RTT 分布图](./images/fig_rtt_ranking.png)

---

## 三、 第一类实测：用户指定 Flash Lite 载荷基准时延对比 (Suite 1 - 22 次采样)

> **数据出处**：[`data/europe_west4_empirical_raw.json`](./data/europe_west4_empirical_raw.json) 与 [`data/europe_north1_empirical_raw.json`](./data/europe_north1_empirical_raw.json) 之 `suite_1_user_flash_lite` 节点。  
> **载荷特征**：双轮对话历史（包含用户问候与助手思维链） + Minimal Thinking + `googleSearch` / `googleMaps` 双工具声明。

| 核心指标 | europe-west4 荷兰 (最低延迟区) | europe-north1 芬兰 (30ms 仿真区) | 实测差距 ($\Delta$) | 相对增幅 |
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

## 四、 第二类实测：标准 QA 上下文微观 Waterfall 各阶段时延对比 (Suite 2 - 44 次采样)

> **数据出处**：[`data/europe_west4_empirical_raw.json`](./data/europe_west4_empirical_raw.json) 与 [`data/europe_north1_empirical_raw.json`](./data/europe_north1_empirical_raw.json) 之 `suite_2_qa_waterfall` 节点。  
> **载荷特征**：1,000 Tokens 标准 Prompt 上下文输入（约 5KB 高熵文本），模型输出 400 Tokens；分别测试 **22 次 Cold Connect（新建连接）** 与 **22 次 Warm Pool（连接池复用）**。

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

## 五、 第三类实测：Long-Horizon Agent 长程任务多步端到端交付对比 (Suite 3 - 60 次采样)

> **数据出处**：[`data/europe_west4_empirical_raw.json`](./data/europe_west4_empirical_raw.json) 与 [`data/europe_north1_empirical_raw.json`](./data/europe_north1_empirical_raw.json) 之 `suite_3_agent_simulation` 节点。  
> **载荷特征**：长程 ReAct Agent 工具循环调用，Context 随执行步数动态膨胀（2KB $\to$ 25KB $\to$ 75KB $\to$ 180KB）。每档阶梯各执行 20 轮全流程调用。

| Agent 任务复杂度阶梯 | europe-west4 荷兰 (最低延迟区) | europe-north1 芬兰 (30ms 仿真区) | 实测节省时间 ($\Delta$) | 端到端加速收益 (Speedup) |
| :--- | :---: | :---: | :---: | :---: |
| **10-Step Agent 任务 (P50)** | **4.17 秒** | **6.91 秒** | **节省 2.74 秒** | 🚀 **同域部署提速 39.6%** |
| **10-Step Agent 任务 (Avg)** | **4.21 秒** | **6.98 秒** | **节省 2.77 秒** | 🚀 **平均提速 39.7%** |
| **20-Step Agent 任务 (P50)** | **8.40 秒** | **14.05 秒** | **节省 5.65 秒** | 🚀 **同域部署提速 40.2%** |
| **20-Step Agent 任务 (Avg)** | **8.50 秒** | **14.22 秒** | **节省 5.72 秒** | 🚀 **平均提速 40.2%** |
| **30-Step 深度 Agent (P50)** | **13.45 秒** | **22.10 秒** | **节省 8.65 秒** | 🚀 **同域部署提速 39.1%** |
| **30-Step 深度 Agent (Avg)** | **13.57 秒** | **22.03 秒** | **节省 8.46 秒** | 🚀 **平均提速 38.4%** |

---

## 六、 深度技术机理拆解：为什么不是 +30ms？

很多团队在进行云架构规划时，直觉上认为 30ms 物理光纤延迟微不足道。但实测证明，网络开销在大模型与 Agent 系统中被放大了数十倍：

### 1. 微观层面：大 Context 与 TCP 慢启动（Slow Start）陷阱
随着 Agent 历史记忆与工具返回结果的不断膨胀，单次发送的 Payload 经常达到 150KB 以上。
* TCP 初始拥塞窗口（`initcwnd`）通常为 10 MSS（约 14.6KB）。
* 传输 150KB 数据必须经历 **4 轮连续的往返确认（RTT）** 才能将 CWND 爬升至足够大小。
* 在 **荷兰同域（RTT = 0.45ms）** 下，4 轮往返仅需 **1.8 毫秒**；
* 在 **芬兰跨区（RTT = 31.7ms）** 下，4 轮往返纯光纤耗时就达到 **126.8 毫秒**！加上 TLS 与首字下行确认，单步开销直逼 200ms。

### 2. 宏观层面：极速大模型反转了“阿姆达尔定律”
* **老一代模型（Pro / 深度思考）**：单步推理耗时 2,000ms+，网络 30ms 仅占 1.5%，算力是绝对瓶颈；
* **新一代模型（Gemini 3.5 Flash Lite）**：单步模型推理仅需 ~250ms，网络传输开销占比暴增至 **45% 以上**！
* 此时，**网络延迟已经取代算力成为限制 Agent 端到端交付速度的第一大瓶颈**。

---

## 七、 客户解法与推荐全栈同域部署架构

为彻底释放 Gemini 3.5 Flash Lite 的算力优势，我们推荐如下生产级最佳实践：

```
+-----------------------------------------------------------------------------------+
|                        GCP 欧洲核心数据中心 (europe-west4 荷兰)                    |
|                                                                                   |
|   +----------------------------+             +--------------------------------+   |
|   |   Agent 业务引擎 / 网关    |             |   Vertex AI Gemini Endpoint    |   |
|   |  (GKE / Cloud Run / GCE)   |             | (aiplatform.eu.rep.googleapis) |   |
|   +----------------------------+             +--------------------------------+   |
|                 |                                             ^                   |
|                 +======== Andromeda VPC 高速直连 =============+                   |
|                       (物理 RTT < 0.5 ms | HTTP/2 长连接池)                       |
+-----------------------------------------------------------------------------------+
```

### 落地改造路线：
1. **计算就近迁移**：将核心 Agent 编排引擎、API 网关迁移至 **GCP 荷兰 `europe-west4`**。
2. **连接池复用**：开启 HTTP/2 / gRPC Keep-Alive 连接池，彻底消除单次请求的 TCP / TLS 冷握手。
3. **上下文智能缓存**：开启 Vertex AI Context Caching，避免每步重复上传几十 KB 的静态 System Prompt 与工具声明。

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
