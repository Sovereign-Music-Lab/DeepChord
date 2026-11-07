#!/usr/bin/env python3
# Copyright 2026 Sovereign Music Lab contributors
# SPDX-License-Identifier: Apache-2.0
"""Check static locale parity, assets, anchors and public license metadata."""
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
import re
import struct
import tomllib

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'site'
BASE = 'https://sovereign-music-lab.github.io'


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.path = path
        self.ids = []
        self.links = []
        self.meta = {}
        self.lang = None
        self.alternates = {}
        self.canonical = None
        self.icons = []
        self.feed(path.read_text())

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if 'id' in a:
            self.ids.append(a['id'])
        if tag == 'html':
            self.lang = a.get('lang')
        if tag in {'a', 'link', 'script', 'img'}:
            value = a.get('href', a.get('src'))
            if value:
                self.links.append(value)
        if tag == 'link':
            if a.get('rel') == 'alternate':
                self.alternates[a.get('hreflang')] = a.get('href')
            if a.get('rel') == 'canonical':
                self.canonical = a.get('href')
            if 'icon' in a.get('rel', ''):
                self.icons.append(a.get('href'))
        if tag == 'meta':
            self.meta[a.get('property', a.get('name'))] = a.get('content')


def main():
    pages = {lang: Page(SITE / path) for lang, path in [('ko', 'index.html'), ('en', 'en/index.html')]}
    for lang, page in pages.items():
        route = '/' if lang == 'ko' else '/en/'
        assert page.lang == lang
        assert page.canonical == BASE + route
        assert page.meta['og:url'] == page.canonical
        assert page.meta['og:locale'] == {'ko': 'ko_KR', 'en': 'en_US'}[lang]
        assert page.alternates == {'ko': BASE + '/', 'en': BASE + '/en/', 'x-default': BASE + '/'}
        assert page.meta['og:image'] == f'{BASE}/assets/og-{lang}.png'
        assert page.meta['twitter:image'] == page.meta['og:image']
        assert page.meta['twitter:card'] == 'summary_large_image'
        assert page.meta['og:image:width'] == '1200' and page.meta['og:image:height'] == '630'
        assert page.meta['og:image:alt'] and page.meta['twitter:image:alt']
        assert len(page.icons) == 4
        assert not [k for k, v in Counter(page.ids).items() if v > 1]
        for href in page.links:
            url = urlsplit(href)
            if url.scheme or url.netloc:
                continue
            target = SITE / unquote(url.path.lstrip('/')) if url.path.startswith('/') else page.path.parent / unquote(url.path)
            if not url.path:
                target = page.path
            if target.is_dir():
                target /= 'index.html'
            assert target.is_file(), (lang, href)
            if url.fragment and target.suffix == '.html':
                assert unquote(url.fragment) in Page(target).ids, (lang, href)
        text = page.path.read_text()
        assert 'Sungmo Park' in text and 'APACHE 2.0' in text
        assert 'Seong-mo' not in text
        if lang == 'en':
            assert re.findall('[가-힣]+', text) == ['한국어']
        image = (SITE / f'assets/og-{lang}.png').read_bytes()
        assert image[:8] == b'\x89PNG\r\n\x1a\n'
        assert struct.unpack('>II', image[16:24]) == (1200, 630)
    assert set(pages['ko'].ids) == set(pages['en'].ids)
    assert (SITE / 'LICENSE').read_bytes() == (ROOT / 'LICENSE').read_bytes()
    assert (SITE / 'NOTICE').read_bytes() == (ROOT / 'NOTICE').read_bytes()
    assert tomllib.loads((ROOT / 'pyproject.toml').read_text())['project']['license'] == 'Apache-2.0'
    for name in ['README.md', 'docs/logic.md', 'docs/training.md', 'docs/landing-page.md', 'site/README.md']:
        path = ROOT / name
        partner = path.with_name(path.stem + '.ko.md')
        assert partner.is_file()
        assert partner.name in path.read_text() and path.name in partner.read_text()
    print('Site checks passed: two static locales, reciprocal language links, anchors, assets, social metadata, credits and Apache-2.0.')


if __name__ == '__main__':
    main()
