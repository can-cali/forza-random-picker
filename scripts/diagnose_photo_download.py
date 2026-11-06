"""Compare HTTP clients on the user's machine without modifying the app/cache.

Run from the checkout: python -m scripts.diagnose_photo_download
Only selected response headers and a short non-image error body are printed.
Cookies, authorization headers, proxy addresses and environment values are omitted.
"""
import os
import platform
import shutil
import subprocess
import sys

import requests

from forza_picker.wiki_images import http_session

URL = ('https://static.wikia.nocookie.net/forzamotorsport/images/9/9f/'
       'FH6_BMW_M4_CS.png/revision/latest')
SAFE_HEADERS = ('content-type', 'server', 'via', 'cf-mitigated', 'cf-ray',
                'x-cache', 'retry-after', 'location')


def show_response(label, response):
    print(f'\n{label}: HTTP {response.status_code}')
    for name in SAFE_HEADERS:
        if name in response.headers:
            # Avoid printing redirect targets that might contain query tokens.
            value = response.headers[name].split('?', 1)[0] if name == 'location' else response.headers[name]
            print(f'  {name}: {value}')
    print(f'  bytes: {len(response.content)}')
    if response.status_code >= 400:
        print('  error body:', response.text[:600].replace('\n', ' '))


def main():
    print('Python:', sys.version.split()[0], 'OS:', platform.system(), platform.release())
    print('Requests:', requests.__version__)
    print('Proxy variable names present:', ', '.join(
        name for name in ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY',
                          'http_proxy', 'https_proxy', 'all_proxy', 'no_proxy')
        if name in os.environ) or 'none')
    print('Target:', URL)
    for label, get in [('App session', http_session().get), ('Default Requests', requests.get)]:
        try:
            show_response(label, get(URL, timeout=15, allow_redirects=False))
        except requests.RequestException as exc:
            # Exception strings can embed proxy credentials; print only their class.
            print(f'\n{label}: {type(exc).__name__}')
    curl = shutil.which('curl.exe') if platform.system() == 'Windows' else None
    if curl:
        print('\nWindows curl.exe (same URL, default client settings):', flush=True)
        # Stream the first 600 body bytes and selected headers; never verbose-log requests.
        result = subprocess.run([curl, '--silent', '--show-error', '--max-time', '20',
                                 '--dump-header', '-', URL], capture_output=True)
        if result.returncode:
            print('  curl exit code:', result.returncode)
        else:
            output = result.stdout
            header = b''
            while b'\r\n\r\n' in output:
                header, output = output.split(b'\r\n\r\n', 1)
                lines = header.decode('latin1').splitlines()
                print(' ', lines[0])
                for line in lines[1:]:
                    if line.split(':', 1)[0].lower() in SAFE_HEADERS:
                        print(' ', line.split('?', 1)[0])
                if not output.startswith(b'HTTP/'):
                    break
            if 'image/' not in header.decode('latin1').lower():
                print('  error body:', output[:600].decode('utf-8', errors='replace').replace('\n', ' '))
    else:
        print('\nWindows curl.exe comparison unavailable on this machine.')
    print('\nNo application data or settings were changed.')


if __name__ == '__main__':
    main()
