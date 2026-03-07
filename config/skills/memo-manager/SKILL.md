---
name: memo-manager
description: "备忘录管理：记录和检索个人备忘信息（软件 License、账号信息、重要链接等）。当用户说\"帮我记一下\"、\"记录\"、\"备忘\"或需要查找已保存信息时触发。"
metadata: { "openclaw": { "emoji": "📝" } }
---

# 备忘录管理技能

备忘录文件路径：`config/data/memos.md`

## When to Use

✅ **USE this skill when:**

- 用户说"帮我记一下"、"记录"、"备忘"、"记住这个"
- 用户提供软件 License、账号密码、下载链接、API Key 等需要保存的信息
- 用户说"帮我查一下"、"找一下"、"xxx 的 key 是什么"、"xxx 怎么下载"

## When NOT to Use

❌ **DON'T use this skill when:**

- 用户只是闲聊或提到信息但无保存意图
- 敏感凭据应通过 `/set` 指令安全存储的场景

## 备忘格式

每条备忘用 `---` 分隔，包含 YAML 头信息和正文：

```
---
id: memo-{时间戳，如20260306001}
type: {software|account|link|note|api}
title: {简短标题，是检索的主要入口}
tags: [{标签1}, {标签2}]
date: {YYYY-MM-DD}
---
{完整的备忘内容，保留所有细节}

```

type 类型说明：
- `software`：软件相关（License、下载地址、激活方式）
- `account`：账号信息（用户名、平台、订阅状态）
- `api`：API Key、Token 等
- `link`：重要链接、资源地址
- `note`：其他备忘事项

## 添加备忘

1. 使用 `read_file` 读取 `config/data/memos.md` 获取现有内容
2. 生成新的备忘条目（id 使用日期+序号，如 `memo-20260306001`）
3. 使用 `edit_file` 将新条目追加到文件末尾（在最后一个 `---` 分隔符之后）
4. 回复用户"✅ 已记录：{title}"

## 检索备忘

1. 优先使用 `bash_execute` 执行 grep 检索：
   ```bash
   grep -i -A 20 "{关键字}" config/data/memos.md
   ```
2. 如果 grep 结果不够完整，使用 `read_file` 读取全文，让 AI 理解完整上下文
3. 将找到的完整条目信息回复给用户

## 示例检索命令

```bash
# 查找 CleanMyMac 相关信息
grep -i -A 20 "cleanmymac" config/data/memos.md

# 查找所有软件类备忘
grep -A 20 "type: software" config/data/memos.md

# 查找包含 license 的条目
grep -i -A 15 "license" config/data/memos.md

# 查找某个平台账号
grep -i -A 15 "cursor" config/data/memos.md
```

## 注意事项

- 保存时保留用户提供的所有信息，不要省略（Key、URL、账号等都要完整保存）
- title 要简洁且有代表性，方便后续检索
- 如果文件不存在，使用 `write_file` 创建文件并写入初始模板和第一条备忘
