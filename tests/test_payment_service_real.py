import pytest

from services.payment_service import PaymentGateway


# ----------------------------
# process_payment coverage
# ----------------------------

def test_process_payment_success_basic():
    """
    Valid patron and reasonable amount -> success path.
    """
    gateway = PaymentGateway()
    success, transaction_id, message = gateway.process_payment(
        patron_id="123456",
        amount=10.0,
        description="Normal test payment",
    )

    assert success is True
    assert isinstance(transaction_id, str)
    assert transaction_id.startswith("txn_")
    assert "Payment of $10.00 processed successfully" in message


def test_process_payment_invalid_amount_zero():
    """
    amount <= 0 branch.
    """
    gateway = PaymentGateway()
    success, transaction_id, message = gateway.process_payment(
        patron_id="123456",
        amount=0.0,
        description="Zero amount payment",
    )

    assert success is False
    assert transaction_id == ""
    assert "Invalid amount" in message


def test_process_payment_amount_exceeds_limit():
    """
    amount > 1000 branch.
    """
    gateway = PaymentGateway()
    success, transaction_id, message = gateway.process_payment(
        patron_id="123456",
        amount=2000.0,
        description="Too large payment",
    )

    assert success is False
    assert transaction_id == ""
    assert "exceeds limit" in message


def test_process_payment_invalid_patron_id_format():
    """
    len(patron_id) != 6 branch.
    """
    gateway = PaymentGateway()
    success, transaction_id, message = gateway.process_payment(
        patron_id="123",  # invalid length
        amount=50.0,
        description="Bad patron",
    )

    assert success is False
    assert transaction_id == ""
    assert "Invalid patron ID format" in message


# ----------------------------
# refund_payment coverage
# ----------------------------

def test_refund_payment_success_basic():
    gateway = PaymentGateway()
    success, message = gateway.refund_payment(
        transaction_id="txn_123456_000000",
        amount=5.0,
    )

    assert success is True
    assert "Refund of $5.00 processed successfully" in message
    assert "Refund ID:" in message


def test_refund_payment_invalid_transaction_id():
    gateway = PaymentGateway()
    success, message = gateway.refund_payment(
        transaction_id="bad_txn",
        amount=5.0,
    )

    assert success is False
    assert message == "Invalid transaction ID"


def test_refund_payment_invalid_amount():
    gateway = PaymentGateway()
    success, message = gateway.refund_payment(
        transaction_id="txn_123456_000000",
        amount=0.0,
    )

    assert success is False
    assert message == "Invalid refund amount"


# ----------------------------
# verify_payment_status coverage
# ----------------------------

def test_verify_payment_status_not_found():
    gateway = PaymentGateway()
    info = gateway.verify_payment_status(transaction_id="bad_txn")

    assert isinstance(info, dict)
    assert info["status"] == "not_found"
    assert "Transaction not found" in info["message"]


def test_verify_payment_status_completed():
    gateway = PaymentGateway()
    info = gateway.verify_payment_status(transaction_id="txn_123456_000000")

    assert isinstance(info, dict)
    assert info["status"] == "completed"
    assert info["transaction_id"].startswith("txn_")
    assert "amount" in info
    assert "timestamp" in info
