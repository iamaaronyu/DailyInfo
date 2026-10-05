# Agent Rollout & Evaluation Platform
## 完整需求规格与 Vibecoding 开发计划

**版本：V1.0**  
**日期：2026-10-05**  
**目标：作为项目唯一主规格文档，直接驱动 Vibecoding 开发**

---

# 0. 最终结论

本项目不再自研推理服务、不 Fork Harbor Runtime、不自研 Sandbox 内核。

最终技术路线：

```text
推理服务              已有，直接复用
Harbor Runtime         开源复用
Agent Harness          Claude Code / Codex / OpenHands 等复用
Sandbox Runtime        E2B Self-host 优先，开源复用
Harbor Worker          自研薄层
Harbor Hub             核心自研
Scheduler              自研
Rollout Data Platform  核心自研
IAM                    优先复用企业 IAM
Secret                 自研集成
Analytics              自研
```

平台正式定位：

> **Agent Rollout & Evaluation Platform**

而不是：

> Harbor Hub Clone

核心目标：

> 用 Harbor + 开源 Sandbox 作为执行 Runtime，自研企业内部 Agent Rollout 控制面与数据平台。

---

# 1. 项目目标

平台需要完整支持：

```text
Task / Dataset
      ↓
创建 Job
      ↓
展开 Trial
      ↓
Scheduler
      ↓
Harbor Worker
      ↓
Harbor Runtime
      ↓
E2B Sandbox
      ↓
Agent Harness
      ↓
内部推理服务
      ↓
Trajectory / Artifact
      ↓
Verifier
      ↓
Reward
      ↓
Harbor Hub
      ↓
分析 / 数据生产 / RL
```

第一阶段的成功标准不是“Harbor 能跑”。

Harbor 本身已经能跑。

真正的成功标准是：

> 用户无需 SSH、无需手工执行 Harbor、无需查找本地 JSON 文件，仅通过 Portal 即可创建规模化 Agent Experiment，并查看每个 Trial 的完整执行轨迹、产物、评分和异常。

---

# 2. 架构边界

## 2.1 不做

以下能力明确不重复建设：

```text
LLM Serving Engine
vLLM / SGLang Core
Prefill / Decode
KV Cache
Model Scheduling Core

Claude Code
Codex
OpenHands

Harbor Trial Runtime
Harbor Verifier Core
Harbor RewardKit Core

Firecracker 管理平台
Sandbox VM Runtime
```

---

## 2.2 直接复用

### 推理服务

已有：

```text
Internal Inference API
OpenAI-Compatible API
Model Deployment
Model Serving
```

当前项目只做：

```text
Model Registry
→ serving_name / endpoint 映射
```

---

### Harbor Runtime

复用：

```text
Task Runtime
Dataset Runtime
Trial Runtime
Agent Adapter
Environment API
Trajectory
Artifact
Verifier
RewardKit
```

原则：

> **尽量不 Fork Harbor Core。**

如需扩展，优先：

```text
Adapter
Wrapper
Plugin
Output Parser
```

---

### Sandbox Runtime

第一阶段：

> **Self-hosted E2B**

使用：

```text
Sandbox Lifecycle
Exec
File
Template
Firecracker microVM
Pause / Resume
Snapshot
Fork
Network Isolation
```

但内部必须定义自己的：

```text
SandboxProvider
```

避免 Hub / Worker 强绑定 E2B。

---

# 3. 最终总体架构

```text
┌─────────────────────────────────────────────────────────────┐
│                      Portal / Web                           │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    Harbor Hub【自研】                        │
│                                                             │
│ Registry          Experiment         Analytics              │
│ ─────────         ──────────         ─────────              │
│ Task              Job                Metrics                 │
│ Dataset           Trial              Comparison              │
│ Agent             Config             Failure Mining          │
│ Model             History            Leaderboard             │
│                                                             │
│ IAM / Secret      Scheduler          Rollout Data            │
└────────────────────────────┬────────────────────────────────┘
                             │
                        Trial Queue
                             │
                 ┌───────────▼───────────┐
                 │ Harbor Worker【自研】  │
                 └───────────┬───────────┘
                             │
                 ┌───────────▼───────────┐
                 │ Harbor Runtime【复用】 │
                 └───────────┬───────────┘
                             │
                   Environment Provider
                             │
                 ┌───────────▼───────────┐
                 │ E2B Runtime【复用】    │
                 │ Firecracker microVM    │
                 └───────────┬───────────┘
                             │
                             ▼
                 Claude Code / Codex / ...
                             │
                             ▼
                   Internal Inference API
                          【已有】
                             │
                             ▼
                  Trajectory / Artifact
                             │
                             ▼
                         Verifier
                             │
                             ▼
                          Reward
                             │
                             └──────────────→ Harbor Hub
```

---

# 4. 核心对象模型

```text
资产对象
Package / Task / Dataset / Agent / Model

实验对象
Job / Trial / Execution

结果对象
Trajectory / Artifact / Log / Reward / Metrics
```

核心关系：

```text
Task
 +
Agent
 +
Model
 +
Environment
      ↓
    Trial
      ↓
Trajectory + Artifact + Log
      ↓
   Verifier
      ↓
    Reward
```

---

# 5. 核心对象定义

## 5.1 Task

定义：

> 一道可执行 Agent 任务。

至少包含：

```text
instruction
task.toml
environment
tests
solution/reference（可选）
metadata
```

要求：

- 支持 Harbor Task 导入；
- Revision 创建后不可修改；
- 内容变化生成新 Revision；
- 生成 Content Digest；
- Job 必须绑定具体 Revision/Digest。

---

## 5.2 Dataset

定义：

> 一组固定版本 Task 的集合。

必须保存：

```text
dataset_id
name
revision
description
task_refs[]
tags
visibility
```

`task_refs` 必须引用：

```text
Task Revision / Digest
```

禁止 Job 运行时仅引用：

```text
task@latest
```

---

## 5.3 Agent

定义：

> Agent Harness 的平台化注册信息。

典型：

```text
Claude Code
Codex
OpenHands
Custom Agent
```

AgentDefinition：

```text
agent_id
name
version
adapter
image
default_config
capabilities
enabled
```

Capabilities 示例：

```text
trajectory
resume
handoff
browser
subagent
multimodal
windows
```

---

## 5.4 Model

定义：

> Hub 中用于 Experiment 配置的逻辑模型对象。

ModelDefinition：

```text
model_id
display_name
serving_name
endpoint
context_length
max_output_tokens
capabilities
tokenizer
enabled
```

注意：

> Model Registry 不负责 Serving。

---

## 5.5 Job

定义：

> 一次批量实验计划。

JobConfig：

```text
name
dataset_revision
agents[]
models[]
attempts
retries
concurrency
timeout
priority
secret_refs[]
tags[]
```

---

## 5.6 Trial

定义：

```text
Trial
=
Task
× Agent
× Model
× Attempt
```

Trial 是平台最重要的原子对象。

---

## 5.7 Execution

必须新增 Execution 概念。

原因：

```text
Attempt
≠
Retry
```

一个 Logical Trial / Attempt 可以因为基础设施失败对应多个 Execution。

```text
Trial / Attempt
   ├─ Execution #1  sandbox lost
   ├─ Execution #2  model 429
   └─ Execution #3  success
```

Benchmark 统计只计算：

```text
Logical Trial
```

而不是 Retry 次数。

---

# 6. 完整功能需求

# 6.1 Registry

## Task Registry

### P0

- REG-T01 创建 Task
- REG-T02 导入 Harbor Task
- REG-T03 查看 Task
- REG-T04 创建 Revision
- REG-T05 Content Digest
- REG-T06 查看 Revision History
- REG-T07 Metadata
- REG-T08 Tags
- REG-T09 Task 启用/禁用

### P1

- REG-T10 搜索
- REG-T11 Clone
- REG-T12 Archive
- REG-T13 ACL
- REG-T14 批量导入

### 验收

```text
上传一个 Harbor Task
→ 自动生成 Revision + Digest
→ 创建新 Job
→ Trial 使用固定 Digest
→ 修改 Task 内容
→ 必须生成新 Revision
→ 历史 Job 不受影响
```

---

# 6.2 Dataset Registry

### P0

- REG-D01 创建 Dataset
- REG-D02 添加 TaskRef
- REG-D03 创建 Revision
- REG-D04 Dataset Digest
- REG-D05 查看 Task List
- REG-D06 Dataset 启用/禁用

### P1

- REG-D07 按 Tag 过滤
- REG-D08 Random Sample
- REG-D09 Limit
- REG-D10 Clone
- REG-D11 ACL
- REG-D12 从已有 Job 生成 Dataset

### 验收

```text
Dataset V1
├─ Task A@digest1
├─ Task B@digest2
└─ Task C@digest3

Task A 发布新版本后
Dataset V1 仍然绑定 digest1
```

---

# 6.3 Agent Registry

### P0

- REG-A01 注册 Agent
- REG-A02 Agent Version
- REG-A03 Harbor Adapter
- REG-A04 Default Config
- REG-A05 Enable/Disable

### P1

- REG-A06 Capabilities
- REG-A07 Agent Image
- REG-A08 Config Template
- REG-A09 Secret Requirements
- REG-A10 Supported Model Types

---

# 6.4 Model Registry

### P0

- REG-M01 注册 Model
- REG-M02 Serving Name 映射
- REG-M03 Endpoint
- REG-M04 Context Length
- REG-M05 Max Output Token
- REG-M06 Enable/Disable

### P1

- REG-M07 Capabilities
- REG-M08 Tokenizer
- REG-M09 Rate Limit
- REG-M10 Cost Metadata
- REG-M11 Deployment Metadata

---

# 7. Job 管理

## 7.1 Create Job

### P0

用户可以：

```text
选择 Dataset
选择 Agent
选择 Model
设置 Attempts
设置 Concurrency
设置 Timeout
点击 Run
```

API：

```text
POST /api/v1/jobs
```

---

## 7.2 Job Expansion

例如：

```text
Dataset     500 tasks
Agents      2
Models      3
Attempts    4

Logical Trials
= 500 × 2 × 3 × 4
= 12,000
```

### P0

支持：

- Task × Agent × Model × Attempt 展开；
- 小规模 Job 直接 materialize。

### P1

实现：

```text
Lazy Expansion
Paged Materialization
```

避免百万级 Job 一次生成全部 Trial。

---

## 7.3 Job Config Snapshot

Job 启动后必须固定：

```text
Dataset Revision
Task Digests
Agent Versions
Agent Config
Model Versions
Model Params
Harbor Version
Sandbox Provider
Timeout
Attempts
Retries
Verifier Config
```

启动后不可直接修改。

---

## 7.4 Job 状态机

```text
DRAFT
 ↓
QUEUED
 ↓
PLANNING
 ↓
RUNNING
 │
 ├─ COMPLETED
 ├─ PARTIAL_SUCCESS
 ├─ FAILED
 └─ CANCELLED
```

P1 增加：

```text
PAUSING
PAUSED
RESUMING
```

---

## 7.5 Job 操作

### P0

- Create
- Query
- List
- View Progress

### P1

- Cancel
- Pause
- Resume
- Clone
- Rerun
- Retry Failed
- Archive

---

# 8. Trial 管理

## 8.1 Trial 状态机

```text
PENDING
 ↓
QUEUED
 ↓
LEASED
 ↓
PROVISIONING
 ↓
ENV_SETUP
 ↓
AGENT_SETUP
 ↓
AGENT_RUNNING
 ↓
VERIFYING
 ↓
COLLECTING
 ↓
COMPLETED
```

异常终态：

```text
INFRA_FAILED
AGENT_FAILED
VERIFY_FAILED
TIMEOUT
CANCELLED
```

---

## 8.2 Trial 数据

P0 必须记录：

```text
trial_id
job_id
task_ref
agent_ref
model_ref
attempt_index

status

created_at
started_at
finished_at

reward

token_usage
timing

current_execution_id
error_type
error_message
```

---

## 8.3 Trial 操作

### P0

- Query
- List
- View Detail

### P1

- Cancel
- Retry
- Download Result

### P2

- Replay
- Fork
- Resume Agent Session

---

# 9. Execution / Retry

## 9.1 Execution 数据模型

```text
execution_id
trial_id
retry_index
worker_id
sandbox_id

status

started_at
finished_at

error_type
error_message

harbor_version
sandbox_provider
```

---

## 9.2 Failure Taxonomy

至少：

```text
SANDBOX_CREATE_FAILED
SANDBOX_LOST

WORKER_LOST

MODEL_RATE_LIMIT
MODEL_TIMEOUT
MODEL_AUTH_ERROR

NETWORK_ERROR
IMAGE_PULL_ERROR

AGENT_CRASH
AGENT_TIMEOUT

VERIFIER_ERROR

TASK_FAILED
REWARD_ZERO

USER_CANCELLED
```

---

## 9.3 Retry Policy

### 自动 Retry

```text
SANDBOX_CREATE_FAILED
SANDBOX_LOST
WORKER_LOST
NETWORK_ERROR
MODEL_RATE_LIMIT
```

### 可配置 Retry

```text
MODEL_TIMEOUT
IMAGE_PULL_ERROR
AGENT_CRASH
VERIFIER_ERROR
```

### 不 Retry

```text
REWARD_ZERO
TASK_FAILED
USER_CANCELLED
```

核心规则：

> **Agent 做错题不是基础设施失败。**

---

# 10. Scheduler

# 10.1 P0 Scheduler

只实现：

```text
Pending Queue
+
FIFO
+
Job Concurrency
+
Worker Capacity
```

流程：

```text
Pending Trial
     ↓
FIFO
     ↓
检查 Job Concurrency
     ↓
检查 Available Worker Slot
     ↓
Lease Trial
```

---

## 10.2 P1 Scheduler

增加：

```text
Priority
Org Concurrency
Agent Concurrency
Model Concurrency
Quota
Retry Backoff
429 Awareness
```

---

## 10.3 P2 Scheduler

增加：

```text
Fair Share
Dynamic Concurrency
Cost-aware Scheduling
Sandbox Locality
Task/Image Cache Affinity
```

---

# 11. Harbor Worker

Worker 必须保持薄。

职责：

```text
Register
Heartbeat
Lease Trial

Resolve Config

Prepare Harbor TrialConfig

Invoke Harbor

Track Status

Upload:
Trajectory
Artifact
Log
Reward
Metrics

Cleanup
```

---

## 11.1 Worker Register

```json
{
  "worker_id": "worker-001",
  "version": "0.1.0",
  "harbor_version": "0.23.x",
  "capacity": 32,
  "sandbox_provider": "e2b",
  "capabilities": []
}
```

---

## 11.2 Worker Heartbeat

建议：

```text
20s
```

记录：

```text
running_trials
available_slots
cpu
memory
health
version
```

---

## 11.3 Trial Lease

建议：

```text
lease_ttl = 60s
heartbeat = 20s
```

Worker 失联：

```text
Lease Expire
→ Execution 标记 WORKER_LOST
→ Trial 根据 RetryPolicy 重新 QUEUED
```

---

# 12. Harbor Runtime Integration

## 12.1 原则

```text
No Harbor Core Fork
```

优先：

```text
Wrapper
Adapter
Config Builder
Output Parser
```

---

## 12.2 P0 集成能力

- HBR-01 固定 Harbor Version；
- HBR-02 TrialConfig Builder；
- HBR-03 Agent Config Mapper；
- HBR-04 Internal Model Endpoint Mapper；
- HBR-05 E2B Environment；
- HBR-06 Harbor Output Parser；
- HBR-07 Harbor Log Collector；
- HBR-08 Harbor Version 写入 Execution。

---

# 13. Sandbox Provider

内部定义接口：

```python
class SandboxProvider:
    create(...)
    get(...)
    destroy(...)

    exec(...)
    upload(...)
    download(...)

    get_status(...)

    pause(...)
    resume(...)
    snapshot(...)
    fork(...)
```

P0 Provider：

```text
E2BProvider
```

未来：

```text
K8sAgentSandboxProvider
```

---

# 14. E2B 集成需求

## P0

- Self-host 部署；
- Sandbox Create；
- Destroy；
- Exec；
- Upload；
- Download；
- Status；
- Timeout；
- Template/Image；
- Harbor 原生 E2B 路径验证。

## P1

- Network Policy；
- Private Registry；
- Resource Limit；
- Metrics；
- Warm Pool；
- 企业网络接入。

## P2

- Pause；
- Resume；
- Snapshot；
- Fork；
- Rollback 产品化。

---

# 15. Rollout Data Platform

这是整个平台长期价值最大的部分。

每个 Trial 最终沉淀：

```text
Config
Trajectory
Artifact
Logs
Reward
Exception
Token Usage
Timing
```

---

# 16. Trajectory

## 16.1 P0 数据

必须兼容 Harbor 输出。

至少保存：

```text
message
role
reasoning
tool_call
tool_arguments
tool_result
timestamp
token_usage
```

---

## 16.2 P0 Viewer

Trial 页面展示：

```text
User
 ↓
Assistant
 ↓
Tool Call
 ↓
Tool Result
 ↓
Assistant
 ...
```

需要：

- 折叠/展开；
- 时间展示；
- Tool 高亮；
- Error 高亮；
- Token 展示；
- Lazy Loading。

---

## 16.3 P1

支持：

```text
Search
Filter by Tool
Filter by Error
Filter by Role
Sub-agent
Multimodal
```

---

## 16.4 P2

支持：

```text
Trajectory Dataset
Trajectory Query
Trajectory Replay
Trajectory Compare
```

---

# 17. Artifact

## P0

- Artifact Manifest；
- Object Storage；
- Directory Tree；
- Download；
- File Size；
- Content Type。

## P1

- Preview；
- Checksum；
- ACL；
- Signed URL；
- Diff。

典型：

```text
patch.diff
output.json
generated code
screenshots
reports
agent session
```

---

# 18. Logs

分类：

```text
Harbor Log
Worker Log
Sandbox Log
Agent Log
Verifier Log
Infrastructure Log
```

## P0

- 保存；
- 分类查看；
- Secret Masking。

## P1

- Streaming；
- Search；
- Download；
- Structured Log。

---

# 19. Reward

支持：

```text
Scalar Reward
Multi-dimensional Reward
```

例如：

```json
{
  "reward": 0.91,
  "correctness": 1.0,
  "quality": 0.85,
  "efficiency": 0.72
}
```

## P0

- 保存原始 Reward；
- 展示；
- Job 聚合；
- Metrics Schema。

## P1

- Filter；
- Reward Distribution。

## P2

- Reward Pipeline；
- Reward Recompute；
- Process Reward。

---

# 20. Timing

P0 每 Trial 必须统计：

```text
queue_wait
sandbox_create
environment_setup
agent_setup
agent_execution
verifier
artifact_upload
total
```

---

# 21. Token / Usage

P0：

```text
input_tokens
output_tokens
cached_tokens
requests
tool_calls
```

如果内部推理平台可提供，P1 接入：

```text
TTFT
TBT
KV Cache Hit
Serving Instance
Inference Queue Time
```

---

# 22. Storage Architecture

推荐：

```text
PostgreSQL
+
Object Storage
+
Redis
```

---

## PostgreSQL

保存：

```text
User
Organization
Project

Task Metadata
Dataset Metadata
Agent
Model

Job
Trial
Execution

Reward
Metrics
ACL
Audit
```

---

## Object Storage

保存：

```text
Task Archive
Trajectory
Artifact
Logs
Screenshots
Agent Session
Job Export
```

原则：

> 大对象禁止全部塞 PostgreSQL。

---

## Redis

P0：

```text
Trial Queue
Worker Heartbeat
Trial Lease
Temporary State
```

P1：

```text
Rate Limit
Backoff
Distributed Lock
```

---

# 23. IAM

优先对接企业 IAM。

内部对象：

```text
User
Organization
Project
Role
ServiceAccount
APIKey
```

角色：

```text
PlatformAdmin
OrgOwner
Developer
Viewer
```

---

# 24. Secret Manager

Secret 类型：

```text
Agent Secret
Tool Secret
Git Credential
Registry Credential
External API Credential
```

规则：

```text
Job 只保存 secret_id

Secret Value 加密存储

Worker 按 Trial 身份获取

Sandbox 运行时注入

Trial 结束后销毁

日志自动脱敏
```

---

# 25. Security

必须满足：

```text
TLS
RBAC
Secret Encryption
Audit
Network Policy
Artifact ACL
Signed URL
API Token Rotation
```

隔离要求：

```text
Trial A
不能访问 Trial B

Agent Sandbox
不能访问 Verifier Secret

Registry Credential
不能直接暴露给 Agent
```

---

# 26. Portal 信息架构

```text
Home

Registry
├─ Tasks
├─ Datasets
├─ Agents
└─ Models

Experiments
├─ Jobs
└─ Trials

Data
├─ Trajectories
├─ Artifacts
└─ Failure Mining

Administration
├─ Organizations
├─ Projects
├─ Members
├─ Secrets
├─ Workers
└─ Quotas
```

---

# 27. Trial Detail 页面

这是 P0 第一优先 UI。

Tab：

```text
Overview
Trajectory
Artifacts
Reward
Logs
Config
Runtime
Exception
```

目标：

> 不登录 Worker，就能判断 Trial 为什么成功/失败。

---

# 28. Job Detail 页面

Tab：

```text
Overview
Trials
Metrics
Config
Logs
```

Overview：

```text
Total
Pending
Running
Completed
Failed
Retries

Mean Reward
Success Rate
Duration
Tokens
```

---

# 29. Analytics

## P0

```text
Mean Reward
Success Rate
Duration
Tokens
Errors
Trial Status Distribution
```

## P1

```text
pass@1
pass@k

Agent A vs Agent B
Model A vs Model B
Job A vs Job B

Failure Type
Tool Calls
```

## P2

```text
Failure Mining
Pareto
Reward / Token
Reward / Time
Reward / Cost
Trajectory Analytics
```

---

# 30. Observability

平台 Metrics：

```text
pending_trials
running_trials

trial_throughput
trial_success_rate
infra_failure_rate

worker_count
worker_utilization

sandbox_create_latency
sandbox_failure_rate

agent_execution_duration

model_429
model_timeout

trajectory_upload_bytes
artifact_upload_bytes
```

---

# 31. Reliability

## P0

```text
API Idempotency
Trial State Machine
Immutable Config Snapshot
Result Upload Idempotency
```

## P1

```text
Worker Lost Recovery
Lease Timeout
Retry
Backoff
Queue Recovery
Object Upload Retry
Scheduler Recovery
```

---

# 32. API 设计

基础前缀：

```text
/api/v1
```

---

## Registry

```text
POST   /tasks
GET    /tasks
GET    /tasks/{id}

POST   /datasets
GET    /datasets
GET    /datasets/{id}

POST   /agents
GET    /agents

POST   /models
GET    /models
```

---

## Job

```text
POST /jobs
GET  /jobs
GET  /jobs/{id}

POST /jobs/{id}/cancel
POST /jobs/{id}/pause
POST /jobs/{id}/resume
POST /jobs/{id}/clone
```

---

## Trial

```text
GET  /trials
GET  /trials/{id}

POST /trials/{id}/cancel
POST /trials/{id}/retry
```

---

## Worker

```text
POST /workers/register
POST /workers/{id}/heartbeat

POST /trials/lease
POST /trials/{id}/heartbeat
POST /trials/{id}/status
POST /trials/{id}/result
```

---

## Data

```text
GET /trials/{id}/trajectory
GET /trials/{id}/artifacts
GET /trials/{id}/logs
GET /trials/{id}/reward
```

---

# 33. 推荐技术栈

## Backend

```text
Python
FastAPI
Pydantic
SQLAlchemy
Alembic
```

## Database

```text
PostgreSQL
```

## Queue / Lease

```text
Redis
```

## Object Storage

开发环境：

```text
MinIO
```

生产：

```text
S3 / OBS Compatible Storage
```

## Frontend

```text
Next.js
TypeScript
```

## Observability

```text
Prometheus
Grafana
OpenTelemetry
```

## Local Development

```text
Docker Compose
```

P0 不要先引入复杂 K8s Control Plane。

---

# 34. Monorepo

```text
agent-rollout-platform/
│
├── apps/
│   ├── hub-api/
│   └── hub-web/
│
├── services/
│   ├── worker/
│   └── scheduler/
│
├── packages/
│   ├── schemas/
│   ├── harbor-adapter/
│   ├── sandbox-provider/
│   │   ├── base/
│   │   └── e2b/
│   ├── hub-sdk/
│   └── common/
│
├── infra/
│   ├── e2b/
│   ├── postgres/
│   ├── redis/
│   ├── minio/
│   └── docker-compose/
│
├── examples/
│   ├── hello-task/
│   └── coding-task/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── docs/
│   ├── architecture.md
│   ├── data-model.md
│   ├── api.md
│   └── development.md
│
└── CLAUDE.md
```

---

# 35. Vibecoding 基本原则

开发不能按照：

```text
“实现 Harbor Hub”
```

这种超大 Prompt 推进。

必须按照：

```text
Vertical Slice
```

推进。

固定循环：

```text
SPEC
 ↓
Schema
 ↓
API
 ↓
Minimal Implementation
 ↓
Integration Test
 ↓
Real Harbor Run
 ↓
UI
```

---

# 36. Coding Agent 强制规则

仓库根目录必须维护：

```text
CLAUDE.md
```

至少加入：

```text
1. 不允许虚构 Harbor API。
2. 修改 Harbor 集成前必须读取当前实际 Harbor 源码。
3. 不 Fork Harbor Core，除非明确批准。
4. E2B 只能通过 SandboxProvider 接入业务层。
5. Domain Schema 只能定义在 packages/schemas。
6. Job/Trial 状态修改必须经过状态机。
7. 所有执行接口必须幂等。
8. Attempt 与 Retry 不得混淆。
9. Secret 不得出现在日志和 Trial Config 明文。
10. Trajectory/Artifact 大对象不得直接存 PostgreSQL。
11. 每个 Feature 必须包含测试。
12. 每个 Sprint 必须通过真实 Harbor E2E。
13. 禁止为了通过测试 Mock 掉整个 Harbor/E2B 主链。
14. 禁止 UI 先于 Domain/API 自己发明状态字段。
15. 修改公共 Schema 必须检查所有消费者。
```

---

# 37. 开发阶段

# Phase 0：Harbor + E2B 技术 Spike

目标：

```text
真实 Task
 ↓
Harbor
 ↓
Self-host E2B
 ↓
Claude Code / Custom Agent
 ↓
Internal Inference
 ↓
Verifier
 ↓
Reward
```

必须确认：

```text
Harbor TrialConfig
Agent Config
Model Endpoint
E2B Lifecycle

Trajectory 输出
Artifact 输出
Reward 输出
Log 输出
```

输出：

```text
examples/run_one_trial.py
```

### DoD

执行：

```bash
python examples/run_one_trial.py
```

可以：

```text
创建 Sandbox
运行真实 Agent
调用内部模型
执行工具
完成 Verifier
得到 Reward
生成 Trajectory
生成 Artifact
```

这一阶段不开发 Hub UI。

---

# Phase 1：Single Trial Platform

实现：

```text
POST /trials
 ↓
PostgreSQL
 ↓
Redis Queue
 ↓
Worker
 ↓
Harbor
 ↓
E2B
 ↓
Result
```

需求：

```text
Trial Schema
Trial State Machine
Worker Register
Heartbeat
Trial Lease
Harbor Runner
Result Upload
```

### DoD

```text
curl POST /trials
→ Trial 自动进入队列
→ Worker 自动领取
→ Harbor 执行
→ Reward 写回 DB
→ status=COMPLETED
```

---

# Phase 2：Rollout Data

实现：

```text
Trajectory
Artifact
Log
Reward
Timing
Token Usage
```

同时开发：

> **Trial Detail 页面**

### DoD

选择一个失败 Trial：

```text
打开网页
→ 查看 Trajectory
→ 查看 Error
→ 查看 Agent Log
→ 查看 Artifact
→ 查看 Reward
```

无需登录 Worker 即可判断失败原因。

---

# Phase 3：Dataset + Job

实现：

```text
Task Registry
Dataset Registry
Agent Registry
Model Registry

Job
Job Planner
100 Trials
```

Scheduler 仅：

```text
FIFO + Job Concurrency
```

### DoD

```text
Dataset = 100 tasks
Agent = Claude Code
Model = Internal Model
Concurrency = 20

Run

→ 自动生成 100 Logical Trials
→ 并发执行
→ Job 最终 Completed
→ Trial 数量正确
→ Reward 聚合正确
```

---

# Phase 4：Portal MVP

实现：

```text
Registry
Job List
Create Job
Job Detail
Trial List
Trial Detail
```

形成：

```text
Create Job
→ Run
→ View Results
```

这是：

> **MVP 1.0**

---

# Phase 5：生产可靠性

实现：

```text
Execution
Retry Policy
Worker Lost Recovery
Lease Timeout

Cancel
Pause / Resume Job

Priority
Quota

429 Awareness
Backoff

Secret Manager
Private Registry

Audit
Monitoring
Alerting
```

### Chaos 验收

必须主动测试：

```text
Kill Worker
Kill Hub API
Redis Restart
E2B Create Failure
Sandbox Lost
Model 429
Model Timeout
Verifier Crash
Object Storage Upload Failure
```

要求：

```text
Logical Trial 不重复
状态最终一致
可恢复任务自动恢复
不可恢复任务明确终态
```

---

# Phase 6：高级 Sandbox

接入：

```text
Pause
Resume
Snapshot
Fork
Rollback
```

产品场景：

### Suspend / Resume

```text
Agent Waiting
 ↓
Pause Sandbox
 ↓
Resume
 ↓
Continue Trial
```

### Snapshot / Fork

```text
Common Prefix
     ↓
Snapshot
 ├─ Fork Trial A
 ├─ Fork Trial B
 └─ Fork Trial C
```

---

# Phase 7：Analytics / Agent Data

实现：

```text
Experiment Compare
Failure Mining
Trajectory Search
Trajectory Dataset
Dataset Builder
Reward Filter
```

目标：

```text
Eval Platform
      ↓
Agent Data Platform
```

---

# Phase 8：Agentic RL

实现：

```text
Policy Version
 ↓
Rollout Job
 ↓
N Trials
 ↓
Trajectory + Reward
 ↓
Filter / Sample
 ↓
RL Trainer
 ↓
New Policy
```

Hub 负责：

```text
Rollout
Data
Reward
Version
```

Trainer 负责：

```text
Gradient
Optimizer
Policy Update
```

---

# 38. Sprint 计划

| Sprint | 核心输出 | 验收 |
|---|---|---|
| S0 | Harbor + E2B + Internal Model Spike | 单 Trial 完整运行 |
| S1 | Trial Schema/API + Worker | API 创建 Trial 自动完成 |
| S2 | Trajectory/Artifact/Reward Store | 完整保存结果 |
| S3 | Trial Viewer | 页面定位 Trial 失败原因 |
| S4 | Registry + Dataset | 可创建 100 Task Dataset |
| S5 | Job Planner + FIFO Scheduler | 100 Trial 并发执行 |
| S6 | Portal MVP | 用户全程无需 SSH |
| S7 | Execution/Retry/Lease/Recovery | Worker 故障自动恢复 |
| S8 | IAM/Secret/Quota | 多用户生产可用 |
| S9 | Analytics/Comparison | Agent/Model 横向比较 |
| S10 | Pause/Resume/Snapshot/Fork | Sandbox 高阶能力 |
| S11 | Failure Mining/Trajectory Dataset | Agent 数据生产 |
| S12 | RL Integration | Rollout → Trainer 闭环 |

---

# 39. Sprint 开发顺序要求

必须严格：

```text
Domain
 ↓
Schema
 ↓
Migration
 ↓
Service
 ↓
API
 ↓
Integration Test
 ↓
E2E
 ↓
UI
```

禁止：

```text
先画完整 Portal
再倒推 API
```

---

# 40. 前三个里程碑

## Milestone 1：Single Trial

```text
Task
→ Harbor
→ E2B
→ Agent
→ Internal Model
→ Reward
```

这是技术可行性的分界线。

---

## Milestone 2：Observable Trial

```text
Trial
→ Trajectory
→ Artifact
→ Logs
→ Viewer
```

这是平台可用性的分界线。

---

## Milestone 3：100 Trial Job

```text
Dataset
→ Job
→ Scheduler
→ 20 Concurrent Trials
→ Job Metrics
```

这是 MVP 的分界线。

---

# 41. P0 完整需求范围

P0 只做：

```text
E2B Self-host

Harbor Integration

Harbor Worker

Task Registry
Dataset Registry
Agent Registry
Model Registry

Job
Trial

FIFO Scheduler

Trajectory
Artifact
Reward
Logs
Timing
Token Usage

Trial Viewer
Job Viewer

Basic IAM

Basic Metrics
```

明确不做：

```text
复杂 FairShare
高级 Billing
Leaderboard
Pareto
Failure Mining

Snapshot 产品化
Fork 产品化

RL
复杂 Workflow
```

---

# 42. P1 完整需求范围

```text
Execution 模型

Trial Lease
Worker Recovery

Retry / Backoff

Cancel
Pause / Resume Job

Priority Scheduler

Org / Job / Model Quota

Model 429 Awareness

Secret Manager

Private Registry

Network Policy

Audit

Monitoring
Alerting

Agent / Model / Job Compare
Failure Taxonomy
```

---

# 43. P2 完整需求范围

```text
Pause / Resume Sandbox
Snapshot
Fork
Rollback

Failure Mining
Trajectory Search
Trajectory Dataset

Leaderboard
Pareto

Trial Replay
Trial Fork

Dataset Builder

Reward Pipeline

SFT Export
RL Export
```

---

# 44. P3 完整需求范围

```text
Policy Version

Massive Rollout

Sampling Policy

Reward Pipeline

Training Dataset Version

RL Trainer Integration

RL Experiment Tracking

Rollout / Train Closed Loop
```

---

# 45. API 幂等要求

以下必须幂等：

```text
Create Trial
Lease Trial
Update Trial Status
Upload Reward
Upload Artifact Manifest
Finalize Execution
Finalize Trial
Worker Heartbeat
```

建议所有写操作支持：

```text
Idempotency-Key
```

---

# 46. 数据一致性要求

Trial 进入 `COMPLETED` 前至少满足：

```text
Config Snapshot 已保存

Execution 已终态

Verifier 完成

Reward 已保存

Trajectory 状态明确

Artifact Manifest 已保存
```

Artifact Blob 可以异步上传，但必须有：

```text
artifact_upload_state
```

---

# 47. SLO 建议

P1：

```text
Control Plane Availability ≥ 99.9%

Job Create P99 < 1s

Trial Schedule Delay P95 < 10s
（资源充足）

Worker Lost Detection < 60s

Trial 状态最终一致性 < 30s
```

---

# 48. 最终研发 Workstreams

## WS0 Open Source Integration

```text
Harbor
E2B
Internal Inference
```

## WS1 Worker

```text
Lease
Heartbeat
Harbor Run
Result Upload
```

## WS2 Control Plane

```text
Job
Trial
Execution
Scheduler
```

## WS3 Registry

```text
Task
Dataset
Agent
Model
```

## WS4 Rollout Data

```text
Trajectory
Artifact
Reward
Logs
Metrics
```

## WS5 Portal

```text
Trial Viewer
Job Viewer
Registry UI
Create Job
```

## WS6 Reliability & Governance

```text
Retry
Recovery
IAM
Secret
Quota
Audit
```

## WS7 Analytics & Data

```text
Compare
Failure Mining
Trajectory Dataset
RL Export
```

---

# 49. 推荐并行 Vibecoding 分工

可以使用多个 Coding Agent，但必须共享统一 Schema。

### Agent A：Harbor Integration

```text
Harbor Spike
TrialConfig
Output Parser
```

### Agent B：Worker

```text
Lease
Heartbeat
Runner
Upload
```

### Agent C：Hub Backend

```text
Job
Trial
Execution
Registry
```

### Agent D：Data Platform

```text
Trajectory
Artifact
Reward
Object Storage
```

### Agent E：Frontend

只在 API/Schema 稳定后：

```text
Trial Viewer
Job Viewer
Registry UI
```

### Agent F：Tests

```text
Integration
E2E
Chaos
```

---

# 50. Vibecoding Task 模板

每个任务必须用类似下面的形式。

```text
任务：
实现 Trial Lease。

背景：
Worker 通过 lease 获取待执行 Trial。

范围：
- PostgreSQL 为 Trial source of truth
- Redis 可用于 lease 临时状态
- lease TTL = 60s
- Worker 每20秒续租
- 同一 Trial 同一时间最多一个有效 lease
- Worker 失联后 Execution 标记 WORKER_LOST
- RetryPolicy 决定 Trial 是否重新 QUEUED

必须实现：
1. Schema
2. Migration
3. Service
4. API
5. Unit Test
6. Integration Test

禁止：
- 修改 Job Planner
- 修改 Harbor Adapter
- 在 Controller 中直接写数据库
- Mock 掉 lease 核心逻辑

验收：
同时启动两个 Worker 竞争同一个 Trial，
只能一个 Worker 成功获得 Lease。
Worker 停止 heartbeat 后，
60s 内 Trial 可被重新调度。
```

---

# 51. Definition of Done

每个 Feature 完成必须满足：

```text
代码完成
+
Schema/Migration 完成
+
Unit Test
+
Integration Test
+
真实链路验证
+
错误路径验证
+
文档更新
```

P0 主链 Feature 必须额外满足：

```text
Real Harbor
+
Real E2B
+
Real Internal Inference
```

不能全部 Mock。

---

# 52. 最终主链

项目任何阶段都应该围绕下面这条链工作：

```text
Portal
 ↓
Job
 ↓
Trial
 ↓
Scheduler
 ↓
Worker
 ↓
Harbor
 ↓
E2B
 ↓
Agent
 ↓
Internal Inference
 ↓
Trajectory
 ↓
Verifier
 ↓
Reward
 ↓
Hub
```

判断一个需求是否进入 P0 的最简单标准：

> **它是否直接影响这条链从 Create 到 Analyze 完整跑通？**

如果不是：

> 先后移。

---

# 53. 最终目标

最终平台形成：

```text
            Asset Plane
Task / Dataset / Agent / Model
                 │
                 ▼
          Experiment Plane
            Job / Trial
                 │
                 ▼
           Execution Plane
Worker / Harbor / E2B / Agent
                 │
                 ▼
             Data Plane
Trajectory / Artifact / Reward
                 │
                 ▼
           Analysis Plane
Compare / Failure Mining
                 │
                 ▼
           Training Plane
          SFT / Agentic RL
```

最终一句话：

> **Harbor 负责运行 Rollout，E2B 提供 Sandbox，内部推理平台提供 Model Serving；我们自研的核心是控制 Rollout、管理实验、沉淀 Trajectory/Reward，并最终把这些数据用于 Agent 评测、优化与训练。**
