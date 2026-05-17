# Hermes Feishu Multi-Agent

让多个 Hermes Agent 在飞书群聊中通过 @mention 互相触发、协作对话。

## 为什么需要这个

飞书原生不支持机器人互相 @mention。当你在飞书群里部署多个 Hermes Agent 时：

1. Agent A 写 `@AgentB 帮我查一下数据` → 飞书只当纯文本发送，Agent B 收不到通知
2. Agent 之间没有实时通信通道，只能通过读文件等方式间接协作
3. 用户体验割裂，看不到 Agent 之间的协作过程

本项目通过一个轻量 patch 解决这个问题：Agent 发出的 `@BotName` 文本会被自动转换为飞书原生的 `<at>` 标签，**真正触发目标 Agent 响应**。

## 工作原理

```
Agent LLM 回复: "@项目经理 帮我查一下获客数据"
        │
        ▼
┌─────────────────────────────┐
│  feishu_at_patch (运行时补丁)  │
│  识别 @BotName → 查 registry │
│  转换为 Feishu <at> 标签     │
└─────────────────────────────┘
        │
        ▼
飞书 API 发送: post 格式消息
  elements: [
    {"tag": "text", "text": "帮我查一下获客数据"},
    {"tag": "at", "user_id": "ou_xxx"}   ← 真正的 @提醒
  ]
        │
        ▼
项目经理 Agent 收到通知 → 自动响应
```

三层机制：

| 层 | 文件 | 作用 |
|----|------|------|
| 运行时补丁 | `patch/feishu_at_patch.py` | 在 feishu.py 出站消息中转换 @mention |
| 环境变量 | `.env` 中的 `FEISHU_BOT_REGISTRY` | Agent 名称 → open_id 映射表 |
| 提示词协议 | SOUL.md 协作段落 | 教会 LLM 使用 `@AgentName` 格式 |

## 前置条件

### 飞书应用权限

每个 Agent 对应一个飞书机器人应用，需要开通以下权限并发布：

| 权限 | 说明 |
|------|------|
| `im:chat:readonly` | 接收群聊消息 |
| `im:message:send` | 发送消息 |
| `im:message:send_as_bot` | 以机器人身份发送（推荐） |

事件订阅：
- `im.message.receive_v1` — 接收消息事件

### Hermes 环境

- Hermes Agent v0.11.0+（本项目在 v0.11.0 上开发测试）
- Python 3.11+
- 每个 Agent 独立的 `.env` 配置

## 安装

### 1. 应用补丁

```bash
# 找到你的 feishu.py 路径
# 通常在 ~/.hermes/hermes-agent/gateway/platforms/feishu.py

# 应用补丁（幂等，重复运行会自动跳过）
python patch/feishu_at_patch.py ~/.hermes/hermes-agent/gateway/platforms/feishu.py
```

### 2. 获取每个 Bot 的 open_id

```bash
# 设置当前 bot 的凭证
export FEISHU_APP_ID=cli_xxxxxxxx
export FEISHU_APP_SECRET=xxxxxxxx

# 查询 open_id
python scripts/get_bot_open_id.py
```

输出示例：
```
机器人名称: 柯柯
open_id:    ou_6e8ed6f0dd266744255aba3f2b88f886
```

### 3. 配置环境变量

在**每个** Agent 的 `.env` 文件中添加 `FEISHU_BOT_REGISTRY`：

```bash
# ~/.hermes/.env（主 Agent）
# ~/.hermes/profiles/pm/.env（PM Agent）
# 所有 Agent 的值必须完全一致！

FEISHU_BOT_REGISTRY={"柯柯":"ou_6e8ed6f0dd266744255aba3f2b88f886","项目经理":"ou_89e3695532a9bf5c44193c5be82c3565"}
```

完整 `.env` 配置参见 `examples/.env.example`。

### 4. 添加协作协议到 SOUL.md

在每个 Agent 的 `SOUL.md` 文件末尾添加协作段落。
模板见 `examples/collaboration-protocol.md`，根据实际 Agent 名称和职责修改。

### 5. 重启 Gateway

```bash
systemctl --user restart hermes-gateway        # 主 Agent
systemctl --user restart hermes-gateway-pm      # PM Agent（如有）
```

## 验证

启动后查看日志，确认 bot registry 加载成功：

```bash
# 查看日志
tail -f ~/.hermes/logs/gateway.log | grep "Loaded.*bot.*mention"
```

预期输出：
```
[Feishu] Loaded 2 bot(s) for @mention conversion: ['柯柯', '项目经理']
```

在飞书群中发送测试消息，观察 Agent 是否用 `@AgentName` 格式回复。

## 调试

### 查看 @mention 转换日志

```bash
grep "Feishu-AT\|_convert_mentions" ~/.hermes/logs/gateway.log | tail -20
```

### 常见问题

**Agent 回复中没有 `@BotName`**
- 检查 SOUL.md 协作协议是否已添加
- 确认指令明确要求使用 `@` 前缀

**@mention 没有变成蓝色可点击标签**
- 确认 `FEISHU_BOT_REGISTRY` 已配置且所有 Agent 值一致
- 检查日志中是否有 `Loaded X bot(s)` 输出
- 确认补丁已应用（检查 feishu.py 中是否有 `feishu-at-patch` 标记）

**群聊中 Agent 卡住不回复**
- 检查 `config.yaml` 中 `approvals.mode` 设置
- 飞书交互卡片回调可能不支持 WebSocket 模式，建议设置 `mode: off` 或 `mode: smart`

## 限制

- 补丁只修改 `feishu.py` 的出站消息处理，不影响入站逻辑
- 需要每个 Agent 独立的飞书应用（不同 app_id/app_secret）
- 所有 Agent 必须在同一个飞书群中才能互相触发
- `FEISHU_BOT_REGISTRY` 不支持动态更新，修改后需重启 gateway
- 目前只支持飞书（Feishu/Lark）平台

## 项目结构

```
hermes-feishu-multi-agent/
├── README.md                          # 本文档
├── LICENSE                            # MIT
├── CLAUDE.md                          # AI 助手指引
├── patch/
│   └── feishu_at_patch.py             # 核心补丁脚本
├── examples/
│   ├── collaboration-protocol.md      # SOUL.md 协作协议模板
│   └── .env.example                   # 环境变量配置示例
├── docs/
│   └── setup-guide.md                 # 详细部署指南
└── scripts/
    └── get_bot_open_id.py             # 获取 Bot open_id 辅助脚本
```

## License

MIT
