# ElectrsRocksDBBackgroundErrors

**Alerts:** `ElectrsRocksDBBackgroundErrors`  
**Severity:** critical

A RocksDB flush or compaction failed in one of electrs's databases.

## Impact

RocksDB may switch the database to read-only, which stops indexing.

## Triage

1. electrs log and the RocksDB `LOG` file in that database's directory for the error.
2. Disk space and kernel I/O errors (`dmesg`).

## Likely causes

Disk full, I/O errors from failing or network storage, or file-descriptor exhaustion.

## Mitigation

Fix the disk or limit, then restart electrs so RocksDB reopens the database. Never delete files from the database directory by hand.

## Escalate when

I/O errors from the device, or the database fails to reopen.

## Handoff

Use the [handoff note](README.md#handoff-note).
