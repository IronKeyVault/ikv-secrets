"""Tests for EnvProxy."""

import pytest
from unittest.mock import MagicMock, patch

from ikv_secrets.env import EnvProxy


class TestEnvProxy:
    """Tests for EnvProxy class."""
    
    def test_initial_state(self):
        """Test proxy starts unloaded."""
        proxy = EnvProxy()
        assert not proxy._loaded
        assert proxy._cache == {}
    
    def test_getattr_raises_when_not_loaded(self):
        """Test accessing attribute before load raises."""
        proxy = EnvProxy()
        proxy._loaded = True  # Pretend loaded but empty
        
        with pytest.raises(AttributeError, match="DATABASE_URL"):
            _ = proxy.DATABASE_URL
    
    def test_getattr_returns_cached_value(self):
        """Test accessing cached value works."""
        proxy = EnvProxy()
        proxy._loaded = True
        proxy._cache = {"DATABASE_URL": "postgres://localhost/db"}
        
        assert proxy.DATABASE_URL == "postgres://localhost/db"
    
    def test_get_with_default(self):
        """Test get with default value."""
        proxy = EnvProxy()
        proxy._loaded = True
        proxy._cache = {}
        
        assert proxy.get("MISSING", "default") == "default"
    
    def test_has_key(self):
        """Test has method."""
        proxy = EnvProxy()
        proxy._loaded = True
        proxy._cache = {"EXISTS": "value"}
        
        assert proxy.has("EXISTS")
        assert not proxy.has("MISSING")
    
    def test_to_dotenv(self):
        """Test dotenv export format."""
        proxy = EnvProxy()
        proxy._loaded = True
        proxy._cache = {
            "DB_HOST": "localhost",
            "DB_PORT": "5432",
        }
        
        result = proxy.to_dotenv()
        assert 'DB_HOST="localhost"' in result
        assert 'DB_PORT="5432"' in result
    
    def test_to_shell(self):
        """Test shell export format."""
        proxy = EnvProxy()
        proxy._loaded = True
        proxy._cache = {"API_KEY": "secret123"}
        
        result = proxy.to_shell()
        assert 'export API_KEY="secret123"' in result
    
    def test_clear(self):
        """Test clearing cached data."""
        proxy = EnvProxy()
        proxy._loaded = True
        proxy._cache = {"KEY": "value"}
        proxy._record_id = "123"
        
        proxy.clear()
        
        assert not proxy._loaded
        assert proxy._cache == {}
        assert proxy._record_id is None
    
    def test_repr(self):
        """Test string representation."""
        proxy = EnvProxy()
        assert "not loaded" in repr(proxy)
        
        proxy._loaded = True
        proxy._cache = {"A": "1", "B": "2"}
        proxy._record_id = "test-record"
        
        rep = repr(proxy)
        assert "loaded" in rep
        assert "2 vars" in rep
        assert "test-record" in rep
