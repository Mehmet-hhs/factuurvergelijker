# formatter.py
# v1.2.2: Number formatting voor gebruiksvriendelijke presentatie

"""
formatter.py
============

Verantwoordelijkheid:
    Centraal punt voor number formatting in Excel en Streamlit.

Functies:
    - formatteer_aantal: Float → Integer string (10.0 → "10")
    - formatteer_prijs: Float → Valuta string (10.80 → "€10,80")
    - formatteer_excel_kolom: Zet Excel number format per kolom

Belangrijk:
    Data blijft intern float voor berekeningen.
    Alleen presentatie-laag gebruikt formatting.
"""

from typing import Optional
import pandas as pd


def formatteer_aantal(waarde: Optional[float]) -> str:
    """
    Formatteert aantal als integer (zonder decimalen).

    Parameters
    ----------
    waarde : float, optional
        Numerieke waarde (aantal producten).

    Returns
    -------
    str
        Geformatteerde string zonder decimalen, of lege string bij None/NaN.

    Voorbeelden
    -----------
    >>> formatteer_aantal(10.0)
    '10'
    >>> formatteer_aantal(1.0)
    '1'
    >>> formatteer_aantal(None)
    ''
    >>> formatteer_aantal(np.nan)
    ''
    """
    if pd.isna(waarde) or waarde is None:
        return ""

    try:
        return f"{int(waarde)}"
    except (ValueError, TypeError):
        return ""


def formatteer_prijs(waarde: Optional[float]) -> str:
    """
    Formatteert prijs als valuta met Nederlandse locale (€X.XXX,XX).

    Parameters
    ----------
    waarde : float, optional
        Numerieke waarde (prijs in euro's).

    Returns
    -------
    str
        Geformatteerde valuta string, of lege string bij None/NaN.

    Voorbeelden
    -----------
    >>> formatteer_prijs(10.80)
    '€10,80'
    >>> formatteer_prijs(1234.56)
    '€1.234,56'
    >>> formatteer_prijs(0.99)
    '€0,99'
    >>> formatteer_prijs(None)
    ''
    """
    if pd.isna(waarde) or waarde is None:
        return ""

    try:
        # Python default: 1,234.56 (comma = thousands, dot = decimal)
        formatted = f"{waarde:,.2f}"

        # Converteer naar Nederlandse locale: 1.234,56
        # Stap 1: Comma → X (tijdelijk)
        # Stap 2: Dot → Comma (decimaal)
        # Stap 3: X → Dot (duizendtallen)
        nl_formatted = formatted.replace(',', 'X').replace('.', ',').replace('X', '.')

        return f"€{nl_formatted}"
    except (ValueError, TypeError):
        return ""


def formatteer_excel_kolom(worksheet, kolom_letter: str, kolom_type: str):
    """
    Zet Excel number format voor hele kolom.

    Parameters
    ----------
    worksheet : openpyxl.worksheet.worksheet.Worksheet
        Excel worksheet om te formatteren.
    kolom_letter : str
        Kolom letter (bijv. 'B', 'C', 'D').
    kolom_type : str
        Type formatting: 'aantal' of 'prijs'.

    Voorbeelden
    -----------
    >>> formatteer_excel_kolom(worksheet, 'C', 'aantal')
    >>> formatteer_excel_kolom(worksheet, 'E', 'prijs')
    """
    # Bepaal Excel format code
    if kolom_type == 'aantal':
        format_code = '0'  # Integer zonder decimalen
    elif kolom_type == 'prijs':
        # Nederlandse valuta format: [$€-413] = Euro symbool met NL locale
        format_code = '[$€-413] #,##0.00'
    else:
        # Default: geen speciale formatting
        return

    # Pas format toe op alle cellen in kolom (behalve header)
    for cell in worksheet[kolom_letter]:
        if cell.row > 1:  # Skip header rij
            cell.number_format = format_code


def formatteer_dataframe_voor_display(df: pd.DataFrame, kolom_config: dict) -> pd.DataFrame:
    """
    Formatteert DataFrame kolommen voor display (gebruikt voor preview).

    NIET GEBRUIKT in v1.2.2 (we gebruiken pandas .style.format() direct).
    Bewaard voor toekomstige uitbreidingen.

    Parameters
    ----------
    df : pd.DataFrame
        Originele DataFrame met float waarden.
    kolom_config : dict
        Mapping van kolom naam naar type: {'aantal_systeem': 'aantal', 'prijs_systeem': 'prijs'}

    Returns
    -------
    pd.DataFrame
        Nieuwe DataFrame met geformatteerde strings (voor display only).
    """
    df_display = df.copy()

    for kolom, kolom_type in kolom_config.items():
        if kolom in df_display.columns:
            if kolom_type == 'aantal':
                df_display[kolom] = df_display[kolom].apply(formatteer_aantal)
            elif kolom_type == 'prijs':
                df_display[kolom] = df_display[kolom].apply(formatteer_prijs)

    return df_display
