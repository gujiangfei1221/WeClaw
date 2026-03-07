# 我的微信 AI 助理实践：从 OpenClaw 到 WeClaw

> 一个专注于微信生态的轻量级 AI 助理实现，保留核心能力，去除复杂性

---

## 一、为什么要做这个项目？

### 背景

市面上有很多 AI 助理项目，其中 **OpenClaw** 是一个功能极其完善的开源个人 AI 助理平台。它支持 WhatsApp、Telegram、Slack、Discord、Signal、iMessage 等十几种消息渠道，拥有完整的插件系统、多平台客户端（macOS 菜单栏、iOS/Android App、Web UI）、浏览器控制、语音通话等高级功能。

但对于我这样的**个人用户**来说，OpenClaw 有几个痛点：

1. **太重了**：5 万多行代码，38 个扩展包，部署和维护成本高
2. **功能过剩**：我只用微信，不需要支持十几种消息渠道
3. **学习曲线陡**：复杂的配置系统、插件机制、多 Agent 路由等，上手门槛高
4. **微信支持不足**：OpenClaw 主要面向国际市场，对微信公众号的支持不是核心功能

所以我决定基于 OpenClaw 的核心设计理念，做一个**专注于微信生态的轻量级 AI 助理**——**WeClaw**。

---

## 二、核心设计理念

### 从 OpenClaw 学到的精华

OpenClaw 的架构设计非常优秀，我保留了以下核心概念：

#### 1. **Gateway 作为中心化控制面板**
所有消息路由、会话管理、工具调用都通过一个统一的服务器处理，而不是分散在各个模块。

#### 2. **Session 隔离**
每个用户（通过微信 OpenID 标识）拥有独立的对话历史，互不干扰。

#### 3. **Agent Loop（ReAct 循环）**
AI 可以调用工具（执行命令、读写文件、搜索记忆等），根据工具结果继续思考，形成"推理-行动-观察"的循环。

#### 4. **Skill 系统**
通过 Markdown 文件定义技能，AI 可以动态加载和使用这些技能，无需修改代码。

### 我的简化策略

| OpenClaw | WeClaw | 原因 |
|----------|--------|------|
| 支持 10+ 消息渠道 | 只支持微信公众号 | 专注单一场景 |
| WebSocket + HTTP 双协议 | 只用 HTTP | 微信是 Webhook 推送模式 |
| 38 个扩展包 | 0 个扩展包 | 功能内置，不需要插件系统 |
| macOS/iOS/Android 原生 App | 无客户端 | 直接用微信聊天 |
| 5 万+ 行代码 | ~2000 行代码 | 保留核心，去除冗余 |
| 复杂的配置系统（JSON5 + Schema） | 简单的 .env 文件 | 降低配置门槛 |
| 多 AI 提供商故障转移 | 单一提供商 | 个人使用够用 |
| Docker 沙箱 + 权限系统 | 无沙箱 | 个人服务器，风险可控 |

---

## 三、技术架构

### 整体架构图

```
微信用户
   │
   ▼
微信公众号平台（Webhook 推送）
   │
   ▼
┌─────────────────────────────────┐
│      Express HTTP 服务器         │
│      (src/server.ts)            │
│                                 │
│  ┌───────────────────────────┐  │
│  │  消息解析（XML → JSON）    │  │
│  │  指令拦截（/set /config）  │  │
│  │  会话管理（Session Store） │  │
│  │  Agent Loop（ReAct 循环）  │  │
│  │  工具系统（Bash/File/...） │  │
│  │  技能加载（Skills Loader） │  │
│  │  记忆系统（SQLite 向量）   │  │
│  │  定时任务（Cron Manager）  │  │
│  └───────────────────────────┘  │
│                                 │
│  客服消息 API（主动推送结果）    │
└─────────────────────────────────┘
         │
         ▼
    AI 模型 API
  （硅基流动 / 百炼）
```

### 核心模块说明

| 模块 | 文件 | 职责 |
|------|------|------|
| **服务器入口** | `src/server.ts` | 接收微信 Webhook、消息解析、指令拦截 |
| **Agent 循环** | `src/agent/loop.ts` | AI 模型调用、工具路由、ReAct 循环 |
| **会话管理** | `src/agent/session.ts` | 对话历史存储、过期清理 |
| **工具系统** | `src/tools/` | bash、read_file、write_file、edit_file |
| **技能加载** | `src/skills/loader.ts` | 动态加载 .md 技能文件 |
| **记忆系统** | `src/memory/index.ts` | SQLite + 向量搜索 |
| **定时任务** | `src/cron/manager.ts` | Cron 表达式定时触发 AI |
| **配置存储** | `src/config/store.ts` | AES-256 加密存储 API Key |
| **微信 API** | `src/wechat/` | XML 解析、客服消息推送 |

---

## 四、核心功能实现

### 1. 微信消息处理流程

```
用户发送消息
    │
    ▼
微信服务器推送 XML 到 /wechat
    │
    ▼
解析 XML → { fromUserName, content, msgType, ... }
    │
    ▼
检查是否为指令（/set /config /help）
    │
    ├─ 是 → 直接处理，不进入 AI
    │
    └─ 否 → 进入 Agent Loop
        │
        ▼
    构建 System Prompt（身份 + 工具 + 技能 + 记忆）
        │
        ▼
    加载对话历史（Session）
        │
        ▼
    调用 AI 模型（流式）
        │
        ├─ 文本回复 → 通过客服消息 API 推送
        │
        └─ 工具调用（bash / read_file / ...）
            │
            ▼
        执行工具 → 结果追加到上下文 → 再次调用 AI
        │
        ▼
    循环最多 15 轮，直到 AI 给出最终回复
```

**关键设计点：**
- **5 秒超时问题**：微信要求 Webhook 在 5 秒内返回，否则会重试。我的做法是先返回"收到，正在思考..."，然后后台异步跑 Agent Loop，结果通过客服消息 API 主动推送。
- **防重复处理**：用 `Set<taskKey>` 记录正在处理的消息，避免微信重试导致重复执行。

### 2. 配置管理（密钥安全）

这是我和 OpenClaw 的一个重要区别。OpenClaw 的配置存储在 `~/.openclaw/openclaw.json`，是明文的。

我实现了一个**加密配置存储系统**：

```typescript
// 用户通过微信发送（不进入 AI 上下文）
/set TICKTICK.API_TOKEN=abc123

// 服务器端
setConfig("TICKTICK.API_TOKEN", "abc123")
  → AES-256-GCM 加密
  → 存储到 data/skill-config.enc.json
  → 回复用户"✅ 配置已加密保存"
```

**为什么这样设计？**
- **安全性**：用户的 API Key 不会出现在聊天记录中，也不会被发送给 AI 模型厂商
- **易用性**：用户不需要 SSH 到服务器改配置文件，直接在微信里发指令即可
- **持久化**：主密钥来自 `CONFIG_MASTER_KEY` 环境变量，重启后配置不丢失

### 3. Skill 系统

技能是 Markdown 文件，放在 `config/skills/` 目录下。AI 启动时会自动加载，注入到 System Prompt 中。

**示例：A 股定投技能**

```markdown
# A 股 ETF 定投助手

## 描述
帮助用户进行 A 股 ETF 定投决策，基于 MA20 均线偏离度判断买入时机。

## 使用场景
- 用户问"今天需要定投吗"
- 用户问"159338 现在价格多少"

## 执行方式
使用 bash_execute 工具执行以下命令：
python3 scripts/a-share-investor/dip_invest.py --json

## 输出格式
根据脚本返回的 JSON 数据，用通俗易懂的语言告诉用户：
- 当前价格
- MA20 均线
- 偏离度
- 是否建议定投
```

**技能摘要模式**：如果技能文件超过 2000 字符，只注入摘要到 System Prompt，AI 需要时会主动 `read_file` 读取完整内容。

### 4. 工具系统

AI 可以调用的工具：

| 工具 | 功能 | 示例 |
|------|------|------|
| `bash_execute` | 执行终端命令 | 运行 Python 脚本、curl 请求、数据处理 |
| `read_file` | 读取文件 | 读取技能文档、配置文件 |
| `write_file` | 写入文件 | 保存数据、生成报告 |
| `edit_file` | 编辑文件 | 修改配置、更新代码 |
| `save_memory` | 保存记忆 | 记住用户偏好、重要信息 |
| `search_memory` | 搜索记忆 | 查找历史对话中的信息 |
| `add_cron_job` | 添加定时任务 | 每天 9 点提醒定投 |
| `list_cron_jobs` | 列出定时任务 | 查看所有定时任务 |
| `remove_cron_job` | 删除定时任务 | 取消定时提醒 |
| `edit_file` + `bash_execute` | 备忘录管理 | 记录/检索软件 License、账号信息等 |

**工具调用示例：**

```
用户：今天需要定投吗？

AI 思考：用户在询问定投，我需要调用 a-share-investor 技能

AI 调用工具：
bash_execute("python3 scripts/a-share-investor/dip_invest.py --json")

工具返回：
{"159338": {"name": "沪深300ETF", "price": 3.85, "ma20": 3.92, "deviation": -1.79%, "suggest": "建议定投"}}

AI 回复用户：
今天 159338 沪深300ETF 价格 3.85 元，低于 MA20 均线 1.79%，建议定投 200 元。
```

### 5. 记忆系统

基于 SQLite + 向量搜索，AI 可以记住用户的偏好和重要信息。

```sql
CREATE TABLE memories (
  id INTEGER PRIMARY KEY,
  user_id TEXT NOT NULL,
  category TEXT NOT NULL DEFAULT 'general',
  content TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
```

**使用场景：**
- 用户说"我的定投基础金额是 200 元" → AI 调用 `save_memory` 保存
- 下次用户问"帮我定投" → AI 调用 `search_memory` 查到"定投基础金额 200 元"

### 6. 备忘录系统

#### 设计背景：两类信息的分离

WeClaw 管理两类截然不同的信息：

| 类型 | 工具 | 特点 |
|------|------|------|
| **任务** | 滴答清单技能 | 有截止时间、需要完成、需要提醒 |
| **备忘** | 本地 Markdown 文件 | 结构化信息片段、需要随时检索 |

备忘的典型场景：软件 License Key、账号信息、下载链接、API Token 等——这些信息没有截止时间，但需要随时能查到。

#### 为什么不用向量数据库（RAG）？

这是一个值得深思的技术选型问题。传统 RAG 的流程是：

```
用户问题 → embedding → 向量检索 → top-k 文档片段 → LLM 回答
```

但对于结构化备忘场景，传统 RAG 有几个根本性缺陷：

1. **分块破坏信息完整性**：一条软件备忘包含名称、下载地址、License Key、账号等字段，向量分块会把这些字段切到不同 chunk，导致信息不完整
2. **精确字段不适合语义检索**：License Key、URL 这类精确信息，embedding 相似度检索反而不如关键字匹配准确
3. **复杂度与收益不匹配**：向量数据库需要额外服务、embedding 调用、索引维护，而几百条备忘用 grep 毫秒级搞定

#### AI 友好文档 + grep：更优的方案

灵感来源于 Claude Code、Cursor 等工具的实践：**与其依赖向量相似度，不如让 AI 直接读取结构化的、对 AI 友好的文档**。

```
用户问题 → grep 关键字 → 返回完整条目 → LLM 理解完整上下文 → 精准回答
```

核心优势：
- **grep 精确命中**：没有召回率问题，关键字一定找到对应条目
- **完整条目**：LLM 拿到的是一整条完整备忘，不会丢失 Key 或 URL
- **零额外依赖**：用现有 `bash_execute` + `read_file` + `edit_file` 工具，不需要写任何新代码
- **人也能直接读**：Markdown 格式，打开文件一目了然

#### 备忘录格式设计

每条备忘是一个独立的、可 grep 的原子单元：

```markdown
---
id: memo-20260306001
type: software
title: CleanMyMac X
tags: [工具软件, Mac清理]
date: 2026-03-06
---
软件名：CleanMyMac X
下载地址：https://macpaw.com/download/cleanmymac
License Key：XXXX-XXXX-XXXX-XXXX
支持设备数：3台
购买邮箱：xxx@gmail.com
```

`type` 分类：`software`、`account`、`api`、`link`、`note`

**检索方式：**

```bash
# 查找 CleanMyMac 的 Key
grep -i -A 20 "cleanmymac" config/data/memos.md

# 查找所有软件类备忘
grep -A 20 "type: software" config/data/memos.md
```

#### 与记忆系统的区别

| 维度 | 记忆系统（Memory） | 备忘录（Memo） |
|------|-------------------|---------------|
| **存储** | SQLite | Markdown 文件 |
| **内容** | 用户偏好、对话摘要 | 软件、账号、链接等结构化信息 |
| **检索** | 关键字模糊匹配 | grep 精确匹配 |
| **写入时机** | AI 自动判断保存 | 用户明确说"帮我记一下" |
| **适用场景** | "记住我喜欢吃辣" | "记下 Cursor 的 License Key" |

### 7. 定时任务

支持 Cron 表达式，AI 可以主动在指定时间触发任务。

```
用户：每天早上 9 点提醒我定投

AI 调用：
add_cron_job(
  expression: "0 9 * * *",
  description: "定投提醒",
  prompt: "检查今天是否需要定投，如果需要则提醒用户"
)

系统：每天 9:00 自动触发 AI，AI 执行 dip_invest.py，如果建议定投则推送微信消息
```

---

## 五、部署指南

### 环境要求

- Node.js 20+
- 微信公众号（服务号或订阅号）
- 一台有公网 IP 的服务器（或内网穿透）

### 部署步骤

#### 1. 克隆项目

```bash
git clone https://github.com/your-repo/wechat-ai-assistant.git
cd wechat-ai-assistant
```

#### 2. 安装依赖

```bash
npm install
```

#### 3. 配置环境变量

复制 `.env.example` 为 `.env`，填写以下配置：

```bash
# 微信公众号配置
WECHAT_TOKEN=your_token_here
WECHAT_APP_ID=your_app_id
WECHAT_APP_SECRET=your_app_secret

# AI 模型配置（硅基流动）
SILICONFLOW_API_KEY=your_api_key
SILICONFLOW_MODEL=deepseek-ai/DeepSeek-V3

# 配置加密主密钥（重要！）
CONFIG_MASTER_KEY=your_random_secret_here

# 服务器端口
PORT=3000
```

#### 4. 启动服务

```bash
npm run dev
```

#### 5. 配置微信 Webhook

在微信公众号后台设置：
- URL: `http://your-domain.com:3000/wechat`
- Token: 与 `.env` 中的 `WECHAT_TOKEN` 一致

#### 6. 验证

向公众号发送消息"你好"，如果收到回复，说明部署成功。

---

## 六、使用指南

### 基础对话

直接发送消息，AI 会自动回复：

```
你：今天天气怎么样？
AI：正在为你查询天气...（调用 bash_execute 执行 curl 请求）
AI：北京今天晴，气温 15-25℃。
```

### 配置管理

```
你：/set TICKTICK.API_TOKEN=abc123
AI：✅ 配置已加密保存：TICKTICK.API_TOKEN
    明文已从本次会话中丢弃，不会进入 AI 上下文。

你：/config
AI：📋 已配置的 Skill 配置项（共 1 个）：
      • TICKTICK.API_TOKEN

你：/get TICKTICK.API_TOKEN
AI：✅ TICKTICK.API_TOKEN 已配置（出于安全考虑不显示明文值）
```

### 定时任务

```
你：每天早上 9 点提醒我定投
AI：好的，我已设置定时任务：
    - 调度: 0 9 * * *
    - 描述: 定投提醒
    每天早上 9 点我会主动检查并提醒你。

你：/cron list
AI：当前定时任务：
    1. 定投提醒 (0 9 * * *)
```

### 技能使用

```
你：今天需要定投吗？
AI：（自动识别 a-share-investor 技能）
    （调用 bash_execute 执行 Python 脚本）
    今天 159338 沪深300ETF 价格 3.85 元，
    低于 MA20 均线 1.79%，建议定投 200 元。
```

---

## 七、对比 OpenClaw

### 优势

| 维度 | WeClaw | OpenClaw |
|------|--------|----------|
| **代码量** | ~2000 行 | ~50000 行 |
| **部署难度** | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **学习曲线** | ⭐⭐ | ⭐⭐⭐⭐ |
| **微信支持** | ⭐⭐⭐⭐⭐ 原生支持 | ⭐⭐ 需要扩展 |
| **配置方式** | 微信聊天 `/set` | SSH 改配置文件 |
| **启动速度** | < 1s | ~5s |
| **内存占用** | ~100MB | ~300MB |
| **适用场景** | 个人微信助理 | 多渠道 AI 平台 |

### 劣势

| 维度 | WeClaw | OpenClaw |
|------|--------|----------|
| **消息渠道** | 只支持微信 | 支持 10+ 渠道 |
| **客户端** | 无（只能用微信） | macOS/iOS/Android App |
| **浏览器控制** | 无 | 支持（Playwright） |
| **语音通话** | 无 | 支持（ElevenLabs TTS） |
| **插件生态** | 无 | 38 个扩展包 |
| **多 Agent** | 单 Agent | 支持多 Agent 协作 |
| **安全性** | 无沙箱 | Docker 沙箱 + 权限系统 |

### 适用人群

**选择 WeClaw 的理由：**
- 只用微信，不需要其他消息渠道
- 想要轻量、易部署的方案
- 个人使用，不需要复杂的权限管理
- 希望通过微信聊天配置，而不是改配置文件

**选择 OpenClaw 的理由：**
- 需要支持多个消息渠道（Telegram、Slack、Discord 等）
- 需要原生客户端（macOS/iOS/Android App）
- 需要高级功能（浏览器控制、语音通话、多 Agent 协作）
- 团队使用，需要权限管理和沙箱隔离

---

## 八、技术细节

### 1. 为什么选择硅基流动？

- **价格便宜**：DeepSeek-V3 模型，1M tokens 只需 ¥1.33（OpenAI GPT-4 需要 ¥210）
- **速度快**：国内节点，延迟低
- **兼容 OpenAI API**：无缝切换，代码不需要改

### 2. 如何实现 Access Token 自动续期？

微信的 Access Token 有效期 7200 秒（2 小时），我实现了：
- **并发锁**：多个请求同时触发刷新时，只发起一次接口调用
- **主动定时刷新**：提前 5 分钟自动续期，不等到过期才刷新
- **失败重试**：续期失败时，5 分钟后自动重试

```typescript
// 标准 OAuth2 缓存模式
if (tokenCache && now < tokenCache.refreshAt) {
  return tokenCache.token; // 缓存有效，直接返回
}
if (refreshPromise) {
  return refreshPromise; // 正在刷新，等待同一个 Promise
}
refreshPromise = fetchNewToken(); // 发起新的刷新
```

### 3. 如何防止密钥泄露给 AI 厂商？

用户通过 `/set KEY=VALUE` 设置的配置，在 `server.ts` 层拦截，**不进入 Agent Loop**，AI 模型永远看不到明文。

```typescript
// server.ts 消息入口
const cmdResult = handleCommand(userText);
if (cmdResult !== null) {
  // 是指令，直接处理，不调用 runAgentLoop
  res.send(cmdResult);
  return;
}
// 不是指令，才进入 AI
await runAgentLoop(userId, userText);
```

### 4. 如何实现日志时间戳？

统一日志工具 `src/utils/logger.ts`：

```typescript
export const logger = {
  info(module: string, msg: string, ...args: any[]): void {
    console.log(`[${timestamp()}] [INFO ] [${module}] ${msg}`, ...args);
  },
  // ...
};

// 输出示例
[2026-03-06 12:10:48.453] [INFO ] [Server] 服务启动
[2026-03-06 12:10:48.453] [WARN ] [微信] Webhook 验证失败
[2026-03-06 12:10:48.453] [ERROR] [Agent] API 调用出错
```

---

## 九、未来规划

### 短期（1-2 个月）

- [ ] 支持图片消息（OCR 识别文字）
- [ ] 支持语音消息（转文字）
- [ ] 优化 Agent Loop 的"放弃策略"（避免 15 轮死循环）
- [ ] 添加更多内置技能（天气、新闻、翻译等）

### 中期（3-6 个月）

- [ ] Web 管理后台（查看对话历史、配置管理）
- [ ] 支持企业微信
- [ ] 多用户隔离（支持多个微信号）
- [ ] 技能商店（从 ClawHub 安装技能）

### 长期（6 个月+）

- [ ] 支持钉钉、飞书
- [ ] 浏览器控制（Playwright）
- [ ] 本地模型支持（Ollama）
- [ ] Docker 一键部署

---

## 十、总结

WeClaw 是一个**专注于微信生态的轻量级 AI 助理**，它从 OpenClaw 学习了核心架构设计，但去除了大量的复杂性，专注于解决个人用户的实际需求。

**核心优势：**
- 轻量（2000 行代码 vs 50000 行）
- 易部署（.env 配置 vs 复杂的 JSON5 配置）
- 易用（微信聊天配置 vs SSH 改文件）
- 专注（微信生态 vs 多渠道平台）

**适用场景：**
- 个人微信助理
- 定投提醒、日程管理、信息查询
- 需要 AI + 工具能力的自动化任务

如果你也想拥有一个属于自己的 AI 助理，不妨试试 WeClaw！

---

**项目地址：** https://github.com/your-repo/wechat-ai-assistant  
**技术交流：** 欢迎提 Issue 或 PR
