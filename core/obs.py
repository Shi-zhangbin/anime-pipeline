"""
core/obs.py — Huawei Cloud OBS utility for reference image hosting.

Upload local reference images to OBS so wuyinkeji can fetch them by public URL.

Usage:
    python3 -m core.obs upload <local_path> <remote_key>
    python3 -m core.obs list [prefix]
    python3 -m core.obs url <remote_key>
"""
import os
import sys
import logging
from typing import Optional

from obs import ObsClient
from core.config import (
    OBS_ACCESS_KEY_ID,
    OBS_SECRET_ACCESS_KEY,
    OBS_ENDPOINT,
    OBS_BUCKET,
    OBS_DOMAIN,
)

logger = logging.getLogger(__name__)


def get_client() -> Optional[ObsClient]:
    """Initialize and return an OBS client. Returns None if credentials missing."""
    if not OBS_ACCESS_KEY_ID or not OBS_SECRET_ACCESS_KEY:
        logger.warning("OBS credentials not configured")
        return None
    return ObsClient(
        access_key_id=OBS_ACCESS_KEY_ID,
        secret_access_key=OBS_SECRET_ACCESS_KEY,
        server=OBS_ENDPOINT,
    )


def upload_file(
    client: ObsClient,
    local_path: str,
    remote_key: str,
    content_type: Optional[str] = None,
    public_read: bool = True,
) -> Optional[str]:
    """Upload a local file to OBS and return its public URL."""
    if not os.path.exists(local_path):
        logger.error(f"Local file not found: {local_path}")
        return None

    if content_type is None:
        ext = os.path.splitext(local_path)[1].lower()
        content_type = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".svg": "image/svg+xml",
        }.get(ext, "application/octet-stream")

    try:
        resp = client.putFile(
            bucketName=OBS_BUCKET,
            objectKey=remote_key,
            file_path=os.path.abspath(local_path),
        )
        status = getattr(
            resp, "status", resp.get("status", 500) if isinstance(resp, dict) else 500
        )
        if status >= 300:
            logger.error(f"Upload failed (status {status}): {resp}")
            return None

        if public_read:
            try:
                client.setObjectAcl(
                    bucketName=OBS_BUCKET,
                    objectKey=remote_key,
                    acl="public-read",
                )
            except Exception:
                pass

        public_url = f"https://{OBS_DOMAIN}/{remote_key}"
        logger.info(f"Uploaded: {local_path} → {public_url}")
        return public_url

    except Exception as e:
        logger.error(f"Upload error: {e}")
        return None


def list_objects(client: ObsClient, prefix: str = "", max_keys: int = 100) -> list[dict]:
    """List objects under a prefix."""
    try:
        resp = client.listObjects(
            bucketName=OBS_BUCKET, prefix=prefix, max_keys=max_keys
        )
        if resp.status >= 300:
            logger.error(f"List failed (status {resp.status})")
            return []
        return [
            {
                "key": c.key,
                "size": c.size,
                "last_modified": str(c.last_modified),
                "url": f"https://{OBS_DOMAIN}/{c.key}",
            }
            for c in resp.body.contents
        ]
    except Exception as e:
        logger.error(f"List error: {e}")
        return []


def get_public_url(remote_key: str) -> str:
    """Get the public URL for a remote key."""
    return f"https://{OBS_DOMAIN}/{remote_key}"


def upload_reference(local_path: str, remote_key: str) -> Optional[str]:
    """Convenience wrapper: upload a reference image and return its public URL."""
    client = get_client()
    if not client:
        print("OBS not configured; skipping upload.")
        return None
    url = upload_file(client, local_path, remote_key, public_read=True)
    if url:
        print(f"  ☁️  Reference uploaded: {url}")
    else:
        print("  ⚠️  Upload failed")
    return url


# ══════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════

def _cli_upload(args: list[str]):
    if len(args) < 2:
        print("Usage: python3 -m core.obs upload <local_path> <remote_key>")
        sys.exit(1)
    client = get_client()
    if not client:
        print("ERROR: OBS not configured. Check .env")
        sys.exit(1)
    url = upload_file(client, args[0], args[1])
    print(f"OK: {url}" if url else "FAILED")
    sys.exit(0 if url else 1)


def _cli_list(args: list[str]):
    prefix = args[0] if args else ""
    client = get_client()
    if not client:
        print("ERROR: OBS not configured. Check .env")
        sys.exit(1)
    objects = list_objects(client, prefix=prefix)
    if not objects:
        print("(empty)")
        return
    for obj in objects:
        print(f"{obj['key']:60s} {obj['size']:>10,}  {obj['last_modified']}")


def _cli_url(args: list[str]):
    if not args:
        print("Usage: python3 -m core.obs url <remote_key>")
        sys.exit(1)
    print(get_public_url(args[0]))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:]
    commands = {
        "upload": _cli_upload,
        "list": _cli_list,
        "url": _cli_url,
    }
    handler = commands.get(command)
    if not handler:
        print(f"Unknown command: {command}")
        print("Available: upload, list, url")
        sys.exit(1)
    handler(args)


if __name__ == "__main__":
    main()
