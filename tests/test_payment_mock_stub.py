import pytest
from unittest.mock import Mock

from services.payment_service import PaymentGateway
from services.library_service import pay_late_fees, refund_late_fee_payment


# ============
# pay_late_fees tests
# ============

def test_pay_late_fees_success(mocker):
    # STUBS: database functions
    mocker.patch(
        "services.library_service.calculate_late_fee_for_book",
        return_value={
            "fee_amount": 5.00,
            "days_overdue": 3,
            "status": "ok",
        },
    )
    mocker.patch(
        "services.library_service.get_book_by_id",
        return_value={"id": 1, "title": "Test Book"},
    )

    # MOCK: payment gateway (passed in explicitly)
    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.process_payment.return_value = (
        True,
        "txn_123",
        "Paid successfully",
    )

    success, message, txn_id = pay_late_fees("123456", 1, mock_gateway)

    mock_gateway.process_payment.assert_called_once_with(
        patron_id="123456",
        amount=5.00,
        description="Late fees for 'Test Book'",
    )
    assert success is True
    assert "Payment successful" in message
    assert "Paid successfully" in message
    assert txn_id == "txn_123"


def test_pay_late_fees_payment_declined(mocker):
    mocker.patch(
        "services.library_service.calculate_late_fee_for_book",
        return_value={
            "fee_amount": 8.50,
            "days_overdue": 5,
            "status": "ok",
        },
    )
    mocker.patch(
        "services.library_service.get_book_by_id",
        return_value={"id": 2, "title": "Another Book"},
    )

    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.process_payment.return_value = (
        False,
        "txn_999",
        "Card declined",
    )

    success, message, txn_id = pay_late_fees("654321", 2, mock_gateway)

    mock_gateway.process_payment.assert_called_once_with(
        patron_id="654321",
        amount=8.50,
        description="Late fees for 'Another Book'",
    )
    assert success is False
    assert message == "Payment failed: Card declined"
    assert txn_id is None


def test_pay_late_fees_invalid_patron_id_does_not_call_gateway():
    mock_gateway = Mock(spec=PaymentGateway)

    success, message, txn_id = pay_late_fees("abc", 1, mock_gateway)

    assert success is False
    assert "Invalid patron ID" in message
    assert txn_id is None
    mock_gateway.process_payment.assert_not_called()


def test_pay_late_fees_unable_to_calculate_fee(mocker):
    mocker.patch(
        "services.library_service.calculate_late_fee_for_book",
        return_value=None,
    )
    mock_gateway = Mock(spec=PaymentGateway)

    success, message, txn_id = pay_late_fees("123456", 1, mock_gateway)

    assert success is False
    assert message == "Unable to calculate late fees."
    assert txn_id is None
    mock_gateway.process_payment.assert_not_called()


def test_pay_late_fees_zero_fee_does_not_call_gateway(mocker):
    mocker.patch(
        "services.library_service.calculate_late_fee_for_book",
        return_value={
            "fee_amount": 0.0,
            "days_overdue": 0,
            "status": "ok",
        },
    )
    mock_gateway = Mock(spec=PaymentGateway)

    success, message, txn_id = pay_late_fees("123456", 1, mock_gateway)

    assert success is False
    assert message == "No late fees to pay for this book."
    assert txn_id is None
    mock_gateway.process_payment.assert_not_called()


def test_pay_late_fees_book_not_found(mocker):
    mocker.patch(
        "services.library_service.calculate_late_fee_for_book",
        return_value={
            "fee_amount": 3.25,
            "days_overdue": 2,
            "status": "ok",
        },
    )
    mocker.patch(
        "services.library_service.get_book_by_id",
        return_value=None,
    )
    mock_gateway = Mock(spec=PaymentGateway)

    success, message, txn_id = pay_late_fees("123456", 99, mock_gateway)

    assert success is False
    assert message == "Book not found."
    assert txn_id is None
    mock_gateway.process_payment.assert_not_called()


def test_pay_late_fees_network_error(mocker):
    mocker.patch(
        "services.library_service.calculate_late_fee_for_book",
        return_value={
            "fee_amount": 7.00,
            "days_overdue": 4,
            "status": "ok",
        },
    )
    mocker.patch(
        "services.library_service.get_book_by_id",
        return_value={"id": 3, "title": "Network Book"},
    )

    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.process_payment.side_effect = Exception("Network down")

    success, message, txn_id = pay_late_fees("123456", 3, mock_gateway)

    mock_gateway.process_payment.assert_called_once()
    assert success is False
    assert "Payment processing error" in message
    assert "Network down" in message
    assert txn_id is None


def test_pay_late_fees_uses_default_gateway_when_none(mocker):
    """
    New test to hit the branch:
        if payment_gateway is None:
            payment_gateway = PaymentGateway()
    while still mocking PaymentGateway.
    """
    # Stub DB calls
    mocker.patch(
        "services.library_service.calculate_late_fee_for_book",
        return_value={
            "fee_amount": 4.0,
            "days_overdue": 2,
            "status": "ok",
        },
    )
    mocker.patch(
        "services.library_service.get_book_by_id",
        return_value={"id": 10, "title": "Default Gateway Book"},
    )

    # Patch the PaymentGateway class inside library_service
    mock_gateway_instance = Mock(spec=PaymentGateway)
    mock_gateway_class = mocker.patch(
        "services.library_service.PaymentGateway",
        return_value=mock_gateway_instance,
    )
    mock_gateway_instance.process_payment.return_value = (
        True,
        "txn_default",
        "Paid via default gateway",
    )

    # Call with payment_gateway=None to hit the branch
    success, message, txn_id = pay_late_fees("123456", 10, payment_gateway=None)

    mock_gateway_class.assert_called_once_with()
    mock_gateway_instance.process_payment.assert_called_once_with(
        patron_id="123456",
        amount=4.0,
        description="Late fees for 'Default Gateway Book'",
    )
    assert success is True
    assert "Payment successful" in message
    assert "Paid via default gateway" in message
    assert txn_id == "txn_default"


# ============
# refund_late_fee_payment tests
# ============

def test_refund_late_fee_payment_success():
    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.refund_payment.return_value = (
        True,
        "Refund processed",
    )

    success, message = refund_late_fee_payment("txn_123", 10.0, mock_gateway)

    mock_gateway.refund_payment.assert_called_once_with("txn_123", 10.0)
    assert success is True
    assert message == "Refund processed"


def test_refund_late_fee_payment_invalid_transaction_id():
    mock_gateway = Mock(spec=PaymentGateway)

    success, message = refund_late_fee_payment("", 10.0, mock_gateway)

    assert success is False
    assert message == "Invalid transaction ID."
    mock_gateway.refund_payment.assert_not_called()


@pytest.mark.parametrize("amount", [-5.0, 0.0])
def test_refund_late_fee_payment_invalid_non_positive_amount(amount):
    mock_gateway = Mock(spec=PaymentGateway)

    success, message = refund_late_fee_payment("txn_123", amount, mock_gateway)

    assert success is False
    assert message == "Refund amount must be greater than 0."
    mock_gateway.refund_payment.assert_not_called()


def test_refund_late_fee_payment_amount_exceeds_max():
    mock_gateway = Mock(spec=PaymentGateway)

    success, message = refund_late_fee_payment("txn_123", 20.0, mock_gateway)

    assert success is False
    assert message == "Refund amount exceeds maximum late fee."
    mock_gateway.refund_payment.assert_not_called()


def test_refund_late_fee_payment_gateway_failure():
    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.refund_payment.return_value = (False, "Gateway error")

    success, message = refund_late_fee_payment("txn_123", 10.0, mock_gateway)

    mock_gateway.refund_payment.assert_called_once_with("txn_123", 10.0)
    assert success is False
    assert message == "Refund failed: Gateway error"


def test_refund_late_fee_payment_gateway_exception():
    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.refund_payment.side_effect = Exception("Timeout")

    success, message = refund_late_fee_payment("txn_123", 10.0, mock_gateway)

    mock_gateway.refund_payment.assert_called_once_with("txn_123", 10.0)
    assert success is False
    assert "Refund processing error" in message
    assert "Timeout" in message


def test_refund_late_fee_payment_uses_default_gateway_when_none(mocker):
    """
    New test to hit:
        if payment_gateway is None:
            payment_gateway = PaymentGateway()
    in refund_late_fee_payment.
    """
    # Patch PaymentGateway class used inside library_service
    mock_gateway_instance = Mock(spec=PaymentGateway)
    mock_gateway_class = mocker.patch(
        "services.library_service.PaymentGateway",
        return_value=mock_gateway_instance,
    )
    mock_gateway_instance.refund_payment.return_value = (
        True,
        "Refund via default gateway",
    )

    success, message = refund_late_fee_payment(
        "txn_123_default",
        5.0,
        payment_gateway=None,
    )

    mock_gateway_class.assert_called_once_with()
    mock_gateway_instance.refund_payment.assert_called_once_with(
        "txn_123_default",
        5.0,
    )
    assert success is True
    assert "Refund via default gateway" in message
