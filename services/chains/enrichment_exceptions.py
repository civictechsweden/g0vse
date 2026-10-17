"""Incorrect source→target shortcuts verified on regeringen.se, 2026-10-17.

Keep exceptions specific to the link: a corrected shortcut should qualify without
a code change. These exclusions affect inference only, never official chains.
"""

EXCLUDED_SHORTCUTS = {
    (
        "/remisser/2019/05/remiss-av-2018-ars-andringar-av-sjoarbetskonventionen-mlc--analys-och-forslag-till-genomforande/",
        "/rattsliga-dokument/departementsserien-och-promemorior/2019/05/kompletterande-forslag-till-betankandet-frekvenser-i-samhallets-tjanst-sou-201892/",
    ): "Maritime labour consultation links to an unrelated frequency-spectrum proposal.",
    (
        "/remisser/2020/05/remiss-av-promemorian-tillfalliga-bestammelser-om-forebyggande-sjukpenning-med-anledning-av-sjukdomen-covid-19/",
        "/rattsliga-dokument/departementsserien-och-promemorior/2020/06/tillfalliga-bestammelser-om-viss-smittbararpenning-med-anledning-av-sjukdomen-covid-19/",
    ): "S2020/04874/SF links to S2020/05402/SF, a different proposal with its own consultation.",
    (
        "/remisser/2017/06/remiss-av-naturvardsverkets-utredning-av-konsekvenserna-for-verkets-forslag-till-nationell-fosforforordning-av-eu-kommissionens-forslag-till-godselproduktforordning/",
        "/rattsliga-dokument/departementsserien-och-promemorior/2003/02/ds-20032/",
    ): "Fertiliser consultation links PM 2003:2 to an unrelated rehabilitation paper, Ds 2003:2.",
}
