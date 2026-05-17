#!/usr/bin/env bash
# Hermes Feishu Multi-Agent — 一键安装脚本
# 自动检测 Hermes 路径、应用补丁、引导配置
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# === 1. 检测 Hermes 安装路径 ===
echo ""
echo "=== Hermes Feishu Multi-Agent 安装 ==="
echo ""

HERMES_DIR="${HERMES_DIR:-$HOME/.hermes}"
FEISHU_PY=""

if [ -f "$HERMES_DIR/hermes-agent/gateway/platforms/feishu.py" ]; then
    FEISHU_PY="$HERMES_DIR/hermes-agent/gateway/platforms/feishu.py"
    info "找到 feishu.py: $FEISHU_PY"
else
    # 尝试搜索
    SEARCH_RESULT=$(find "$HERMES_DIR" -name "feishu.py" -path "*/platforms/*" 2>/dev/null | head -1)
    if [ -n "$SEARCH_RESULT" ]; then
        FEISHU_PY="$SEARCH_RESULT"
        info "找到 feishu.py: $FEISHU_PY"
    else
        error "找不到 feishu.py"
        echo "  请手动指定路径: HERMES_DIR=/path/to/.hermes bash install.sh"
        exit 1
    fi
fi

# === 2. 兼容性检查 ===
echo ""
echo "--- 兼容性检查 ---"
python3 "$SCRIPT_DIR/patch/feishu_at_patch.py" "$FEISHU_PY" --check

# === 3. 应用补丁 ===
echo "--- 应用补丁 ---"
python3 "$SCRIPT_DIR/patch/feishu_at_patch.py" "$FEISHU_PY"

# === 4. 引导配置 ===
echo ""
echo "--- 配置指引 ---"
echo ""
echo "补丁已应用。接下来请配置："
echo ""
echo "1. 获取每个 Bot 的 open_id:"
echo "   export FEISHU_APP_ID=cli_xxxxxxxx"
echo "   export FEISHU_APP_SECRET=xxxxxxxx"
echo "   python3 $SCRIPT_DIR/scripts/get_bot_open_id.py"
echo ""
echo "2. 在每个 Agent 的 .env 中添加 FEISHU_BOT_REGISTRY:"
echo "   文件位置: $HERMES_DIR/.env"
echo "   如果有 profile: $HERMES_DIR/profiles/<name>/.env"
echo ""
echo '   FEISHU_BOT_REGISTRY={"BotA":"ou_xxx","BotB":"ou_yyy"}'
echo ""
echo "3. 在每个 Agent 的 SOUL.md 末尾添加协作协议:"
echo "   参考: $SCRIPT_DIR/examples/collaboration-protocol.md"
echo ""
echo "4. 重启 Gateway:"
echo "   systemctl --user restart hermes-gateway"
echo ""
echo "5. 验证日志:"
echo "   grep 'Loaded.*bot.*mention' $HERMES_DIR/logs/gateway.log"
echo ""
info "安装完成！"
