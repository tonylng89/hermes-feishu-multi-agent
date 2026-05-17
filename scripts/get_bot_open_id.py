"""
获取飞书机器人的 open_id。

使用方法:
  python get_bot_open_id.py

需要设置环境变量:
  FEISHU_APP_ID     - 飞书应用 App ID
  FEISHU_APP_SECRET - 飞书应用 App Secret

输出每个机器人的名称和 open_id，用于配置 FEISHU_BOT_REGISTRY。
"""

import json
import os
import sys
import urllib.request
import urllib.error


def get_tenant_access_token(app_id: str, app_secret: str) -> str:
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
    if result.get("code") != 0:
        print(f"Error getting token: {result}")
        sys.exit(1)
    return result["tenant_access_token"]


def get_bot_info(token: str) -> dict:
    url = "https://open.feishu.cn/open-apis/bot/v3/info"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
    if result.get("code") != 0:
        print(f"Error getting bot info: {result}")
        sys.exit(1)
    return result.get("bot", {})


def main():
    app_id = os.getenv("FEISHU_APP_ID", "").strip()
    app_secret = os.getenv("FEISHU_APP_SECRET", "").strip()

    if not app_id or not app_secret:
        print("请设置环境变量:")
        print("  export FEISHU_APP_ID=cli_xxxxxxxx")
        print("  export FEISHU_APP_SECRET=xxxxxxxx")
        print()
        print("然后重新运行此脚本。")
        sys.exit(1)

    token = get_tenant_access_token(app_id, app_secret)
    bot = get_bot_info(token)

    name = bot.get("app_name", "unknown")
    open_id = bot.get("open_id", "unknown")

    print(f"机器人名称: {name}")
    print(f"open_id:    {open_id}")
    print()
    print(f"FEISHU_BOT_REGISTRY 配置示例:")
    print(f'  FEISHU_BOT_REGISTRY={{"{name}": "{open_id}"}}')


if __name__ == "__main__":
    main()
