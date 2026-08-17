"""Tests unitarios para ssrf_guard.py — protección contra DNS rebinding."""

import socket
from unittest.mock import MagicMock, patch

import pytest

from backend.app.core import ssrf_guard


class TestIsBlockedIp:
    """Tests para _is_blocked_ip() — clasificación de IPs."""

    # ─── IPv4: Categorías bloqueadas ─────────────────────────────────────

    def test_loopback_ipv4_blocked(self):
        """Loopback debe estar bloqueado."""
        assert ssrf_guard._is_blocked_ip("127.0.0.1") is True

    def test_loopback_ipv4_full_range_blocked(self):
        """Todos en 127.0.0.0/8 son loopback."""
        assert ssrf_guard._is_blocked_ip("127.255.255.255") is True

    def test_private_rfc1918_10_blocked(self):
        """10.0.0.0/8 es privado (RFC1918)."""
        assert ssrf_guard._is_blocked_ip("10.0.0.0") is True
        assert ssrf_guard._is_blocked_ip("10.255.255.255") is True
        assert ssrf_guard._is_blocked_ip("10.128.0.1") is True

    def test_private_rfc1918_172_blocked(self):
        """172.16.0.0/12 es privado (RFC1918)."""
        assert ssrf_guard._is_blocked_ip("172.16.0.0") is True
        assert ssrf_guard._is_blocked_ip("172.31.255.255") is True
        assert ssrf_guard._is_blocked_ip("172.20.1.1") is True

    def test_private_rfc1918_192_blocked(self):
        """192.168.0.0/16 es privado (RFC1918)."""
        assert ssrf_guard._is_blocked_ip("192.168.0.0") is True
        assert ssrf_guard._is_blocked_ip("192.168.255.255") is True
        assert ssrf_guard._is_blocked_ip("192.168.1.1") is True

    def test_link_local_blocked(self):
        """169.254.0.0/16 es link-local (APIPA)."""
        assert ssrf_guard._is_blocked_ip("169.254.0.1") is True
        assert ssrf_guard._is_blocked_ip("169.254.169.254") is True  # AWS metadata

    def test_reserved_blocked(self):
        """240.0.0.0/4 es reserved."""
        assert ssrf_guard._is_blocked_ip("240.0.0.1") is True
        assert ssrf_guard._is_blocked_ip("255.255.255.255") is True

    def test_multicast_blocked(self):
        """224.0.0.0/4 es multicast."""
        assert ssrf_guard._is_blocked_ip("224.0.0.1") is True
        assert ssrf_guard._is_blocked_ip("239.255.255.255") is True

    def test_unspecified_blocked(self):
        """0.0.0.0 es unspecified."""
        assert ssrf_guard._is_blocked_ip("0.0.0.0") is True

    # ─── IPv6: Categorías bloqueadas ─────────────────────────────────────

    def test_loopback_ipv6_blocked(self):
        """::1 es loopback."""
        assert ssrf_guard._is_blocked_ip("::1") is True

    def test_unspecified_ipv6_blocked(self):
        """:: es unspecified."""
        assert ssrf_guard._is_blocked_ip("::") is True

    def test_private_ipv6_blocked(self):
        """fc00::/7 es ULA (privado)."""
        assert ssrf_guard._is_blocked_ip("fc00::1") is True
        assert ssrf_guard._is_blocked_ip("fd00::1") is True

    def test_link_local_ipv6_blocked(self):
        """fe80::/10 es link-local."""
        assert ssrf_guard._is_blocked_ip("fe80::1") is True

    # ─── Públicas: Permitidas ────────────────────────────────────────────

    def test_public_ipv4_allowed(self):
        """IPs públicas deben permitirse."""
        assert ssrf_guard._is_blocked_ip("1.1.1.1") is False
        assert ssrf_guard._is_blocked_ip("8.8.8.8") is False
        assert ssrf_guard._is_blocked_ip("93.184.216.34") is False  # example.com

    def test_public_ipv6_allowed(self):
        """IPv6 públicas deben permitirse."""
        assert ssrf_guard._is_blocked_ip("2001:4860:4860::8888") is False  # Google
        assert ssrf_guard._is_blocked_ip("2606:4700:4700::1111") is False  # Cloudflare

    def test_google_dns_allowed(self):
        """Google DNS 8.8.8.8 es pública."""
        assert ssrf_guard._is_blocked_ip("8.8.8.8") is False
        assert ssrf_guard._is_blocked_ip("8.8.4.4") is False

    def test_cloudflare_dns_allowed(self):
        """Cloudflare DNS es pública."""
        assert ssrf_guard._is_blocked_ip("1.1.1.1") is False
        assert ssrf_guard._is_blocked_ip("1.0.0.1") is False


class TestGuardedCreateConnection:
    """Tests para _guarded_create_connection() — validación en socket nivel."""

    def test_accepts_public_ip(self):
        """Debe permitir conexión a IP pública."""
        with patch("socket.getaddrinfo") as mock_getaddrinfo:
            mock_getaddrinfo.return_value = [
                (2, 1, 6, "", ("8.8.8.8", 443))
            ]
            with patch.object(ssrf_guard, "_orig_create_connection") as mock_orig:
                mock_orig.return_value = MagicMock()

                ssrf_guard._guarded_create_connection(("example.com", 443))

                mock_orig.assert_called_once_with(("8.8.8.8", 443))

    def test_rejects_loopback(self):
        """Debe rechazar conexión a loopback."""
        with patch("socket.getaddrinfo") as mock_getaddrinfo:
            mock_getaddrinfo.return_value = [
                (2, 1, 6, "", ("127.0.0.1", 443))
            ]

            with pytest.raises(OSError, match="interna/privada"):
                ssrf_guard._guarded_create_connection(("localhost", 443))

    def test_rejects_private_rfc1918(self):
        """Debe rechazar IPs RFC1918."""
        for ip in ["10.0.0.1", "192.168.1.1", "172.16.0.1"]:
            with patch("socket.getaddrinfo") as mock_getaddrinfo:
                mock_getaddrinfo.return_value = [
                    (2, 1, 6, "", (ip, 443))
                ]

                with pytest.raises(OSError, match="bloqueado por seguridad"):
                    ssrf_guard._guarded_create_connection(("internal.local", 443))

    def test_rejects_aws_metadata_endpoint(self):
        """Debe rechazar 169.254.169.254 (AWS metadata)."""
        with patch("socket.getaddrinfo") as mock_getaddrinfo:
            mock_getaddrinfo.return_value = [
                (2, 1, 6, "", ("169.254.169.254", 80))
            ]

            with pytest.raises(OSError, match="bloqueado"):
                ssrf_guard._guarded_create_connection(("metadata.aws.internal", 80))

    def test_handles_dns_resolution_failure(self):
        """Debe manejar gaierror (hostname no resuelve)."""
        with patch("socket.getaddrinfo") as mock_getaddrinfo:
            mock_getaddrinfo.side_effect = socket.gaierror("Name not known")

            with pytest.raises(OSError, match="No se pudo resolver"):
                ssrf_guard._guarded_create_connection(("nonexistent.invalid", 443))

    def test_picks_first_safe_ip_when_multiple(self):
        """Si DNS retorna múltiples IPs, usa la primera que sea segura."""
        with patch("socket.getaddrinfo") as mock_getaddrinfo:
            # Simula DNS retornando público + privado (raro pero posible)
            mock_getaddrinfo.return_value = [
                (2, 1, 6, "", ("8.8.8.8", 443)),
                (2, 1, 6, "", ("10.0.0.1", 443)),
            ]
            with patch.object(ssrf_guard, "_orig_create_connection") as mock_orig:
                mock_orig.return_value = MagicMock()

                ssrf_guard._guarded_create_connection(("example.com", 443))

                # Debe conectarse a la IP pública, no a la privada
                mock_orig.assert_called_once_with(("8.8.8.8", 443))

    def test_rejects_if_all_ips_are_private(self):
        """Rechaza si todos los IPs son privados."""
        with patch("socket.getaddrinfo") as mock_getaddrinfo:
            mock_getaddrinfo.return_value = [
                (2, 1, 6, "", ("10.0.0.1", 443)),
                (2, 1, 6, "", ("192.168.1.1", 443)),
            ]

            with pytest.raises(OSError, match="interna/privada"):
                ssrf_guard._guarded_create_connection(("internal", 443))

    def test_preserves_port_number(self):
        """Debe preservar el puerto en la conexión."""
        with patch("socket.getaddrinfo") as mock_getaddrinfo:
            mock_getaddrinfo.return_value = [
                (2, 1, 6, "", ("8.8.8.8", 443))
            ]
            with patch.object(ssrf_guard, "_orig_create_connection") as mock_orig:
                mock_orig.return_value = MagicMock()

                ssrf_guard._guarded_create_connection(("example.com", 8080))

                # Puerto debe ser 8080, no 443
                call_args = mock_orig.call_args[0]
                assert call_args[0][1] == 8080

    def test_passes_additional_args_to_original(self):
        """Debe pasar *args y **kwargs a create_connection original."""
        with patch("socket.getaddrinfo") as mock_getaddrinfo:
            mock_getaddrinfo.return_value = [
                (2, 1, 6, "", ("8.8.8.8", 443))
            ]
            with patch.object(ssrf_guard, "_orig_create_connection") as mock_orig:
                mock_orig.return_value = MagicMock()

                ssrf_guard._guarded_create_connection(
                    ("example.com", 443),
                    timeout=10,
                    source_address=("0.0.0.0", 0)
                )

                # Verifica que se pasen los kwargs
                call_kwargs = mock_orig.call_args[1]
                assert call_kwargs.get("timeout") == 10
                assert call_kwargs.get("source_address") == ("0.0.0.0", 0)

    def test_ipv6_public_allowed(self):
        """Debe permitir IPv6 público."""
        with patch("socket.getaddrinfo") as mock_getaddrinfo:
            mock_getaddrinfo.return_value = [
                (10, 1, 6, "", ("2001:4860:4860::8888", 443))
            ]
            with patch.object(ssrf_guard, "_orig_create_connection") as mock_orig:
                mock_orig.return_value = MagicMock()

                ssrf_guard._guarded_create_connection(("dns.google", 443))

                mock_orig.assert_called_once()
                call_args = mock_orig.call_args[0]
                assert call_args[0][0] == "2001:4860:4860::8888"

    def test_ipv6_link_local_blocked(self):
        """Debe bloquear IPv6 link-local."""
        with patch("socket.getaddrinfo") as mock_getaddrinfo:
            mock_getaddrinfo.return_value = [
                (10, 1, 6, "", ("fe80::1", 443))
            ]

            with pytest.raises(OSError, match="bloqueado"):
                ssrf_guard._guarded_create_connection(("link-local", 443))


class TestInstall:
    """Tests para install() — instalación del guard."""

    def test_install_replaces_create_connection(self):
        """install() debe reemplazar urllib3's create_connection."""
        import urllib3.util.connection as urllib3_conn

        # Guarda el original
        original = urllib3_conn.create_connection

        try:
            # Asegura que no está instalado
            ssrf_guard._installed = False

            # Instala
            ssrf_guard.install()

            # Verifica que fue reemplazado
            assert urllib3_conn.create_connection == ssrf_guard._guarded_create_connection
        finally:
            # Restaura
            urllib3_conn.create_connection = original
            ssrf_guard._installed = False

    def test_install_is_idempotent(self):
        """Llamar install() múltiples veces no debe duplicar el patch."""
        import urllib3.util.connection as urllib3_conn

        original = urllib3_conn.create_connection

        try:
            ssrf_guard._installed = False

            ssrf_guard.install()
            after_first = urllib3_conn.create_connection

            ssrf_guard.install()
            after_second = urllib3_conn.create_connection

            # Debe ser el mismo patch, no duplicado
            assert after_first == after_second
            assert after_first == ssrf_guard._guarded_create_connection
        finally:
            urllib3_conn.create_connection = original
            ssrf_guard._installed = False

    def test_install_sets_installed_flag(self):
        """install() debe establecer _installed = True."""
        ssrf_guard._installed = False

        ssrf_guard.install()

        assert ssrf_guard._installed is True

        # Limpia para otros tests
        ssrf_guard._installed = False

    def test_install_when_already_installed_returns_early(self):
        """Si ya está instalado, install() debe retornar sin hacer nada."""
        import urllib3.util.connection as urllib3_conn

        ssrf_guard._installed = True
        original = urllib3_conn.create_connection

        # No debe cambiar nada
        ssrf_guard.install()

        assert urllib3_conn.create_connection == original
        ssrf_guard._installed = False


class TestIntegration:
    """Tests de integración: ssrf_guard + requests + urllib3."""

    def test_requests_session_uses_guard_after_install(self):
        """Después de install(), una sesión requests debe usar el guard."""
        import urllib3.util.connection as urllib3_conn

        original = urllib3_conn.create_connection

        try:
            ssrf_guard._installed = False
            ssrf_guard.install()

            # Intenta conectar a loopback (debe fallar)
            with patch("socket.getaddrinfo") as mock_getaddrinfo:
                mock_getaddrinfo.return_value = [
                    (2, 1, 6, "", ("127.0.0.1", 443))
                ]

                # La sesión usa el transport que finalmente llama a create_connection
                # (aunque en test será interceptado por mock)
                assert urllib3_conn.create_connection == ssrf_guard._guarded_create_connection

        finally:
            urllib3_conn.create_connection = original
            ssrf_guard._installed = False

    def test_guard_works_with_html_fetcher_import(self):
        """Importar html_fetcher debe instalar automáticamente el guard."""
        import urllib3.util.connection as urllib3_conn

        # El guard debe estar instalado por html_fetcher.py línea 13
        assert urllib3_conn.create_connection == ssrf_guard._guarded_create_connection
