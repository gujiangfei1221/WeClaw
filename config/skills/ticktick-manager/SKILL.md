---
name: ticktick-manager
description: "Manage TickTick (Dida365) tasks and projects via OpenAPI. Use when user asks to create/list/update/complete tasks, manage projects, or sync task status with TickTick. Requires OAuth access token."
metadata: { "openclaw": { "emoji": "✅", "requires": { "bins": ["curl"] } } }
---

# TickTick Manager Skill

通过 bash_execute + curl 调用滴答清单 (Dida365) OpenAPI 管理任务。

## Prerequisites

需要通过 `/set` 指令配置 access token：

```
/set TICKTICK.ACCESS_TOKEN=<your-oauth-access-token>
```

如果未配置，使用 `getConfig("TICKTICK.ACCESS_TOKEN")` 读取。如果返回空，提示用户先配置。

**⚠️ 关键说明：这不是一个独立工具！**

使用 `bash_execute` 工具执行下方 curl 命令，不存在 `ticktick` 工具。

## When to Use

✅ **USE this skill when:**

- "我今天有什么任务"、"今日待办"
- "帮我创建/添加一个任务"
- "完成/删除/更新某个任务"
- "列出我的项目"
- 晨间问候需要获取待办信息时

## When NOT to Use

❌ **DON'T use this skill when:**

- 用户只是口头提到任务但无操作意图
- 备忘录类型的记录（应使用 memo-manager 技能）

## Core Rules

- **所有 API 调用都通过 bash_execute + curl 执行**
- Never print full tokens in output; mask with `***` if needed
- If API returns 401, ask user to refresh OAuth token
- 所有请求加 `--max-time 10` 超时限制

## API Base URL

```
https://api.dida365.com/open/v1
```

## Common Workflows

### 1) List projects

```bash
curl -s --max-time 10 \
  -H "Authorization: Bearer $(cat /var/www/weclaw/data/skill-config.enc.json 2>/dev/null | node -e "
    const crypto = require('crypto');
    const data = JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'));
    const key = data['TICKTICK.ACCESS_TOKEN'];
    if(key){const d=Buffer.from(key.data,'base64');const iv=Buffer.from(key.iv,'base64');const dc=crypto.createDecipheriv('aes-256-cbc',crypto.scryptSync(process.env.CONFIG_ENCRYPTION_KEY||'weclaw-default-key-change-me','salt',32),iv);console.log(dc.update(d,'binary','utf8')+dc.final('utf8'))}
  " 2>/dev/null)" \
  "https://api.dida365.com/open/v1/project"
```

> ⚠️ 上述命令较复杂。**更推荐的做法**：先用 `search_memory` 或读取配置获取 token，然后直接在 curl 命令中使用。

### 简化版（推荐）

如果已知 ACCESS_TOKEN（通过 getConfig 获取），直接使用：

```bash
# 列出所有项目
curl -s --max-time 10 \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  "https://api.dida365.com/open/v1/project"

# 获取项目中的任务
curl -s --max-time 10 \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  "https://api.dida365.com/open/v1/project/<projectId>/data"

# 创建任务
curl -s --max-time 10 -X POST \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"title":"<任务标题>","projectId":"<projectId>","content":"<详细内容>","dueDate":"<ISO日期>"}' \
  "https://api.dida365.com/open/v1/task"

# 完成任务
curl -s --max-time 10 -X POST \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  "https://api.dida365.com/open/v1/project/<projectId>/task/<taskId>/complete"

# 删除任务
curl -s --max-time 10 -X DELETE \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  "https://api.dida365.com/open/v1/project/<projectId>/task/<taskId>"

# 更新任务
curl -s --max-time 10 -X POST \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"title":"<新标题>","content":"<新内容>","dueDate":"<新日期>","priority":<0-5>}' \
  "https://api.dida365.com/open/v1/task/<taskId>"
```

## Error Handling

- `401 Unauthorized`: Access token expired/invalid → 提示用户重新配置
- `403 Forbidden`: App lacks required scope
- `404 Not Found`: projectId/taskId invalid
- `429 Too Many Requests`: retry with backoff
- **超时/连接失败**: 跳过待办获取，不要反复重试

## References

- API notes: `references/openapi-notes.md`
- Official docs: https://developer.dida365.com/docs#/openapi
