"""
Patch feishu.py to support outbound @mention -> <at> tag conversion.

Adds bot-to-bot @mention support by:
1. Loading a bot registry from FEISHU_BOT_REGISTRY env var (JSON)
2. Converting @BotName text to <at> tags in outgoing messages

Usage:
  python feishu_at_patch.py /path/to/feishu.py

Env var format:
  FEISHU_BOT_REGISTRY='{"AgentA": "ou_xxx", "AgentB": "ou_yyy"}'
"""

import sys

PATCH_MARKER = "# -- feishu-at-patch v1 --"

REGISTRY_INIT_BLOCK = """
        --MARKER--
        # Bot registry for outbound @mention -> <at> tag conversion.
        # Loaded from FEISHU_BOT_REGISTRY env var: '{"BotName": "ou_xxx", ...}'
        self._at_registry: dict[str, str] = {}
        self._at_pattern: re.Pattern | None = None
        self._load_at_registry()"""

LOAD_REGISTRY_METHOD = '''    --MARKER--
    def _load_at_registry(self) -> None:
        """Load bot name->open_id registry from FEISHU_BOT_REGISTRY env var."""
        raw = os.getenv("FEISHU_BOT_REGISTRY", "").strip()
        if not raw:
            return
        try:
            registry = json.loads(raw)
            if not isinstance(registry, dict):
                logger.warning("[Feishu] FEISHU_BOT_REGISTRY must be a JSON object, got %s", type(registry).__name__)
                return
            self._at_registry = {k.lower(): v for k, v in registry.items() if v}
            if self._at_registry:
                escaped = [re.escape(name) for name in self._at_registry]
                pattern = "@(" + "|".join(escaped) + r")\\b"
                self._at_pattern = re.compile(pattern, re.IGNORECASE)
                logger.info("[Feishu] Loaded %d bot(s) for @mention conversion: %s",
                            len(self._at_registry), list(self._at_registry.keys()))
        except json.JSONDecodeError as e:
            logger.warning("[Feishu] Failed to parse FEISHU_BOT_REGISTRY: %s", e)

'''

CONVERT_MENTIONS_METHOD = '''    --MARKER--
    def _convert_mentions_at(self, content: str) -> tuple[str, str | None]:
        """Convert @BotName to Feishu <at> tags.

        Returns (msg_type, payload) if mentions were converted (post format),
        or (content, None) if no conversion needed.
        """
        if not self._at_pattern or not self._at_registry:
            return content, None

        parts = self._at_pattern.split(content)
        if len(parts) == 1:
            return content, None

        elements = []
        i = 0
        while i < len(parts):
            if parts[i]:
                elements.append({"tag": "text", "text": parts[i]})
            i += 1
            if i < len(parts):
                bot_name = parts[i]
                open_id = self._at_registry.get(bot_name.lower(), "")
                if open_id:
                    elements.append({"tag": "at", "user_id": open_id})
                else:
                    elements.append({"tag": "text", "text": f"@{bot_name}"})
                i += 1

        if not any(e.get("tag") == "at" for e in elements):
            return content, None

        payload = json.dumps(
            {"zh_cn": {"content": [elements]}},
            ensure_ascii=False,
        )
        return "post", payload

'''

NEW_OUTBOUND_METHOD = '''    --MARKER--
    def _build_outbound_payload(self, content: str) -> tuple[str, str]:
        # Convert @BotName -> <at> tags if bot registry is configured
        msg_type, at_payload = self._convert_mentions_at(content)
        if at_payload is not None:
            return msg_type, at_payload

        # Fallback: standard text/post detection
        if _MARKDOWN_HINT_RE.search(content):
            return "post", _build_markdown_post_payload(content)
        text_payload = {"text": content}
        return "text", json.dumps(text_payload, ensure_ascii=False)
'''


def patch_feishu(filepath: str) -> None:
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if PATCH_MARKER in content:
        print("Patch already applied. Skipping.")
        return

    lines = content.split("\n")

    # === Patch 1: Add _load_at_registry after self._bot_name assignment ===
    bot_name_line_idx = None
    for i, line in enumerate(lines):
        if "self._bot_name = settings.bot_name" in line:
            bot_name_line_idx = i
            break

    if bot_name_line_idx is None:
        print("ERROR: Could not find 'self._bot_name = settings.bot_name' line")
        sys.exit(1)

    init_block = REGISTRY_INIT_BLOCK.replace("--MARKER--", PATCH_MARKER)
    lines.insert(bot_name_line_idx + 1, init_block)

    # === Patch 2: Add methods before _is_self_sent_bot_message ===
    self_sent_idx = None
    for i, line in enumerate(lines):
        if "def _is_self_sent_bot_message" in line:
            self_sent_idx = i
            break

    if self_sent_idx is None:
        print("ERROR: Could not find '_is_self_sent_bot_message' method")
        sys.exit(1)

    load_method = LOAD_REGISTRY_METHOD.replace("--MARKER--", PATCH_MARKER)
    convert_method = CONVERT_MENTIONS_METHOD.replace("--MARKER--", PATCH_MARKER)
    methods_block = load_method + convert_method
    lines.insert(self_sent_idx, methods_block)

    # === Patch 3: Replace _build_outbound_payload method ===
    outbound_idx = None
    for i, line in enumerate(lines):
        if "def _build_outbound_payload(self, content: str)" in line:
            outbound_idx = i
            break

    if outbound_idx is None:
        print("ERROR: Could not find '_build_outbound_payload' method")
        sys.exit(1)

    method_start = outbound_idx
    method_end = method_start + 1
    while method_end < len(lines):
        line = lines[method_end]
        stripped = line.lstrip()
        if stripped and not line.startswith("        ") and not line.startswith("\t\t"):
            break
        if line.startswith("    (async )?def ") or (line.startswith("    def ") and method_end > method_start):
            break
        method_end += 1

    new_method = NEW_OUTBOUND_METHOD.replace("--MARKER--", PATCH_MARKER)
    lines[method_start:method_end] = new_method.rstrip("\n").split("\n")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Patch applied successfully to {filepath}")
    print()
    print("Next steps:")
    print("1. Get each bot's open_id (run: python scripts/get_bot_open_id.py)")
    print()
    print("2. Set FEISHU_BOT_REGISTRY in each agent's .env:")
    print('   FEISHU_BOT_REGISTRY={"AgentA": "ou_xxx", "AgentB": "ou_yyy"}')
    print()
    print("3. Add collaboration protocol to each agent's SOUL.md")
    print("   See examples/collaboration-protocol.md")
    print()
    print("4. Restart Hermes gateway:")
    print("   systemctl --user restart hermes-gateway")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} /path/to/feishu.py")
        sys.exit(1)
    patch_feishu(sys.argv[1])
