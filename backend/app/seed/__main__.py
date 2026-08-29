"""Seed data script — deterministic demo data for development.

Run with:
    python -m app.seed

Credentials:
    admin@ledgerpilot.dev    / Admin@123
    manager@ledgerpilot.dev  / Manager@123
    analyst@ledgerpilot.dev  / Analyst@123
    viewer@ledgerpilot.dev   / Viewer@123
"""

import random
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from faker import Faker

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.audit_log import AuditAction, AuditLog
from app.models.bank_transaction import BankTransaction, BankTransactionType
from app.models.exception import Exception as FinancialException
from app.models.exception import ExceptionSeverity, ExceptionStatus, ExceptionType
from app.models.invoice import Invoice, InvoiceStatus
from app.models.merchant import Merchant
from app.models.settlement import Settlement, SettlementStatus
from app.models.transaction import Transaction, TransactionStatus
from app.models.user import Role, User

try:
    from app.rag.ingestion import ingest_finance_rules, ingest_historical_cases
    _RAG_AVAILABLE = True
except ImportError:
    _RAG_AVAILABLE = False

fake = Faker("en_IN")
SEED = 42
Faker.seed(SEED)
random.seed(SEED)

PAYMENT_METHODS = ["UPI", "NEFT", "IMPS", "RTGS", "Card", "NetBanking", "Wallet"]


def _rand_amount(low: float, high: float) -> Decimal:
    return Decimal(str(round(random.uniform(low, high), 2)))


def _rand_date_in_range(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def _rand_datetime_in_range(start: datetime, end: datetime) -> datetime:
    delta = int((end - start).total_seconds())
    return start + timedelta(seconds=random.randint(0, delta))


def seed_users(db) -> list[User]:
    from app.core.config import get_settings
    settings = get_settings()

    users_data = [
        ("Admin User", "admin@ledgerpilot.dev", settings.SEED_ADMIN_PASSWORD, Role.ADMIN),
        ("Finance Manager", "manager@ledgerpilot.dev", settings.SEED_MANAGER_PASSWORD, Role.FINANCE_MANAGER),
        ("Finance Analyst", "analyst@ledgerpilot.dev", settings.SEED_ANALYST_PASSWORD, Role.FINANCE_ANALYST),
        ("View Only", "viewer@ledgerpilot.dev", settings.SEED_VIEWER_PASSWORD, Role.VIEWER),
    ]

    users = []
    for full_name, email, password, role in users_data:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f"  [skip] User {email} already exists")
            users.append(existing)
            continue
        user = User(
            full_name=full_name,
            email=email,
            password_hash=hash_password(password),
            role=role,
            is_active=True,
        )
        db.add(user)
        users.append(user)
        print(f"  [+] User {email} ({role})")

    db.commit()
    return users


def seed_merchant(db) -> Merchant:
    existing = db.query(Merchant).filter(Merchant.business_name == "Acme Commerce Pvt Ltd").first()
    if existing:
        print("  [skip] Merchant already exists")
        return existing

    merchant = Merchant(
        name="Acme Commerce",
        business_name="Acme Commerce Pvt Ltd",
        email="accounts@acmecommerce.in",
        currency="INR",
        timezone="Asia/Kolkata",
    )
    db.add(merchant)
    db.commit()
    db.refresh(merchant)
    print(f"  [+] Merchant: {merchant.business_name}")
    return merchant


def seed_transactions(db, merchant: Merchant) -> list[Transaction]:
    existing_count = db.query(Transaction).filter(Transaction.merchant_id == merchant.id).count()
    if existing_count >= 100:
        print(f"  [skip] Transactions already seeded ({existing_count})")
        return db.query(Transaction).filter(Transaction.merchant_id == merchant.id).all()

    statuses = (
        [TransactionStatus.SUCCESS] * 65
        + [TransactionStatus.FAILED] * 10
        + [TransactionStatus.REFUNDED] * 8
        + [TransactionStatus.PARTIAL_REFUND] * 5
        + [TransactionStatus.PENDING] * 12
    )

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=60)

    txns = []
    for i in range(100):
        amount = _rand_amount(500, 150000)
        fee = (amount * Decimal("0.02")).quantize(Decimal("0.0001"))
        tax = (fee * Decimal("0.18")).quantize(Decimal("0.0001"))
        ts = _rand_datetime_in_range(start, now)
        txn = Transaction(
            merchant_id=merchant.id,
            payment_id=f"PAY{str(i+1).zfill(6)}{fake.bothify('??##')}",
            order_id=f"ORD{str(i+1).zfill(6)}{fake.bothify('??##')}",
            customer_id=f"CUST{random.randint(1000, 9999)}",
            amount=amount,
            fee=fee,
            tax=tax,
            status=statuses[i],
            payment_method=random.choice(PAYMENT_METHODS),
            transaction_timestamp=ts,
            created_at=ts,
            updated_at=ts,
        )
        db.add(txn)
        txns.append(txn)

    db.commit()
    print(f"  [+] {len(txns)} transactions seeded")
    return txns


def seed_invoices(db, merchant: Merchant) -> list[Invoice]:
    existing_count = db.query(Invoice).filter(Invoice.merchant_id == merchant.id).count()
    if existing_count >= 60:
        print(f"  [skip] Invoices already seeded ({existing_count})")
        return db.query(Invoice).filter(Invoice.merchant_id == merchant.id).all()

    statuses = (
        [InvoiceStatus.PAID] * 30
        + [InvoiceStatus.ISSUED] * 10
        + [InvoiceStatus.OVERDUE] * 10
        + [InvoiceStatus.PARTIALLY_PAID] * 7
        + [InvoiceStatus.CANCELLED] * 3
    )

    today = date.today()
    start = today - timedelta(days=60)

    invoices = []
    for i in range(60):
        inv_date = _rand_date_in_range(start, today)
        due_date = inv_date + timedelta(days=random.choice([15, 30, 45]))
        amount = _rand_amount(2000, 500000)
        tax = (amount * Decimal("0.18")).quantize(Decimal("0.0001"))
        inv = Invoice(
            merchant_id=merchant.id,
            invoice_id=f"INV{str(i+1).zfill(5)}{fake.bothify('??##')}",
            customer_id=f"CUST{random.randint(1000, 9999)}",
            amount=amount,
            tax=tax,
            status=statuses[i],
            invoice_date=inv_date,
            due_date=due_date,
            payment_reference=f"PAY{str(i+1).zfill(6)}" if statuses[i] == InvoiceStatus.PAID else None,
        )
        db.add(inv)
        invoices.append(inv)

    db.commit()
    print(f"  [+] {len(invoices)} invoices seeded")
    return invoices


def seed_settlements(db, merchant: Merchant, transactions: list[Transaction]) -> list[Settlement]:
    existing_count = db.query(Settlement).filter(Settlement.merchant_id == merchant.id).count()
    if existing_count >= 80:
        print(f"  [skip] Settlements already seeded ({existing_count})")
        return db.query(Settlement).filter(Settlement.merchant_id == merchant.id).all()

    today = date.today()
    statuses = (
        [SettlementStatus.PROCESSED] * 65
        + [SettlementStatus.PENDING] * 10
        + [SettlementStatus.FAILED] * 5
    )

    # Use successful transaction payment_ids where possible
    success_txns = [t for t in transactions if t.status == TransactionStatus.SUCCESS]

    settlements = []
    for i in range(80):
        stl_date = today - timedelta(days=random.randint(0, 60))
        if i < len(success_txns):
            payment_id = success_txns[i].payment_id
            amount = success_txns[i].amount - success_txns[i].fee
        else:
            payment_id = f"PAY{str(i+200).zfill(6)}"
            amount = _rand_amount(500, 100000)
        fee = (amount * Decimal("0.01")).quantize(Decimal("0.0001"))
        stl = Settlement(
            merchant_id=merchant.id,
            settlement_id=f"STL{str(i+1).zfill(5)}{fake.bothify('??##')}",
            payment_id=payment_id,
            settlement_amount=amount - fee,
            fee=fee,
            settlement_date=stl_date,
            status=statuses[i],
        )
        db.add(stl)
        settlements.append(stl)

    db.commit()
    print(f"  [+] {len(settlements)} settlements seeded")
    return settlements


def seed_bank_transactions(db, merchant: Merchant) -> list[BankTransaction]:
    existing_count = db.query(BankTransaction).filter(BankTransaction.merchant_id == merchant.id).count()
    if existing_count >= 100:
        print(f"  [skip] Bank transactions already seeded ({existing_count})")
        return db.query(BankTransaction).filter(BankTransaction.merchant_id == merchant.id).all()

    today = date.today()
    bank_txns = []
    for i in range(100):
        txn_date = today - timedelta(days=random.randint(0, 60))
        tx_type = BankTransactionType.CREDIT if i % 3 != 0 else BankTransactionType.DEBIT
        amount = _rand_amount(1000, 250000)
        bt = BankTransaction(
            merchant_id=merchant.id,
            bank_transaction_id=f"BNK{str(i+1).zfill(6)}{fake.bothify('??##')}",
            reference=f"REF{fake.bothify('######')}",
            amount=amount,
            transaction_type=tx_type,
            transaction_date=txn_date,
            description=fake.sentence(nb_words=6),
        )
        db.add(bt)
        bank_txns.append(bt)

    db.commit()
    print(f"  [+] {len(bank_txns)} bank transactions seeded")
    return bank_txns


def seed_exceptions(db, merchant: Merchant, transactions: list[Transaction]) -> list[FinancialException]:
    existing_count = db.query(FinancialException).filter(FinancialException.merchant_id == merchant.id).count()
    if existing_count >= 15:
        print(f"  [skip] Exceptions already seeded ({existing_count})")
        return db.query(FinancialException).filter(FinancialException.merchant_id == merchant.id).all()

    exception_scenarios = [
        (ExceptionType.AMOUNT_MISMATCH, ExceptionSeverity.HIGH, "Settlement amount does not match transaction amount."),
        (ExceptionType.MISSING_INVOICE, ExceptionSeverity.MEDIUM, "No invoice found for this payment."),
        (ExceptionType.MISSING_SETTLEMENT, ExceptionSeverity.HIGH, "Successful payment has no corresponding settlement."),
        (ExceptionType.DUPLICATE, ExceptionSeverity.CRITICAL, "Duplicate payment_id detected across multiple transactions."),
        (ExceptionType.REFUND_MISMATCH, ExceptionSeverity.HIGH, "Refund amount exceeds original transaction amount."),
        (ExceptionType.AMOUNT_MISMATCH, ExceptionSeverity.CRITICAL, "Large discrepancy between invoice and payment received."),
        (ExceptionType.MISSING_INVOICE, ExceptionSeverity.LOW, "Invoice reference missing on bank statement entry."),
        (ExceptionType.UNKNOWN, ExceptionSeverity.MEDIUM, "Unclassified anomaly detected in reconciliation data."),
        (ExceptionType.MISSING_SETTLEMENT, ExceptionSeverity.MEDIUM, "Settlement expected within 2 days but not received."),
        (ExceptionType.REFUND_MISMATCH, ExceptionSeverity.MEDIUM, "Partial refund amount inconsistent with records."),
        (ExceptionType.DUPLICATE, ExceptionSeverity.HIGH, "Possible duplicate order_id on separate transactions."),
        (ExceptionType.AMOUNT_MISMATCH, ExceptionSeverity.LOW, "Minor fee discrepancy on settlement record."),
        (ExceptionType.MISSING_INVOICE, ExceptionSeverity.HIGH, "Payment received with no linked invoice in system."),
        (ExceptionType.MISSING_SETTLEMENT, ExceptionSeverity.CRITICAL, "High-value transaction unsettled beyond SLA."),
        (ExceptionType.UNKNOWN, ExceptionSeverity.LOW, "Unrecognized bank reference code on credit entry."),
    ]

    statuses = (
        [ExceptionStatus.OPEN] * 7
        + [ExceptionStatus.IN_REVIEW] * 4
        + [ExceptionStatus.RESOLVED] * 3
        + [ExceptionStatus.DISMISSED] * 1
    )

    exceptions = []
    for i, (exc_type, severity, description) in enumerate(exception_scenarios):
        source_tx = transactions[i % len(transactions)]
        exc = FinancialException(
            merchant_id=merchant.id,
            source_type="transaction",
            source_id=source_tx.payment_id,
            exception_type=exc_type,
            severity=severity,
            amount=source_tx.amount,
            description=description,
            status=statuses[i],
        )
        db.add(exc)
        exceptions.append(exc)

    db.commit()
    print(f"  [+] {len(exceptions)} exceptions seeded")
    return exceptions


def seed_audit_logs(db, users: list[User], merchant: Merchant) -> None:
    existing_count = db.query(AuditLog).count()
    if existing_count > 0:
        print(f"  [skip] Audit logs already seeded ({existing_count})")
        return

    admin = next((u for u in users if u.role == Role.ADMIN), users[0])

    log_entries = [
        AuditLog(user_id=admin.id, merchant_id=merchant.id, action=AuditAction.LOGIN,
                 description="Admin user logged in", metadata_={"ip": "127.0.0.1"}),
        AuditLog(user_id=admin.id, merchant_id=merchant.id, action=AuditAction.VIEW_DASHBOARD,
                 description="Dashboard summary viewed"),
        AuditLog(user_id=admin.id, merchant_id=merchant.id, action=AuditAction.VIEW_EXCEPTION,
                 entity_type="exception", description="Exception reviewed by admin"),
    ]

    for log in log_entries:
        db.add(log)
    db.commit()
    print(f"  [+] {len(log_entries)} audit log entries seeded")


def main() -> None:
    print("\n🌱 LedgerPilot — Seeding demo data\n")
    db = SessionLocal()
    try:
        print("→ Users")
        users = seed_users(db)

        print("\n→ Merchant")
        merchant = seed_merchant(db)

        print("\n→ Transactions")
        transactions = seed_transactions(db, merchant)

        print("\n→ Invoices")
        seed_invoices(db, merchant)

        print("\n→ Settlements")
        seed_settlements(db, merchant, transactions)

        print("\n→ Bank Transactions")
        seed_bank_transactions(db, merchant)

        print("\n→ Exceptions")
        seed_exceptions(db, merchant, transactions)

        print("\n→ Audit Logs")
        seed_audit_logs(db, users, merchant)

        # ── Phase 3A: Evidence ingestion ──────────────────────────────────────
        if _RAG_AVAILABLE:
            try:
                print("\n→ Evidence: Finance Rules")
                rules = ingest_finance_rules(db)
                print(f"  [+] {len(rules)} finance rules ingested")

                print("\n→ Evidence: Historical Cases")
                cases = ingest_historical_cases(db)
                print(f"  [+] {len(cases)} historical cases ingested")
            except Exception as rag_err:
                print(
                    f"  [!] Evidence ingestion failed (pgvector may not be available): {rag_err}"
                )
                print("  [!] Run migrations first: alembic upgrade head")
        else:
            print("\n→ Evidence: [skipped — RAG dependencies not installed]")

        print("\n✅ Seed complete!\n")
        print("Demo credentials:")
        print("  admin@ledgerpilot.dev    / Admin@123")
        print("  manager@ledgerpilot.dev  / Manager@123")
        print("  analyst@ledgerpilot.dev  / Analyst@123")
        print("  viewer@ledgerpilot.dev   / Viewer@123\n")
    except Exception as e:
        print(f"\n❌ Seed failed: {e}", file=sys.stderr)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
