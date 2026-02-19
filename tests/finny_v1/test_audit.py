"""Tests for Finny V1 audit logger."""

from __future__ import annotations

import os
import tempfile

import pytest

from p2p_agents.finny_v1.audit import AuditLogger


@pytest.fixture
def audit_logger():
    """Create a temporary audit logger for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    logger = AuditLogger(db_path=path)
    yield logger
    os.unlink(path)


class TestAuditLogger:
    def test_new_correlation_id_unique(self):
        id1 = AuditLogger.new_correlation_id()
        id2 = AuditLogger.new_correlation_id()
        assert id1 != id2

    def test_log_query_and_get(self, audit_logger):
        cid = audit_logger.new_correlation_id()
        audit_logger.log_query(
            correlation_id=cid,
            user_id="U001",
            query_text="What is the status of INV-2024-001?",
            query_type="payment_status",
        )

        log = audit_logger.get_log(cid)
        assert log is not None
        assert log["user_id"] == "U001"
        assert log["query_text"] == "What is the status of INV-2024-001?"
        assert log["query_type"] == "payment_status"

    def test_log_response_updates(self, audit_logger):
        cid = audit_logger.new_correlation_id()
        audit_logger.log_query(
            correlation_id=cid,
            user_id="U001",
            query_text="test query",
        )
        audit_logger.log_response(
            correlation_id=cid,
            response_status="ok",
            netsuite_records=["1001", "1002"],
        )

        log = audit_logger.get_log(cid)
        assert log["response_status"] == "ok"
        assert "1001" in log["netsuite_records"]

    def test_log_response_with_error(self, audit_logger):
        cid = audit_logger.new_correlation_id()
        audit_logger.log_query(
            correlation_id=cid,
            user_id="U002",
            query_text="bad query",
        )
        audit_logger.log_response(
            correlation_id=cid,
            response_status="error",
            error_message="Connection refused",
        )

        log = audit_logger.get_log(cid)
        assert log["response_status"] == "error"
        assert log["error_message"] == "Connection refused"

    def test_get_nonexistent_log(self, audit_logger):
        log = audit_logger.get_log("nonexistent-id")
        assert log is None

    def test_correlation_id_links_query_to_response(self, audit_logger):
        cid = audit_logger.new_correlation_id()

        audit_logger.log_query(
            correlation_id=cid,
            user_id="U001",
            query_text="status of INV-001",
        )
        audit_logger.log_response(
            correlation_id=cid,
            response_status="ok",
            netsuite_records=["5001"],
        )

        log = audit_logger.get_log(cid)
        # Both query and response fields should be populated
        assert log["user_id"] == "U001"
        assert log["query_text"] == "status of INV-001"
        assert log["response_status"] == "ok"
        assert "5001" in log["netsuite_records"]
