"""
Dry-run and cleanup utility for orphaned uploaded images.

This script scans the image bucket for objects whose DynamoDB metadata is
missing, expired, or inconsistent. It defaults to dry-run mode and only
deletes objects when --delete is provided explicitly.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import boto3

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.env import Config


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)


@dataclass(frozen=True)
class CleanupCandidate:
    key: str
    reason: str
    last_modified: str
    session_id: Optional[str] = None
    image_id: Optional[str] = None


def extract_image_identity(s3_key: str) -> tuple[Optional[str], Optional[str]]:
    """Extract the session ID and image ID from a canonical upload key."""
    if not s3_key or "/" not in s3_key:
        return None, None

    session_id, filename = s3_key.split("/", 1)
    if not session_id or "." not in filename:
        return None, None

    image_id, _, extension = filename.partition(".")
    if not image_id.startswith("img_") or not extension:
        return None, None

    return session_id, image_id


def object_is_past_grace_period(
    last_modified: datetime,
    grace_period_minutes: int,
    now: Optional[datetime] = None,
) -> bool:
    """Skip very recent uploads so in-flight writes are not treated as orphaned."""
    current_time = now or datetime.now(timezone.utc)
    if last_modified.tzinfo is None:
        last_modified = last_modified.replace(tzinfo=timezone.utc)

    threshold = current_time - timedelta(minutes=grace_period_minutes)
    return last_modified <= threshold


def get_metadata_item(sessions_table: Any, session_id: str, image_id: str) -> Optional[dict[str, Any]]:
    """Load the image metadata record from the sessions table."""
    response = sessions_table.get_item(
        Key={
            "session_id": session_id,
            "data_type": f"image#{image_id}",
        }
    )
    return response.get("Item")


def classify_cleanup_candidate(
    s3_object: dict[str, Any],
    sessions_table: Any,
    grace_period_minutes: int,
    now: Optional[datetime] = None,
) -> Optional[CleanupCandidate]:
    """Classify a single object as an orphan cleanup candidate, if applicable."""
    current_time = now or datetime.now(timezone.utc)
    key = s3_object["Key"]
    last_modified = s3_object["LastModified"]

    if not object_is_past_grace_period(last_modified, grace_period_minutes, current_time):
        return None

    last_modified_iso = last_modified.astimezone(timezone.utc).isoformat()
    session_id, image_id = extract_image_identity(key)
    if not session_id or not image_id:
        return CleanupCandidate(
            key=key,
            reason="invalid_key_format",
            last_modified=last_modified_iso,
        )

    metadata = get_metadata_item(sessions_table, session_id, image_id)
    if not metadata:
        return CleanupCandidate(
            key=key,
            reason="missing_metadata",
            last_modified=last_modified_iso,
            session_id=session_id,
            image_id=image_id,
        )

    if metadata.get("s3_key") != key:
        return CleanupCandidate(
            key=key,
            reason="metadata_key_mismatch",
            last_modified=last_modified_iso,
            session_id=session_id,
            image_id=image_id,
        )

    expiry_timestamp = metadata.get("expiry_timestamp")
    if expiry_timestamp is None:
        return CleanupCandidate(
            key=key,
            reason="missing_metadata_expiry",
            last_modified=last_modified_iso,
            session_id=session_id,
            image_id=image_id,
        )

    try:
        expiry_timestamp_int = int(expiry_timestamp)
    except (TypeError, ValueError, OverflowError):
        return CleanupCandidate(
            key=key,
            reason="invalid_metadata_expiry",
            last_modified=last_modified_iso,
            session_id=session_id,
            image_id=image_id,
        )

    if expiry_timestamp_int <= int(current_time.timestamp()):
        return CleanupCandidate(
            key=key,
            reason="metadata_expired",
            last_modified=last_modified_iso,
            session_id=session_id,
            image_id=image_id,
        )

    return None


def find_cleanup_candidates(
    s3_client: Any,
    sessions_table: Any,
    bucket: str,
    grace_period_minutes: int = 15,
    max_objects: Optional[int] = None,
    now: Optional[datetime] = None,
) -> tuple[list[CleanupCandidate], int]:
    """Scan the bucket and return orphaned image candidates plus the scan count."""
    paginator = s3_client.get_paginator("list_objects_v2")
    candidates: list[CleanupCandidate] = []
    scanned_objects = 0

    for page in paginator.paginate(Bucket=bucket):
        for s3_object in page.get("Contents", []):
            scanned_objects += 1
            candidate = classify_cleanup_candidate(
                s3_object=s3_object,
                sessions_table=sessions_table,
                grace_period_minutes=grace_period_minutes,
                now=now,
            )
            if candidate:
                candidates.append(candidate)

            if max_objects is not None and scanned_objects >= max_objects:
                return candidates, scanned_objects

    return candidates, scanned_objects


def execute_cleanup(
    s3_client: Any,
    bucket: str,
    candidates: list[CleanupCandidate],
    delete: bool = False,
) -> dict[str, Any]:
    """Delete cleanup candidates when requested and return a structured summary."""
    deleted_keys: list[str] = []
    failed_deletions: list[dict[str, str]] = []

    for candidate in candidates:
        if not delete:
            continue

        try:
            s3_client.delete_object(Bucket=bucket, Key=candidate.key)
            deleted_keys.append(candidate.key)
            logger.info("Deleted orphaned image: key=%s reason=%s", candidate.key, candidate.reason)
        except Exception as exc:  # pragma: no cover - boto errors are mocked in tests
            logger.error(
                "Failed to delete orphaned image: key=%s reason=%s error=%s",
                candidate.key,
                candidate.reason,
                exc,
            )
            failed_deletions.append({"key": candidate.key, "error": str(exc)})

    return {
        "candidates_found": len(candidates),
        "deleted_count": len(deleted_keys),
        "failed_deletions": failed_deletions,
        "deleted_keys": deleted_keys,
    }


def run_cleanup(
    bucket: str,
    sessions_table_name: str,
    region: str,
    grace_period_minutes: int = 15,
    max_objects: Optional[int] = None,
    delete: bool = False,
) -> dict[str, Any]:
    """Run a full orphan scan using live AWS clients."""
    s3_client = boto3.client("s3", region_name=region)
    dynamodb = boto3.resource("dynamodb", region_name=region)
    sessions_table = dynamodb.Table(sessions_table_name)

    candidates, scanned_objects = find_cleanup_candidates(
        s3_client=s3_client,
        sessions_table=sessions_table,
        bucket=bucket,
        grace_period_minutes=grace_period_minutes,
        max_objects=max_objects,
    )
    cleanup_summary = execute_cleanup(
        s3_client=s3_client,
        bucket=bucket,
        candidates=candidates,
        delete=delete,
    )

    return {
        "bucket": bucket,
        "sessions_table": sessions_table_name,
        "region": region,
        "mode": "delete" if delete else "dry-run",
        "grace_period_minutes": grace_period_minutes,
        "scanned_objects": scanned_objects,
        "candidates": [asdict(candidate) for candidate in candidates],
        **cleanup_summary,
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Scan for orphaned uploaded images.")
    parser.add_argument("--bucket", default=Config.IMAGE_BUCKET, help="S3 bucket to scan")
    parser.add_argument(
        "--sessions-table",
        default=Config.SESSIONS_TABLE,
        help="DynamoDB sessions table that stores image metadata",
    )
    parser.add_argument("--region", default=Config.AWS_REGION, help="AWS region for S3 and DynamoDB")
    parser.add_argument(
        "--grace-period-minutes",
        type=int,
        default=15,
        help="Ignore objects newer than this many minutes",
    )
    parser.add_argument(
        "--max-objects",
        type=int,
        default=None,
        help="Stop scanning after this many objects (for spot checks)",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete orphaned objects instead of only reporting them",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of human-readable output",
    )
    return parser.parse_args()


def main() -> int:
    """Entry point for the orphan cleanup utility."""
    args = parse_args()
    if not args.bucket:
        raise ValueError("An image bucket is required. Set IMAGE_BUCKET or pass --bucket.")
    if not args.sessions_table:
        raise ValueError("A sessions table is required. Set SESSIONS_TABLE or pass --sessions-table.")
    if args.grace_period_minutes < 0:
        raise ValueError("--grace-period-minutes must be zero or greater.")

    summary = run_cleanup(
        bucket=args.bucket,
        sessions_table_name=args.sessions_table,
        region=args.region,
        grace_period_minutes=args.grace_period_minutes,
        max_objects=args.max_objects,
        delete=args.delete,
    )

    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(f"Bucket: {summary['bucket']}")
        print(f"Sessions table: {summary['sessions_table']}")
        print(f"Mode: {summary['mode']}")
        print(f"Scanned objects: {summary['scanned_objects']}")
        print(f"Cleanup candidates: {summary['candidates_found']}")
        print(f"Deleted: {summary['deleted_count']}")
        if summary["failed_deletions"]:
            print(f"Failed deletions: {len(summary['failed_deletions'])}")
        if summary["candidates"]:
            print("Candidates:")
            for candidate in summary["candidates"]:
                print(
                    f"  - key={candidate['key']} reason={candidate['reason']} "
                    f"last_modified={candidate['last_modified']}"
                )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
