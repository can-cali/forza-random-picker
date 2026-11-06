# Replacement photo sources: investigation, 2026-11-06

The Windows diagnostic establishes a Cloudflare browser challenge on Fandom's image CDN: HTTP 403, `cf-mitigated: challenge`. Direct CDN resolution and API-resolved URLs both encounter it. Tests through the cloud proxy do not reproduce that connection. No challenge bypass or browser-cookie extraction is implemented.

## Findings

| Source | Verified access and interface | Coverage / decision |
| --- | --- | --- |
| Official Forza car list | HTTP 200; car metadata table | No per-car image links on the examined page. Retain for metadata; not a verified photo provider. |
| Wikimedia Commons | Documented MediaWiki API returned HTTP 200, file URLs, authors, and per-file licenses; an API-returned thumbnail downloaded and decoded | Best candidate for reviewed, real-world fallback photos. Search results require model/year/trim validation. Not a full replacement for game renders. |
| Openverse | API documentation accessible, but image-search endpoint returned HTTP 403 with a browser-challenge page from this cloud environment | Not selected as an alternative to the current challenge problem. Openverse is also an index; downstream image hosts can fail independently. |
| Curated image pack | No redistributable, adequately covered pack verified | Could provide predictable offline behavior, but requires a verified source and appropriate redistribution permission per image. |

## Commons coverage sample

Queries used file namespace 6 and up to five results each, requesting `imageinfo` URLs and `extmetadata`. These are observations of the returned sample, not a complete coverage audit.

| Query | Returned sample and implication |
| --- | --- |
| `"Alfa Romeo Giulietta" "Quadrifoglio Verde"` | Includes `2011 Alfa Romeo Giulietta (940) QV hatchback (2015-07-24) 01.jpg`, author OSX, public domain according to API metadata; thumbnail HTTP 200 and decoded. Other hits include different years. |
| `"Audi RS 4 Avant" "2018"` | Front/rear files explicitly named 2018 Audi RS 4 Avant; author Vauxford, CC BY-SA 4.0. |
| `"BMW M4 CS" "2025"` | Returned older F82 photos as well as G82 VR46 edition photos. Relevance ranking does not enforce correct generation/edition. |
| `"Ford Mustang GTD"` | First five hits included EcoBoost, convertible and other Mustang photos. Do not automatically select the first hit. |
| `"Honda S2260 Alpha"` | No returned files. Do not silently correct model names from the official catalog. |
| `"Luftauto 002"` | No returned files. |
| `"Nissan" "Xtreme GTR"` | No returned files. |

## Recommended integration

Use Commons as an explicitly labeled **real-world fallback**, with reviewed file mappings or a user selection step for uncertain results. Keep valid existing game images. Store the author, source file page, license, license URL, and any modification information alongside each installed fallback and expose attribution in the GUI. Use API-returned thumbnail URLs rather than inventing paths. Respect the API's descriptive User-Agent, maxlag, caching, and request-limit guidance. A supported API and an image's reuse license are separate requirements.

Do not automatically replace an image with the first search hit. A fallback cannot fill all game-specific, custom-build or fictional-edition gaps. Exact match and generation/trim correctness need review even when a filename mentions the year. No Commons provider has been enabled in the application by this investigation.

## Reproduce on Windows

From the activated virtual environment:

```powershell
python -m scripts.research_photo_sources
python -m scripts.research_photo_sources --query '"Audi RS 4 Avant" "2018"'
```

The command prints candidate file pages and license metadata and checks the first thumbnail in memory. It does not write application data. Cloud success does not establish Windows success; this command permits validation on the affected connection before integration.

## Authoritative references

- [Commons API](https://commons.wikimedia.org/w/api.php)
- [MediaWiki imageinfo API](https://www.mediawiki.org/wiki/API:Imageinfo)
- [MediaWiki API etiquette](https://www.mediawiki.org/wiki/API:Etiquette)
- [Commons reuse requirements](https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia)
- [Openverse API documentation](https://docs.openverse.org/api/)
- [Official car list](https://forza.net/fh6cars)
