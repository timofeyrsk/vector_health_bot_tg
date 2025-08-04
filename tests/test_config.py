import unittest
import os
import sys
from unittest.mock import Mock, patch

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestConfig:
    """Test configuration"""
    DATABASE_URL = 'sqlite:///test.db'
    TESTING = True
    SECRET_KEY = 'test-secret-key'
    OPENAI_API_KEY = 'test-openai-key'
    TELEGRAM_BOT_TOKEN = 'test-telegram-token'
    TERRA_DEV_ID = 'test-terra-dev-id'
    TERRA_API_KEY = 'test-terra-api-key'

class BaseTestCase(unittest.TestCase):
    """Base test case with common setup"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_openai = Mock()
        self.mock_requests = Mock()
        
    def tearDown(self):
        """Clean up after tests"""
        pass

