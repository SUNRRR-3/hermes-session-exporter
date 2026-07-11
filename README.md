# Hermes Session Exporter

从 Hermes Agent 的 `state.db` 数据库导出会话历史为可读 Markdown 文件的通用技能，适用于任何项目。

## 适用场景

- Hermes 压缩上下文后需要回顾完整对话
- 跨会话需要对齐项目认知
- 为任意项目生成对话备份文档

## 安装

```bash
# 克隆到 Hermes 技能目录
git clone https://github.com/SUNRRR-3/hermes-session-exporter.git ~/AppData/Local/hermes/skills/productivity/session-exporter/
```

或手动复制 `SKILL.md` 和 `scripts/` 到 `~/.hermes/skills/productivity/session-exporter/`。

## 触发方式

在 Hermes 对话中说：
- "导出会话历史" / "备份对话"
- "保存完整对话到文档"
- "把当前项目的会话导出来"

## 功能

| 功能 | 说明 |
|------|------|
| 按关键词匹配 | `title LIKE '%关键词%'` 过滤项目相关会话 |
| 按 session_id | 精确导出指定会话 |
| 全角色导出 | 用户 + AI + 工具输出 |
| 工具输出折叠 | `<details>` 标签折叠，5000+ 字符自动截断 |
| 索引导航 | 自动生成 README.md 索引 |

## 使用示例

```bash
# 导出包含指定关键词的会话
python3 scripts/export_sessions.py --keyword "项目关键词" --output docs/sessions/

# 导出指定会话
python3 scripts/export_sessions.py --ids "session_id_1,session_id_2" --output docs/sessions/
```

## 输出格式

```
docs/sessions/
├── README.md                              # 索引
├── 01-会话标题.md                          # 👤🤖 对话 + 🔧 工具输出
├── 02-另一个会话.md
└── ...
```

## 跨平台支持

| OS | state.db 路径 |
|----|-------------|
| Windows | `~/AppData/Local/hermes/state.db` |
| macOS | `~/Library/Application Support/hermes/state.db` |
| Linux | `~/.local/share/hermes/state.db` |

## License

MIT
