# CLAUDE.md

## 项目概述

Hermes Feishu Multi-Agent — 让多个 Hermes Agent 在飞书群聊中通过 @mention 互相触发协作。

## 架构

三层机制：
1. **patch/feishu_at_patch.py** — Python 补丁脚本，修改 Hermes 的 feishu.py，在出站消息中将 `@BotName` 文本转换为飞书 `<at>` 标签
2. **FEISHU_BOT_REGISTRY** 环境变量 — JSON 映射表，所有 Agent 共享相同的名称→open_id 映射
3. **SOUL.md 协作协议** — 提示词模板，教会 LLM 使用 `@AgentName` 格式进行通信

## 关键文件

- `patch/feishu_at_patch.py` — 核心补丁，4 处代码注入（init、registry loader、mention converter、 outbound payload）
- `examples/collaboration-protocol.md` — SOUL.md 协作协议模板
- `scripts/get_bot_open_id.py` — 飞书 API 查询 bot open_id
- `docs/setup-guide.md` — 完整部署指南

## 开发约定

- 补丁脚本使用 `# -- feishu-at-patch v1 --` 标记，保证幂等性
- 补丁注入点：`self._bot_name` 赋值后、`_is_self_sent_bot_message` 方法前、`_build_outbound_payload` 方法替换
- 所有文档使用中文
- 不使用 f-string 拼接代码块（避免转义问题），使用 `--MARKER--` 占位符替换

## 测试方式

1. 应用补丁到 feishu.py
2. 配置 FEISHU_BOT_REGISTRY
3. 重启 gateway
4. 在飞书群中发送包含 @BotName 的消息
5. 检查日志中 `Loaded X bot(s)` 和 `_convert_mentions_at` 输出
