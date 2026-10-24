# MoreThanMeetsAI V2

MoreThanMeetsAI is a Transformers toy-identification and accessible instruction-guidance prototype. It uses TFWiki for toy identity, Unicron.com for instruction sources, and Portkey for optional multimodal interpretation.

## Run locally

Requirements: Python, Node.js, and npm.

From the project folder, create a local environment file without committing it:

```powershell
Copy-Item .env.example .env
```

Add a valid Portkey key to `.env` if interpretation is enabled. Never commit `.env` or an API key.

When run as a class submission, the backend looks for environment variables in
this order: first `<repo>/.env`, then the parent folder's `.env`. This supports
the teaching layout where staff keys are stored in `submissions/.env` beside
the cloned repository. The app uses `PORTKEY_API_KEY`; it does not require
`OPENAI_API_KEY`. If a Portkey key is present, interpretation is enabled by
default; `MORETHANMEETSAI_INTERPRETATION_ENABLED=false` can disable it.

For a GitHub upload, include `.env.example` but leave `.env` out. The
repository does not need `frontend/node_modules`; GitHub users can recreate it
with `npm.cmd install`.

Start the backend in one PowerShell window:

```powershell
Set-Location "C:\Users\gavin\Downloads\MGT 409 AI for Managers\Final Project V2"
python -m pip install -r requirements.txt
python -m uvicorn backend.main:app --reload --port 8000
```

Start the frontend in a second window:

```powershell
Set-Location "C:\Users\gavin\Downloads\MGT 409 AI for Managers\Final Project V2\frontend"
npm.cmd install
npm.cmd run dev
```

Open the local URL printed by Vite, usually `http://localhost:5173`.

## Search behavior

Card 1 separates character, fictional property or universe, parent toyline, subline or edition, and size class. If a recognized subline is entered in the toyline field, the backend infers its parent—for example, `Titans Return` becomes `Generations` plus the `Titans Return` subline.

TFWiki searching keeps each product entry, heading, metadata, description, and adjacent image together. It checks the general `/toys` page, the main character page as fallback, and then discovers additional same-character page branches containing `toys`. This supports pages such as `Generations_toys` without relying on a fixed list of every possible affiliated page.

Once the continuity-specific character page is found, that page supplies the
fictional-property context. Candidate selection prioritizes the requested
toyline, then subline or edition and size class; it does not allow a broad
property label such as `Movie (2007)` to outrank an explicit release match such
as `ROTF` / `Revenge of the Fallen`.

Card 2 always preserves the three-position experience: the best result, a second candidate, and a third candidate before `Refine my search`. Card 3 confirms the selected toy and can save it to the device-local Toybox.

## Instruction behavior

After confirmation, Card 4 searches Unicron's instruction catalog and checks all available year pages. Parent-series aliases are supported when Unicron uses a parent catalog name—for example, `Titans Return` searches the `Generations` catalog while retaining the subline for matching.

If the instruction archive does not expose the exact toy record, a bounded Unicron legacy-catalog fallback can locate a matching toy page, such as the 2017 Titans Return Optimus Prime page. Card 4 preserves the matched toy-page source link and reports when a related repaint, remold, redeco, or retool was used instead of the original toy.

Card 5 sends the TFWiki entry, Unicron toy record, instruction page, and instruction images to Portkey. It presents supported safety and accessory notes, states the starting and destination modes, and provides one step at a time. Steps must independently describe perspective and changes in orientation for blind or low-vision users; they must not say “as shown,” refer to an unseen inset or arrow, or rely on the user having the source image open.

Card 5 supports `Go back`, left/right arrow navigation, and text-to-speech. The keyboard controls are announced once when Card 5 opens; space pauses or resumes speech, and a double-tap repeats the current instruction.

Generated instructions are assistive guidance, not a definitive guarantee. Users should stop if a movement is unclear or resisted, and working with another person is encouraged. A full launch should involve appropriate collaboration with Hasbro and established Transformers fan resources regarding permissions, attribution, source preservation, and accessibility.

## Verification

```powershell
python -c "import ast,pathlib; [ast.parse(path.read_text(encoding='utf-8')) for path in pathlib.Path('backend').glob('*.py')]; print('PYTHON_OK')"
frontend\node_modules\.bin\tsc.cmd --noEmit --project frontend\tsconfig.json
```

## GitHub checklist

Before publishing, confirm that `.env` is ignored and contains no committed
credentials. Commit the source files, `requirements.txt`,
`frontend/package.json`, `frontend/package-lock.json`, `.env.example`, and the
documentation. Do not commit `node_modules`, `frontend/dist`, Python cache
files, or local logs.
