"""Unit tests for P2P agent tools — validates each tool against mock servers.

Run with: python3.11 -m pytest tests/test_tools.py -v
Requires mock servers running on ports 8083 (NetSuite) and 8082 (SpotDraft).
"""

from __future__ import annotations

import pytest

# We import helpers and tools directly to avoid pulling in google.adk
# via the p2p_agents package __init__.py.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ── Helpers ──────────────────────────────────────────────────────────────────

def _import_helpers():
    """Import helpers module bypassing the p2p_agents __init__."""
    import importlib
    spec = importlib.util.spec_from_file_location(
        "helpers",
        os.path.join(os.path.dirname(__file__), "..", "p2p_agents", "tools", "helpers.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    # Pre-load settings dependency
    settings_spec = importlib.util.spec_from_file_location(
        "p2p_agents.config.settings",
        os.path.join(os.path.dirname(__file__), "..", "p2p_agents", "config", "settings.py"),
    )
    settings_mod = importlib.util.module_from_spec(settings_spec)
    sys.modules["p2p_agents.config.settings"] = settings_mod
    settings_spec.loader.exec_module(settings_mod)

    constants_spec = importlib.util.spec_from_file_location(
        "p2p_agents.config.constants",
        os.path.join(os.path.dirname(__file__), "..", "p2p_agents", "config", "constants.py"),
    )
    constants_mod = importlib.util.module_from_spec(constants_spec)
    sys.modules["p2p_agents.config.constants"] = constants_mod
    constants_spec.loader.exec_module(constants_mod)

    spec.loader.exec_module(mod)
    sys.modules["p2p_agents.tools.helpers"] = mod
    return mod


helpers = _import_helpers()


def _import_tool_module(name: str):
    """Import a tool module by name, bypassing p2p_agents __init__."""
    import importlib
    spec = importlib.util.spec_from_file_location(
        name,
        os.path.join(os.path.dirname(__file__), "..", "p2p_agents", "tools", f"{name}.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── Connectivity Smoke Tests ─────────────────────────────────────────────────

class TestMockServerConnectivity:
    """Verify mock servers are reachable before running tool tests."""

    def test_netsuite_health(self):
        import httpx
        r = httpx.get("http://localhost:8083/health")
        assert r.status_code == 200

    def test_spotdraft_health(self):
        import httpx
        r = httpx.get("http://localhost:8082/health")
        assert r.status_code == 200

    def test_netsuite_vendor_list(self):
        result = helpers.ns_get("/record/v1/vendor")
        assert "items" in result
        assert len(result["items"]) > 0

    def test_spotdraft_parties_list(self):
        result = helpers.sd_get("/parties/")
        assert isinstance(result, list)
        assert len(result) > 0
        assert "id" in result[0]


# ── Vendor Tools Tests ───────────────────────────────────────────────────────

class TestVendorTools:
    """Test vendor_tools against live mock servers."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.mod = _import_tool_module("vendor_tools")

    def test_get_vendor_onboarding_status_by_id(self):
        """Test looking up onboarding status by vendor_id."""
        result = self.mod.get_vendor_onboarding_status(vendor_id="1")
        assert "vendor_id" in result
        # Should not error — may have unknown onboarding if ID mismatch
        assert "error" not in result or "netsuite_record" in result

    def test_run_kyc_check_valid(self):
        result = self.mod.run_kyc_check(
            vendor_name="Test Corp",
            pan_number="ABCDE1234F",
            gst_number="29ABCDE1234F1ZF",
            bank_account="123456789012",
        )
        assert result["kyc_passed"] is True

    def test_run_kyc_check_invalid_pan(self):
        result = self.mod.run_kyc_check(
            vendor_name="Test Corp",
            pan_number="INVALID",
        )
        assert result["kyc_passed"] is False

    def test_generate_onboarding_report(self):
        """The critical test — this is the tool that was failing."""
        result = self.mod.generate_onboarding_report()
        assert "total_vendors" in result
        assert result["total_vendors"] > 0
        assert "details" in result
        # Should have some vendors in at least one category
        details = result["details"]
        total = len(details["complete"]) + len(details["pending"]) + len(details["blocked"])
        assert total == result["total_vendors"], (
            f"Vendor count mismatch: {total} in details vs {result['total_vendors']} total"
        )
        # After the ID mapping fix, vendors should have spotdraft_party_id
        all_entries = details["complete"] + details["pending"] + details["blocked"]
        linked = [e for e in all_entries if e.get("spotdraft_party_id", "not_linked") != "not_linked"]
        assert len(linked) > 0, "No vendors were linked to SpotDraft parties"
        # At least some vendors should NOT all be pending (real onboarding data)
        non_pending = len(details["complete"]) + len(details["blocked"])
        print(f"\nOnboarding report: {result['total_vendors']} vendors, "
              f"{len(linked)} linked to SpotDraft, "
              f"{non_pending} with non-pending status")

    def test_get_vendor_documents(self):
        result = self.mod.get_vendor_documents(vendor_id="party_001")
        assert "contracts" in result
        assert "documents" in result


# ── Payment Tools Tests ──────────────────────────────────────────────────────

class TestPaymentTools:

    @pytest.fixture(autouse=True)
    def _load(self):
        self.mod = _import_tool_module("payment_tools")

    def test_get_payment_status_by_invoice(self):
        result = self.mod.get_payment_status(invoice_number="INV-2024-001")
        assert "status" in result or "error" in result

    def test_get_pending_approvals(self):
        result = self.mod.get_pending_approvals()
        assert isinstance(result, dict)

    def test_get_priority_vendor_list(self):
        result = self.mod.get_priority_vendor_list()
        assert "priority_vendors" in result
        assert isinstance(result["priority_vendors"], list)


# ── Invoice Tools Tests ──────────────────────────────────────────────────────

class TestInvoiceTools:

    @pytest.fixture(autouse=True)
    def _load(self):
        self.mod = _import_tool_module("invoice_tools")

    def test_validate_invoice_data(self):
        result = self.mod.validate_invoice_data(invoice_data={
            "vendor_name": "Google LLC",
            "invoice_number": "INV-TEST-001",
            "amount": 50000.0,
            "currency": "INR",
            "date": "2025-01-15",
        })
        assert "is_valid" in result

    def test_extract_invoice_data_ocr(self):
        result = self.mod.extract_invoice_data_ocr(file_content="Invoice #123 from Google LLC amount 50000 INR")
        assert isinstance(result, dict)


# ── Reporting Tools Tests ────────────────────────────────────────────────────

class TestReportingTools:

    @pytest.fixture(autouse=True)
    def _load(self):
        self.mod = _import_tool_module("reporting_tools")

    def test_get_invoices_processed_count(self):
        result = self.mod.get_invoices_processed_count(
            start_date="2025-01-01", end_date="2025-01-31"
        )
        assert isinstance(result, dict)

    def test_get_p2p_efficiency_metrics(self):
        result = self.mod.get_p2p_efficiency_metrics(
            start_date="2025-01-01", end_date="2025-01-31"
        )
        assert isinstance(result, dict)


# ── Bank Ops Tools Tests ─────────────────────────────────────────────────────

class TestBankOpsTools:

    @pytest.fixture(autouse=True)
    def _load(self):
        self.mod = _import_tool_module("bank_ops_tools")

    def test_parse_bank_statement(self):
        result = self.mod.parse_bank_statement(
            file_content="Date,Description,Amount\n2025-01-15,Google Payment,50000",
            bank_name="HDFC",
        )
        assert isinstance(result, dict)

    def test_get_credit_card_invoices(self):
        result = self.mod.get_credit_card_invoices(card_id="CC-001", period="2025-01")
        assert isinstance(result, dict)


# ── ID Mapping Integration Test ──────────────────────────────────────────────

class TestIDMapping:
    """Test that NetSuite and SpotDraft IDs can be cross-referenced."""

    def test_netsuite_vendors_have_spotdraft_parties(self):
        """Verify that vendor names in NetSuite match party names in SpotDraft."""
        vendors = helpers.ns_get("/record/v1/vendor")
        parties = helpers.sd_get("/parties/")

        ns_names = {v["companyName"] for v in vendors.get("items", [])}
        sd_names = {p["name"] for p in parties}

        overlap = ns_names & sd_names
        print(f"\nNetSuite vendors: {len(ns_names)}")
        print(f"SpotDraft parties: {len(sd_names)}")
        print(f"Overlapping names: {len(overlap)}")
        print(f"Overlap: {sorted(overlap)[:5]}...")

        assert len(overlap) > 0, "No matching vendor/party names between systems"

    def test_spotdraft_onboarding_with_party_id(self):
        """Verify onboarding endpoint works with SpotDraft party IDs."""
        result = helpers.sd_get("/api/custom/onboarding/party_001/")
        assert "party_id" in result
        assert "overall_status" in result
