import json
import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def _parse_portkey_json(raw: str):
    cleaned = raw.replace('```json', '').replace('```', '').strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find('{'), cleaned.rfind('}')
        if start >= 0 and end > start:
            return json.loads(cleaned[start:end + 1])
        raise ValueError('Portkey returned non-JSON content: ' + cleaned[:500])


def _portkey_request(prompt: dict, max_tokens: int = 700):
    key = os.getenv('PORTKEY_API_KEY', '').strip()
    if not key or os.getenv('MORETHANMEETSAI_INTERPRETATION_ENABLED', 'true').lower() != 'true':
        return None
    body = json.dumps({
        'model': os.getenv('MORETHANMEETSAI_INTERPRETATION_MODEL', 'gpt-4o-mini'),
        'messages': [{'role': 'user', 'content': json.dumps(prompt)}],
        'max_completion_tokens': max_tokens,
    }).encode()
    request = Request(
        os.getenv('PORTKEY_API_ENDPOINT', 'https://api.portkey.ai/v1/chat/completions'),
        data=body,
        headers={'x-portkey-api-key': key, 'x-portkey-provider': 'openai', 'Content-Type': 'application/json', 'Accept': 'application/json', 'User-Agent': 'Mozilla/5.0 (MoreThanMeetsAI V2)'},
        method='POST',
    )
    with urlopen(request, timeout=12) as response:
        content = json.loads(response.read().decode())['choices'][0]['message']['content']
    return _parse_portkey_json(content)


def rank(fields, candidates, tfwiki_entry=None, source_page=None):
    key = os.getenv('PORTKEY_API_KEY', '').strip()
    if not key or not candidates or os.getenv('MORETHANMEETSAI_INTERPRETATION_ENABLED', 'true').lower() != 'true':
        return list(range(len(candidates)))
    prompt = {
        'fields': fields,
        'tfwiki_entry': tfwiki_entry or {},
        'candidates': [{'index': i, **{k: item.get(k) for k in ('product_name', 'criteria', 'series', 'toyline_evidence', 'subline_evidence', 'summary', 'source_url', 'section_heading', 'entry_html')}} for i, item in enumerate(candidates)],
        'instruction': 'Return JSON only: {"order":[candidate indexes]}. Rank candidates against every user field and the confirmed TFWiki identity. Treat subline or edition as structured evidence just like toyline: an exact section heading or explicit Series metadata is strong evidence, explicit release language is next, and an incidental word in a description is weak evidence. Prefer an exact subline match over a generic parent-toyline match. Do not let a generic word such as prime or an incidental Generation 1 reference override explicit toyline or subline metadata.',
    }
    try:
        data = _portkey_request(prompt, 160)
        order = data.get('order', []) if data else []
        return [i for i in order if isinstance(i, int) and 0 <= i < len(candidates)] + [i for i in range(len(candidates)) if i not in order]
    except Exception:
        return list(range(len(candidates)))


def interpret_related_toy(fields, tfwiki_entry):
    """Use one bounded Portkey call to identify an explicit related toy."""
    if not tfwiki_entry or not tfwiki_entry.get('entry_html'):
        return None
    prompt = {
        'fields': fields,
        'tfwiki_entry': tfwiki_entry,
        'instruction': 'Return JSON only as {"related_toy":{"name":"","url":"","relationship":""}} or {"related_toy":null}. Inspect the complete supplied TFWiki toy entry. Only return a related toy when the entry explicitly says the requested toy is a redeco, recolor, repaint, retool, or remold of that toy, or uses equivalent direct mold-reuse language, and a nearby hyperlink identifies the comparison toy. Preserve the linked toy name and URL. Do not infer from a generic character mention or from an unrelated description. The relationship must be one of: redeco, recolor, repaint, retool, remold.',
    }
    try:
        result = _portkey_request(prompt, 240)
        related = result.get('related_toy') if isinstance(result, dict) else None
        if not isinstance(related, dict):
            return None
        name, url, relationship = (str(related.get(key, '')).strip() for key in ('name', 'url', 'relationship'))
        if not name or not url.startswith('https://tfwiki.net/wiki/') or relationship.lower() not in {'redeco', 'recolor', 'repaint', 'retool', 'remold'}:
            return None
        return {'name': name, 'url': url, 'relationship': relationship.lower(), 'interpreted_by': 'Portkey'}
    except Exception:
        return None


def _portkey_vision_request(prompt: dict, image_urls: list[str], max_tokens: int = 1800):
    key = os.getenv('PORTKEY_API_KEY', '').strip()
    if not key or os.getenv('MORETHANMEETSAI_INTERPRETATION_ENABLED', 'true').lower() != 'true':
        return None
    content = [{'type': 'text', 'text': json.dumps(prompt)}]
    content.extend({'type': 'image_url', 'image_url': {'url': url, 'detail': 'high'}} for url in image_urls[:24])
    body = json.dumps({
        'model': os.getenv('MORETHANMEETSAI_INTERPRETATION_MODEL', 'gpt-4o-mini'),
        'messages': [{'role': 'user', 'content': content}],
        'max_completion_tokens': max_tokens,
    }).encode()
    request = Request(
        os.getenv('PORTKEY_API_ENDPOINT', 'https://api.portkey.ai/v1/chat/completions'),
        data=body,
        headers={'x-portkey-api-key': key, 'x-portkey-provider': 'openai', 'Content-Type': 'application/json', 'Accept': 'application/json', 'User-Agent': 'Mozilla/5.0 (MoreThanMeetsAI V2)'},
        method='POST',
    )
    with urlopen(request, timeout=45) as response:
        content = json.loads(response.read().decode())['choices'][0]['message']['content']
    return json.loads(content.replace('```json', '').replace('```', '').strip())


def interpret_instruction_steps(fields, tfwiki_entry, unicron_context):
    """Interpret numbered instruction-box images into confirmable steps."""
    images = unicron_context.get('image_urls', [])
    if not images:
        return {'status': 'interpretation_unavailable', 'message': 'No instruction images were available to interpret.', 'steps': []}
    prompt = {
        'fields': fields,
        'tfwiki_entry': tfwiki_entry,
        'matched_unicron_entry': unicron_context.get('matched_entry', {}),
        'instruction_page_html': unicron_context.get('instruction_page_html', ''),
        'toy_page_html': unicron_context.get('toy_page_html', ''),
        'instruction': 'Return JSON only as {"alt_mode":"","starting_mode":"robot or alternate","accessories":[""],"safety_notes":[""],"steps":[{"number":1,"orientation":"","instruction":""}]}. Treat every numbered box as a separate physical state. For every step, identify the current viewpoint as front, rear, left, right, top-down, underside, or uncertain; state which way the toy faces relative to the user; and explicitly compare that viewpoint with the immediately preceding box. Re-evaluate the main figure and every inset independently: do not claim that one is front-facing merely because another is top-down, and do not assume different panels have different perspectives. If both views are top-down, say both are top-down. Never inherit orientation without visual evidence. The user may not have the Unicron instructions or be able to see them. The user-facing text must never mention an image, panel, box, inset, depiction, drawing, arrow, marking, illustration, source instruction, or phrase such as as shown, as illustrated, as indicated, follow the arrows, or move this part. Translate all visual evidence into physical toy language. Name the moving part, its connection point, fixed pivot, axis, start position, end position, and toward or away direction. Track accessories and connections. Include safety notes and accessories from the TFWiki and Unicron context. Determine alt_mode and starting_mode. If viewpoint evidence is insufficient, say the the toy viewpoint is uncertain and give the safest supported physical action. Preserve the requested character in a multipack.'
    }
    try:
        result = _portkey_vision_request(prompt, images, max_tokens=3200)
        if not isinstance(result, dict) or not isinstance(result.get('steps'), list) or not result.get('steps'):
            return {'status': 'interpretation_unavailable', 'message': 'Portkey did not return usable numbered transformation steps.', 'steps': []}
        steps = [step for step in result['steps'] if isinstance(step, dict) and step.get('instruction')]
        accessories = [str(accessory).strip() for accessory in result.get('accessories', []) if str(accessory).strip()][:12]
        safety_notes = [str(note).strip() for note in result.get('safety_notes', []) if str(note).strip()][:8]
        return {'status': 'steps_ready', 'alt_mode': str(result.get('alt_mode', '')).strip(), 'starting_mode': str(result.get('starting_mode', '')).strip(), 'accessories': accessories, 'safety_notes': safety_notes, 'steps': steps, 'message': 'Portkey interpreted the safety notes and numbered instruction boxes.'}
    except Exception as error:
        result = {'status': 'interpretation_unavailable', 'message': 'The instruction images were retrieved, but Portkey could not interpret them.', 'steps': [], 'error_type': type(error).__name__}
        result['error_detail'] = str(error)[:1000]
        if isinstance(error, HTTPError):
            result['portkey_status'] = error.code
            result['message'] = f'Portkey could not interpret the retrieved instruction images (HTTP {error.code}).'
            try:
                provider_body = error.read().decode('utf-8', errors='replace')
                if provider_body:
                    result['portkey_error'] = provider_body[:1000]
            except Exception:
                pass
        return result
























