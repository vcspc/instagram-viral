"""Controle de taxa e resiliência contra bloqueios do Instagram."""
import logging
import random
import time

logger = logging.getLogger(__name__)


class RateLimiter:
    """Gerencia atrasos com jitter aleatório e backoff exponencial."""

    def __init__(self, delay_min: float = 3.0, delay_max: float = 6.0):
        self.delay_min = delay_min
        self.delay_max = delay_max
        self._consecutive_errors = 0

    def wait(self) -> None:
        """Aplica um jitter aleatório entre requisições."""
        sleep_time = random.uniform(self.delay_min, self.delay_max)
        logger.debug(f"Pausa de segurança: {sleep_time:.2f}s")
        time.sleep(sleep_time)

    def handle_rate_limit(self) -> None:
        """Aplica espera progressiva ao detectar rate limiting."""
        self._consecutive_errors += 1
        wait_seconds = min(60 * (2 ** (self._consecutive_errors - 1)), 600)
        logger.warning(
            f"Alerta de rate limit detectado no Instagram! Pausando por {wait_seconds}s para proteger a conta..."
        )
        time.sleep(wait_seconds)

    def reset_errors(self) -> None:
        """Reinicia o contador de erros consecutivos após sucesso."""
        self._consecutive_errors = 0
