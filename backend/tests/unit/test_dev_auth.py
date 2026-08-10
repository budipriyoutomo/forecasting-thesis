"""
Unit test DevAuthenticator — authenticator lokal khusus development.

Fokus test: guard-nya. Authenticator ini melewati Supabase Auth, jadi yang wajib
dijamin adalah ia MUSTAHIL aktif di luar ENVIRONMENT=development.
"""
import pytest

from app.config import Settings
from app.services.dev_auth import DevAuthenticator, DevAuthNotAllowedError, build_authenticator
from app.services.supabase_auth import SupabaseAuthenticator
from app.utils.exceptions import InvalidCredentialsError


def _settings(**overrides) -> Settings:
    base = {
        "ENVIRONMENT": "development",
        "DEV_AUTH_ENABLED": True,
        "DEV_AUTH_PASSWORD": "demo1234",
        "SUPABASE_URL": None,
        "SUPABASE_KEY": None,
    }
    base.update(overrides)
    return Settings(**base)


@pytest.mark.asyncio
async def test_password_benar_menghasilkan_identity():
    auth = DevAuthenticator(_settings())

    identity = await auth.authenticate("admin@forecastiq.dev", "demo1234")

    assert identity.email == "admin@forecastiq.dev"
    assert identity.id


@pytest.mark.asyncio
async def test_password_salah_ditolak():
    auth = DevAuthenticator(_settings())

    with pytest.raises(InvalidCredentialsError):
        await auth.authenticate("admin@forecastiq.dev", "salah")


@pytest.mark.parametrize("environment", ["production", "staging"])
def test_menolak_dibuat_di_luar_development(environment):
    with pytest.raises(DevAuthNotAllowedError):
        DevAuthenticator(_settings(ENVIRONMENT=environment))


def test_menolak_password_kosong():
    with pytest.raises(DevAuthNotAllowedError):
        DevAuthenticator(_settings(DEV_AUTH_PASSWORD=""))


def test_build_authenticator_pilih_dev_saat_flag_aktif():
    assert isinstance(build_authenticator(_settings()), DevAuthenticator)


def test_build_authenticator_pilih_supabase_saat_flag_mati():
    auth = build_authenticator(_settings(DEV_AUTH_ENABLED=False))
    assert isinstance(auth, SupabaseAuthenticator)


@pytest.mark.parametrize("environment", ["production", "staging"])
def test_build_authenticator_abaikan_flag_di_luar_development(environment):
    """Flag DEV_AUTH_ENABLED yang ikut ter-deploy tidak boleh membuka bypass."""
    auth = build_authenticator(_settings(ENVIRONMENT=environment))
    assert isinstance(auth, SupabaseAuthenticator)
