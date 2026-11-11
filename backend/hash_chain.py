"""Cryptographic SHA-256 hash-chain audit engine for tamper-evident MRV records."""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import sqlite3


GENESIS_HASH = "0" * 64


def canonical_json(obj: Any) -> str:
    """Produce deterministic canonical JSON so hashes are 100% reproducible."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compute_record_hash(
    prev_hash: str,
    farm_id: str,
    event_type: str,
    timestamp: str,
    payload_json: str,
) -> str:
    """Compute SHA-256 over previous hash + canonical record fields."""
    preimage = f"{prev_hash}|{farm_id}|{event_type}|{timestamp}|{payload_json}"
    return hashlib.sha256(preimage.encode("utf-8")).hexdigest()


def append_audit_event(
    conn: sqlite3.Connection,
    farm_id: str,
    event_type: str,
    payload: Dict[str, Any],
    timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    """Append a tamper-evident block to the farm's SHA-256 hash chain."""
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    row = conn.execute(
        "SELECT record_hash FROM audit_chain WHERE farm_id = ? ORDER BY seq_id DESC LIMIT 1",
        (farm_id,),
    ).fetchone()
    prev_hash = row["record_hash"] if row else GENESIS_HASH
    payload_str = canonical_json(payload)
    record_hash = compute_record_hash(prev_hash, farm_id, event_type, ts, payload_str)

    cur = conn.execute(
        """
        INSERT INTO audit_chain (farm_id, event_type, payload_json, prev_hash, record_hash, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (farm_id, event_type, payload_str, prev_hash, record_hash, ts),
    )
    return {
        "seq_id": cur.lastrowid,
        "farm_id": farm_id,
        "event_type": event_type,
        "payload": payload,
        "prev_hash": prev_hash,
        "record_hash": record_hash,
        "timestamp": ts,
    }


def verify_farm_chain(
    conn: sqlite3.Connection,
    farm_id: str,
    simulate_tamper_seq: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Walk every block in the farm's audit chain from genesis to head hash.
    If `simulate_tamper_seq` is specified (for live judge demonstrations), a copy of
    that block's payload is mutated in-memory during verification so the judge can
    observe exact cryptographic link failure without corrupting stored evidence.
    """
    rows = conn.execute(
        "SELECT seq_id, farm_id, event_type, payload_json, prev_hash, record_hash, timestamp "
        "FROM audit_chain WHERE farm_id = ? ORDER BY seq_id ASC",
        (farm_id,),
    ).fetchall()

    if not rows:
        return {
            "farm_id": farm_id,
            "verified": False,
            "block_count": 0,
            "head_hash": None,
            "broken_at_seq": None,
            "tamper_simulated": False,
            "blocks": [],
            "message": "No audit blocks recorded for this farm.",
        }

    expected_prev = GENESIS_HASH
    broken_at_seq = None
    failure_reason = None
    blocks: List[Dict[str, Any]] = []

    for idx, r in enumerate(rows):
        payload_str = r["payload_json"]
        tampered_here = False
        if simulate_tamper_seq is not None and (r["seq_id"] == simulate_tamper_seq or (idx + 1) == simulate_tamper_seq):
            # Mutate a single digit/field in-memory to simulate post-issuance tampering
            payload_obj = json.loads(payload_str)
            payload_obj["_tampered_field_demo"] = "INFLATED_+50.0_tCO2e"
            payload_str = canonical_json(payload_obj)
            tampered_here = True

        recomputed_hash = compute_record_hash(
            expected_prev,
            r["farm_id"],
            r["event_type"],
            r["timestamp"],
            payload_str,
        )
        prev_matches = r["prev_hash"] == expected_prev
        hash_matches = recomputed_hash == r["record_hash"]
        block_valid = prev_matches and hash_matches

        if not block_valid and broken_at_seq is None:
            broken_at_seq = idx + 1
            failure_reason = (
                f"Block #{idx + 1} ({r['event_type']}) hash mismatch! "
                f"Stored {r['record_hash'][:12]}... != Recomputed {recomputed_hash[:12]}..."
            )

        blocks.append(
            {
                "index": idx + 1,
                "seq_id": r["seq_id"],
                "event_type": r["event_type"],
                "timestamp": r["timestamp"],
                "prev_hash": r["prev_hash"],
                "stored_hash": r["record_hash"],
                "recomputed_hash": recomputed_hash,
                "valid": block_valid,
                "tampered_demo": tampered_here,
                "payload": json.loads(r["payload_json"]),
            }
        )
        expected_prev = r["record_hash"]

    verified = broken_at_seq is None
    return {
        "farm_id": farm_id,
        "verified": verified,
        "block_count": len(blocks),
        "head_hash": rows[-1]["record_hash"],
        "broken_at_seq": broken_at_seq,
        "tamper_simulated": simulate_tamper_seq is not None,
        "blocks": blocks,
        "message": (
            f"All {len(blocks)} SHA-256 blocks verified intact from GENESIS to HEAD."
            if verified
            else failure_reason
        ),
    }

