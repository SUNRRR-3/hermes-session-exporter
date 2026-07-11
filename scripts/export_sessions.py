#!/usr/bin/env python3
"""
Hermes Session Exporter
从 state.db 读取会话消息，导出为 Markdown 文件。

用法:
  python3 export_sessions.py --keyword "github-know" --output docs/sessions/
  python3 export_sessions.py --ids "session_id_1,session_id_2" --output docs/sessions/
"""

import sqlite3
import json
import os
import re
import argparse
from datetime import datetime


def find_sessions(db_path, keywords=None, ids=None):
    """查找匹配的会话"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    if ids:
        id_list = [i.strip() for i in ids.split(",")]
        places = ",".join(["?"] * len(id_list))
        rows = conn.execute(
            f"SELECT id, title, message_count, parent_session_id FROM sessions WHERE id IN ({places}) ORDER BY started_at",
            id_list
        ).fetchall()
    elif keywords:
        clauses = " OR ".join(["title LIKE ?"] * len(keywords))
        params = [f"%{kw}%" for kw in keywords]
        rows = conn.execute(
            f"SELECT id, title, message_count, parent_session_id FROM sessions WHERE {clauses} ORDER BY started_at",
            params
        ).fetchall()
    else:
        conn.close()
        return []
    
    conn.close()
    return rows


def export_session(db_path, session_id, output_dir, include_tools=True, max_tool_len=5000):
    """导出单个会话"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    msgs = conn.execute(
        "SELECT role, content, tool_calls, tool_name, id FROM messages WHERE session_id = ? ORDER BY id",
        (session_id,)
    ).fetchall()
    
    conn.close()
    
    if not msgs:
        return None
    
    # Build markdown
    lines = []
    u = a = t = 0
    
    for msg in msgs:
        role = msg["role"] or ""
        content = (msg["content"] or "").strip()
        
        if role == "user":
            if content:
                lines.append(f"## 👤 用户\n\n{content}\n\n---\n")
                u += 1
        elif role == "assistant":
            if content:
                lines.append(f"## 🤖 AI\n\n{content}\n")
                a += 1
                tcs = msg["tool_calls"]
                if tcs:
                    try:
                        tc_list = json.loads(tcs) if isinstance(tcs, str) else tcs
                        if tc_list:
                            names = set()
                            for tc in tc_list:
                                fn = tc["function"]["name"] if "function" in tc else ""
                                if fn:
                                    names.add(fn)
                            if names:
                                lines.append(f"> 🔧 调用工具: {', '.join(names)}\n")
                    except:
                        pass
                lines.append("\n---\n")
        elif role == "tool" and include_tools:
            tool_name = msg["tool_name"] or "tool"
            if len(content) > max_tool_len:
                content = content[:max_tool_len] + f"\n\n... (截断，原始 {len(content)} 字符)"
            lines.append(f"<details>\n<summary>🔧 工具输出: {tool_name}</summary>\n\n```\n{content}\n```\n\n</details>\n\n---\n")
            t += 1
    
    return {
        "content": "".join(lines),
        "stats": {"user": u, "assistant": a, "tool": t, "total": u + a + t}
    }


def main():
    parser = argparse.ArgumentParser(description="Hermes Session Exporter")
    parser.add_argument("--keyword", "-k", action="append", help="标题关键词 (可多次使用)")
    parser.add_argument("--ids", help="逗号分隔的 session_id 列表")
    parser.add_argument("--output", "-o", default="docs/sessions/", help="输出目录")
    parser.add_argument("--no-tools", action="store_true", help="不包含工具输出")
    parser.add_argument("--max-tool-len", type=int, default=5000, help="工具输出截断长度")
    parser.add_argument("--db", help="state.db 路径 (默认自动检测)")
    args = parser.parse_args()
    
    # Detect db path
    if args.db:
        db_path = args.db
    else:
        home = os.path.expanduser("~")
        candidates = [
            os.path.join(home, "AppData/Local/hermes/state.db"),  # Windows
            os.path.join(home, "Library/Application Support/hermes/state.db"),  # macOS
            os.path.join(home, ".local/share/hermes/state.db"),  # Linux
        ]
        db_path = next((p for p in candidates if os.path.exists(p)), None)
        if not db_path:
            print("❌ 未找到 state.db，请用 --db 指定路径")
            return
    
    keywords = args.keyword
    ids = args.ids
    
    if not keywords and not ids:
        print("❌ 请指定 --keyword 或 --ids")
        return
    
    # Find sessions
    sessions = find_sessions(db_path, keywords, ids.split(",") if ids else None)
    if not sessions:
        print("❌ 未找到匹配的会话")
        return
    
    # Export
    os.makedirs(args.output, exist_ok=True)
    
    for idx, s in enumerate(sessions):
        safe_title = re.sub(r'[\\/*?:"<>|]', '_', s["title"])[:50]
        fname = f"{idx+1:02d}-{safe_title}.md"
        fpath = os.path.join(args.output, fname)
        
        result = export_session(db_path, s["id"], args.output, 
                               include_tools=not args.no_tools,
                               max_tool_len=args.max_tool_len)
        if not result:
            continue
        
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(f"# {s['title']}\n\n")
            f.write(f"**会话ID**: `{s['id']}`\n")
            f.write(f"**总消息数**: {s['message_count']}\n\n")
            f.write("---\n\n")
            f.write(result["content"])
        
        size_kb = os.path.getsize(fpath) / 1024
        st = result["stats"]
        print(f"✅ [{idx+1:02d}] {safe_title[:40]} — {st['user']}U+{st['assistant']}A+{st['tool']}T — {size_kb:.0f}KB")
    
    # Generate index
    readme_path = os.path.join(args.output, "README.md")
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write("# Session Export Index\n\n")
        f.write(f"> Exported: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write("| # | Session | Messages | Size |\n")
        f.write("|---|---------|----------|------|\n")
        for idx, s in enumerate(sessions):
            safe_title = re.sub(r'[\\/*?:"<>|]', '_', s["title"])[:50]
            fname = f"{idx+1:02d}-{safe_title}.md"
            fsize = os.path.getsize(os.path.join(args.output, fname))
            f.write(f"| {idx+1} | [{s['title'][:50]}](./{fname}) | {s['message_count']} | {fsize/1024:.0f}KB |\n")
    
    print(f"\n📁 {os.path.abspath(args.output)}")


if __name__ == "__main__":
    main()
