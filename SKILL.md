---
name: session-exporter
description: Use when user asks to export/backup/save Hermes conversation history, or when compression is about to lose context. Reads state.db, filters relevant sessions by title/ID, exports to readable markdown files with user/AI/tool messages, and generates a navigation index.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [session, export, backup, context, history]
    related_skills: [project-context-doc]
---

# Session Exporter — 会话历史导出备份

## Overview

从 Hermes 的 `state.db` SQLite 数据库中导出任意会话的完整对话历史为 Markdown 文件。适用于**任何项目**——只需提供标题关键词或 session_id，即可导出为可读的备份文档，防止上下文压缩后信息丢失。

示例场景：
- 搜索项目会话 → 导出 `title LIKE '%项目关键词%'`
- 精确导出 → 导出 `--ids "session_id_1,session_id_2"`
- 按时间范围 → 结合 SQL 时间过滤批量导出

## When to Use

- 用户说"导出会话历史" / "备份对话" / "保存完整对话"
- 用户担心 Hermes 压缩上下文后丢失对话信息
- 跨会话需要回顾之前讨论的细节

Don't use for:
- 简单的上下文摘要（用 `project-context-doc` 技能）
- 单个会话的快速查看（用 `session_search` 工具）

## Workflow

### Step 1: 确认导出范围

询问用户：
- **导出哪些会话？** 按标题关键词匹配 / 按 session_id 列表 / 按时间范围
- **导出目录？** 默认 `{project_root}/docs/sessions/`
- **是否包含工具输出？** 默认包含（折叠在 `<details>` 中），超过 5000 字符截断

### Step 2: 读取数据库

```python
import sqlite3
db_path = os.path.expanduser("~/AppData/Local/hermes/state.db")  # Windows
# db_path = os.path.expanduser("~/.local/share/hermes/state.db") # Linux/Mac

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
```

### Step 3: 查找目标会话

```sql
-- 按标题关键词匹配
SELECT id, title, message_count, parent_session_id
FROM sessions 
WHERE title LIKE '%keyword%'
ORDER BY started_at

-- 按 session_id 精确匹配
SELECT id, title, message_count, parent_session_id
FROM sessions 
WHERE id IN ('session_id_1', 'session_id_2')
```

### Step 4: 导出消息

对每个会话执行：

```sql
SELECT role, content, tool_calls, tool_name, id
FROM messages 
WHERE session_id = ?
ORDER BY id
```

### Step 5: 生成 Markdown

每条消息按角色格式化：

```
## 👤 用户
{content}
---

## 🤖 AI
{content}
> 🔧 调用工具: tool_name_1, tool_name_2
---

<details>
<summary>🔧 工具输出: tool_name</summary>

```
{content (超过5000字符截断)}
```

</details>
---
```

### Step 6: 生成索引

创建 `README.md` 包含所有导出文件的清单、消息统计和内容摘要。

### Step 7: 清理无关会话

如果用户要求只保留与当前项目相关的会话，删除明显无关的（如 LLM-wiki 技能分析、模型配置修复等）。

## Technical Notes

### 数据库位置

| OS | 路径 |
|----|------|
| Windows | `~/AppData/Local/hermes/state.db` |
| macOS | `~/Library/Application Support/hermes/state.db` |
| Linux | `~/.local/share/hermes/state.db` |

### 消息表结构

```sql
messages (
  id INTEGER PRIMARY KEY,
  session_id TEXT,
  role TEXT,           -- 'user', 'assistant', 'tool'
  content TEXT,        -- 消息正文
  tool_calls TEXT,     -- JSON: assistant 调用的工具列表
  tool_name TEXT,      -- tool 消息的工具名
  timestamp REAL       -- Unix 时间戳
)
```

### 消息量估算

| 角色 | 占比 | 处理方式 |
|------|------|---------|
| user | ~15% | 直接展示 |
| assistant | ~45% | 直接展示 + 工具调用标注 |
| tool | ~40% | `<details>` 折叠，超 5000 字截断 |

一个典型 150 条消息的会话导出约 150-200 KB。

## One-Shot Recipe

### 导出项目全部相关会话

```python
import sqlite3, json, os, re

db_path = os.path.expanduser("~/AppData/Local/hermes/state.db")
output_dir = "{project_root}/docs/sessions"

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

# 查找包含关键词的会话
sessions = conn.execute("""
    SELECT id, title, message_count, parent_session_id
    FROM sessions 
    WHERE title LIKE '%keyword1%' OR title LIKE '%keyword2%'
    ORDER BY started_at
""").fetchall()

# 导出每个会话的消息到 Markdown
for idx, s in enumerate(sessions):
    msgs = conn.execute("""
        SELECT role, content, tool_calls, tool_name
        FROM messages WHERE session_id = ? ORDER BY id
    """, (s["id"],)).fetchall()
    
    # Write to {idx+1:02d}-{safe_title}.md
    # Format: 👤 user / 🤖 AI / <details> tool

conn.close()
```

## Common Pitfalls

1. **忘记设置 `row_factory`**：不设置 `conn.row_factory = sqlite3.Row` 会导致 `s["id"]` 报 `TypeError: tuple indices must be integers`
2. **工具输出过大**：单条 tool 消息可能超过 100KB，务必截断（5000 字符上限），否则导出文件难以打开
3. **数据库被锁定**：Hermes 运行时 state.db 可能被其他进程占用，用只读模式打开（`sqlite3.connect(db_path, uri=True)` + `file:/path?mode=ro`）
4. **会话 ID 混淆**：`title` 可能相同但 `id` 不同（压缩产生的子会话），需要通过 `parent_session_id` 追溯血缘
5. **路径不存在**：`output_dir` 必须先 `os.makedirs(exist_ok=True)` 再写入
6. **文件命名冲突**：用 `re.sub(r'[\\/*?:"<>|]', '_', title)` 清理文件名中的非法字符
7. **跨平台路径**：Windows 用 `~/AppData/Local/hermes/state.db`，不是 `~/.hermes/state.db`

## Verification Checklist

- [ ] 所有目标会话的消息都已导出
- [ ] 用户消息和 AI 消息直接可见
- [ ] 工具输出折叠在 `<details>` 中，可点击展开
- [ ] 索引文件 `README.md` 包含所有导出文件的链接和统计
- [ ] 无关会话已按用户要求删除
- [ ] 总文件大小可接受（< 2 MB 为宜）
