# logger.py
# Fase 3: Audit logging (privacy-proof)

"""
logger.py
=========

Verantwoordelijkheid:
    Privacy-proof audit logging voor compliance en controle.

Functies:
    - configureer_logger: Initialiseert logging naar bestand
    - log_vergelijking_start: Logt start van vergelijking
    - log_vergelijking_resultaat: Logt resultaten (zonder gevoelige data)

Privacyregels:
    ✅ WEL loggen: timestamps, bestandsnamen, aantallen, toleranties
    ❌ NIET loggen: bedragen, artikelcodes, artikelnamen
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import Dict
import sys

# Voeg parent directory toe zodat config.py gevonden kan worden
sys.path.append(str(Path(__file__).parent.parent))
import config


def configureer_logger(log_directory: Path = None, log_level: int = logging.INFO) -> logging.Logger:
    """
    Configureert de audit logger.
    
    Parameters
    ----------
    log_directory : Path, optional
        Directory waar logbestanden opgeslagen worden.
        Default: ./logs
    log_level : int, optional
        Logging level (bijv. logging.INFO, logging.DEBUG).
        Default: logging.INFO
    
    Returns
    -------
    logging.Logger
        Geconfigureerde logger instance.
    
    Voorbeelden
    -----------
    >>> logger = configureer_logger()
    >>> logger.info("Test bericht")
    """
    
    # Gebruik standaard log directory als niet opgegeven
    if log_directory is None:
        log_directory = Path('./logs')
    
    # Zorg dat directory bestaat
    log_directory.mkdir(parents=True, exist_ok=True)
    
    # Genereer logbestandsnaam met datum
    log_bestandsnaam = f"factuur_vergelijker_{datetime.now().strftime('%Y%m%d')}.log"
    log_pad = log_directory / log_bestandsnaam
    
    # Configureer logger
    logger = logging.getLogger('factuur_vergelijker')
    logger.setLevel(log_level)
    
    # Voorkom dubbele handlers als logger al bestaat
    if logger.handlers:
        return logger
    
    # File handler
    file_handler = logging.FileHandler(log_pad, encoding='utf-8')
    file_handler.setLevel(log_level)
    
    # Formatter
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    # Voeg handler toe
    logger.addHandler(file_handler)
    
    return logger


def log_vergelijking_start(
    logger: logging.Logger,
    bestandsnaam_systeem: str,
    bestandsnaam_factuur: str,
    aantal_regels_systeem: int,
    aantal_regels_factuur: int
):
    """
    Logt de start van een vergelijking.
    
    Parameters
    ----------
    logger : logging.Logger
        Logger instance.
    bestandsnaam_systeem : str
        Naam van systeemexport bestand.
    bestandsnaam_factuur : str
        Naam van leveranciersfactuur bestand.
    aantal_regels_systeem : int
        Aantal regels in systeemexport.
    aantal_regels_factuur : int
        Aantal regels in leveranciersfactuur.
    """
    
    logger.info("=" * 70)
    logger.info("VERGELIJKING GESTART")
    logger.info("-" * 70)
    logger.info(f"Systeembestand: {bestandsnaam_systeem} ({aantal_regels_systeem} regels)")
    logger.info(f"Leveranciersbestand: {bestandsnaam_factuur} ({aantal_regels_factuur} regels)")
    logger.info(f"Toleranties gebruikt:")
    logger.info(f"  - Prijs: €{config.TOLERANTIE_PRIJS}")
    logger.info(f"  - Totaal: €{config.TOLERANTIE_TOTAAL}")
    logger.info(f"  - Aantal: {config.TOLERANTIE_AANTAL}")
    logger.info(f"  - BTW: {config.TOLERANTIE_BTW}%")


def log_matching_resultaat(
    logger: logging.Logger,
    aantal_gematchte_regels: int,
    aantal_systeem_zonder_match: int,
    aantal_factuur_zonder_match: int
):
    """
    Logt resultaten van de matching-fase.
    
    Parameters
    ----------
    logger : logging.Logger
        Logger instance.
    aantal_gematchte_regels : int
        Aantal succesvol gematchte regels.
    aantal_systeem_zonder_match : int
        Aantal systeemregels zonder match.
    aantal_factuur_zonder_match : int
        Aantal factuurregels zonder match.
    """
    
    logger.info("-" * 70)
    logger.info("MATCHING VOLTOOID")
    logger.info(f"  - Gematchte regels: {aantal_gematchte_regels}")
    logger.info(f"  - Systeemregels zonder match: {aantal_systeem_zonder_match}")
    logger.info(f"  - Factuurregels zonder match: {aantal_factuur_zonder_match}")


def log_vergelijking_resultaat(
    logger: logging.Logger,
    samenvatting: Dict,
    verwerkingstijd: float,
    output_bestand: Path = None
):
    """
    Logt de resultaten van een vergelijking (privacy-proof).
    
    Parameters
    ----------
    logger : logging.Logger
        Logger instance.
    samenvatting : dict
        Samenvatting zoals gegenereerd door reporter.genereer_samenvatting().
    verwerkingstijd : float
        Verwerkingstijd in seconden.
    output_bestand : Path, optional
        Pad naar gegenereerd Excel-bestand.
    """
    
    logger.info("-" * 70)
    logger.info("VERGELIJKING AFGEROND")
    logger.info(f"Totaal regels verwerkt: {samenvatting['totaal_regels']}")
    logger.info("Resultaten per status:")
    
    status_counts = samenvatting['status_counts']
    
    for status_key in [
        config.STATUS_OK,
        config.STATUS_AFWIJKING,
        config.STATUS_ONTBREEKT_FACTUUR,
        config.STATUS_ONTBREEKT_SYSTEEM,
        config.STATUS_GEDEELTELIJK,
        config.STATUS_FOUT
    ]:
        aantal = status_counts.get(status_key, 0)
        logger.info(f"  - {status_key}: {aantal}")
    
    logger.info(f"Verwerkingstijd: {verwerkingstijd:.2f} seconden")
    
    if output_bestand:
        logger.info(f"Output bestand: {output_bestand.name}")
    
    logger.info("=" * 70)


def log_fout(logger: logging.Logger, foutmelding: str, details: str = None):
    """
    Logt een fout tijdens de vergelijking.
    
    Parameters
    ----------
    logger : logging.Logger
        Logger instance.
    foutmelding : str
        Korte foutomschrijving.
    details : str, optional
        Aanvullende details over de fout.
    """
    
    logger.error(f"FOUT: {foutmelding}")
    if details:
        logger.error(f"Details: {details}")