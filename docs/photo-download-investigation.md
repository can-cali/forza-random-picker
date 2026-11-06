# Photo download investigation

Live verification on 2026-11-06, using Python 3.12 and the app's Requests session.

## Request flow

1. Decode an existing cached image; return it only if valid.
2. Remove `File:` from the wiki title and replace spaces with underscores.
3. Compute MD5 over that UTF-8 filename (MediaWiki's directory convention, not a security checksum).
4. URL-encode the filename and request `https://static.wikia.nocookie.net/forzamotorsport/images/<first hash character>/<first two hash characters>/<encoded filename>/revision/latest`.
5. Require successful HTTP status and a decodable image before atomically replacing the cache file.
6. For known titles, fall back to the wiki API if direct resolution fails. For inferred titles, a 404 means absent; do not call the API once for every guess.

For unmapped cars, try at most nine distinct `.png` names: year suffix, no year, and year prefix, using the exact make/model, an ASCII spelling, and an ASCII spelling without hash/apostrophe punctuation. No fuzzy model matching or other game editions are used. Successful filenames are persisted in the local catalog snapshot. Reports list attempted filenames for unmatched cars and retain errors separately.

## Live observations

- Official `https://forza.net/fh6cars`: HTTP 200, metadata table, no per-car image links.
- Fandom API and HTML pages: HTTP 402, `Please contact the site owner for access.` from this environment.
- All 28 exact filenames in the Windows failure report were retrieved and decoded successfully in an isolated temporary cache using the new downloader. They include `FH6 BMW M4 CS.png`, `FH6 Citroen Ami.png`, `FH6 Ford Mustang GTD.png`, and `FH6 Mercedes-AMG GT63 4MATIC+.png`.
- CDN responses can be WebP despite `.png` filenames; Qt decodes them by content.
- Missing files return HTTP 404 with a decodable placeholder image. Decoding alone must not count as a successful download.
- A real worker run on 38 selected cars completed: six downloaded, 32 unmatched, zero failed. This comprised the 31 user-reported unmatched cars and seven known-file targets. The bundled cloud map lacked the Mercedes mapping present in the user's local saved catalog, so its exact spelling was unavailable in this worker run; the separate known-filename test retrieved it successfully.
- None of the exact variants for the 31 user-reported unmatched cars resolved. This does not establish that an image does not exist under a different name.
- Current official HTML parsed as 667 cars. The updater merges existing cars, so a locally retained catalog may have more entries.

## Validation and limits

Run deterministic tests with `.venv/bin/python -m pytest tests -q` (Windows: `python -m pytest tests -q` in the activated venv). Network requests are mocked or target a local HTTP test server; these tests do not depend on Fandom availability.

The live results establish access from the cloud environment, not Windows. The exact cause of the earlier Windows CDN 403 remains unconfirmed. This change removes API dependence and uses a stable revision URL without its cache-busting query; it does not claim to bypass CDN restrictions. Windows verification: pull `feature`, restart the app, select **Updates → Retry missing photos**, then inspect **Show photo download report**. Do not delete the existing valid cache.

Live checks wrote only under `/tmp/forza-direct-live`; bundled catalog and image map were not modified. Remote services can change independently of these recorded observations.
