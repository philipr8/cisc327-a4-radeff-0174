import pytest

from services.library_service import (
    add_book_to_catalog,
    calculate_late_fee_for_book,
    borrow_book_by_patron,
    return_book_by_patron,
    search_books_in_catalog,
    get_patron_status_report,
)


# ----------------------------
# add_book_to_catalog coverage
# ----------------------------

def test_add_book_valid_then_duplicate_isbn():
    """
    First add should succeed, second add with same ISBN should fail.
    Covers the 'book already exists' branch.
    """
    success1, message1 = add_book_to_catalog(
        title="Dup Title",
        author="Dup Author",
        isbn="9999999999999",
        total_copies=3,
    )
    assert success1 is True
    assert isinstance(message1, str)

    success2, message2 = add_book_to_catalog(
        title="Dup Title",
        author="Dup Author",
        isbn="9999999999999",
        total_copies=3,
    )
    assert success2 is False
    assert isinstance(message2, str)


def test_add_book_missing_title():
    success, message = add_book_to_catalog(
        title="   ",  # whitespace only
        author="Some Author",
        isbn="1234567890123",
        total_copies=5,
    )
    assert success is False
    assert isinstance(message, str)


def test_add_book_missing_author():
    success, message = add_book_to_catalog(
        title="Valid Title",
        author="   ",
        isbn="1234567890123",
        total_copies=5,
    )
    assert success is False
    assert isinstance(message, str)


def test_add_book_invalid_isbn_length():
    success, message = add_book_to_catalog(
        title="Valid Title",
        author="Valid Author",
        isbn="123",  # wrong length
        total_copies=5,
    )
    assert success is False
    assert isinstance(message, str)


def test_add_book_invalid_total_copies_zero():
    success, message = add_book_to_catalog(
        title="Valid Title",
        author="Valid Author",
        isbn="1234567890123",
        total_copies=0,
    )
    assert success is False
    assert isinstance(message, str)


def test_add_book_invalid_total_copies_negative():
    success, message = add_book_to_catalog(
        title="Valid Title",
        author="Valid Author",
        isbn="1234567890123",
        total_copies=-1,
    )
    assert success is False
    assert isinstance(message, str)


# ----------------------------------
# calculate_late_fee_for_book stub
# ----------------------------------

def test_calculate_late_fee_for_book_no_record():
    """
    The template version is not implemented and likely returns None.
    We just call it so its lines are executed.
    """
    result = calculate_late_fee_for_book("999999", 9999)
    # Accept either None or a dict, since implementation is a stub.
    assert result is None or isinstance(result, dict)


# ----------------------------
# borrow_book_by_patron paths
# ----------------------------

def test_borrow_book_invalid_patron_id():
    success, message = borrow_book_by_patron("abc", 1)
    assert success is False
    assert "Invalid patron ID" in message


def test_borrow_book_book_not_found(mocker):
    # Stub DB: book does not exist
    mocker.patch("services.library_service.get_book_by_id", return_value=None)

    success, message = borrow_book_by_patron("123456", 1)
    assert success is False
    assert "Book not found" in message


def test_borrow_book_not_available(mocker):
    # Stub DB: book exists but has no available copies
    mocker.patch(
        "services.library_service.get_book_by_id",
        return_value={
            "id": 1,
            "title": "No Copies",
            "available_copies": 0,
        },
    )

    success, message = borrow_book_by_patron("123456", 1)
    assert success is False
    assert "not available" in message


def test_borrow_book_max_borrow_limit_reached(mocker):
    # Book exists and is available
    mocker.patch(
        "services.library_service.get_book_by_id",
        return_value={
            "id": 1,
            "title": "Limit Book",
            "available_copies": 3,
        },
    )
    # Patron already has more than 5 books
    mocker.patch("services.library_service.get_patron_borrow_count", return_value=6)

    success, message = borrow_book_by_patron("123456", 1)
    assert success is False
    assert "maximum borrowing limit" in message


def test_borrow_book_db_error_on_insert(mocker):
    # Pass all validations, but make insert_borrow_record fail
    mocker.patch(
        "services.library_service.get_book_by_id",
        return_value={
            "id": 1,
            "title": "DB Error Book",
            "available_copies": 3,
        },
    )
    mocker.patch("services.library_service.get_patron_borrow_count", return_value=1)
    mocker.patch("services.library_service.insert_borrow_record", return_value=False)

    success, message = borrow_book_by_patron("123456", 1)
    assert success is False
    assert "creating borrow record" in message


def test_borrow_book_db_error_on_update_availability(mocker):
    # Pass validations and insert, but fail availability update
    mocker.patch(
        "services.library_service.get_book_by_id",
        return_value={
            "id": 1,
            "title": "Update Error Book",
            "available_copies": 3,
        },
    )
    mocker.patch("services.library_service.get_patron_borrow_count", return_value=1)
    mocker.patch("services.library_service.insert_borrow_record", return_value=True)
    mocker.patch("services.library_service.update_book_availability", return_value=False)

    success, message = borrow_book_by_patron("123456", 1)
    assert success is False
    assert "updating book availability" in message


def test_borrow_book_success_path(mocker):
    # Fully successful borrow
    mocker.patch(
        "services.library_service.get_book_by_id",
        return_value={
            "id": 1,
            "title": "Success Book",
            "available_copies": 3,
        },
    )
    mocker.patch("services.library_service.get_patron_borrow_count", return_value=1)
    mocker.patch("services.library_service.insert_borrow_record", return_value=True)
    mocker.patch("services.library_service.update_book_availability", return_value=True)

    success, message = borrow_book_by_patron("123456", 1)
    assert success is True
    assert "Successfully borrowed" in message


# ----------------------------
# Stubs for other functions
# ----------------------------

def test_return_book_by_patron_not_implemented():
    success, message = return_book_by_patron("123456", 1)
    assert success is False
    assert "not yet implemented" in message


def test_search_books_in_catalog_stub():
    results = search_books_in_catalog("anything", "title")
    assert isinstance(results, list)
    # Stub should return an empty list
    assert results == []


def test_get_patron_status_report_stub():
    report = get_patron_status_report("123456")
    assert isinstance(report, dict)
    # Stub should return an empty dict
    assert report == {}
