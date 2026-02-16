"""NetSuite REST API Mock Server.

FastAPI application implementing a subset of the NetSuite REST API (2025.2)
for local development and testing of P2P ShareChat agents.

Start with:
    uvicorn mock_servers.netsuite_mock.app:app --port 8081
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mock_servers.netsuite_mock.auth import NetSuiteAuthMiddleware
from mock_servers.netsuite_mock.routes.vendor import router as vendor_router
from mock_servers.netsuite_mock.routes.vendor_bill import router as vendor_bill_router
from mock_servers.netsuite_mock.routes.vendor_payment import router as vendor_payment_router
from mock_servers.netsuite_mock.routes.expense import router as expense_router
from mock_servers.netsuite_mock.routes.suiteql import router as suiteql_router
from mock_servers.netsuite_mock.routes.bank import router as bank_router

app = FastAPI(
    title="NetSuite REST API Mock",
    description="Mock implementation of NetSuite REST API for P2P agent development",
    version="2025.2-mock",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth
app.add_middleware(NetSuiteAuthMiddleware)

# Routes
app.include_router(vendor_router, prefix="/record/v1")
app.include_router(vendor_bill_router, prefix="/record/v1")
app.include_router(vendor_payment_router, prefix="/record/v1")
app.include_router(expense_router, prefix="/record/v1")
app.include_router(suiteql_router, prefix="/query/v1")
app.include_router(bank_router, prefix="/api/custom")


@app.get("/")
async def root():
    return {
        "type": "mock",
        "name": "NetSuite REST API Mock",
        "version": "2025.2",
        "endpoints": [
            "/record/v1/vendor",
            "/record/v1/vendorBill",
            "/record/v1/vendorPayment",
            "/record/v1/expense",
            "/query/v1/suiteql",
            "/api/custom/bank-entries",
            "/api/custom/cc-invoices",
            "/api/custom/accruals",
        ],
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
