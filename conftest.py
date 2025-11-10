import pytest
from database import init_db

@pytest.fixture(autouse=True)
def reset_database():
    """
    Automatically run before each test function to ensure the
    database schema exists and the books table is empty.
    """
    init_db()
