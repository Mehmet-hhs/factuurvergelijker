# test_aggregator.py
# Unit tests voor aggregator.py v1.3

"""
Unit tests voor multi-document aggregatie.

Test coverage:
- Basis aggregatie (2+ documenten)
- Weighted average prijs berekening
- Prijs inconsistentie detectie
- Edge cases (lege input, 1 document, aantal=0)
- Metadata tracking
- Warning generatie
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Voeg parent directory toe
sys.path.append(str(Path(__file__).parent.parent))

from modules.aggregator import (
    aggregeer_documenten,
    _detecteer_prijs_inconsistenties,
    _aggregeer_enkel_document,
    validate_aggregatie_resultaat,
    AggregatieResultaat
)
import config


# ============================================================================
# TESTS: BASIS AGGREGATIE
# ============================================================================

class TestBasisAggregatie:
    """Tests voor basis aggregatie functionaliteit."""

    def test_aggregeer_twee_documenten_zelfde_artikel(self):
        """Test aggregatie van 2 documenten met hetzelfde artikel."""
        df1 = pd.DataFrame({
            'artikelcode': ['A123'],
            'artikelnaam': ['Widget Pro'],
            'aantal': [10.0],
            'prijs_per_stuk': [5.0],
            'totaal': [50.0],
            'btw_percentage': [21.0]
        })

        df2 = pd.DataFrame({
            'artikelcode': ['A123'],
            'artikelnaam': ['Widget Pro'],
            'aantal': [5.0],
            'prijs_per_stuk': [5.0],
            'totaal': [25.0],
            'btw_percentage': [21.0]
        })

        result = aggregeer_documenten(
            df_list=[df1, df2],
            document_namen=["doc1.pdf", "doc2.pdf"],
            document_rollen=["pakbon", "pakbon"]
        )

        # Check aggregatie
        assert len(result.df_aggregaat) == 1
        assert result.df_aggregaat.iloc[0]['artikelcode'] == 'A123'
        assert result.df_aggregaat.iloc[0]['aantal'] == 15.0  # 10 + 5
        assert result.df_aggregaat.iloc[0]['totaal'] == 75.0  # 50 + 25
        assert result.df_aggregaat.iloc[0]['prijs_per_stuk'] == 5.0  # 75 / 15

    def test_aggregeer_verschillende_artikelen(self):
        """Test aggregatie met verschillende artikelen."""
        df1 = pd.DataFrame({
            'artikelcode': ['A123', 'B456'],
            'artikelnaam': ['Widget', 'Gadget'],
            'aantal': [10.0, 5.0],
            'prijs_per_stuk': [5.0, 10.0],
            'totaal': [50.0, 50.0],
            'btw_percentage': [21.0, 21.0]
        })

        df2 = pd.DataFrame({
            'artikelcode': ['A123'],
            'artikelnaam': ['Widget'],
            'aantal': [5.0],
            'prijs_per_stuk': [5.0],
            'totaal': [25.0],
            'btw_percentage': [21.0]
        })

        result = aggregeer_documenten(
            df_list=[df1, df2],
            document_namen=["doc1.pdf", "doc2.pdf"],
            document_rollen=["pakbon", "factuur"]
        )

        # Check aggregatie
        assert len(result.df_aggregaat) == 2

        # Widget: moet geaggregeerd zijn
        widget_row = result.df_aggregaat[result.df_aggregaat['artikelcode'] == 'A123'].iloc[0]
        assert widget_row['aantal'] == 15.0
        assert widget_row['totaal'] == 75.0

        # Gadget: moet ongemoeid zijn
        gadget_row = result.df_aggregaat[result.df_aggregaat['artikelcode'] == 'B456'].iloc[0]
        assert gadget_row['aantal'] == 5.0
        assert gadget_row['totaal'] == 50.0

    def test_aggregeer_drie_documenten(self):
        """Test aggregatie van 3 documenten."""
        df1 = pd.DataFrame({
            'artikelcode': ['A123'],
            'artikelnaam': ['Widget'],
            'aantal': [10.0],
            'prijs_per_stuk': [5.0],
            'totaal': [50.0],
            'btw_percentage': [21.0]
        })

        df2 = pd.DataFrame({
            'artikelcode': ['A123'],
            'artikelnaam': ['Widget'],
            'aantal': [5.0],
            'prijs_per_stuk': [5.0],
            'totaal': [25.0],
            'btw_percentage': [21.0]
        })

        df3 = pd.DataFrame({
            'artikelcode': ['A123'],
            'artikelnaam': ['Widget'],
            'aantal': [3.0],
            'prijs_per_stuk': [5.0],
            'totaal': [15.0],
            'btw_percentage': [21.0]
        })

        result = aggregeer_documenten(
            df_list=[df1, df2, df3],
            document_namen=["doc1.pdf", "doc2.pdf", "doc3.pdf"],
            document_rollen=["pakbon", "pakbon", "pakbon"]
        )

        # Check aggregatie
        assert len(result.df_aggregaat) == 1
        assert result.df_aggregaat.iloc[0]['aantal'] == 18.0  # 10 + 5 + 3
        assert result.df_aggregaat.iloc[0]['totaal'] == 90.0  # 50 + 25 + 15


# ============================================================================
# TESTS: WEIGHTED AVERAGE PRIJS
# ============================================================================

class TestWeightedAveragePrijs:
    """Tests voor weighted average prijs berekening."""

    def test_weighted_average_prijs(self):
        """Test correcte berekening van weighted average prijs."""
        df1 = pd.DataFrame({
            'artikelcode': ['A123'],
            'artikelnaam': ['Widget'],
            'aantal': [10.0],
            'prijs_per_stuk': [5.00],
            'totaal': [50.0],
            'btw_percentage': [21.0]
        })

        df2 = pd.DataFrame({
            'artikelcode': ['A123'],
            'artikelnaam': ['Widget'],
            'aantal': [5.0],
            'prijs_per_stuk': [6.00],
            'totaal': [30.0],
            'btw_percentage': [21.0]
        })

        result = aggregeer_documenten(
            df_list=[df1, df2],
            document_namen=["doc1.pdf", "doc2.pdf"],
            document_rollen=["pakbon", "pakbon"]
        )

        # Weighted average: (50 + 30) / (10 + 5) = 80 / 15 = 5.333...
        prijs = result.df_aggregaat.iloc[0]['prijs_per_stuk']
        assert abs(prijs - (80.0 / 15.0)) < 0.001

    def test_weighted_average_met_verschillende_hoeveelheden(self):
        """Test weighted average met sterk verschillende aantallen."""
        df1 = pd.DataFrame({
            'artikelcode': ['A123'],
            'artikelnaam': ['Widget'],
            'aantal': [100.0],
            'prijs_per_stuk': [5.00],
            'totaal': [500.0],
            'btw_percentage': [21.0]
        })

        df2 = pd.DataFrame({
            'artikelcode': ['A123'],
            'artikelnaam': ['Widget'],
            'aantal': [1.0],
            'prijs_per_stuk': [10.00],
            'totaal': [10.0],
            'btw_percentage': [21.0]
        })

        result = aggregeer_documenten(
            df_list=[df1, df2],
            document_namen=["doc1.pdf", "doc2.pdf"],
            document_rollen=["pakbon", "pakbon"]
        )

        # Weighted average: (500 + 10) / (100 + 1) = 510 / 101 ≈ 5.05
        prijs = result.df_aggregaat.iloc[0]['prijs_per_stuk']
        assert abs(prijs - 5.049) < 0.01


# ============================================================================
# TESTS: PRIJS INCONSISTENTIE DETECTIE
# ============================================================================

class TestPrijsInconsistentieDetectie:
    """Tests voor prijs inconsistentie detectie."""

    def test_detecteer_prijs_inconsistentie(self):
        """Test dat prijs inconsistenties worden gedetecteerd."""
        df1 = pd.DataFrame({
            'artikelcode': ['A123'],
            'artikelnaam': ['Widget'],
            'aantal': [10.0],
            'prijs_per_stuk': [5.00],
            'totaal': [50.0],
            'btw_percentage': [21.0]
        })

        df2 = pd.DataFrame({
            'artikelcode': ['A123'],
            'artikelnaam': ['Widget'],
            'aantal': [5.0],
            'prijs_per_stuk': [5.50],  # Verschil!
            'totaal': [27.5],
            'btw_percentage': [21.0]
        })

        result = aggregeer_documenten(
            df_list=[df1, df2],
            document_namen=["doc1.pdf", "doc2.pdf"],
            document_rollen=["pakbon", "factuur"]
        )

        # Check warning
        assert len(result.warnings) > 0
        assert any('A123' in w for w in result.warnings)
        assert any('verschillende prijzen' in w.lower() for w in result.warnings)

    def test_geen_warning_bij_identieke_prijzen(self):
        """Test dat geen warning komt bij identieke prijzen."""
        df1 = pd.DataFrame({
            'artikelcode': ['A123'],
            'artikelnaam': ['Widget'],
            'aantal': [10.0],
            'prijs_per_stuk': [5.00],
            'totaal': [50.0],
            'btw_percentage': [21.0]
        })

        df2 = pd.DataFrame({
            'artikelcode': ['A123'],
            'artikelnaam': ['Widget'],
            'aantal': [5.0],
            'prijs_per_stuk': [5.00],  # Zelfde prijs
            'totaal': [25.0],
            'btw_percentage': [21.0]
        })

        result = aggregeer_documenten(
            df_list=[df1, df2],
            document_namen=["doc1.pdf", "doc2.pdf"],
            document_rollen=["pakbon", "factuur"]
        )

        # Geen warnings over prijzen
        assert not any('verschillende prijzen' in w.lower() for w in result.warnings)

    def test_detecteer_prijs_inconsistenties_functie(self):
        """Test _detecteer_prijs_inconsistenties helper functie."""
        df = pd.DataFrame({
            'artikelcode': ['A123', 'A123', 'B456'],
            'artikelnaam': ['Widget', 'Widget', 'Gadget'],
            'aantal': [10.0, 5.0, 3.0],
            'prijs_per_stuk': [5.00, 5.50, 10.00],  # A123 heeft verschil
            'totaal': [50.0, 27.5, 30.0],
            'btw_percentage': [21.0, 21.0, 21.0]
        })

        warnings = _detecteer_prijs_inconsistenties(df)

        # Check warning voor A123
        assert len(warnings) == 1
        assert 'A123' in warnings[0]


# ============================================================================
# TESTS: EDGE CASES
# ============================================================================

class TestEdgeCases:
    """Tests voor edge cases en corner cases."""

    def test_lege_input_lijst_geeft_error(self):
        """Test dat lege df_list een ValueError geeft."""
        with pytest.raises(ValueError, match="df_list mag niet leeg zijn"):
            aggregeer_documenten(
                df_list=[],
                document_namen=[],
                document_rollen=[]
            )

    def test_enkel_document_identity_aggregatie(self):
        """Test dat 1 document ongewijzigd terugkomt."""
        df = pd.DataFrame({
            'artikelcode': ['A123'],
            'artikelnaam': ['Widget'],
            'aantal': [10.0],
            'prijs_per_stuk': [5.0],
            'totaal': [50.0],
            'btw_percentage': [21.0]
        })

        result = aggregeer_documenten(
            df_list=[df],
            document_namen=["doc1.pdf"],
            document_rollen=["pakbon"]
        )

        # Check identity
        assert len(result.df_aggregaat) == 1
        assert result.df_aggregaat.iloc[0]['artikelcode'] == 'A123'
        assert result.df_aggregaat.iloc[0]['aantal'] == 10.0
        assert result.metadata['aantal_documenten'] == 1

    def test_leeg_document_wordt_overgeslagen(self):
        """Test dat lege DataFrames worden overgeslagen met warning."""
        df1 = pd.DataFrame({
            'artikelcode': ['A123'],
            'artikelnaam': ['Widget'],
            'aantal': [10.0],
            'prijs_per_stuk': [5.0],
            'totaal': [50.0],
            'btw_percentage': [21.0]
        })

        df2 = pd.DataFrame()  # Leeg

        result = aggregeer_documenten(
            df_list=[df1, df2],
            document_namen=["doc1.pdf", "doc2.pdf"],
            document_rollen=["pakbon", "pakbon"]
        )

        # Check dat df2 is overgeslagen
        assert result.metadata['aantal_documenten_verwerkt'] == 1
        assert len(result.warnings) > 0
        assert any('leeg' in w.lower() for w in result.warnings)

    def test_alle_documenten_leeg_geeft_error(self):
        """Test dat alleen lege documenten een ValueError geeft."""
        df1 = pd.DataFrame()
        df2 = pd.DataFrame()

        with pytest.raises(ValueError, match="Alle documenten zijn leeg"):
            aggregeer_documenten(
                df_list=[df1, df2],
                document_namen=["doc1.pdf", "doc2.pdf"],
                document_rollen=["pakbon", "pakbon"]
            )

    def test_artikel_met_aantal_nul_wordt_overgeslagen(self):
        """Test dat regels met aantal=0 worden overgeslagen."""
        df = pd.DataFrame({
            'artikelcode': ['A123', 'B456'],
            'artikelnaam': ['Widget', 'Gadget'],
            'aantal': [10.0, 0.0],  # B456 heeft aantal=0
            'prijs_per_stuk': [5.0, 10.0],
            'totaal': [50.0, 0.0],
            'btw_percentage': [21.0, 21.0]
        })

        result = aggregeer_documenten(
            df_list=[df],
            document_namen=["doc1.pdf"],
            document_rollen=["pakbon"]
        )

        # Check dat B456 is overgeslagen
        assert len(result.df_aggregaat) == 1
        assert result.df_aggregaat.iloc[0]['artikelcode'] == 'A123'
        assert any('aantal=0' in w.lower() for w in result.warnings)

    def test_artikel_met_aantal_none_wordt_overgeslagen(self):
        """Test dat regels met aantal=None worden overgeslagen."""
        df = pd.DataFrame({
            'artikelcode': ['A123', 'B456'],
            'artikelnaam': ['Widget', 'Gadget'],
            'aantal': [10.0, None],  # B456 heeft aantal=None
            'prijs_per_stuk': [5.0, 10.0],
            'totaal': [50.0, 0.0],
            'btw_percentage': [21.0, 21.0]
        })

        result = aggregeer_documenten(
            df_list=[df],
            document_namen=["doc1.pdf"],
            document_rollen=["pakbon"]
        )

        # Check dat B456 is overgeslagen
        assert len(result.df_aggregaat) == 1
        assert result.df_aggregaat.iloc[0]['artikelcode'] == 'A123'

    def test_lengte_mismatch_geeft_error(self):
        """Test dat verschillende lengtes van input lijsten een error geeft."""
        df = pd.DataFrame({'artikelcode': ['A123']})

        with pytest.raises(ValueError, match="Lengte mismatch"):
            aggregeer_documenten(
                df_list=[df, df],
                document_namen=["doc1.pdf"],  # Te kort
                document_rollen=["pakbon", "pakbon"]
            )


# ============================================================================
# TESTS: ARTIKELNAAM NORMALISATIE
# ============================================================================

class TestArtikelnaamNormalisatie:
    """Tests voor artikelnaam normalisatie bij matching."""

    def test_aggregeer_met_verschillende_whitespace(self):
        """Test dat artikelen met verschillende whitespace worden gemerged."""
        df1 = pd.DataFrame({
            'artikelcode': ['A123'],
            'artikelnaam': ['Widget  Pro'],  # Dubbele spatie
            'aantal': [10.0],
            'prijs_per_stuk': [5.0],
            'totaal': [50.0],
            'btw_percentage': [21.0]
        })

        df2 = pd.DataFrame({
            'artikelcode': ['A123'],
            'artikelnaam': ['Widget Pro'],  # Enkele spatie
            'aantal': [5.0],
            'prijs_per_stuk': [5.0],
            'totaal': [25.0],
            'btw_percentage': [21.0]
        })

        result = aggregeer_documenten(
            df_list=[df1, df2],
            document_namen=["doc1.pdf", "doc2.pdf"],
            document_rollen=["pakbon", "pakbon"]
        )

        # Check dat ze zijn gemerged
        assert len(result.df_aggregaat) == 1
        assert result.df_aggregaat.iloc[0]['aantal'] == 15.0

    def test_aggregeer_met_verschillende_case(self):
        """Test dat artikelen met verschillende case worden gemerged."""
        df1 = pd.DataFrame({
            'artikelcode': ['A123'],
            'artikelnaam': ['WIDGET PRO'],  # UPPERCASE
            'aantal': [10.0],
            'prijs_per_stuk': [5.0],
            'totaal': [50.0],
            'btw_percentage': [21.0]
        })

        df2 = pd.DataFrame({
            'artikelcode': ['A123'],
            'artikelnaam': ['widget pro'],  # lowercase
            'aantal': [5.0],
            'prijs_per_stuk': [5.0],
            'totaal': [25.0],
            'btw_percentage': [21.0]
        })

        result = aggregeer_documenten(
            df_list=[df1, df2],
            document_namen=["doc1.pdf", "doc2.pdf"],
            document_rollen=["pakbon", "pakbon"]
        )

        # Check dat ze zijn gemerged
        assert len(result.df_aggregaat) == 1
        assert result.df_aggregaat.iloc[0]['aantal'] == 15.0

    def test_originele_artikelnaam_behouden(self):
        """Test dat originele artikelnaam (eerste waarde) behouden blijft."""
        df1 = pd.DataFrame({
            'artikelcode': ['A123'],
            'artikelnaam': ['Widget Pro Deluxe'],
            'aantal': [10.0],
            'prijs_per_stuk': [5.0],
            'totaal': [50.0],
            'btw_percentage': [21.0]
        })

        df2 = pd.DataFrame({
            'artikelcode': ['A123'],
            'artikelnaam': ['WIDGET PRO DELUXE'],  # Andere case
            'aantal': [5.0],
            'prijs_per_stuk': [5.0],
            'totaal': [25.0],
            'btw_percentage': [21.0]
        })

        result = aggregeer_documenten(
            df_list=[df1, df2],
            document_namen=["doc1.pdf", "doc2.pdf"],
            document_rollen=["pakbon", "pakbon"]
        )

        # Check dat eerste originele naam behouden is
        assert result.df_aggregaat.iloc[0]['artikelnaam'] == 'Widget Pro Deluxe'


# ============================================================================
# TESTS: METADATA
# ============================================================================

class TestMetadata:
    """Tests voor metadata tracking."""

    def test_metadata_bevat_verplichte_velden(self):
        """Test dat metadata alle verplichte velden bevat."""
        df = pd.DataFrame({
            'artikelcode': ['A123'],
            'artikelnaam': ['Widget'],
            'aantal': [10.0],
            'prijs_per_stuk': [5.0],
            'totaal': [50.0],
            'btw_percentage': [21.0]
        })

        result = aggregeer_documenten(
            df_list=[df],
            document_namen=["doc1.pdf"],
            document_rollen=["pakbon"]
        )

        # Check verplichte velden
        assert 'aantal_documenten' in result.metadata
        assert 'document_namen' in result.metadata
        assert 'document_rollen' in result.metadata
        assert 'totaal_regels_input' in result.metadata
        assert 'totaal_regels_output' in result.metadata

    def test_metadata_aantal_documenten_correct(self):
        """Test dat metadata correct aantal documenten telt."""
        df1 = pd.DataFrame({
            'artikelcode': ['A123'],
            'artikelnaam': ['Widget'],
            'aantal': [10.0],
            'prijs_per_stuk': [5.0],
            'totaal': [50.0],
            'btw_percentage': [21.0]
        })

        df2 = pd.DataFrame({
            'artikelcode': ['B456'],
            'artikelnaam': ['Gadget'],
            'aantal': [5.0],
            'prijs_per_stuk': [10.0],
            'totaal': [50.0],
            'btw_percentage': [21.0]
        })

        result = aggregeer_documenten(
            df_list=[df1, df2],
            document_namen=["doc1.pdf", "doc2.pdf"],
            document_rollen=["pakbon", "factuur"]
        )

        assert result.metadata['aantal_documenten'] == 2
        assert len(result.metadata['document_namen']) == 2
        assert result.metadata['document_namen'] == ["doc1.pdf", "doc2.pdf"]

    def test_metadata_regeltelling_correct(self):
        """Test dat metadata correct aantal regels telt."""
        df1 = pd.DataFrame({
            'artikelcode': ['A123', 'B456', 'C789'],
            'artikelnaam': ['Widget', 'Gadget', 'Tool'],
            'aantal': [10.0, 5.0, 3.0],
            'prijs_per_stuk': [5.0, 10.0, 15.0],
            'totaal': [50.0, 50.0, 45.0],
            'btw_percentage': [21.0, 21.0, 21.0]
        })

        df2 = pd.DataFrame({
            'artikelcode': ['A123'],
            'artikelnaam': ['Widget'],
            'aantal': [5.0],
            'prijs_per_stuk': [5.0],
            'totaal': [25.0],
            'btw_percentage': [21.0]
        })

        result = aggregeer_documenten(
            df_list=[df1, df2],
            document_namen=["doc1.pdf", "doc2.pdf"],
            document_rollen=["pakbon", "factuur"]
        )

        # Input: 3 + 1 = 4 regels
        # Output: 3 regels (A123 gemerged)
        assert result.metadata['totaal_regels_input'] == 4
        assert result.metadata['totaal_regels_output'] == 3


# ============================================================================
# TESTS: VALIDATIE
# ============================================================================

class TestValidatie:
    """Tests voor validatie functies."""

    def test_validate_aggregatie_resultaat_geldig(self):
        """Test dat geldige resultaten worden gevalideerd."""
        df = pd.DataFrame({
            'artikelcode': ['A123'],
            'artikelnaam': ['Widget'],
            'aantal': [10.0],
            'prijs_per_stuk': [5.0],
            'totaal': [50.0],
            'btw_percentage': [21.0]
        })

        result = aggregeer_documenten(
            df_list=[df],
            document_namen=["doc1.pdf"],
            document_rollen=["pakbon"]
        )

        assert validate_aggregatie_resultaat(result) == True

    def test_validate_aggregatie_resultaat_ongeldig(self):
        """Test dat ongeldige resultaten worden afgewezen."""
        # Maak ongeldig resultaat (missende metadata)
        result = AggregatieResultaat(
            df_aggregaat=pd.DataFrame(),
            metadata={'aantal_documenten': 1},  # Missende velden
            warnings=[]
        )

        assert validate_aggregatie_resultaat(result) == False


# ============================================================================
# TESTS: BTW PERCENTAGE
# ============================================================================

class TestBTWPercentage:
    """Tests voor BTW percentage aggregatie."""

    def test_btw_percentage_most_frequent(self):
        """Test dat most frequent BTW percentage wordt gebruikt."""
        df1 = pd.DataFrame({
            'artikelcode': ['A123'],
            'artikelnaam': ['Widget'],
            'aantal': [10.0],
            'prijs_per_stuk': [5.0],
            'totaal': [50.0],
            'btw_percentage': [21.0]
        })

        df2 = pd.DataFrame({
            'artikelcode': ['A123'],
            'artikelnaam': ['Widget'],
            'aantal': [5.0],
            'prijs_per_stuk': [5.0],
            'totaal': [25.0],
            'btw_percentage': [21.0]
        })

        result = aggregeer_documenten(
            df_list=[df1, df2],
            document_namen=["doc1.pdf", "doc2.pdf"],
            document_rollen=["pakbon", "pakbon"]
        )

        # BTW moet 21.0 zijn (most frequent)
        assert result.df_aggregaat.iloc[0]['btw_percentage'] == 21.0

    def test_btw_percentage_none_als_niet_aanwezig(self):
        """Test dat BTW None wordt als niet aanwezig."""
        df = pd.DataFrame({
            'artikelcode': ['A123'],
            'artikelnaam': ['Widget'],
            'aantal': [10.0],
            'prijs_per_stuk': [5.0],
            'totaal': [50.0],
            'btw_percentage': [None]
        })

        result = aggregeer_documenten(
            df_list=[df],
            document_namen=["doc1.pdf"],
            document_rollen=["pakbon"]
        )

        # BTW moet None zijn
        assert result.df_aggregaat.iloc[0]['btw_percentage'] is None


# ============================================================================
# TESTS: ARTIKELCODE NONE HANDLING
# ============================================================================

class TestArtikelcodeNoneHandling:
    """Tests voor artikelen zonder artikelcode."""

    def test_aggregeer_artikelen_zonder_code(self):
        """Test aggregatie van artikelen zonder artikelcode."""
        df1 = pd.DataFrame({
            'artikelcode': [None],
            'artikelnaam': ['Widget'],
            'aantal': [10.0],
            'prijs_per_stuk': [5.0],
            'totaal': [50.0],
            'btw_percentage': [21.0]
        })

        df2 = pd.DataFrame({
            'artikelcode': [None],
            'artikelnaam': ['Widget'],  # Zelfde naam
            'aantal': [5.0],
            'prijs_per_stuk': [5.0],
            'totaal': [25.0],
            'btw_percentage': [21.0]
        })

        result = aggregeer_documenten(
            df_list=[df1, df2],
            document_namen=["doc1.pdf", "doc2.pdf"],
            document_rollen=["pakbon", "pakbon"]
        )

        # Check dat ze zijn gemerged op basis van naam alleen
        assert len(result.df_aggregaat) == 1
        assert result.df_aggregaat.iloc[0]['aantal'] == 15.0

    def test_aggregeer_mix_met_en_zonder_code(self):
        """Test aggregatie van mix artikelen (met en zonder code)."""
        df1 = pd.DataFrame({
            'artikelcode': ['A123', None],
            'artikelnaam': ['Widget', 'Gadget'],
            'aantal': [10.0, 5.0],
            'prijs_per_stuk': [5.0, 10.0],
            'totaal': [50.0, 50.0],
            'btw_percentage': [21.0, 21.0]
        })

        df2 = pd.DataFrame({
            'artikelcode': ['A123', None],
            'artikelnaam': ['Widget', 'Gadget'],
            'aantal': [5.0, 3.0],
            'prijs_per_stuk': [5.0, 10.0],
            'totaal': [25.0, 30.0],
            'btw_percentage': [21.0, 21.0]
        })

        result = aggregeer_documenten(
            df_list=[df1, df2],
            document_namen=["doc1.pdf", "doc2.pdf"],
            document_rollen=["pakbon", "pakbon"]
        )

        # Check dat beide zijn gemerged
        assert len(result.df_aggregaat) == 2

        # Widget met code
        widget_row = result.df_aggregaat[result.df_aggregaat['artikelcode'] == 'A123'].iloc[0]
        assert widget_row['aantal'] == 15.0

        # Gadget zonder code
        gadget_row = result.df_aggregaat[result.df_aggregaat['artikelcode'].isna()].iloc[0]
        assert gadget_row['aantal'] == 8.0
