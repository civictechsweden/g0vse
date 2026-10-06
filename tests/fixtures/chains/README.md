# Legislative chain fixtures

These are unmodified HTML fragments saved from regeringen.se on 2026-09-26.
Only the chain navigation and (for EU) the chain chooser are retained.

- `legacy.html`: https://www.regeringen.se/rattsliga-dokument/proposition/2019/11/prop.-20192038/
  Includes nested wrappers, empty stages, explicit `aria-disabled` values and
  two Swedish statute links in one list item.
- `domestic.html`: https://www.regeringen.se/rattsliga-dokument/statens-offentliga-utredningar/2026/02/sou-202612/
  The current domestic layout, with h4 stage headings and tooltips.
- `eu.html`: https://www.regeringen.se/kommenterade-dagordningar/2026/06/kommenterad-dagordning-radet-for-ekonomiska-och-finansiella-fragor-den-12-juni-2026/?id=52025PC0989
  Three phases, multiple actors, an explicit current-page marker, external
  documents, empty stages and alternative selectors, including a CELEX bundle.
- `redirects.json`: resolved targets of the `.aspx` links in these fragments,
  captured on the same date. Tests inject this mapping and never access the web.
