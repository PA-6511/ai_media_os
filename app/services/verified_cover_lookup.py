"""Official Kobo cover lookup; no DB writes, page images, or link rewrites."""
from __future__ import annotations

import json
import re
import os
import shlex
from pathlib import Path
import html
import unicodedata
from html.parser import HTMLParser
from types import SimpleNamespace
from urllib.parse import urlsplit

from app.integrations.rakuten_kobo_api_client import RakutenKoboApiClient, RequestsGetTransport
from app.integrations.rakuten_kobo_live_configuration import load_repository_live_configuration
from app.services.rakuten_kobo_manual_offer_resolver import (
    _normalized_product_identity,
)
from app.services.ebook_product_identity import (
    matches_kobo_cover_title_identity,
)


class VerifiedCoverLookupError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _same_cover_title(requested, provider):
    # PI2C_VERIFIED_COVER_SHARED_IDENTITY_V1
    return matches_kobo_cover_title_identity(
        requested_title=str(requested or ""),
        provider_title=str(provider or ""),
    )

def _resolve_official_product_page(*,requested_title,product_url,entered_price=''):
    """Resolve identity only; prices are not a prerequisite for an API cover."""
    _normalized_product_identity(product_url)
    response=RequestsGetTransport().get(url=product_url,headers={'User-Agent':'Mozilla/5.0 AI-Media-OS-Cover-Identity/1.0'},timeout_seconds=20,maximum_bytes=8*1024*1024)
    if response.status_code!=200:raise VerifiedCoverLookupError('KOBO_OFFICIAL_PRODUCT_PAGE_HTTP_ERROR')
    source=response.body.decode('utf-8')
    class Metadata(HTMLParser):
        def __init__(self):super().__init__();self.numbers=[]
        def handle_starttag(self,tag,attrs):
            values=dict(attrs)
            if tag=='meta' and values.get('property')=='books:isbn':self.numbers.append(values.get('content',''))
    meta=Metadata();meta.feed(source)
    title=re.search(r'<title[^>]*>(.*?)</title>',source,re.I|re.S)
    if not title:raise VerifiedCoverLookupError('KOBO_OFFICIAL_PAGE_TITLE_MISSING')
    title=unicodedata.normalize('NFKC',html.unescape(title.group(1)))
    parts=title.rsplit(' - ',2)
    if len(parts)!=3 or not re.fullmatch(r'\d{13}',parts[-1].strip()):raise VerifiedCoverLookupError('KOBO_OFFICIAL_PAGE_ITEM_NUMBER_AMBIGUOUS')
    number=parts[-1].strip()
    if set(meta.numbers)!={number}:raise VerifiedCoverLookupError('KOBO_OFFICIAL_PAGE_ITEM_NUMBER_AMBIGUOUS')
    provider=re.sub(r'^楽天Kobo電子書籍ストア:\s*','',parts[0])
    if not _same_cover_title(requested_title,provider):raise VerifiedCoverLookupError('KOBO_OFFICIAL_PAGE_TITLE_MISMATCH')
    return SimpleNamespace(item_number=number)


def configured_cover_request(**kwargs):
    """Use the existing service credential file when a one-shot lacks env."""
    names = {'RAKUTEN_KOBO_APPLICATION_ID', 'RAKUTEN_KOBO_ACCESS_KEY', 'RAKUTEN_AFFILIATE_ID'}
    values = dict(os.environ)
    if not all(values.get(name) for name in names):
        try:
            for line in Path('/etc/ai-media-os/credential.env').read_text().splitlines():
                if '=' not in line or line.lstrip().startswith('#'): continue
                key, value = line.split('=', 1)
                if key.strip() in names and not values.get(key.strip()):
                    parsed = shlex.split(value)
                    if parsed: values[key.strip()] = parsed[0]
        except OSError:
            pass
    return load_repository_live_configuration(environment=values, **kwargs)


def verified_kobo_item(item, offer, *, api_client=None, configuration_loader=None):
    expected = str(offer.store_item_id or '').strip()
    product_url = str(offer.product_url or '').strip()
    legacy_id = not re.fullmatch(r'[0-9]{13}', expected)
    if legacy_id:
        product_identity = _normalized_product_identity(product_url)[1:]
        # This existing resolver binds title, canonical product page and number.
        # Only the number is used; the image must still come from the API.
        resolved = _resolve_official_product_page(
            requested_title=item.title, product_url=product_url, entered_price='',
        )
        expected = resolved.item_number
    loader = configuration_loader or load_repository_live_configuration
    configuration = loader(title=None, item_number=expected)
    if configuration is None:
        raise VerifiedCoverLookupError('STORE_NOT_CONNECTED')
    client = api_client or RakutenKoboApiClient(RequestsGetTransport())
    response = client.fetch(configuration)
    payload = json.loads(response.body.decode('utf-8'))
    wrappers = payload.get('Items', [])
    if len(wrappers) != 1:
        raise VerifiedCoverLookupError('API_ITEM_NOT_UNIQUE')
    value = wrappers[0].get('Item', wrappers[0])
    if str(value.get('itemNumber', '')) != expected:
        raise VerifiedCoverLookupError('ITEM_MISMATCH')
    if legacy_id and _normalized_product_identity(value.get('itemUrl', ''))[1:] != product_identity:
        raise VerifiedCoverLookupError('PRODUCT_URL_MISMATCH')
    image = str(value.get('largeImageUrl') or '')
    if not image:
        raise VerifiedCoverLookupError('IMAGE_MISSING')
    parsed = urlsplit(image)
    if parsed.scheme != 'https' or parsed.hostname != 'thumbnail.image.rakuten.co.jp' or parsed.username or parsed.password:
        raise VerifiedCoverLookupError('OFFICIAL_IMAGE_URL_INVALID')
    return value
