"""
core/obs.py — 华为云 OBS 工具（转发 shim）

实现已收敛到全局唯一真相源：~/.agents/skills/wuyinkeji-imagegen/scripts/obs_util.py
本文件只做转发，不含实现。
"""
import os
import sys

sys.path.insert(0, os.path.join(
    os.environ.get("AGENT_SKILLS_HOME", os.path.expanduser("~/.agents/skills")),
    "wuyinkeji-imagegen", "scripts"))

from obs_util import (  # noqa: F401,E402
    get_client,
    upload_file,
    upload_reference,
    build_temp_key,
    list_objects,
    delete_object,
    get_public_url,
    ensure_lifecycle_rule,
    get_lifecycle_rules,
)

if __name__ == "__main__":
    # CLI 透传到 canonical；兼容旧命令 set-lifecycle <prefix> <days>
    import obs_util

    if len(sys.argv) > 1 and sys.argv[1] == "set-lifecycle":
        sys.argv = [sys.argv[0], "lifecycle", "ensure"] + sys.argv[2:]
    obs_util.main()
