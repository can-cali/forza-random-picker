"""Inspect licensed Commons candidates without modifying the catalog or cache.

Example: python -m scripts.research_photo_sources --query '"Audi RS 4 Avant" "2018"'
Search relevance is not proof of the correct trim/model/year. Review file pages.
"""
import argparse
import json

import requests
from bs4 import BeautifulSoup
from PySide6.QtGui import QImage


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--query', default='"Alfa Romeo Giulietta" "Quadrifoglio Verde"')
    args = parser.parse_args()
    with requests.Session() as session:
        session.headers['User-Agent'] = 'ForzaRandomPicker/1.0 (https://github.com/can-cali/forza-random-picker)'
        response = session.get('https://commons.wikimedia.org/w/api.php', params={
            'action': 'query', 'format': 'json', 'generator': 'search', 'gsrnamespace': 6,
            'gsrsearch': args.query, 'gsrlimit': 5, 'prop': 'imageinfo',
            'iiprop': 'url|extmetadata', 'iiurlwidth': 640, 'maxlag': 5,
        }, timeout=20)
        response.raise_for_status()
        data = response.json()
        if 'error' in data:
            raise RuntimeError(data['error'])
        candidates = []
        for page in data.get('query', {}).get('pages', {}).values():
            info = page.get('imageinfo', [{}])[0]
            metadata = info.get('extmetadata', {})
            candidates.append({
                'title': page['title'], 'file_page': info.get('descriptionurl'),
                'thumbnail': info.get('thumburl'),
                'artist': BeautifulSoup(metadata.get('Artist', {}).get('value', ''), 'html.parser').get_text(' ', strip=True),
                'license': metadata.get('LicenseShortName', {}).get('value'),
                'license_url': metadata.get('LicenseUrl', {}).get('value'),
            })
        print(json.dumps({'query': args.query, 'candidates': candidates}, ensure_ascii=False, indent=2))
        if candidates and candidates[0]['thumbnail']:
            thumbnail = session.get(candidates[0]['thumbnail'], timeout=20)
            thumbnail.raise_for_status()
            print('First candidate thumbnail decoded:', not QImage.fromData(thumbnail.content).isNull())
        print('Research only: no image was selected, saved, or installed in the app.')


if __name__ == '__main__':
    main()
