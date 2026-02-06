# test_document_classifier.py
# Unit tests voor document_classifier.py v1.3

"""
Unit tests voor document rol classificatie.

Test coverage:
- Rol-detectie heuristieken (pakbon/factuur/onbekend)
- Totaalbedrag detectie
- Gebruiksvriendelijke meldingen (geen angst-woorden)
- Dataclass structuur
"""

import pytest
from pathlib import Path
from modules.document_classifier import (
    _detecteer_document_rol,
    _heeft_totaalbedrag,
    _genereer_bericht_pdf,
    _genereer_bericht_csv_excel,
    DocumentClassificatieResultaat,
    lijst_ondersteunde_documentrollen
)


# ============================================================================
# TESTS: ROL-DETECTIE
# ============================================================================

class TestDetecteerDocumentRol:
    """Tests voor rol-detectie heuristieken."""

    def test_detecteert_pakbon_met_keywords(self):
        tekst = "pakbonnummer 12345 leverdatum 01-03-2025 geleverd 50 stuks"
        assert _detecteer_document_rol(tekst) == 'pakbon'

    def test_detecteert_pakbon_met_levering(self):
        tekst = "levering van artikelen pakbon ref 99887"
        assert _detecteer_document_rol(tekst) == 'pakbon'

    def test_detecteert_pakbon_met_leverdatum(self):
        tekst = "leverdatum: 15-03-2025 artikel lijst"
        assert _detecteer_document_rol(tekst) == 'pakbon'

    def test_detecteert_factuur_met_keywords(self):
        tekst = "factuur nummer F-2025-001 te betalen €500,00"
        assert _detecteer_document_rol(tekst) == 'factuur'

    def test_detecteert_verzamelfactuur(self):
        tekst = "verzamelfactuur maart 2025 totaal excl btw"
        assert _detecteer_document_rol(tekst) == 'factuur'

    def test_detecteert_factuur_met_btw(self):
        tekst = "factuur totaal excl btw €500 btw bedrag €105"
        assert _detecteer_document_rol(tekst) == 'factuur'

    def test_factuur_heeft_voorrang_boven_pakbon(self):
        # Als beide keywords aanwezig, factuur wint (specifiekere match)
        tekst = "factuur voor pakbon 12345 te betalen €100"
        assert _detecteer_document_rol(tekst) == 'factuur'

    def test_onbekend_zonder_keywords(self):
        tekst = "artikel omschrijving aantal prijs totaal"
        assert _detecteer_document_rol(tekst) == 'onbekend'

    def test_onbekend_met_alleen_artikelinfo(self):
        tekst = "artikel A1234 prijs €10,00 aantal 5"
        assert _detecteer_document_rol(tekst) == 'onbekend'

    def test_case_insensitive(self):
        tekst = "PAKBONNUMMER 12345 LEVERDATUM"
        assert _detecteer_document_rol(tekst) == 'pakbon'

    def test_case_insensitive_factuur(self):
        tekst = "FACTUUR TE BETALEN"
        assert _detecteer_document_rol(tekst) == 'factuur'


# ============================================================================
# TESTS: TOTAALBEDRAG DETECTIE
# ============================================================================

class TestHeeftTotaalbedrag:
    """Tests voor totaalbedrag detectie."""

    def test_detecteert_totaal_excl_btw(self):
        tekst = "artikelen lijst totaal excl btw: €500,00"
        assert _heeft_totaalbedrag(tekst) == True

    def test_detecteert_totaal_incl_btw(self):
        tekst = "totaal incl btw: €605,00"
        assert _heeft_totaalbedrag(tekst) == True

    def test_detecteert_te_betalen(self):
        tekst = "te betalen €605,00"
        assert _heeft_totaalbedrag(tekst) == True

    def test_detecteert_totaal_te_betalen(self):
        tekst = "totaal te betalen: €605,00"
        assert _heeft_totaalbedrag(tekst) == True

    def test_detecteert_btw_bedrag(self):
        tekst = "subtotaal €500 btw bedrag €105 totaal €605"
        assert _heeft_totaalbedrag(tekst) == True

    def test_detecteert_btw_percentage_21(self):
        tekst = "artikelen met 21% btw"
        assert _heeft_totaalbedrag(tekst) == True

    def test_detecteert_btw_percentage_6(self):
        tekst = "6% btw tarief"
        assert _heeft_totaalbedrag(tekst) == True

    def test_detecteert_btw_percentage_9(self):
        tekst = "9% btw"
        assert _heeft_totaalbedrag(tekst) == True

    def test_detecteert_subtotaal(self):
        tekst = "subtotaal: €500,00"
        assert _heeft_totaalbedrag(tekst) == True

    def test_geen_totaal_in_pakbon(self):
        tekst = "pakbon artikelen aantal prijs"
        assert _heeft_totaalbedrag(tekst) == False

    def test_geen_totaal_alleen_artikelen(self):
        tekst = "artikel A1234 aantal 10 prijs €5,00"
        assert _heeft_totaalbedrag(tekst) == False

    def test_case_insensitive_totaal(self):
        tekst = "TOTAAL EXCL BTW"
        assert _heeft_totaalbedrag(tekst) == True


# ============================================================================
# TESTS: GEBRUIKSVRIENDELIJKE MELDINGEN
# ============================================================================

class TestGenereerBerichtPDF:
    """Tests voor gebruiksvriendelijke meldingen (geen angst-woorden)."""

    def test_bericht_pakbon_zonder_totaal(self):
        from modules.pdf_classifier import PDFClassificatieResultaat as PDFClass

        pdf_class = PDFClass(
            type='template_herkend',
            leverancier='Bosal',
            tekst_lengte=1000,
            heeft_tabel_structuur=True,
            bericht_gebruiker='...'
        )

        bericht = _genereer_bericht_pdf(pdf_class, 'pakbon', False)

        # Moet pakbon en leverancier noemen
        assert 'pakbon' in bericht.lower()
        assert 'bosal' in bericht.lower()
        assert 'totalen volgen' in bericht.lower()

        # GEEN angst-woorden
        assert 'onvolledig' not in bericht.lower()
        assert 'risico' not in bericht.lower()
        assert 'fout' not in bericht.lower()

    def test_bericht_pakbon_met_totaal(self):
        from modules.pdf_classifier import PDFClassificatieResultaat as PDFClass

        pdf_class = PDFClass(
            type='template_herkend',
            leverancier='Bosal',
            tekst_lengte=1000,
            heeft_tabel_structuur=True,
            bericht_gebruiker='...'
        )

        bericht = _genereer_bericht_pdf(pdf_class, 'pakbon', True)

        assert 'pakbon' in bericht.lower()
        assert 'bosal' in bericht.lower()
        # Geen melding over "totalen volgen" (want al aanwezig)

    def test_bericht_factuur_met_totaal(self):
        from modules.pdf_classifier import PDFClassificatieResultaat as PDFClass

        pdf_class = PDFClass(
            type='template_herkend',
            leverancier='Fource',
            tekst_lengte=2000,
            heeft_tabel_structuur=True,
            bericht_gebruiker='...'
        )

        bericht = _genereer_bericht_pdf(pdf_class, 'factuur', True)

        assert 'factuur' in bericht.lower()
        assert 'fource' in bericht.lower()

    def test_bericht_gescand_pdf(self):
        from modules.pdf_classifier import PDFClassificatieResultaat as PDFClass

        pdf_class = PDFClass(
            type='gescand',
            leverancier=None,
            tekst_lengte=0,
            heeft_tabel_structuur=False,
            bericht_gebruiker='...'
        )

        bericht = _genereer_bericht_pdf(pdf_class, 'onbekend', False)

        assert 'gescand' in bericht.lower()
        assert 'digitale versie' in bericht.lower()

    def test_bericht_geen_artikelregels(self):
        from modules.pdf_classifier import PDFClassificatieResultaat as PDFClass

        pdf_class = PDFClass(
            type='geen_artikelregels',
            leverancier=None,
            tekst_lengte=500,
            heeft_tabel_structuur=False,
            bericht_gebruiker='...'
        )

        bericht = _genereer_bericht_pdf(pdf_class, 'onbekend', False)

        assert 'geen artikeltabel' in bericht.lower()
        assert 'juiste pagina' in bericht.lower()

    def test_bericht_text_geen_template_pakbon(self):
        from modules.pdf_classifier import PDFClassificatieResultaat as PDFClass

        pdf_class = PDFClass(
            type='text_geen_template',
            leverancier=None,
            tekst_lengte=1500,
            heeft_tabel_structuur=True,
            bericht_gebruiker='...'
        )

        bericht = _genereer_bericht_pdf(pdf_class, 'pakbon', False)

        assert 'pakbon' in bericht.lower()
        assert 'csv' in bericht.lower()  # Suggestie voor CSV export


class TestGenereerBerichtCSVExcel:
    """Tests voor CSV/Excel meldingen."""

    def test_bericht_csv_pakbon(self):
        bericht = _genereer_bericht_csv_excel('csv', 'pakbon')
        assert 'csv' in bericht.lower()
        assert 'pakbon' in bericht.lower()

    def test_bericht_csv_factuur(self):
        bericht = _genereer_bericht_csv_excel('csv', 'factuur')
        assert 'csv' in bericht.lower()
        assert 'factuur' in bericht.lower()

    def test_bericht_excel_pakbon(self):
        bericht = _genereer_bericht_csv_excel('excel', 'pakbon')
        assert 'excel' in bericht.lower()
        assert 'pakbon' in bericht.lower()

    def test_bericht_excel_onbekend(self):
        bericht = _genereer_bericht_csv_excel('excel', 'onbekend')
        assert 'excel' in bericht.lower()
        assert 'verwerkt' in bericht.lower()


# ============================================================================
# TESTS: DATACLASS STRUCTUUR
# ============================================================================

class TestDocumentClassificatieResultaat:
    """Tests voor dataclass structuur."""

    def test_dataclass_fields_exist(self):
        result = DocumentClassificatieResultaat(
            type='template_herkend',
            leverancier='Bosal',
            rol='pakbon',
            heeft_totaalbedrag=False,
            bestandstype='pdf',
            tekst_lengte=1000,
            bericht_gebruiker='Test bericht'
        )

        assert result.type == 'template_herkend'
        assert result.leverancier == 'Bosal'
        assert result.rol == 'pakbon'
        assert result.heeft_totaalbedrag == False
        assert result.bestandstype == 'pdf'
        assert result.tekst_lengte == 1000
        assert result.bericht_gebruiker == 'Test bericht'

    def test_optional_fields_can_be_none(self):
        result = DocumentClassificatieResultaat(
            type=None,
            leverancier=None,
            rol='onbekend',
            heeft_totaalbedrag=False,
            bestandstype='csv',
            tekst_lengte=0,
            bericht_gebruiker='CSV verwerkt'
        )

        assert result.type is None
        assert result.leverancier is None
        assert result.rol == 'onbekend'

    def test_rol_types_valid(self):
        # Test dat alle rol types werken
        for rol in ['pakbon', 'factuur', 'onbekend']:
            result = DocumentClassificatieResultaat(
                type=None,
                leverancier=None,
                rol=rol,
                heeft_totaalbedrag=False,
                bestandstype='pdf',
                tekst_lengte=0,
                bericht_gebruiker='Test'
            )
            assert result.rol == rol

    def test_bestandstype_types_valid(self):
        # Test dat alle bestandstype types werken
        for btype in ['pdf', 'csv', 'excel']:
            result = DocumentClassificatieResultaat(
                type=None,
                leverancier=None,
                rol='onbekend',
                heeft_totaalbedrag=False,
                bestandstype=btype,
                tekst_lengte=0,
                bericht_gebruiker='Test'
            )
            assert result.bestandstype == btype


# ============================================================================
# TESTS: UTILITY FUNCTIES
# ============================================================================

class TestUtilityFuncties:
    """Tests voor utility functies."""

    def test_lijst_ondersteunde_documentrollen(self):
        rollen = lijst_ondersteunde_documentrollen()
        assert isinstance(rollen, list)
        assert 'pakbon' in rollen
        assert 'factuur' in rollen
        assert 'onbekend' in rollen
        assert len(rollen) == 3


# ============================================================================
# INTEGRATION TESTS (optioneel, vereist echte bestanden)
# ============================================================================

@pytest.mark.integration
class TestClassificeerDocument:
    """Integration tests met echte bestanden (skip als niet beschikbaar)."""

    def test_classificeer_pakbon_pdf(self):
        # Deze test vereist een echt PDF-bestand
        # Skip als bestand niet beschikbaar
        pytest.skip("Integration test - vereist echt pakbon PDF")

    def test_classificeer_factuur_pdf(self):
        pytest.skip("Integration test - vereist echt factuur PDF")

    def test_classificeer_csv(self, tmp_path):
        # Maak test CSV
        csv_content = "artikelcode,artikelnaam,aantal,prijs\nA1,Widget,10,5.00\n"
        csv_path = tmp_path / "test.csv"
        csv_path.write_text(csv_content)

        # Classificeer (zou moeten werken)
        from modules.document_classifier import classificeer_document
        result = classificeer_document(csv_path)

        assert result.bestandstype == 'csv'
        assert result.rol in ['pakbon', 'factuur', 'onbekend']


# ============================================================================
# EDGE CASES
# ============================================================================

class TestEdgeCases:
    """Tests voor edge cases en corner cases."""

    def test_lege_tekst_rol_detectie(self):
        assert _detecteer_document_rol("") == 'onbekend'

    def test_lege_tekst_totaalbedrag(self):
        assert _heeft_totaalbedrag("") == False

    def test_special_characters_in_tekst(self):
        tekst = "pakbon !@#$%^&*() leverdatum"
        assert _detecteer_document_rol(tekst) == 'pakbon'

    def test_multiple_spaces_in_keywords(self):
        tekst = "pakbon     nummer     leverdatum"
        assert _detecteer_document_rol(tekst) == 'pakbon'

    def test_partial_keyword_match_fails(self):
        # "pak" is niet "pakbon"
        tekst = "pak nummer levering"
        # Zou 'pakbon' moeten zijn door "levering"
        assert _detecteer_document_rol(tekst) == 'pakbon'

    def test_btw_zonder_percentage_symbool(self):
        tekst = "21 btw artikel"
        assert _heeft_totaalbedrag(tekst) == True

    def test_totaal_zonder_bedrag(self):
        tekst = "totaal excl"
        assert _heeft_totaalbedrag(tekst) == True
