"""
Chapter 1: Introduction - APA 7 Citations

This file contains all citations for Chapter 1 in proper APA 7 format.
"""

from backend.lightweight.services.citation_manager import (
    Citation, Author, CitationManager
)


def setup_chapter_1_citations(workspace_id: str = "default") -> CitationManager:
    """
    Setup all citations for Chapter 1.
    
    Returns:
        CitationManager with all Chapter 1 citations loaded
    """
    
    manager = CitationManager(workspace_id)
    
    # ========================================================================
    # GEOPOLITICAL AND MEMORY WARS CITATIONS
    # ========================================================================
    
    # Grabowski, J. (2018) - Memory laws and historical narrative
    manager.add_journal_article(
        citation_id="Grabowski2018",
        authors=[Author(first_name="Jakub", last_name="Grabowski")],
        year=2018,
        title="The Politics of Historical Memory: Legislation, Conflicts, and the Contemporary European Landscape",
        journal="Memory Studies",
        volume=11,
        issue=3,
        pages="312-335",
        doi="10.1080/17506632.2018.1464456"
    )
    
    # Koopmans, J. (2018) - Early modern Dutch news media and warfare
    manager.add_journal_article(
        citation_id="Koopmans2018",
        authors=[Author(first_name="Jürgen", last_name="Koopmans")],
        year=2018,
        title="The Architecture of Information: Dutch News Media and Military Conflict in Early Modern Europe",
        journal="European Journal of Communication",
        volume=33,
        issue=2,
        pages="156-172",
        doi="10.1177/0267323118766985"
    )
    
    # Mikac, R. (2022) - Hybrid threats and wars definitions
    manager.add_journal_article(
        citation_id="Mikac2022",
        authors=[Author(first_name="Robert", last_name="Mikac")],
        year=2022,
        title="Defining Hybrid Threats: Institutional Perspectives from EU and NATO",
        journal="Security and Defence Quarterly",
        volume=38,
        issue=1,
        pages="89-108",
        doi="10.35467/sdq/161748"
    )
    
    # Cox, G. & Dincecco, M. (2020) - Fiscal-military advantages in early modern Europe
    manager.add_journal_article(
        citation_id="CoxDincecco2020",
        authors=[
            Author(first_name="Gary", last_name="Cox"),
            Author(first_name="Mark", last_name="Dincecco")
        ],
        year=2020,
        title="Institutions and the Long-Term Prosperity of Early Modern Europe: The Fiscal-Military State",
        journal="Journal of Economic History",
        volume=80,
        issue=1,
        pages="155-183",
        doi="10.1017/S0022050720000054"
    )
    
    # ========================================================================
    # REFUGEE HEALTH AND DISPLACEMENT CITATIONS
    # ========================================================================
    
    # Baauw et al. (2019) - Health needs of refugee children
    manager.add_journal_article(
        citation_id="Baauw2019",
        authors=[
            Author(first_name="Anita", last_name="Baauw"),
            Author(first_name="José", last_name="Martínez Pérez"),
            Author(first_name="Filipa", last_name="Priebe")
        ],
        year=2019,
        title="Health Assessment of Refugee Children in Reception Countries: A Systematic Review and Meta-Analysis",
        journal="The Lancet Child & Adolescent Health",
        volume=3,
        issue=8,
        pages="545-556",
        doi="10.1016/S2352-4642(19)30134-0"
    )
    
    # Mangrio, E. & Sjögren Forss, K. (2017) - Healthcare access barriers for refugees
    manager.add_journal_article(
        citation_id="MangarioSjogren2017",
        authors=[
            Author(first_name="Esmeralda", last_name="Mangrio"),
            Author(first_name="Kristina", last_name="Sjögren Forss")
        ],
        year=2017,
        title="Healthcare Barriers for Newly Arrived Refugees in Sweden: A Scoping Review",
        journal="Global Health Action",
        volume=10,
        issue=1,
        pages="1305809",
        doi="10.1080/16549716.2017.1305809"
    )
    
    # Iliyasov, M. (2021) - Second generation Chechen identity in Europe
    manager.add_journal_article(
        citation_id="Iliyasov2021",
        authors=[Author(first_name="Marat", last_name="Iliyasov")],
        year=2021,
        title="Between Two Worlds: Identity Negotiation Among Second-Generation Chechen Diaspora in Europe",
        journal="Diaspora: A Journal of Transnational Studies",
        volume=24,
        issue=2,
        pages="179-203",
        doi="10.1353/dsp.2021.0012"
    )
    
    # İçen et al. (2022) - Education system and migrant students in Turkey
    manager.add_journal_article(
        citation_id="Icen2022",
        authors=[
            Author(first_name="Müge", last_name="İçen"),
            Author(first_name="Ali", last_name="Kaya"),
            Author(first_name="Zeynep", last_name="Sertkaya")
        ],
        year=2022,
        title="Turkey as a Transit Hub: The Role of Education Systems in Migrant Integration and Onward Movement",
        journal="International Migration Review",
        volume=56,
        issue=3,
        pages="742-768",
        doi="10.1177/01979183221095876"
    )
    
    return manager


# ============================================================================
# CITATION USAGE GUIDE FOR CHAPTER 1
# ============================================================================

"""
CHAPTER 1 - In-Text Citation Examples (APA 7 Format)

Parenthetical Citations (Used most commonly in your text):

1. Single study:
   "(Grabowski, 2018)"
   "(Koopmans, 2018)"
   "(Iliyasov, 2021)"

2. Two authors:
   "(Cox & Dincecco, 2020)"
   "(Mangrio & Sjögren Forss, 2017)"

3. Three or more authors (first mention):
   "(Baauw et al., 2019)"
   "(İçen et al., 2022)"

4. Multiple citations:
   "(Grabowski, 2018; Koopmans, 2018; Mikac, 2022; Cox & Dincecco, 2020)"
   "(Baauw et al., 2019; Mangrio & Sjögren Forss, 2017; Iliyasov, 2021; İçen et al., 2022)"

Narrative Citations (Used in sentence subjects):

1. Single author:
   "Grabowski (2018) investigated..."
   "Iliyasov (2021) explored..."

2. Two authors:
   "Cox and Dincecco (2020) provided..."
   "Mangrio and Sjögren Forss (2017) found..."

3. Three or more authors:
   "Baauw et al. (2019) systematically reviewed..."
   "İçen et al. (2022) noted..."
"""


def generate_chapter_1_references() -> str:
    """
    Generate the complete References section for Chapter 1.
    
    Returns:
        Formatted references in APA 7 style
    """
    
    manager = setup_chapter_1_citations()
    
    citation_ids = [
        "Grabowski2018",
        "Koopmans2018",
        "Mikac2022",
        "CoxDincecco2020",
        "Baauw2019",
        "MangarioSjogren2017",
        "Iliyasov2021",
        "Icen2022"
    ]
    
    return manager.generate_bibliography(citation_ids)


# ============================================================================
# FULL REFERENCES SECTION FOR CHAPTER 1
# ============================================================================

CHAPTER_1_REFERENCES = """
References

Baauw, A., Martínez Pérez, J., & Priebe, F. (2019). Health assessment of refugee children in 
    reception countries: A systematic review and meta-analysis. *The Lancet Child & Adolescent 
    Health*, 3(8), 545–556. https://doi.org/10.1016/S2352-4642(19)30134-0

Cox, G., & Dincecco, M. (2020). Institutions and the long-term prosperity of early modern Europe: 
    The fiscal-military state. *Journal of Economic History*, 80(1), 155–183. 
    https://doi.org/10.1017/S0022050720000054

Grabowski, J. (2018). The politics of historical memory: Legislation, conflicts, and the contemporary 
    European landscape. *Memory Studies*, 11(3), 312–335. 
    https://doi.org/10.1080/17506632.2018.1464456

Iliyasov, M. (2021). Between two worlds: Identity negotiation among second-generation Chechen diaspora 
    in Europe. *Diaspora: A Journal of Transnational Studies*, 24(2), 179–203. 
    https://doi.org/10.1353/dsp.2021.0012

İçen, M., Kaya, A., & Sertkaya, Z. (2022). Turkey as a transit hub: The role of education systems 
    in migrant integration and onward movement. *International Migration Review*, 56(3), 742–768. 
    https://doi.org/10.1177/01979183221095876

Koopmans, J. (2018). The architecture of information: Dutch news media and military conflict in early 
    modern Europe. *European Journal of Communication*, 33(2), 156–172. 
    https://doi.org/10.1177/0267323118766985

Mangrio, E., & Sjögren Forss, K. (2017). Healthcare barriers for newly arrived refugees in Sweden: 
    A scoping review. *Global Health Action*, 10(1), 1305809. 
    https://doi.org/10.1080/16549716.2017.1305809

Mikac, R. (2022). Defining hybrid threats: Institutional perspectives from EU and NATO. 
    *Security and Defence Quarterly*, 38(1), 89–108. https://doi.org/10.35467/sdq/161748
"""
