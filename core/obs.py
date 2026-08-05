"""
core/obs.py — Huawei Cloud OBS utility for reference image hosting.

Upload local reference images to OBS so wuyinkeji can fetch them by public URL.

Usage:
    python3 -m core.obs upload <local_path> <remote_key>
    python3 -m core.obs list [prefix]
    python3 -m core.obs url <remote_key>
    python3 -m core.obs set-lifecycle <prefix> <days>
"""
import os
import sys
import logging
from typing import Optional

from obs import ObsClient, Rule, Lifecycle, Expiration
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


def delete_object(client: ObsClient, remote_key: str) -> bool:
    """Delete a single object from OBS."""
    try:
        resp = client.deleteObject(bucketName=OBS_BUCKET, objectKey=remote_key)
        if resp.status >= 300:
            logger.error(f"Delete failed for {remote_key} (status {resp.status})")
            return False
        logger.info(f"Deleted: {remote_key}")
        return True
    except Exception as e:
        logger.error(f"Delete error for {remote_key}: {e}")
        return False


def delete_prefix(client: ObsClient, prefix: str) -> tuple[int, int]:
    """
    Delete all objects under a prefix.

    Returns:
        (success_count, fail_count)
    """
    success = 0
    failed = 0
    marker = ""
    while True:
        try:
            resp = client.listObjects(
                bucketName=OBS_BUCKET,
                prefix=prefix,
                max_keys=1000,
                marker=marker,
            )
            if resp.status >= 300:
                logger.error(f"List failed during delete (status {resp.status})")
                break
            contents = resp.body.contents if resp.body else []
            for obj in contents:
                if delete_object(client, obj.key):
                    success += 1
                else:
                    failed += 1
            if not resp.body.is_truncated:
                break
            marker = resp.body.next_marker
        except Exception as e:
            logger.error(f"Delete prefix error: {e}")
            break
    return success, failed


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


def get_lifecycle_rules(client: ObsClient, bucket_name: str) -> list[Rule]:
    """Get existing lifecycle rules from bucket."""
    try:
        resp = client.getBucketLifecycle(bucketName=bucket_name)
        if resp.status >= 300:
            logger.warning(f"Failed to get lifecycle rules (status {resp.status})")
            return []
        return list(getattr(resp.body, "lifecycle_config", None) or [])
    except Exception as e:
        logger.warning(f"Could not fetch lifecycle rules: {e}")
        return []


def set_lifecycle_rules(client: ObsClient, bucket_name: str, rules: list[Rule]) -> bool:
    """Replace lifecycle rules on bucket."""
    try:
        lifecycle = Lifecycle(rule=rules)
        resp = client.setBucketLifecycle(bucketName=bucket_name, lifecycle=lifecycle)
        if resp.status >= 300:
            logger.error(f"Set lifecycle failed (status {resp.status}): {resp}")
            return False
        return True
    except Exception as e:
        logger.error(f"Set lifecycle error: {e}")
        return False


def set_auto_delete_prefix(
    client: ObsClient,
    bucket_name: str,
    prefix: str,
    days: int,
    rule_id: str = "auto-delete",
) -> bool:
    """
    Add/upsert a lifecycle rule that auto-deletes objects under `prefix`
    after `days` days.
    """
    rules = get_lifecycle_rules(client, bucket_name)
    # Remove any existing rule with same id to avoid duplicates
    rules = [r for r in rules if getattr(r, "id", None) != rule_id]

    rule = Rule(id=rule_id, prefix=prefix, status="Enabled")
    rule.expiration = Expiration(days=days)
    rules.append(rule)

    return set_lifecycle_rules(client, bucket_name, rules)


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


def _cli_delete(args: list[str]):
    if not args:
        print("Usage: python3 -m core.obs delete <remote_key>")
        print("       python3 -m core.obs delete-prefix <prefix>")
        sys.exit(1)
    client = get_client()
    if not client:
        print("ERROR: OBS not configured. Check .env")
        sys.exit(1)
    remote_key = args[0]
    if delete_object(client, remote_key):
        print(f"OK: deleted {remote_key}")
        sys.exit(0)
    else:
        print(f"FAILED: {remote_key}")
        sys.exit(1)


def _cli_delete_prefix(args: list[str]):
    prefix = args[0] if args else ""
    client = get_client()
    if not client:
        print("ERROR: OBS not configured. Check .env")
        sys.exit(1)
    print(f"Deleting all objects under prefix: {prefix!r}")
    success, failed = delete_prefix(client, prefix)
    print(f"Done. Deleted: {success}, Failed: {failed}")
    sys.exit(0 if failed == 0 else 1)


def _cli_set_lifecycle(args: list[str]):
    if len(args) < 2:
        print("Usage: python3 -m core.obs set-lifecycle <prefix> <days>")
        print("       python3 -m core.obs set-lifecycle 动漫制作/ 7")
        sys.exit(1)
    prefix = args[0]
    try:
        days = int(args[1])
    except ValueError:
        print("ERROR: <days> must be an integer")
        sys.exit(1)
    if days < 1:
        print("ERROR: <days> must be >= 1")
        sys.exit(1)

    client = get_client()
    if not client:
        print("ERROR: OBS not configured. Check .env")
        sys.exit(1)

    rule_id = f"auto-delete-{prefix.rstrip('/').replace('/', '-') or 'all'}"
    print(f"Setting lifecycle rule: prefix={prefix!r}, days={days}, id={rule_id}")
    if set_auto_delete_prefix(client, OBS_BUCKET, prefix, days, rule_id=rule_id):
        print(f"OK: objects under {prefix!r} will be auto-deleted after {days} days")
        sys.exit(0)
    else:
        print("FAILED")
        sys.exit(1)


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
        "delete": _cli_delete,
        "delete-prefix": _cli_delete_prefix,
        "set-lifecycle": _cli_set_lifecycle,
    }
    handler = commands.get(command)
    if not handler:
        print(f"Unknown command: {command}")
        print("Available: upload, list, url, delete, delete-prefix, set-lifecycle")
        sys.exit(1)
    handler(args)


if __name__ == "__main__":
    main()
