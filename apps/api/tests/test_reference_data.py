"""
Tests for reference data registries.
"""

import pytest
from app.reference_data.ports import PortRegistry, get_port_registry
from app.reference_data.currencies import CurrencyRegistry, get_currency_registry
from app.reference_data.countries import CountryRegistry, get_country_registry


class TestPortRegistry:
    """Tests for UN/LOCODE port registry."""
    
    def test_basic_lookup(self):
        registry = PortRegistry()
        
        # By code
        port = registry.get_by_code("BDCGP")
        assert port is not None
        assert port.name == "Chittagong"
        assert port.country_code == "BD"
    
    def test_resolve_by_name(self):
        registry = PortRegistry()
        
        # Exact name
        port = registry.resolve("Chittagong")
        assert port is not None
        assert port.code == "BDCGP"
    
    def test_resolve_alias(self):
        registry = PortRegistry()
        
        # Alias: Chattogram is the Bengali name for Chittagong
        port = registry.resolve("Chattogram")
        assert port is not None
        assert port.code == "BDCGP"
    
    def test_same_port(self):
        registry = PortRegistry()
        
        # Different spellings of the same port
        assert registry.same_port("Chittagong", "Chattogram")
        assert registry.same_port("Chittagong", "CTG")
        assert registry.same_port("Hong Kong", "Hongkong")
        assert registry.same_port("New York", "NYC")
        
        # Different ports
        assert not registry.same_port("Chittagong", "Shanghai")
        assert not registry.same_port("New York", "Los Angeles")
    
    def test_port_with_country(self):
        registry = PortRegistry()
        
        # Port name with country
        port = registry.resolve("Chittagong, Bangladesh")
        assert port is not None
        assert port.code == "BDCGP"
    
    def test_case_insensitive(self):
        registry = PortRegistry()
        
        assert registry.same_port("CHITTAGONG", "chittagong")
        assert registry.same_port("New York", "NEW YORK")
    
    def test_canonical_name(self):
        registry = PortRegistry()
        
        canonical = registry.get_canonical_name("CTG")
        assert "Chittagong" in canonical
        assert "Bangladesh" in canonical


class TestCurrencyRegistry:
    """Tests for ISO 4217 currency registry."""
    
    def test_basic_lookup(self):
        registry = CurrencyRegistry()
        
        usd = registry.get("USD")
        assert usd is not None
        assert usd.name == "US Dollar"
        assert usd.decimals == 2
    
    def test_is_valid(self):
        registry = CurrencyRegistry()
        
        assert registry.is_valid("USD")
        assert registry.is_valid("EUR")
        assert registry.is_valid("BDT")
        assert not registry.is_valid("XYZ")
        assert not registry.is_valid("INVALID")
    
    def test_normalize(self):
        registry = CurrencyRegistry()
        
        assert registry.normalize("USD") == "USD"
        assert registry.normalize("usd") == "USD"
        assert registry.normalize("DOLLAR") == "USD"
        assert registry.normalize("US DOLLAR") == "USD"
        assert registry.normalize("TAKA") == "BDT"
    
    def test_parse_amount(self):
        registry = CurrencyRegistry()
        
        result = registry.parse_amount("USD 125,000.00")
        assert result is not None
        assert result["currency"] == "USD"
        assert result["value"] == 125000.0
        
        result = registry.parse_amount("100000 EUR")
        assert result is not None
        assert result["currency"] == "EUR"
        assert result["value"] == 100000.0


class TestCountryRegistry:
    """Tests for ISO 3166 country registry."""
    
    def test_basic_lookup(self):
        registry = CountryRegistry()
        
        country = registry.get("BD")
        assert country is not None
        assert country.name == "Bangladesh"
        assert country.alpha3 == "BGD"
    
    def test_resolve_by_name(self):
        registry = CountryRegistry()
        
        country = registry.resolve("Bangladesh")
        assert country is not None
        assert country.alpha2 == "BD"
    
    def test_resolve_alias(self):
        registry = CountryRegistry()
        
        # UK aliases
        assert registry.resolve("UK").alpha2 == "GB"
        assert registry.resolve("United Kingdom").alpha2 == "GB"
        assert registry.resolve("Great Britain").alpha2 == "GB"
        
        # US aliases
        assert registry.resolve("USA").alpha2 == "US"
        assert registry.resolve("United States").alpha2 == "US"
        assert registry.resolve("America").alpha2 == "US"
    
    def test_same_country(self):
        registry = CountryRegistry()
        
        assert registry.same_country("USA", "United States")
        assert registry.same_country("UK", "United Kingdom")
        assert not registry.same_country("USA", "UK")


class TestSingletons:
    """Test that singleton accessors work."""
    
    def test_port_singleton(self):
        r1 = get_port_registry()
        r2 = get_port_registry()
        assert r1 is r2
    
    def test_currency_singleton(self):
        r1 = get_currency_registry()
        r2 = get_currency_registry()
        assert r1 is r2
    
    def test_country_singleton(self):
        r1 = get_country_registry()
        r2 = get_country_registry()
        assert r1 is r2

