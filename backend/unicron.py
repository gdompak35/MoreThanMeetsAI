import html
import re
from urllib.parse import urljoin
from urllib.request import Request, urlopen

BASE_URL = 'https://www.unicron.com/tfitem/itemimage_db.php?mode=instructions&seriesID=23'
SIZE_LABELS = ('commander', 'deluxe', 'leader', 'voyager', 'legends', 'scout', 'basic', 'core', 'titan', 'ultimate', 'supreme', 'masterpiece')
LEGACY_CATALOG_PAGES = {
    'titans return': 'https://www2.unicron.com/2017-transformers/581-2017-generations.html',
}

def _fetch(url):
    request = Request(url, headers={'User-Agent': 'MoreThanMeetsAI-V2/0.1'})
    with urlopen(request, timeout=15) as response:
        return response.read().decode('utf-8', errors='replace')

def _clean(value):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', value))).strip()

def _norm(value):
    return re.sub(r'[^a-z0-9]+', ' ', value.lower()).strip()

def _absolute(value):
    return urljoin('https://www.unicron.com', html.unescape(value))

def _toy_page_url(instruction_url):
    try:
        page = _fetch(instruction_url)
    except Exception:
        return ''
    pattern = r"(?is)<a\b[^>]*href=['\"]((?:https?:)?//www2\.unicron\.com/[^'\"]+)['\"][^>]*>(.*?)</a>"
    for match in re.finditer(pattern, page):
        href, label = match.group(1), _clean(match.group(2)).lower()
        if any(excluded in href.lower() for excluded in ('mastercp.html', 'characterlist.html', 'sitecat', 'review')):
            continue
        if re.search(r'(?i)(?:19|20)\d{2}-transformers|transformers', href) or 'toy' in label:
            return _absolute(href)
    return ''

def instruction_context(entry):
    """Fetch the matched instruction record and its linked toy page."""
    detail_url = entry.get('product_url', '')
    toy_url = entry.get('toy_page_url', '')
    detail_html = _fetch(detail_url) if detail_url else ''
    toy_html = _fetch(toy_url) if toy_url else ''
    images = []
    for value in re.findall(r'(?is)(?:src|href)=["\']([^"\']*itemimage_imgsrc\.php[^"\']*)["\']', detail_html):
        url = _absolute(value).replace('size=150', 'size=9999')
        if url not in images: images.append(url)
    if entry.get('image_url') and entry['image_url'] not in images:
        images.insert(0, entry['image_url'])
    return {'matched_entry': entry, 'instruction_page_html': detail_html[:40000], 'toy_page_html': toy_html[:40000], 'image_urls': images[:24]}

def _series_links(page):
    links = []
    pattern = r"(?is)<a\s+href=['\"]([^'\"]*mode=instructions[^'\"]*seriesID=([0-9]+)[^'\"]*)['\"]>(.*?)</a>"
    for match in re.finditer(pattern, page):
        title = _clean(match.group(3))
        if title and not any(item['id'] == match.group(2) for item in links):
            links.append({'id': match.group(2), 'title': title})
    # The configured catalog URL is itself the Movie ROTF series page, so the
    # current series is not always repeated as a navigation link.
    current = next((item for item in links if item['id'] == '23'), None)
    if current:
        current['title'] = 'Movie ROTF'
    else:
        links.append({'id': '23', 'title': 'Movie ROTF'})
    return links

def _series_score(requested, title):
    wanted, found = _norm(requested), _norm(title)
    aliases = {
        'revenge of the fallen': ('movie rotf', 'takara movie revenge'),
        'revenge of fallen': ('movie rotf', 'takara movie revenge'),
        'movie revenge of the fallen': ('movie rotf', 'takara movie revenge'),
        'rotf': ('movie rotf', 'takara movie revenge'),
        'masterpiece movie': ('masterpiece',),
        'masterpiece movie series': ('masterpiece',),
        'g1': ('g1',),
        'titans return': ('generations',),
        'legacy': ('generations',),
        'legacy evolution': ('generations',),
        'legacy united': ('generations',),
        'age of the primes': ('generations',),
        'buzzworthy bumblebee': ('generations', 'studio series'),
        '86': ('studio series',),
        'mtmte': ('studio series',),
        'gamer edition': ('studio series',),
        'mpg': ('masterpiece',),
        'robots in disguise': ('tf prime',),
        'first edition': ('tf prime',),
        'beast hunters': ('tf prime',),
    }
    options = (wanted,) + aliases.get(wanted, ())
    if found in options: return 100
    if any(option in found or found in option for option in options if option): return 70
    return 0

def _years(page):
    result = []
    for match in re.finditer(r"(?is)<a\s+href=['\"]([^'\"]*mode=instructions[^'\"]*year=([0-9]{4})[^'\"]*)['\"]", page):
        if match.group(2) not in result: result.append(match.group(2))
    return result

def _entries(page, fields, tfwiki_entry):
    aliases = {_norm(fields.get('character', ''))}
    for value in (tfwiki_entry.get('name', ''), tfwiki_entry.get('product_name', '')):
        if value:
            primary_value = re.split(r'(?i)\s*(?:\(|\bwith\b|\bvs\.?\b|&)', value, maxsplit=1)[0].strip()
            if primary_value: aliases.add(_norm(primary_value))
    results = []
    pattern = r"(?is)<div\s+class=['\"]inst_title_info['\"]>\s*<b>(.*?)</b>(.*?)(?=<!--\s*item:|<h2\b|\Z)"
    for match in re.finditer(pattern, page):
        name, block = _clean(match.group(1)), match.group(0)
        name_norm = _norm(name)
        primary_name = re.split(r'(?i)\s*(?:\(|\bwith\b|\bvs\.?\b)', name, maxsplit=1)[0].strip()
        name_matches = any(a and (a == name_norm or a in name_norm or name_norm in a) for a in aliases)
        primary_matches = any(a and (a == _norm(primary_name) or a in _norm(primary_name) or _norm(primary_name) in a) for a in aliases)
        # A multipack title can mention another character after "with" or
        # "vs.". That secondary name must not satisfy the user's character
        # request; the leading name is the instruction record's target.
        if not name_norm or not name_matches or (name_matches and not primary_matches and re.search(r'(?i)\b(?:with|vs\.?)\b', name)): continue
        detail = re.search(r"href=['\"]([^'\"]*itemimage_view\.php[^'\"]*)['\"]", block, re.I)
        image = re.search(r"src=['\"]([^'\"]*itemimage_imgsrc\.php[^'\"]*)['\"]", block, re.I)
        if not detail: continue
        detail_url = _absolute(detail.group(1))
        image_url = _absolute(image.group(1)).replace('size=150', 'size=9999') if image else ''
        results.append({'product_name': name, 'image_url': image_url, 'product_url': detail_url,
            'toy_page_url': _toy_page_url(detail_url),
            'criteria': {'character': fields.get('character',''), 'property': fields.get('property',''), 'toyline': fields.get('toyline',''), 'subline': fields.get('subline',''), 'size_class': fields.get('size_class','')},
            'summary': 'Instruction scan for ' + name + '.', 'source_url': detail_url,
            'section_heading': 'Unicron instructions catalog', 'entry_html': block})
    return results

def _entry_score(item, fields, tfwiki_entry):
    name = _norm(item.get('product_name', ''))
    text = _norm(item.get('entry_html', ''))
    score = 0
    character = _norm(fields.get('character', ''))
    property_name = _norm(fields.get('property', ''))
    confirmed_name = _norm(tfwiki_entry.get('product_name', ''))
    confirmed_tokens = [token for token in confirmed_name.split() if len(token) > 2]
    if character and character in name:
        score += 1000
    score += sum(2 for token in confirmed_tokens if token in name)
    score += _series_score(fields.get('toyline', ''), item.get('series_title', ''))
    if property_name in {'g1', 'gen 1', 'generation 1', 'generation 1'}:
        if any(marker in name or marker in text for marker in ('1986', 'tftm', 'generation 1', 'g1')):
            score += 8
        else:
            score -= 3
    if fields.get('subline') and _norm(fields['subline']) in name:
        score += 80
    confirmed_size = _norm((tfwiki_entry.get('criteria') or {}).get('size_class', '') or fields.get('size_class', ''))
    requested_size = next((label for label in SIZE_LABELS if label in confirmed_size), '')
    if requested_size:
        # Unicron often puts the size in the instruction title. A title-level
        # match is stronger than a shared character name, especially when the
        # confirmed TFWiki toy is a redeco whose name is absent from Unicron.
        if re.search(rf'\b{re.escape(requested_size)}(?:\s+class)?\b', name):
            score += 24
        elif re.search(rf'\b{re.escape(requested_size)}(?:\s+class)?\b', text):
            score += 8
        for other in SIZE_LABELS:
            if other != requested_size and re.search(rf'\b{re.escape(other)}(?:\s+class)?\b', name):
                score -= 14
    return score

def has_direct_match(result, tfwiki_entry):
    """Require the Unicron title to identify the confirmed toy itself."""
    confirmed = _norm(tfwiki_entry.get('product_name', ''))
    if not confirmed:
        return bool(result.get('matches'))
    ignored = {'class', 'toy', 'figure', 'series', 'version', 'edition', 'the', 'of', 'and', 'with', 'vs'}
    confirmed_tokens = [token for token in confirmed.split() if token not in ignored]
    for item in result.get('matches', []):
        name = _norm(item.get('product_name', ''))
        if confirmed == name or confirmed in name or name in confirmed:
            return True
        if confirmed_tokens and all(token in name.split() for token in confirmed_tokens):
            return True
    return False

def source_alignment_count(tfwiki_entry, unicron_entry):
    """Compare only evidence present in the two retrieved source records."""
    criteria = tfwiki_entry.get('criteria') or {}
    character = _norm(criteria.get('character', ''))
    product_name = _norm(unicron_entry.get('product_name', ''))
    primary_name = re.split(r'\b(?:with|vs)\b', product_name, maxsplit=1)[0].strip()
    character_match = bool(character and character in primary_name)

    toyline = criteria.get('toyline', '')
    toyline_match = bool(toyline and _series_score(toyline, unicron_entry.get('series_title', '')) > 0)

    size = next((label for label in SIZE_LABELS if label in _norm(criteria.get('size_class', ''))), '')
    size_match = bool(size and re.search(rf'\b{re.escape(size)}(?:\s+class)?\b', product_name))
    return sum((character_match, toyline_match, size_match)), {
        'character': character_match,
        'toyline': toyline_match,
        'size_class': size_match,
    }

def _legacy_catalog_matches(fields, tfwiki_entry):
    requested = _norm(fields.get('subline') or fields.get('toyline', ''))
    catalog_url = LEGACY_CATALOG_PAGES.get(requested)
    if not catalog_url:
        return []
    try:
        page = _fetch(catalog_url)
    except Exception:
        return []
    wanted = _norm(fields.get('character', ''))
    confirmed = _norm(tfwiki_entry.get('product_name', ''))
    results = []
    for match in re.finditer(r"(?is)<a\b[^>]*href=['\"]([^'\"]+\.html)['\"][^>]*>(.*?)</a>", page):
        href, label_html = match.group(1), match.group(2)
        label = _clean(label_html)
        haystack = _norm(href + ' ' + label)
        if not wanted or wanted not in haystack:
            continue
        if requested not in haystack and requested != 'titans return':
            continue
        url = urljoin('https://www2.unicron.com', href)
        if any(item['toy_page_url'] == url for item in results):
            continue
        results.append({
            'product_name': label,
            'image_url': '',
            'product_url': url,
            'toy_page_url': url,
            'criteria': {'character': fields.get('character', ''), 'property': fields.get('property', ''), 'toyline': 'Generations', 'subline': fields.get('subline') or fields.get('toyline', ''), 'size_class': fields.get('size_class', '')},
            'summary': 'Unicron catalog toy page for ' + label + '.',
            'source_url': url,
            'section_heading': 'Unicron catalog toy page',
            'entry_html': '',
        })
    confirmed_tokens = [token for token in confirmed.split() if len(token) > 2]
    results.sort(key=lambda item: (
        requested in _norm(item['product_name'] + ' ' + item['toy_page_url']),
        sum(token in _norm(item['product_name']) for token in confirmed_tokens),
    ), reverse=True)
    return results[:3]

def search(fields, tfwiki_entry):
    try: catalog = _fetch(BASE_URL)
    except Exception as error: return {'status':'source_unavailable','matches':[],'source_url':BASE_URL,'message':'Unicron instructions database could not be reached.','error_type':type(error).__name__}
    series_links = _series_links(catalog)
    requested_series = _norm(fields.get('toyline', ''))
    series = next((item for item in series_links if item['id'] == '23'), None) if requested_series in {'rotf', 'revenge of the fallen', 'revenge of fallen', 'movie revenge of the fallen'} else max(series_links, key=lambda item: _series_score(fields.get('toyline',''), item['title']), default=None)
    if not series or _series_score(fields.get('toyline',''), series['title']) == 0:
        return {'status':'no_match','matches':[],'source_url':BASE_URL,'message':'No matching Unicron instructions series was found.'}
    series_url = _absolute(f"/tfitem/itemimage_db.php?mode=instructions&seriesID={series['id']}")
    try:
        series_page = _fetch(series_url); pages = [(series_page, series_url)]
        # The catalog has a finite set of year pages. Check all of them so a
        # later release, such as a 2017 Titans Return toy, is not skipped.
        for year in _years(series_page):
            year_url = _absolute(f"/tfitem/itemimage_db.php?mode=instructions&year={year}&seriesID={series['id']}")
            pages.append((_fetch(year_url), year_url))
        matches = []
        for page, _ in pages:
            for item in _entries(page, fields, tfwiki_entry):
                item['series_title'] = series['title']
                if not any(existing['product_url'] == item['product_url'] for existing in matches): matches.append(item)
        matches.sort(key=lambda item: _entry_score(item, fields, tfwiki_entry), reverse=True)
        catalog_matches = _legacy_catalog_matches(fields, tfwiki_entry)
        if catalog_matches:
            matches = catalog_matches + [item for item in matches if item.get('toy_page_url') not in {candidate.get('toy_page_url') for candidate in catalog_matches}]
        return {'status':'match' if matches else 'no_match', 'matches':matches[:3], 'source_url':series_url, 'catalog_url':BASE_URL,
            'message':f"Unicron instructions found for the {series['title']} series." if matches else 'The Unicron series was found, but no matching instruction entry was found.'}
    except Exception as error:
        return {'status':'source_unavailable','matches':[],'source_url':series_url,'message':'The Unicron instructions series could not be read.','error_type':type(error).__name__}

def search_related(fields, tfwiki_entry, related):
    alternate_fields = dict(fields)
    alternate_fields['character'] = related['name']
    alternate_entry = dict(tfwiki_entry or {})
    alternate_entry.update({'name': related['name'], 'url': related.get('url', '')})
    result = search(alternate_fields, alternate_entry)
    if result.get('matches'):
        result['status'] = 'alternate_match'
        result['alternate_for'] = fields.get('character', '')
        result['alternate_character'] = related['name']
        result['relationship'] = related.get('relationship', 'related toy')
        result['related_tfwiki_url'] = related.get('url', '')
        result['relationship_source'] = related.get('interpreted_by', 'TFWiki entry')
        original_name = (tfwiki_entry or {}).get('product_name') or fields.get('character', 'that toy')
        relationship = related.get('relationship', 'related toy')
        result['message'] = f"I couldn't find the instructions for {original_name} so I found the instructions for a {relationship} of it!"
    return result
