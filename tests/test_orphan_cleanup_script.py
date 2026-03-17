from datetime import datetime, timedelta, timezone

from scripts.cleanup_orphan_images import (
    classify_cleanup_candidate,
    execute_cleanup,
    extract_image_identity,
    find_cleanup_candidates,
)


class FakePaginator:
    def __init__(self, pages):
        self._pages = pages

    def paginate(self, Bucket):
        return self._pages


class FakeS3Client:
    def __init__(self, pages):
        self._pages = pages
        self.deleted = []

    def get_paginator(self, operation_name):
        assert operation_name == "list_objects_v2"
        return FakePaginator(self._pages)

    def delete_object(self, Bucket, Key):
        self.deleted.append((Bucket, Key))


class FakeSessionsTable:
    def __init__(self, items):
        self._items = items

    def get_item(self, Key):
        item = self._items.get((Key["session_id"], Key["data_type"]))
        return {"Item": item} if item else {}


def test_extract_image_identity_accepts_canonical_key():
    session_id, image_id = extract_image_identity("sess_123/img_abc123.jpg")

    assert session_id == "sess_123"
    assert image_id == "img_abc123"


def test_extract_image_identity_rejects_unexpected_key():
    session_id, image_id = extract_image_identity("bad-key")

    assert session_id is None
    assert image_id is None


def test_classify_cleanup_candidate_flags_missing_metadata():
    now = datetime.now(timezone.utc)
    table = FakeSessionsTable(items={})
    s3_object = {
        "Key": "sess_123/img_abc123.jpg",
        "LastModified": now - timedelta(minutes=30),
    }

    candidate = classify_cleanup_candidate(
        s3_object=s3_object,
        sessions_table=table,
        grace_period_minutes=15,
        now=now,
    )

    assert candidate is not None
    assert candidate.reason == "missing_metadata"


def test_classify_cleanup_candidate_ignores_recent_objects():
    now = datetime.now(timezone.utc)
    table = FakeSessionsTable(items={})
    s3_object = {
        "Key": "sess_123/img_abc123.jpg",
        "LastModified": now - timedelta(minutes=5),
    }

    candidate = classify_cleanup_candidate(
        s3_object=s3_object,
        sessions_table=table,
        grace_period_minutes=15,
        now=now,
    )

    assert candidate is None


def test_find_cleanup_candidates_reports_only_orphans():
    now = datetime.now(timezone.utc)
    s3_client = FakeS3Client(
        pages=[
            {
                "Contents": [
                    {
                        "Key": "sess_123/img_missing.jpg",
                        "LastModified": now - timedelta(minutes=60),
                    },
                    {
                        "Key": "sess_123/img_ok.jpg",
                        "LastModified": now - timedelta(minutes=60),
                    },
                ]
            }
        ]
    )
    table = FakeSessionsTable(
        items={
            (
                "sess_123",
                "image#img_ok",
            ): {
                "session_id": "sess_123",
                "data_type": "image#img_ok",
                "s3_key": "sess_123/img_ok.jpg",
                "expiry_timestamp": int((now + timedelta(hours=1)).timestamp()),
            }
        }
    )

    candidates, scanned_objects = find_cleanup_candidates(
        s3_client=s3_client,
        sessions_table=table,
        bucket="bucket",
        grace_period_minutes=15,
        now=now,
    )

    assert scanned_objects == 2
    assert [candidate.key for candidate in candidates] == ["sess_123/img_missing.jpg"]


def test_execute_cleanup_deletes_candidates_only_when_requested():
    s3_client = FakeS3Client(pages=[])
    candidates = [
        classify_cleanup_candidate(
            s3_object={
                "Key": "sess_123/img_missing.jpg",
                "LastModified": datetime.now(timezone.utc) - timedelta(minutes=60),
            },
            sessions_table=FakeSessionsTable(items={}),
            grace_period_minutes=15,
            now=datetime.now(timezone.utc),
        )
    ]
    candidates = [candidate for candidate in candidates if candidate is not None]

    dry_run_summary = execute_cleanup(
        s3_client=s3_client,
        bucket="bucket",
        candidates=candidates,
        delete=False,
    )
    delete_summary = execute_cleanup(
        s3_client=s3_client,
        bucket="bucket",
        candidates=candidates,
        delete=True,
    )

    assert dry_run_summary["deleted_count"] == 0
    assert delete_summary["deleted_count"] == 1
    assert s3_client.deleted == [("bucket", "sess_123/img_missing.jpg")]
