import sys
import os

# Ensure workspace root is always on sys.path for pytest runs
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from app import app, db

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key-12345'
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
