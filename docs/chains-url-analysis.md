# Document types inferred from chain links

Analysis dated 2026-10-13, using the saved backfill, not a new crawl.

4,313 chains; 16,408 stage memberships; 15,957 distinct URLs. Repeated title/date variants of the same membership are counted once. Hosts differing only by `www` are combined. Other host spellings remain distinct.

URL rules classify **15,939/15,957 distinct URLs**. Checking indexed item types leaves **15,938** classified URLs; contradictions are reported rather than overwritten.

## Popular URL groups

| URL prefix or domain | Memberships | Distinct URLs | Inferred document types |
| --- | ---: | ---: | --- |
| `/rattsliga-dokument/proposition` | 2,443 | 2,401 | Proposition (2,443) |
| `/rattsliga-dokument/kommittedirektiv` | 2,320 | 2,308 | Kommittédirektiv (2,320) |
| `/rattsliga-dokument/lagradsremiss` | 2,138 | 2,121 | Lagrådsremiss (2,138) |
| `/rattsliga-dokument/departementsserien-och-promemorior` | 1,926 | 1,884 | Departementsserien och promemorior (1,925), item_url_conflict (1) |
| `/remisser` | 1,780 | 1,765 | Remiss (1,780) |
| `/rattsliga-dokument/statens-offentliga-utredningar` | 1,705 | 1,696 | Statens offentliga utredningar (1,705) |
| `svenskforfattningssamling.se` | 1,172 | 1,163 | Svensk författningssamling (1,167), unknown (5) |
| `eur-lex.europa.eu` | 1,115 | 1,070 | EU-förslag (487), EU-förordning (203), Europaparlamentets lagstiftningsposition (170), EU-direktiv (140), Övrigt kommissionsdokument (35), EU-beslut (19), EU-yttrande (18), Rådets position (17), EU-rekommendation (8), Kommissionens arbetsdokument (8), unknown (6), JOIN-dokument (2), Europaparlamentets resolution (1), EU-rambeslut (1) |
| `riksdagen.se` | 869 | 830 | Riksdagens betänkande (844), Proposition (15), Skrivelse (8), unknown (2) |
| `/faktapromemoria` | 611 | 590 | Faktapromemoria (611) |
| `/kommenterade-dagordningar` | 263 | 65 | Kommenterad dagordning (263) |
| `rkrattsbaser.gov.se` | 27 | 25 | Svensk författningssamling (27) |
| `/rapporter` | 17 | 17 | Rapport (17) |
| `/rattsliga-dokument/skrivelse` | 8 | 8 | Skrivelse (8) |
| `/informationsmaterial` | 3 | 3 | unknown (3) |
| `/regeringsuppdrag` | 3 | 3 | Regeringsuppdrag (3) |
| `rkrattsdb.gov.se` | 2 | 2 | Svensk författningssamling (2) |
| `svenskförfattningssamling.se` | 2 | 2 | unknown (2) |
| `/` | 1 | 1 | unknown (1) |
| `/artiklar` | 1 | 1 | unknown (1) |
| `coe.int` | 1 | 1 | unknown (1) |
| `europarl.europa.eu` | 1 | 1 | unknown (1) |

## Which exotic stages can be normalized?

The current draft has **156 exotic stage occurrences**, with **101 distinct labels**. Their results are:

- `uniform`: **150** stages.
- `unknown`: **4** stages.
- `mixed`: **2** stages.

`uniform` means every member has the same compatible type. These stages can receive the inferred type while retaining their documents, actor, phase and order. `mixed` stages can be split by document type if that is the chosen presentation rule. `partial` and `unknown` stages remain unresolved. A majority vote is never used.

| Existing heading | Inferred type / candidates | Result | Example source |
| --- | --- | --- | --- |
| Budgetförslag | Proposition | uniform | [source](https://www.regeringen.se/rattsliga-dokument/departementsserien-och-promemorior/2019/02/forlangt-vaxa-stod/) |
| Delrapport | Rapport | uniform | [source](https://www.regeringen.se/rattsliga-dokument/statens-offentliga-utredningar/2016/10/sou-201672/) |
| Departementserien | Departementsserien och promemorior | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2021/10/prop.-20212233/) |
| Direktiv 2014/54/EU | EU-direktiv | uniform | [source](https://www.regeringen.se/rattsliga-dokument/departementsserien-och-promemorior/2015/07/ds-201536/) |
| Ds 2015:32 | Departementsserien och promemorior | uniform | [source](https://www.regeringen.se/rattsliga-dokument/statens-offentliga-utredningar/2013/10/sou-201372/) |
| EU-direkiv (1) | EU-direktiv | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2020/02/prop.-20192074/) |
| EU-direktiv 2014/53/EU | EU-direktiv | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2016/02/prop.-20151693/) |
| EU-fördordning | EU-förordning | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2018/03/prop.-201718133/) |
| EU-lagstiftning | EU-direktiv | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2020/04/prop.-201920156/) |
| EU-rambeslut | EU-rambeslut | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2022/03/prop.-202122172/) |
| Europaparlamentets och rådets direktiv 2014/94/EU | EU-direktiv | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2016/06/prop.-201516186/) |
| Europaparlamentets och rådets förordning | EU-förordning | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2020/04/prop.-201920139/) |
| Europarådets konvention | unknown | unknown | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2020/12/prop.-20202172/) |
| Fakta-PM | Faktapromemoria | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2023/04/prop.-20222395/) |
| Förordning | Svensk författningssamling | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2023/10/prop.-20232430/) |
| Förordning om ändring i internationella upphovsrättsförordningen (1994:193) | Svensk författningssamling | uniform | [source](https://www.regeringen.se/rattsliga-dokument/departementsserien-och-promemorior/2024/10/promemoria-andrade-ersattningsregler-for-anvandning-av-musik/) |
| Lag | Svensk författningssamling | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2024/04/prop.-202324113/) |
| Lag och förordningar | unknown | unknown | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2015/11/prop-20151654/) |
| Promemoria Förslag till lag om ändring i lagen (2010:1882) om åldersgränser för film som ska visas offentligt | Departementsserien och promemorior | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2016/11/prop.-20161735/) |
| Promemoria: Stärkt besittningsskydd för våldsutsatta hyresgäster | Rapport | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2014/03/prop.-201314195/) |
| Regeringsbeslut | Riksdagsbeslut | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2026/04/prop.-202526247/) |
| Remiss (1 st | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2025/12/prop.-20252671/) |
| Remiss 1 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/departementsserien-och-promemorior/2019/09/andringar-i-lagstiftningen-om-sociala-trygghetsformaner-efter-det-att-forenade-kungariket-har-lamnat-europeiska-unionen/) |
| Remiss 2 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/departementsserien-och-promemorior/2019/09/andringar-i-lagstiftningen-om-sociala-trygghetsformaner-efter-det-att-forenade-kungariket-har-lamnat-europeiska-unionen/) |
| Remiss 2015:42 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/departementsserien-och-promemorior/2015/09/ds-201542/) |
| Remiss 2015:54 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2016/04/prop.-201516148/) |
| Remiss 2015:8 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2015/09/prop.-2015163/) |
| Remiss Ds 2015:30 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2016/01/prop.-20151683/) |
| Remiss Ds 2015:37 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2016/10/prop.-20161717/) |
| Remiss Ds 2015:40 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2016/10/prop.-20161718/) |
| Remiss Ds 2015:47 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2016/09/prop.-2016176/) |
| Remiss Ds 2016:14 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/departementsserien-och-promemorior/2016/05/ds-201614/) |
| Remiss Ds 2016:35 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2017/04/prop.-201617175/) |
| Remiss Ds 2016:47 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2017/11/prop.-20171853/) |
| Remiss Ds 2016:6 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/departementsserien-och-promemorior/2016/03/ds-20166/) |
| Remiss Ds 2017:10 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2018/06/prop.-201718272/) |
| Remiss Ds 2017:22 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/departementsserien-och-promemorior/2017/05/ds-201722/) |
| Remiss Ds 2017:30 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2018/04/prop-201718214/) |
| Remiss Ds 2017:55 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2018/03/prop.-201718152/) |
| Remiss Ds 2017:67 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/departementsserien-och-promemorior/2017/12/ds-201767/) |
| Remiss Ds 2017:7 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/departementsserien-och-promemorior/2017/05/kommunikation-for-var-gemensamma-sakerhet--ansvarsfragor-och-samordning/) |
| Remiss Ds 2018:3 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/departementsserien-och-promemorior/2018/03/ds-20183/) |
| Remiss Ds 2018:40 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2019/04/prop.-201819105/) |
| Remiss Promemoria | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/departementsserien-och-promemorior/2015/04/inordnande-av-statens-centrum-for-arkitektur-och-design-i-moderna-museet--en-kraftsamling-for-konsten-arkitekturen-och-formen/) |
| Remiss Promemoria Ku2016/01365/KL | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/departementsserien-och-promemorior/2016/05/promemoria-en-museimyndighet-for-hela-den-historiska-utvecklingen-i-sverige/) |
| Remiss SOU 2015:13 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/statens-offentliga-utredningar/2015/03/sou-201538/) |
| Remiss SOU 2015:38 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/statens-offentliga-utredningar/2015/03/sou-201538/) |
| Remiss SOU 2015:52 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/statens-offentliga-utredningar/2015/06/sou-2015-52/) |
| Remiss SOU 2015:57 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/statens-offentliga-utredningar/2015/06/sou-201557/) |
| Remiss SOU 2015:74 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/statens-offentliga-utredningar/2015/08/sou-201574/) |
| Remiss SOU 2015:77 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/statens-offentliga-utredningar/2015/09/sou-201577/) |
| Remiss SOU 2015:83 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/statens-offentliga-utredningar/2015/09/sou-201583/) |
| Remiss SOU 2015:88 Gestaltad livsmiljö | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2018/02/prop.-201718110/) |
| Remiss SOU 2015:89 Ny museipolitik | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2017/02/prop.-201617116/) |
| Remiss SOU 2016:13 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/skrivelse/2018/05/skr.-201718246/) |
| Remiss SOU 2016:37 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/statens-offentliga-utredningar/2016/05/sou-201637/) |
| Remiss SOU 2016:41 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/statens-offentliga-utredningar/2017/06/sou-201752/) |
| Remiss SOU 2017:24 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2020/03/prop.-201920135/) |
| Remiss SOU 2017:28 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/statens-offentliga-utredningar/2017/03/sou-201728/) |
| Remiss SOU 2017:52 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/statens-offentliga-utredningar/2017/06/sou-201752/) |
| Remiss SOU 2018:24 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/statens-offentliga-utredningar/2019/01/sou-20195/) |
| Remiss SOU 2018:63 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2021/09/prop.-202021224/) |
| Remiss SOU 2020:30 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/statens-offentliga-utredningar/2020/06/sou-202030/) |
| Remiss SOU 2020:68 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2021/09/prop.-202021224/) |
| Remiss av Ds 2016:25 Miljöbedömningar | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/departementsserien-och-promemorior/2017/09/ds-201625/) |
| Remiss av Ds 2017:33 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2018/03/prop.-201718112/) |
| Remiss av Ds 2017:35 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2018/03/prop.-201718161/) |
| Remiss av Ds 2018:28 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2019/04/prop.-20181991/) |
| Remiss av Ds 2019:13 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2020/03/prop/) |
| Remiss av Ds 2020:14 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2022/03/prop.-202122151/) |
| Remiss av Redovisning av regeringsuppdrag om skyldighet att anmäla vissa växtskadegörare | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2016/09/prop.-201516200/) |
| Remiss av SOU | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/statens-offentliga-utredningar/2020/01/sou-20204/) |
| Remiss av SOU 2011:7 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2016/12/prop.-20161757/) |
| Remiss av SOU 2018:45 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2019/06/prop.-201819151/) |
| Remiss av SOU 2020:37 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2025/05/prop.-202425162/) |
| Remiss av SOU 2020:41 | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/statens-offentliga-utredningar/2020/06/sou-202041/) |
| Remiss av Transportstyrelsens promemoria | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2019/04/prop.-201819111/) |
| Remiss av departementspromemoria | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2016/05/prop.-201516178/) |
| Remiss av hemställan (1) | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2019/10/prop.-20192030/) |
| Remiss av promemorian | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/departementsserien-och-promemorior/2019/11/forslag-till-ny-forordning-inom-bildkonst--form--och-konsthantverksomradet/) |
| Remiss av promemorian Promemoria Förslag till lag om ändring i lagen (2010:1882) om åldersgränser för film som ska visas offentligt | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2016/11/prop.-20161735/) |
| Remiss av utkast till lagrådsremiss | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2024/03/prop.-202324108/) |
| Remiss av utkast till lagrådsremiss En konsultationsordning i frågor som rör det samiska folket | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2021/10/prop.-20212219/) |
| Remiss av: SOU 2015:58 EU och kommunernas bostadspolitik | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/statens-offentliga-utredningar/2015/06/eu-och-kommunernas-bostadspolitik/) |
| Remiss promemoria | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2016/03/prop.-201516120/) |
| Remiss promemorian | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2025/06/prop.-202425183/) |
| Remiss utkast till lagrådsremiss | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/statens-offentliga-utredningar/2016/12/sou-201687/) |
| Remisser av promemorior | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2022/04/prop.-202122219/) |
| Remissvar | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2017/05/prop.-201617193/) |
| Remss | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2024/04/prop.-202324129/) |
| Riksdagen | Proposition | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2022/03/vardlandsavtal-mellan-sverige-och-internationella-vaccininstitutet/) |
| Riksdagen | Skrivelse | uniform | [source](https://www.regeringen.se/rattsliga-dokument/skrivelse/2024/04/skr.-202324122/) |
| Riksdagen | Riksdagsbeslut | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2024/05/prop.-202324146/) |
| Riksdagsbehandling | Riksdagsbeslut | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2015/11/prop-20151654/) |
| Riksdagsbslut | Riksdagsbeslut | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2025/05/prop.-202425174/) |
| Socialförsäkringsutredningen | Kommittédirektiv | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2017/11/prop.-20171853/) |
| Tilläggsdirektiv Dir. 2019:57 | Kommittédirektiv | uniform | [source](https://www.regeringen.se/rattsliga-dokument/statens-offentliga-utredningar/2020/11/sou-202063/) |
| Tilläggsremittering | Remiss | uniform | [source](https://www.regeringen.se/rattsliga-dokument/departementsserien-och-promemorior/2022/01/grundlaggande-omstallnings-och-kompetensstod/) |
| Uppdrag | Departementsserien och promemorior | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2017/01/prop.-20161792/) |
| Uppdrag | Rapport | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2017/06/prop.-201617214/) |
| Uppdrag | unknown | unknown | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2019/09/prop.-2019208/) |
| Uppdrag till Trafikverket och remiss av inriktningsunderlaget | Regeringsuppdrag, Remiss | mixed | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2016/10/prop.-20161721/) |
| Uppdraget | Departementsserien och promemorior | uniform | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2017/04/prop.-201617169/) |
| Uppdragsbeskrivning | Departementsserien och promemorior | uniform | [source](https://www.regeringen.se/rattsliga-dokument/departementsserien-och-promemorior/2022/01/grundlaggande-omstallnings-och-kompetensstod/) |
| Övriga utredningar | Departementsserien och promemorior, Statens offentliga utredningar | mixed | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2018/09/prop.-201718302/) |

## URL outliers and contradictory metadata

| Document | Reason | Candidate types | Example source |
| --- | --- | --- | --- |
| [document](https://www.regeringen.se/) | unknown | unknown | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2026/03/prop.-202526210/) |
| [document](https://www.regeringen.se/artiklar/2016/02/forordningar-om-mottagande-av-nyanlanda-for-bosattning/) | unknown | unknown | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2015/11/prop-20151654/) |
| [document](https://www.regeringen.se/informationsmaterial/2017/04/uppdrag-att-utreda-vissa-fragor-pa-vapenlagstiftningens-omrade/) | unknown | unknown | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2021/11/prop.-20212246/) |
| [document](https://www.regeringen.se/informationsmaterial/2017/11/uppdrag-att-se-over-bostadshyresgastens-stallning-nar-en-lagenhet-forstors/) | unknown | unknown | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2019/09/prop.-2019208/) |
| [document](https://www.regeringen.se/informationsmaterial/2018/04/tillaggsuppdrag-till-uppdraget-att-utreda-vissa-fragor-pa-vapenlagstiftningens-omrade-ju-2017e/) | unknown | unknown | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2021/11/prop.-20212246/) |
| [document](https://www.regeringen.se/rattsliga-dokument/departementsserien-och-promemorior/2021/03/utkast-till-lagradsremiss-anpassningar-till-eus-marknadskontrollforordning/) | item_url_conflict | Departementsserien och promemorior, Lagrådsremiss | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2022/05/prop.-202122238/) |
| [document](http://eur-lex.europa.eu/legal-content/SV/ALL/?uri=uriserv:OJ.L_.2017.242.01.0001.01.SWE) | unknown | unknown | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2018/04/prop.-201718241/) |
| [document](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=consil%3AST_15698_2022_INIT) | unknown | unknown | [source](https://www.regeringen.se/kommenterade-dagordningar/2021/06/kommenterad-dagordning-for-radets-mote-for-rattsliga-och-inrikes-fragor-rif-den-78-juni-2021/?id=52021PC0206) |
| [document](https://eur-lex.europa.eu/legal-content/SV/ALL/?uri=CELEX:52021XX0324(01)) | unknown | unknown | [source](https://www.regeringen.se/faktapromemoria/2021/11/202021fpm6/) |
| [document](https://eur-lex.europa.eu/legal-content/SV/TXT/?uri=uriserv:OJ.L_.2015.141.01.0073.01.SWE) | unknown | unknown | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2019/12/prop.-20192055/) |
| [document](https://eur-lex.europa.eu/legal-content/SV/TXT/?uri=uriserv:OJ.L_.2022.305.01.0012.01.SWE) | unknown | unknown | [source](https://www.regeringen.se/rattsliga-dokument/departementsserien-och-promemorior/2023/03/eus-nya-forordning-om-upphandlingsannonser/) |
| [document](https://eur-lex.europa.eu/search.html?scope=EURLEX&text=52023PC0508&lang=sv&type=quick&qid=1698245175370) | unknown | unknown | [source](https://www.regeringen.se/faktapromemoria/2023/10/202324fpm6/) |
| [document](https://svenskforfattningssamling.se/index.html) | unknown | unknown | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2024/10/prop.-20242544/) |
| [document](https://www.coe.int/en/web/conventions/full-list/-/conventions/treaty/185) | unknown | unknown | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2020/12/prop.-20202172/) |
| [document](https://www.europarl.europa.eu/doceo/document/TA-9-2023-0236_EN.html) | unknown | unknown | [source](https://www.regeringen.se/kommenterade-dagordningar/2021/06/kommenterad-dagordning-for-radets-mote-for-rattsliga-och-inrikes-fragor-rif-den-78-juni-2021/?id=52021PC0206) |
| [document](https://www.riksdagen.se/sv/webb-tv/video/beslut/beslut-forbattrade-forutsattningar-for-operativt_hdc320260617föu14/) | unknown | unknown | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2026/06/prop.-202526279/) |
| [document](https://www.riksdagen.se/sv/webb-tv/video/debatt-om-forslag/en-ny-mottagandelag_hd01sfu35/) | unknown | unknown | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2026/04/prop.-202526229/) |
| [document](https://www.svenskförfattningssamling.se/doc/2020574.html) | unknown | unknown | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2020/03/prop.-201920123/) |
| [document](https://www.svenskförfattningssamling.se/doc/2020575.html) | unknown | unknown | [source](https://www.regeringen.se/rattsliga-dokument/proposition/2020/03/prop.-201920123/) |

## Ambiguities that must stay explicit

- **Document type versus process stage.** Riksdagen hosts propositions and government communications too. Committee reports can be displayed under Riksdagsbeslut, but are proposals for a decision, not proof that a decision has been made. Known process-stage headings are not automatically replaced because a linked document has another type.
- **More specific source labels.** Remissvar, Delrapport, Tilläggsremittering and Budgetförslag may convey a role or subtype beyond the linked page's general document type. The 150 uniform results are type-normalization candidates, not 150 proven errors. Adopting a coarser vocabulary is an explicit schema choice.
- **Mixed stages.** A heading can contain multiple types. Normalize each document first; split only exotic stages with complete evidence, preserving the order of first appearance. Keep a diagnostic instead of forcing one type.
- **Item metadata versus URL.** The indexed draft referral on market surveillance is labelled Lagrådsremiss but its path is Departementsserien och promemorior. That conflict requires an explicit precedence decision or a narrowly scoped exception.
- **EUR-Lex.** Use the CELEX sector and document-type letters or an ELI type. A proposal, regulation, directive, framework decision, parliamentary position and recommendation are different types. Domain-only guessing loses that distinction. Official-Journal references and Council-document identifiers without CELEX remain unknown.
- **Generic links.** Information pages, the government homepage, videos and attachments without metadata do not identify a legal document type. The accented hostname `svenskförfattningssamling.se` is not the same hostname as `svenskforfattningssamling.se`; it is not silently treated as a trusted alias.
- **Actors and dates.** Type inference does not establish who issued a legal act, what a chain date means, or whether a process is ongoing. Those findings need separate rules.
- **Wrong targets of the right type.** A link to the wrong proposition or SFS document still matches the same URL rule. This approach does not replace the title/identifier and broken-link checks in the earlier reports.

Across all stages, 104 contain confidently classified documents of different stage types, and 38 uniform stages have another type than their recognized heading. These are diagnostics, not counts of proven website errors. Full cases are retained in `chains-url-report.json`.

Rules are isolated in `services/chain_normalization.py` and also used by the lean exporter. This audit itself changes no stored observations or exported chain data.

Source definitions: [EUR-Lex CELEX numbers](https://eur-lex.europa.eu/content/help/eurlex-content/celex-number.html?locale=en), [EUR-Lex document types](https://eur-lex.europa.eu/content/tools/TableOfSectors/types_of_documents_in_eurlex.html?locale=en), [Riksdagen document types](https://www.riksdagen.se/sv/dokument-och-lagar/).

Reproduce:

```bash
uv run audit_chain_types.py
```
