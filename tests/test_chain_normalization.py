import pytest

from services.chain_normalization import (
    TypeInference,
    infer_document_type,
    infer_stage_type,
    stage_type_from_name,
    type_from_url,
)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("/rattsliga-dokument/kommittedirektiv/2026/06/dir.-202662", "1327"),
        ("https://www.regeringen.se/remisser/2023/10/remiss-av-ds-202329/", "2099"),
        ("/rattsliga-dokument/proposition/2019/09/prop.-2019201/", "1329"),
        ("https://svenskforfattningssamling.se/doc/2023284.html", "sfs"),
        (
            "https://www.svenskforfattningssamling.se/sites/default/files/sfs/2024-02/SFS2024-28.pdf",
            "sfs",
        ),
        ("http://rkrattsbaser.gov.se/sfst?bet=1971:291", "sfs"),
        ("http://rkrattsdb.gov.se/SFSdoc/16/161138.PDF", "sfs"),
        (
            "https://www.riksdagen.se/sv/dokument-och-lagar/dokument/betankande/example_hd01mju3/",
            "riksdagsbetankande",
        ),
        (
            "https://www.riksdagen.se/sv/dokument-lagar/arende/betankande/example_H901FiU36",
            "riksdagsbetankande",
        ),
        (
            "https://www.riksdagen.se/sv/dokument-och-lagar/dokument/_hb01f%C3%B6u10/",
            "riksdagsbetankande",
        ),
        (
            "https://www.riksdagen.se/sv/dokument-och-lagar/dokument/proposition/example_hc03179/",
            "1329",
        ),
        (
            "https://www.riksdagen.se/sv/dokument-och-lagar/dokument/skrivelse/example_hc0377/",
            "1330",
        ),
        (
            "https://eur-lex.europa.eu/legal-content/SV/TXT/?uri=CELEX%3A32016R0679",
            "eu-forordning",
        ),
        (
            "https://eur-lex.europa.eu/legal-content/SV/ALL/?uri=celex:52025PC0989",
            "eu-forslag",
        ),
        (
            "https://eur-lex.europa.eu/legal-content/SV/ALL/?uri=CELEX:52014AP0222",
            "eu-parlamentsposition",
        ),
        (
            "https://eur-lex.europa.eu/legal-content/SV/TXT/?uri=CELEX:32009F0315",
            "eu-rambeslut",
        ),
        (
            "https://eur-lex.europa.eu/legal-content/SV/ALL/?uri=CELEX:32020H1104(01)",
            "eu-rekommendation",
        ),
        (
            "https://eur-lex.europa.eu/legal-content/SV/ALL/?uri=CELEX:32009L0315R(01)",
            "eu-direktiv",
        ),
        ("https://eur-lex.europa.eu/eli/dir/2018/849/oj", "eu-direktiv"),
        ("https://eur-lex.europa.eu/eli/reg_impl/2023/204/oj/eng", "eu-forordning"),
    ],
)
def test_specific_document_urls(url, expected):
    assert type_from_url(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "/remisser/",
        "https:///remisser/example/",
        "https://example.com/rattsliga-dokument/proposition/example/",
        "https://www.svenskförfattningssamling.se/doc/2020574.html",
        "https://svenskforfattningssamling.se/",
        "http://rkrattsbaser.gov.se/sfst",
        "https://www.riksdagen.se/sv/webb-tv/video/debatt-om-forslag/example/",
        "https://eur-lex.europa.eu/legal-content/SV/TXT/?uri=uriserv:OJ.L_.2015.141.01.0073.01.SWE",
        "https://eur-lex.europa.eu/legal-content/SV/TXT/?uri=CELEX:02016R0679-20250101",
        "https://eur-lex.europa.eu/legal-content/SV/TXT/?uri=CELEX:32016R0679&uri=CELEX:32009L0315",
        "https://eur-lex.europa.eu/search.html?uri=CELEX:32016R0679",
        "javascript:/remisser/example/",
    ],
)
def test_unreliable_urls_remain_unknown(url):
    assert type_from_url(url) is None


def test_metadata_disagrees_with_url_on_actual_backfilled_page():
    guess = infer_document_type(
        "/rattsliga-dokument/departementsserien-och-promemorior/2021/03/utkast-till-lagradsremiss-anpassningar-till-eus-marknadskontrollforordning/",
        ["2085", "1332"],
    )
    assert guess.type is None
    assert guess.reason == "item_url_conflict"
    assert guess.candidates == ("1325", "2085")


def test_item_metadata_can_classify_an_uninformative_url():
    assert (
        infer_document_type("/contentassets/example/report.pdf", ["1341"]).type
        == "1341"
    )
    assert infer_document_type("/remisser/example/", ["2099", "1332"]).type == "2099"
    assert infer_document_type("/remisser/example/", ["2099", "1325"]).type is None


def test_exotic_names_can_be_replaced_by_document_evidence():
    assert stage_type_from_name("Remss") is None
    guess = infer_stage_type(
        [infer_document_type("/remisser/2023/10/remiss-av-ds-202329/")]
    )
    assert guess.type == "2099"
    assert (
        infer_stage_type(
            [
                infer_document_type(
                    "/rattsliga-dokument/proposition/2019/09/prop.-2019201/"
                )
            ]
        ).type
        == "1329"
    )


def test_do_not_assign_the_majority_type_to_a_mixed_or_partial_stage():
    sou = TypeInference("1331", "url")
    ds = TypeInference("1325", "url")
    mixed = infer_stage_type([sou, sou, ds])
    assert mixed.type is None
    assert mixed.reason == "mixed"
    assert mixed.candidates == ("1325", "1331")
    assert infer_stage_type([sou, TypeInference(None, "unknown")]).reason == "partial"
    assert (
        infer_stage_type([sou, TypeInference(None, "item_url_conflict")]).type is None
    )
    assert infer_stage_type([]).reason == "empty"


def test_committee_report_display_group_does_not_change_document_type():
    report = TypeInference("riksdagsbetankande", "url")
    assert infer_stage_type([report]).type == "riksdagsbeslut"
    assert report.type == "riksdagsbetankande"
    assert infer_stage_type([report, TypeInference("1329", "url")]).reason == "mixed"


def test_normal_presentational_aliases_do_not_need_url_guessing():
    assert stage_type_from_name("Svensk författ\xadnings\xadsamling (4 st)") == "sfs"
    assert stage_type_from_name("Departementsserien") == "1325"
    assert stage_type_from_name("Remiss (1st)") == "2099"


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (
            "https://eur-lex.europa.eu/legal-content/AUTO/?uri=CELEX:32014L0066",
            "eu-direktiv",
        ),
        (
            "https://eur-lex.europa.eu/legal-content/SV/TXT/PDF/?uri=CELEX:32019R0834",
            "eu-forordning",
        ),
        (
            "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32013R1257.SWE",
            "eu-forordning",
        ),
        (
            "https://www.riksdagen.se/sv/dokument-och-lagar/dokument/betankande/example_hb01mju6/html/",
            "riksdagsbetankande",
        ),
    ],
)
def test_representation_and_language_variants_preserve_type(url, expected):
    assert type_from_url(url) == expected
