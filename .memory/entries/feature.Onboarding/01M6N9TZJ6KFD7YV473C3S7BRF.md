---
id: 01M6N9TZJ6KFD7YV473C3S7BRF
module: feature.Onboarding
entity: Hooks
kind: feature
status: active
supersedes: []
anchors: []
revision: git:4d776a5
author: 1002378395@qq.com
note_date: '2026-11-05'
summary: Windows quiet 闸门 matcher 去掉 Shell/Bash
applies: Windows；pmem init --hooks quiet|auto
---
需求：Windows 上 quiet hooks 不再因每条 Shell/Bash 弹控制台。
行为：CURSOR_HOOKS_QUIET preToolUse matcher 为 Write|…|Delete|MCP|record_memory|search_memory（无 Shell）；
CODEX_HOOKS_QUIET matcher 仅 apply_patch|mcp。
入口：pmem init --hooks quiet|auto（Windows）。
适用：Cursor/Codex Windows。
