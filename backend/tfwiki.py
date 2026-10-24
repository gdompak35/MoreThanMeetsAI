import html
import re
from urllib.parse import quote, unquote
from urllib.request import Request, urlopen

UA = 'MoreThanMeetsAI-V2/0.1'
GEN_SUBLINES = {'legacy','legacy evolution','legacy united','classics','united','reveal the shield','combiner wars','titans return','power of the primes','war for cybertron siege','war for cybertron earthrise','war for cybertron kingdom','age of the primes','universe 2.0','buzzworthy bumblebee'}
STUDIO_SUBLINES = {'86','mtmte','gamer edition','buzzworthy bumblebee'}
PRIME_SUBLINES = {'robots in disguise', 'first edition', 'beast hunters'}
G1_ALIASES = {'g1', 'gen 1', 'generation 1', 'generation-1', 'generation1'}
SUBLINE_ALIASES = {
    'masterpiece movie series': 'masterpiece movie',
    'legacy evolution': 'legacy: evolution',
    'legacy united': 'legacy united',
    'titans return': 'titans return',
}
TOYLINE_ALIASES = {
    'rotf': 'revenge of the fallen',
    'revenge of fallen': 'revenge of the fallen',
    'revenge of the fallen': 'revenge of the fallen',
    'dotm': 'dark of the moon',
    'aoe': 'age of extinction',
    'tlk': 'the last knight',
}
GENERATION_CONTEXT = re.compile(r'(?is)\b(?:released|part of|from|in|under|within|belongs to|comes from)\s+(?:the\s+)?(?:first|second|third|fourth|final|\w+)?\s*(?:wave\s+of\s+)?(?:the\s+)?(?:transformers\s*:\s*)?(legacy\s*(?::|-)?\s*(?:evolution|united)?|classics|united|reveal\s+the\s+shield|combiner\s+wars|titans\s+return|power\s+of\s+the\s+primes|war\s+for\s+cybertron(?:\s+siege|\s+earthrise|\s+kingdom)?|age\s+of\s+the\s+primes|generations)')

def normalize_heading(value: str) -> str:
    return re.sub(r'\s+', ' ', re.sub(r'\s*\([^)]*\)', '', value).lower()).strip(' :')

def canonical_toyline(value: str) -> str:
    normalized = re.sub(r'\s+', ' ', value.lower().replace('_', ' ')).strip()
    normalized = normalized.replace('generation–1', 'generation-1')
    if normalized in G1_ALIASES:
        return 'g1'
    return TOYLINE_ALIASES.get(normalized, normalized)

def canonical_subline(value: str) -> str:
    normalized = re.sub(r'\s+', ' ', value.lower()).strip()
    return SUBLINE_ALIASES.get(normalized, normalized)

def inferred_parent_toyline(value: str) -> str:
    key = canonical_subline(value)
    if key in GEN_SUBLINES:
        return 'generations'
    if key in STUDIO_SUBLINES:
        return 'studio series'
    if key in PRIME_SUBLINES:
        return 'prime'
    if key in {'masterpiece movie', 'mpg'}:
        return 'masterpiece'
    return ''

def normalize_search_fields(fields: dict) -> dict:
    normalized = dict(fields)
    parent = inferred_parent_toyline(normalized.get('toyline', ''))
    if parent and canonical_toyline(normalized.get('toyline', '')) != parent:
        normalized['subline'] = normalized.get('subline') or normalized.get('toyline', '')
        normalized['toyline'] = parent.title() if parent != 'studio series' else 'Studio Series'
    return normalized

def character_matches(character: str, product_name: str, description: str) -> bool:
    # The formal-name fallback applies only to the toy record itself: its
    # product name or opening identity sentence. Distant description mentions
    # cannot make an unrelated toy qualify.
    haystack = product_name.lower()
    query = re.sub(r'\s+prime\s*$', '', character.strip(), flags=re.I)
    if character.lower() in haystack or (query and query.lower() in haystack):
        return True
    opening = description[:500].lower()
    return bool(character.lower() in opening or (query and query.lower() in opening))

def heading_text(heading_html: str, heading_id: str) -> str:
    match = re.search(r'(?is)<span\b[^>]*class="[^"]*mw-headline[^"]*"[^>]*>(.*?)</span>', heading_html)
    return (clean(match.group(1)) if match else heading_id.replace('_', ' ')).strip()

def toyline_from_heading(section_heading: str) -> tuple[str, str]:
    # Product names are not toyline evidence: "The Legacy of Bumblebee"
    # can occur under a Transformers (2007) heading.
    key = normalize_heading(section_heading)
    if key in {'masterpiece movie', 'masterpiece movie series'}:
        return 'Masterpiece', 'Masterpiece Movie'
    if key in GEN_SUBLINES:
        return 'Generations', section_heading.strip()
    return (section_heading.strip() if key not in ('toys', 'contents') else ''), ''

def toyline_from_series(series: str) -> tuple[str, str]:
    """Interpret an explicit TFWiki Series field as high-confidence metadata."""
    label = re.sub(r'\s+', ' ', series).strip(' :')
    key = normalize_heading(label)
    if key in GEN_SUBLINES:
        return 'Generations', label
    if key in {'g1', 'gen 1', 'generation 1', 'generation-1'}:
        return 'G1', ''
    if key.startswith('generations') or key.startswith('legacy'):
        return 'Generations', label
    return label, ''

def fetch(url: str) -> str:
    with urlopen(Request(url, headers={'User-Agent': UA}), timeout=12) as response:
        return response.read().decode('utf-8', errors='replace')

def clean(value: str) -> str:
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', value))).strip()

def size_from_heading(value: str) -> str:
    """Return a size class only when a nested toys heading names one."""
    text = clean(value).lower()
    match = re.search(r'\b(commander|deluxe|leader|voyager|titan|legends?|scout|basic|core|micro|supreme|ultimate|masterpiece)\b', text)
    if not match:
        return ''
    label = match.group(1)
    return 'Legends' if label.startswith('legend') else label.title()

def canonical_size(value: str) -> str:
    normalized = re.sub(r'\s+class(?:\s+toys?)?\b', '', value.lower()).strip()
    return re.sub(r'\s+', ' ', normalized)

def nested_size_heading(section_html: str, offset: int) -> str:
    headings = list(re.finditer(r'(?is)<h[4-6][^>]*>.*?</h[4-6]>', section_html[:offset]))
    return size_from_heading(headings[-1].group(0)) if headings else ''

def article_candidates(character: str, prop: str) -> list[str]:
    continuity = re.sub(r'\s*\([^)]*\)', '', prop).strip()
    aliases = {'bumblebee movie':'Movie','movie (2007)':'Movie','dark of the moon':'Movie','dotm':'Movie','age of extinction':'Movie','aoe':'Movie','the last knight':'Movie','tlk':'Movie','animated':'Animated','armada':'Armada','g1':'G1','gen 1':'G1','generation 1':'G1','generation-1':'G1','generation1':'G1','beast wars':'Beast Wars','beast machines':'Beast Machines','prime':'Prime','transformers: one (2024)':'One','transformers one (2024)':'One','revenge of the fallen':'ROTF','revenge of fallen':'ROTF','movie revenge of the fallen':'ROTF','rotf':'ROTF'}
    prop_key = prop.strip().lower()
    label = aliases.get(prop_key, continuity)
    labels = ['ROTF', 'Movie'] if label == 'ROTF' else [label]
    candidates = [f'{character} ({variant})' for variant in labels]
    # TFWiki sometimes uses the character's formal name while users use the
    # shorter conversational name, e.g. Rodimus -> Rodimus Prime.
    if not re.search(r'\bprime\b', character, re.I):
        candidates.append(f'{character} Prime ({label})')
    candidates.append(character)
    if not re.search(r'\bprime\b', character, re.I):
        candidates.append(f'{character} Prime')
    return list(dict.fromkeys(candidates))

def get_entries(page: str, section_title: str, section_html: str, source_url: str, character: str, prop: str) -> list[dict]:
    blocks = list(re.finditer(r'(?is)<ul[^>]*class="[^"]*iconlist[^"]*"[^>]*>(.*?)</ul>', section_html))
    entries = []
    for index, block in enumerate(blocks):
        line = clean(block.group(1))
        # The list item is the boundary of one toy record; tolerate linked
        # years and small punctuation differences in TFWiki markup.
        meta = re.search(r'(.+?)\s*\(([^,()]+),\s*(\d{4}(?:\s*[/–-]\s*\d{4})?)\s*\)\s*$', line)
        if not meta:
            # Some pages include non-breaking spaces or linked release-date
            # markup that survives differently after HTML cleaning.
            fallback = re.search(r'(.+?)\s*\(([^,()]+),.*?(\d{4})\s*\)\s*$', line)
            if fallback:
                meta = fallback
        if not meta:
            continue
        name, size, year = (part.strip() for part in meta.groups())
        end = blocks[index + 1].start() if index + 1 < len(blocks) else len(section_html)
        body = section_html[block.end():end]
        description = clean(body)
        # Some legitimate entries use a set or multipack name rather than the
        # character name (for example, "Troop Builder Multipack"). Keep them
        # when the searched character is identified in the entry description.
        if not character_matches(character, name, description):
            continue
        sentence = re.split(r'(?<=[.!?])\s+', description, maxsplit=1)[0][:500]
        metadata = clean(body.split('</ul>', 1)[0])
        series_match = re.search(r'\bSeries\s*:\s*(.*?)(?=\s+(?:Accessories|Known designers|Release date|Takara|ID number)\b|$)', metadata, re.I)
        series = series_match.group(1).strip(' :') if series_match else ''
        before = section_html[:block.start()]
        images = [src for src in re.findall(r'(?is)<img[^>]+src="([^"]+)"', before)
                  if 'magnify-clip' not in src.lower()]
        image = images[-1] if images else ''
        if image.startswith('//'): image = 'https:' + image
        elif image.startswith('/'): image = 'https://tfwiki.net' + image
        # Evidence priority: explicit Series metadata, then the section
        # heading, then an explicit description phrase.  A stray Generation 1
        # reference in prose must never turn an entry into Generations.
        evidence = 'series metadata' if series else 'section heading'
        toyline, subline = toyline_from_series(series) if series else toyline_from_heading(section_title)
        if not series and re.search(r'\bgenerations[- ]styled\b', description, re.I):
            toyline = 'Generations'
        contextual_line = None if series else GENERATION_CONTEXT.search(description)
        if contextual_line:
            evidence = 'explicit release context'
            label = contextual_line.group(1).strip()
            toyline = 'Generations'
            label_key = re.sub(r'\s+', ' ', label.lower()).replace('-', ':')
            subline = 'Legacy: Evolution' if 'evolution' in label_key else 'Legacy United' if 'united' in label_key else 'Legacy' if 'legacy' in label_key else label.title()
        heading_size = nested_size_heading(section_html, block.start())
        resolved_size = size or heading_size
        size_evidence = 'product metadata' if size else 'size-class heading' if heading_size else ''
        entries.append({'candidate_id':f'{source_url}::{section_title}::{index}::{name}', 'product_name':name,'image_url':image,'product_url':source_url+'#'+section_title,'criteria':{'character':character,'property':prop,'toyline':toyline,'subline':subline,'size_class':resolved_size,'year':year},'summary':sentence,'series':series,'toyline_evidence':evidence,'subline_evidence':evidence,'size_evidence':size_evidence,'source_url':source_url+'#'+section_title,'section_heading':section_title,'entry_html':body[:5000]})
    # Some TFWiki sections use a plain nested list instead of iconlist. The
    # first bold product name still marks the entry boundary, so preserve it
    # rather than dropping the entire section.
    plain = list(re.finditer(r'(?is)<ul(?:\s[^>]*)?>\s*<li[^>]*>\s*<b>(.*?)</b>\s*\((.*?)\)\s*', section_html))
    for index, match in enumerate(plain):
        name = clean(match.group(1))
        candidate_size = size_from_heading(match.group(2)) or nested_size_heading(section_html, match.start())
        if any(item['product_name'] == name and canonical_size(item['criteria'].get('size_class', '')) == canonical_size(candidate_size) for item in entries):
            continue
        end = plain[index + 1].start() if index + 1 < len(plain) else len(section_html)
        body = section_html[match.end():end]
        description_body = re.split(r'(?is)</ul>\s*</li>\s*</ul>', body, maxsplit=1)[-1]
        description = clean(description_body)
        if not character_matches(character, name, description):
            continue
        year_match = re.search(r'\b(\d{4})\b', clean(match.group(2)))
        year = year_match.group(1) if year_match else ''
        before = section_html[:match.start()]
        images = [src for src in re.findall(r'(?is)<img[^>]+src="([^"]+)"', before) if 'magnify-clip' not in src.lower()]
        image = images[-1] if images else ''
        if image.startswith('//'): image = 'https:' + image
        elif image.startswith('/'): image = 'https://tfwiki.net' + image
        sentence = re.split(r'(?<=[.!?])\s+', description, maxsplit=1)[0][:500]
        toyline, subline = toyline_from_heading(section_title)
        metadata_size = size_from_heading(match.group(2))
        heading_size = nested_size_heading(section_html, match.start())
        resolved_size = metadata_size or heading_size
        size_evidence = 'product metadata' if metadata_size else 'size-class heading' if heading_size else ''
        entries.append({'candidate_id':f'{source_url}::{section_title}::plain::{index}::{name}', 'product_name':name,'image_url':image,'product_url':source_url+'#'+section_title,'criteria':{'character':character,'property':prop,'toyline':toyline,'subline':subline,'size_class':resolved_size,'year':year},'summary':sentence,'series':'','toyline_evidence':'section heading','subline_evidence':'section heading','size_evidence':size_evidence,'source_url':source_url+'#'+section_title,'section_heading':section_title,'entry_html':body[:5000]})
    return entries

def search(character: str, prop: str, toyline: str, subline: str, size: str) -> dict:
    intent = normalize_search_fields({'toyline': toyline, 'subline': subline})
    toyline = intent['toyline']
    subline = intent['subline']
    pages = []
    suffixes = ['/toys', '']
    for candidate in article_candidates(character, prop):
        for suffix in suffixes:
            url = 'https://tfwiki.net/wiki/' + quote((candidate + suffix).replace(' ', '_'))
            try:
                content = fetch(url)
                if 'There is currently no text in this page.' not in content and '"wgIsArticle":false' not in content:
                    pages.append((content, url, candidate))
                    break
            except Exception:
                continue
        if pages:
            break
    if not pages:
        return {'status': 'no_match', 'matches': [], 'message': 'No TFWiki character page was found.'}
    # Third pass: discover same-character affiliated toy branches from the
    # resolved page itself. This is intentionally not a fixed list: TFWiki
    # may use Generations_toys, Masterpiece_toys, or another future branch.
    resolved_page, resolved_url, resolved_candidate = pages[0]
    expected_prefix = resolved_candidate.replace(' ', '_').lower() + '/'
    checked_urls = {unquote(url).rstrip('/').lower() for _, url, _ in pages}
    linked_toy_urls = []
    for href in re.findall(r'(?is)<a\b[^>]*href=["\']([^"\']+)["\']', resolved_page):
        href = html.unescape(href).split('#', 1)[0]
        if not href.startswith('/wiki/'):
            continue
        decoded_path = unquote(href).lower()
        branch = decoded_path[len('/wiki/'):]
        if not branch.startswith(expected_prefix) or 'toys' not in branch:
            continue
        absolute = 'https://tfwiki.net' + href
        normalized_absolute = unquote(absolute).rstrip('/').lower()
        if normalized_absolute in checked_urls or absolute in linked_toy_urls:
            continue
        linked_toy_urls.append(absolute)
    for linked_url in linked_toy_urls:
        try:
            content = fetch(linked_url)
            if 'There is currently no text in this page.' not in content and '"wgIsArticle":false' not in content:
                pages.append((content, linked_url, resolved_candidate))
        except Exception:
            continue
    entries = []
    for page_html, page_url, title in pages:
        heading_matches = list(re.finditer(r'(?is)<h[23][^>]*>.*?</h[23]', page_html))
        headings = []
        for index, match in enumerate(heading_matches):
            heading_html = match.group(0)
            id_match = re.search(r'\bid="([^"]+)"', heading_html)
            if not id_match:
                continue
            end = heading_matches[index + 1].start() if index + 1 < len(heading_matches) else len(page_html)
            headings.append((id_match.group(1), heading_text(heading_html, id_match.group(1)), page_html[match.end():end]))
        for _, heading_label, section in headings:
            entries.extend(get_entries(page_html, heading_label, section, page_url, character, prop))
    def score(item):
        c = item['criteria']
        text = (item['product_name'] + ' ' + item['summary'] + ' ' + item.get('section_heading', '')).lower()
        value = 0
        if character.lower() in item['product_name'].lower():
            value += 4
        # Once the continuity-specific host page is resolved, property text
        # is context rather than release evidence. The toyline and subline
        # identify which product on that page the user wants.
        if c['property'].lower() == prop.lower():
            value += 1
        if toyline:
            requested_toyline = canonical_toyline(toyline)
            actual_toyline = canonical_toyline(c['toyline'])
            if actual_toyline == requested_toyline:
                value += 12
            elif requested_toyline == 'generations' and actual_toyline == 'generations' and canonical_subline(c['subline']) in GEN_SUBLINES:
                value += 12
            elif actual_toyline and actual_toyline != requested_toyline:
                value -= 12
        if subline:
            requested_subline = canonical_subline(subline)
            actual_subline = canonical_subline(c['subline'])
            if actual_subline == requested_subline:
                value += 8
            elif requested_subline in text:
                value += 2
            elif actual_subline:
                value -= 2
        if size:
            requested_size = canonical_size(size)
            actual_size = canonical_size(c.get('size_class', ''))
            evidence = item.get('size_evidence', '')
            if actual_size == requested_size:
                # Product metadata and a dedicated size-class heading are
                # strong evidence. A descriptive comparison is deliberately
                # not treated as equivalent evidence.
                value += 9 if evidence in {'product metadata', 'size-class heading'} else 4
            elif actual_size and evidence in {'product metadata', 'size-class heading'}:
                # Size is a ranking signal, not a hard exclusion.
                value -= 2
            elif re.search(rf'\b{re.escape(requested_size)}(?:\s+class)?\b', text, re.I):
                value += 1
        return value
    entries.sort(key=score, reverse=True)
    primary = pages[0]
    return {
        'status': 'match' if entries else 'no_match',
        'matches': entries[:10],
        'title': primary[2],
        'url': primary[1],
        'pages_checked': [page[1] for page in pages],
        'message': 'TFWiki candidates retrieved. Review the best-supported candidate.' if entries else 'The character page was found, but no readable toy entries were parsed.'
    }

def related_toy_from_entry(entry: dict) -> dict | None:
    """Find an explicitly linked base toy for a redeco/remold-style entry.

    This deliberately requires both transformation language and a nearby wiki
    link. A distant character mention is not enough to trigger the fallback.
    """
    markup = entry.get('entry_html', '') or ''
    relation = re.compile(r'(?i)\b(redeco(?:lor)?|recolou?r|repaint|retool(?:ed)?|remold(?:ed)?|uses the mold of|based on|reuses the mold of)\b')
    for anchor in re.finditer(r'(?is)<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', markup):
        href, label = anchor.group(1), clean(anchor.group(2))
        if not label or href.startswith('#') or re.search(r'(?i)(?:File:|Category:|Template:|Special:)', href):
            continue
        context = clean(markup[max(0, anchor.start() - 500):min(len(markup), anchor.end() + 500)])
        relation_match = relation.search(context)
        if not relation_match:
            continue
        if href.startswith('/'):
            url = 'https://tfwiki.net' + href
        elif href.startswith('http'):
            url = href
        else:
            continue
        return {'name': label, 'url': url, 'relationship': relation_match.group(1).lower()}
    return None
