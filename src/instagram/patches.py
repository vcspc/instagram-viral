"""Patches de compatibilidade para instagrapi e bibliotecas de terceiros."""
import logging

logger = logging.getLogger(__name__)


def apply_patches():
    """Aplica correções em tempo de execução para instagrapi e PyAV."""
    # 1. Patch de password_publickeys no instagrapi (substitui o endpoint 404 qe/sync)
    try:
        from instagrapi.mixins.password import PasswordMixin

        def safe_password_publickeys(self):
            """Obtém chaves públicas de criptografia do Instagram via endpoints ativos."""
            candidate_endpoints = [
                "https://i.instagram.com/api/v1/launcher/mobileconfig/",
                "https://i.instagram.com/api/v1/qe/sync/",
            ]
            for url in candidate_endpoints:
                for sess in [self.private, self.public]:
                    try:
                        resp = sess.get(url, timeout=10)
                        kid = resp.headers.get("ig-set-password-encryption-key-id")
                        kpub = resp.headers.get("ig-set-password-encryption-pub-key")
                        if kid and kpub:
                            return int(kid), kpub
                    except Exception:
                        pass

            # Chave pública conhecida de fallback caso a rede bloqueie os endpoints pré-login
            fallback_kid = 187
            fallback_kpub = (
                "LS0tLS1CRUdJTiBQVUJMSUMgS0VZLS0tLS0KTUlJQklqQU5CZ2txaGtpRzl3MEJBUUVGQUFPQ0FROEFNSUlCQ2dL"
                "Q0FRRUF5Q2drcllIajI5eVFrVmVxdWMxMQpMTGhMOHl4bHZNeEpqVnhMSzhvcm5SdE1MNlJTbVEwR3I2bDVIdVZ1"
                "dDlhdDVHRUFKQjBxckU4Rmt1bThza1BDCjBuVTlvOWpqMklSbXl6cXpMNGV0WEhxSGVyWjdvL0JuVzdBOWd3Wmp0"
                "amFXTVlCY25qM1BjSU93TVpvcHE4OHEKNDY0NHg4VzJwcXZHQ3dZK2hJc1ptZkIrdmpLcUEwSGxoRFB3VDB3dGhp"
                "OHdabWRJRHY2Y013MEJ6NkdvTHdRWQpVRGh3Tm40WGRobmVSL1dxMU83Q1BZektVYnYraUpQVmdZSHRaWm9PUmln"
                "T1psaHlNajNmL3lDTXEvUGh0bDQ3Cnd3SXphWGlLWWZublM1N2NSOVBycW1EWnpqQTVqRTd0OTdwcndqUE9vRFFZ"
                "dXhnUVZ3b2duM2U5ZUszU21laloKeHdJREFRQUIKLS0tLS1FTkQgUFVCTElDIEtFWS0tLS0tCg=="
            )
            logger.warning("Usando chave de criptografia de fallback para o Instagram.")
            return fallback_kid, fallback_kpub

        PasswordMixin.password_publickeys = safe_password_publickeys
        logger.debug("Patch PasswordMixin.password_publickeys aplicado com sucesso.")
    except Exception as exc:
        logger.debug(f"Aviso ao aplicar patch de password_publickeys: {exc}")

    # 2. Patch de compatibilidade para PyAV (remove argumento metadata_errors depreciado)
    try:
        import av
        if hasattr(av, "open") and not getattr(av.open, "_patched", False):
            _original_av_open = av.open

            def _safe_av_open(*args, **kwargs):
                kwargs.pop("metadata_errors", None)
                return _original_av_open(*args, **kwargs)

            _safe_av_open._patched = True
            av.open = _safe_av_open
            logger.debug("Patch av.open aplicado com sucesso.")
    except Exception as exc:
        logger.debug(f"Aviso ao aplicar patch PyAV: {exc}")


# Aplica automaticamente ao importar o módulo
apply_patches()
