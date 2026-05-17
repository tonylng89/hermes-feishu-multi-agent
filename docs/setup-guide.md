# 部署指南

本文档提供从零开始部署多 Agent 飞书协作的完整步骤。

## 第一步：创建飞书机器人应用

### 1.1 在飞书开放平台创建应用

1. 访问 https://open.feishu.cn/app
2. 点击「创建企业自建应用」
3. 填写应用名称（如「柯柯」）
4. 记录 App ID (`cli_xxx`) 和 App Secret

### 1.2 配置权限

进入应用 → 权限管理 → 添加以下权限：

- `im:chat:readonly` — 获取群组信息
- `im:message:send` — 发送消息
- `im:message:send_as_bot` — 以应用身份发消息

### 1.3 配置事件订阅

进入应用 → 事件订阅：
1. 选择 WebSocket 模式
2. 添加事件：`im.message.receive_v1`（接收消息）

### 1.4 发布应用

进入应用 → 版本管理 → 创建版本 → 申请发布

### 1.5 重复以上步骤

为每个 Agent 创建独立的应用（如「项目经理」「数据分析师」等）。

## 第二步：获取每个 Bot 的 open_id

对每个应用，运行辅助脚本：

```bash
# 设置第一个 bot 的凭证
export FEISHU_APP_ID=cli_xxxxxxxx
export FEISHU_APP_SECRET=xxxxxxxx

python scripts/get_bot_open_id.py
```

记录每个 bot 的名称和 open_id。

## 第三步：应用补丁

```bash
# 找到 feishu.py 路径
find ~/.hermes -name "feishu.py" -path "*/platforms/*"

# 应用补丁
python patch/feishu_at_patch.py /home/m/.hermes/hermes-agent/gateway/platforms/feishu.py
```

补丁是幂等的，重复运行会自动跳过。

## 第四步：配置环境变量

### 4.1 主 Agent

编辑 `~/.hermes/.env`，添加：

```bash
FEISHU_BOT_REGISTRY={"柯柯":"ou_xxx1","项目经理":"ou_xxx2"}
```

### 4.2 其他 Agent（如有 profile）

编辑 `~/.hermes/profiles/<name>/.env`，添加**完全相同**的值：

```bash
FEISHU_BOT_REGISTRY={"柯柯":"ou_xxx1","项目经理":"ou_xxx2"}
```

**重要**：所有 Agent 的 `FEISHU_BOT_REGISTRY` 值必须完全一致。

## 第五步：添加协作协议

在每个 Agent 的 SOUL.md 末尾添加协作段落。

参考 `examples/collaboration-protocol.md`，修改其中的 Agent 名称和职责。

关键要求：
- Agent 列表必须包含所有协作的 Agent
- 必须强调使用 `@AgentName` 格式（不是裸名称）
- 必须说明这是真实的 bot-to-bot 通信

## 第六步：重启 Gateway

```bash
# 主 Agent
systemctl --user restart hermes-gateway

# 其他 Agent（如有独立 systemd 服务）
systemctl --user restart hermes-gateway-<name>
```

## 第七步：验证

### 检查日志

```bash
tail -f ~/.hermes/logs/gateway.log | grep "Loaded.*bot.*mention"
```

预期：
```
[Feishu] Loaded 2 bot(s) for @mention conversion: ['柯柯', '项目经理']
```

### 测试协作

在飞书群中发送：
```
@柯柯 帮我问问 @项目经理 今天的数据怎么样
```

观察：
1. 柯柯是否用 `@项目经理` 格式回复
2. 项目经理是否收到通知并响应
3. 回复中 `@项目经理` 是否显示为蓝色可点击标签

## 高级配置

### 审批模式

默认情况下，Hermes 的工具调用需要人工审批。在飞书群中审批卡片按钮可能不工作。

建议在 `config.yaml` 中调整：

```yaml
approvals:
  mode: off      # 完全关闭审批（适合信任的环境）
  # mode: smart  # 使用 AI 判断低风险命令自动通过
  # mode: manual # 手动审批（默认）
```

修改后需重启 gateway。

### 添加新的 Agent

1. 在飞书开放平台创建新的机器人应用
2. 获取 open_id
3. 更新所有 Agent 的 `FEISHU_BOT_REGISTRY`
4. 在所有 Agent 的 SOUL.md 中添加新 Agent 到协作表
5. 重启所有 gateway
