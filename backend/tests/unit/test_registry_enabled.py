"""
Fase 11.2a — daftar metode aktif dari master data Pengaturan Forecast, BUKAN env.

`get_enabled_methods(enabled)`: None (belum diatur) → seluruh metode di MODEL_REGISTRY;
daftar diisi → irisan dengan registry (nama tak dikenal diabaikan).
"""
from app.services.forecasting import registry


def test_default_seluruh_registry():
    assert registry.get_enabled_methods() == set(registry.MODEL_REGISTRY)
    assert registry.get_enabled_methods(None) == set(registry.MODEL_REGISTRY)


def test_irisan_dengan_registry():
    assert registry.get_enabled_methods(["moving_average", "xgboost", "prophet"]) == {"moving_average", "xgboost"}


def test_available_methods_urut():
    assert registry.available_methods() == sorted(registry.MODEL_REGISTRY)
    assert "ets" not in registry.available_methods()  # legacy tidak terdaftar


def test_tidak_lagi_membaca_env():
    from app.config import get_settings

    assert not hasattr(get_settings(), "FORECAST_ENGINES_ENABLED")
