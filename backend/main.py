from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / '.env', override=False)
load_dotenv(PROJECT_ROOT.parent / '.env', override=False)

from backend.tfwiki import normalize_search_fields, search, related_toy_from_entry
from backend.interpreter import rank, interpret_related_toy, interpret_instruction_steps
from backend.unicron import search as search_unicron, search_related, instruction_context, has_direct_match, source_alignment_count
app=FastAPI(title='MoreThanMeetsAI V2')
app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_methods=['*'],allow_headers=['*'])
class SearchInput(BaseModel):
    character:str=''; property:str=''; toyline:str=''; subline:str=''; size_class:str=''
class InstructionInput(SearchInput):
    tfwiki_entry:dict={}
class InstructionStepsInput(InstructionInput):
    unicron_entry:dict={}
@app.get('/api/health')
def health(): return {'status':'ok','service':'MoreThanMeetsAI V2 backend'}
@app.post('/api/products/search')
def products(payload:SearchInput):
    if not payload.character.strip() or not payload.property.strip() or not payload.toyline.strip(): raise HTTPException(400,'Character, property or universe, and toyline are required.')
    result=search(payload.character.strip(),payload.property.strip(),payload.toyline.strip(),payload.subline.strip(),payload.size_class.strip())
    rank_fields=normalize_search_fields(payload.model_dump())
    order=rank(rank_fields,result.get('matches',[])); result['matches']=[result['matches'][i] for i in order if i<len(result.get('matches',[]))][:3]; result['suggestions']=result['matches'][1:3]; result['matches']=result['matches'][:1]; return result
@app.post('/api/first-card/validate')
def first_card(payload:SearchInput): return {'status':'accepted','message':'Identification details received.','fields':payload.model_dump()}
@app.post('/api/instructions/search')
def instructions(payload:InstructionInput):
    fields=payload.model_dump(exclude={'tfwiki_entry'})
    result=search_unicron(fields,payload.tfwiki_entry)
    first = (result.get('matches') or [None])[0]
    direct = has_direct_match(result, payload.tfwiki_entry)
    first_alignment = source_alignment_count(payload.tfwiki_entry, first)[0] if first else 0
    # A direct result that satisfies character and toyline but misses size is
    # eligible for a related-toy check. A two-of-three fallback does not
    # displace it; only a source-supported three-of-three fallback wins.
    should_check_related = result.get('status') == 'no_match' or not direct or first_alignment < 3
    if should_check_related:
        related=interpret_related_toy(fields,payload.tfwiki_entry)
        if not related:
            related=related_toy_from_entry(payload.tfwiki_entry)
        if related:
            related_result=search(related.get('name',''), fields.get('property',''), fields.get('toyline',''), fields.get('subline',''), fields.get('size_class',''))
            related_entry=(related_result.get('matches') or [None])[0]
            alternate=search_related(fields,related_entry or payload.tfwiki_entry,related)
            alternate_first=(alternate.get('matches') or [None])[0]
            alternate_alignment=source_alignment_count(related_entry or {}, alternate_first)[0] if alternate_first and related_entry else 0
            if alternate.get('matches') and alternate_alignment == 3:
                return alternate
            if direct and result.get('status') == 'match' and first_alignment >= 2:
                return result
        if result.get('status') == 'match' and not direct:
            result['status'] = 'no_match'
            result['matches'] = []
            result['message'] = 'The exact toy was not found in Unicron, and no verified related-toy instruction match was found.'
    return result
@app.post('/api/instructions/steps')
def instruction_steps(payload:InstructionStepsInput):
    fields=payload.model_dump(exclude={'tfwiki_entry','unicron_entry'})
    context=instruction_context(payload.unicron_entry)
    return interpret_instruction_steps(fields,payload.tfwiki_entry,context)
