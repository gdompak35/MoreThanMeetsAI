# V2 data

The app currently retrieves and interprets live TFWiki toy-page data. A local
toy catalog is not required; the rules below document how additional source
data and retrieved evidence must be handled.

## Planned additional data

Future catalog records should keep these concepts separate:

- Characters, including continuity-specific identity and aliases.
- Properties or universes, such as Animated, G1, or Bumblebee Movie.
- Parent toylines and sublines, such as Generations and Legacy: Evolution.
- Size classes and product sizes.
- Source records with publisher, URL, retrieval date, and evidence status.

Do not treat user input as verified catalog data. New records should preserve the original source wording and identify which fields are directly supported, inferred, or unknown. Never place API keys, private user information, or medical information in data files.

## Core Transformers interpretation logic

Transformers fictional identities and toyline identities are distinct concepts.

A character may belong to a particular fictional continuity—such as the 2018 *Bumblebee* film, *Animated*, G1, or an IDW comic continuity—while toys representing that character may be released in several different toylines. A toyline may accompany a cartoon or film, but it does not automatically define the fictional identity of every toy released under it.

For example, “Bumblebee Movie Optimus Prime” identifies a continuity-specific version of Optimus Prime with its own appearance, personality, and fictional experiences. “Animated Optimus Prime” identifies a different fictional version. A user may then ask for a toy of Animated Prowl from the Generations Legacy toyline rather than from the Animated toyline.

This distinction drives the first three fields:

1. **Character** identifies who the user is discussing.
2. **Property or universe** identifies which fictional version of that character the user means.
3. **Toyline** identifies which product line the desired physical toy belongs to.

The search system must resolve fields 1 and 2 together before using field 3 to distinguish releases. It must not merge same-name characters across fictional continuities, and it must not infer a toyline solely from a fictional property. A toy may visually represent a fictional character while being released in a different toyline.

## Distinct search logic: TFWiki toy-entry interpretation

TFWiki toy pages are parsed as structured records rather than flat text. Each
record keeps its product name, adjacent image, metadata, description, and
section heading together. A toyline heading is stronger evidence than a word
appearing in a product name: `The Legacy of Bumblebee` under `Transformers
(2007)` is not a Generations toy, while an entry under `Legacy` or a description
that says it was released in `Legacy: United` is Generations-family evidence.

Generations is treated as the parent for its sublines, including Legacy,
Legacy: Evolution, Legacy United, Titans Return, Age of the Primes, and
Buzzworthy Bumblebee.
Buzzworthy Bumblebee is also recognized as a Studio Series subline; the
requested parent toyline determines which interpretation is intended. This
applies to every
character page, whether the toys are in a local `#Toys` section or a dedicated
`/toys` page.

Character-page resolution also tests formal-name variants when a user supplies
a shorter name. For example, `Rodimus` may resolve to `Rodimus Prime
(Animated)`. A generic page is not accepted as the final identity merely
because it exists; the resolver continues testing the continuity-specific
variant when the generic page has no usable toy entries.

### G1 versus Generations disambiguation

`G1`, `Gen 1`, `Generation 1`, and `Generation-1` refer to the original
Transformers era, generally the launch-era toyline, cartoon, and comic of
approximately 1984–1987. “Generation 1” is a later, retroactive label; it was
not the name used at the original launch. These terms must normalize to `G1`
and must never be treated as the modern `Generations` toyline. Conversely,
`Generations` means the later umbrella toyline that includes sublines such as
Legacy and Legacy United. The search keeps these two concepts separate whether
they appear in a user field, a TFWiki heading, a product description, or an
interpretive Portkey prompt.

The search applies this logic in order:

1. Resolve the character and fictional property together, allowing aliases,
   alternate naming, and minor input errors.
2. Check the character page's local Toys section and main character page.
   Then inspect the resolved page for same-character branch URLs containing
   `toys` and check each additional affiliated toys page that was not already
   searched. This is discovered from the page structure rather than limited
   to a fixed list of toyline names.
3. Split the toys material into individual entries at each product-list item,
   retaining the entry's own heading context, image, metadata, and description.
   TFWiki may use an `iconlist`, a named list such as `bp`, or a plain nested
   list for these entries; all product-list classes must be treated
   equivalently.
4. Use the section heading as primary toyline evidence. Do not classify an
   entry as Generations merely because its product name contains “Legacy.”
5. If an entry provides explicit metadata such as `Series: Legacy: Evolution`,
   treat that as higher-confidence toyline evidence than the description or
   the heading. Not every entry has a Series field.
6. Use explicit description context as supporting evidence, such as “released
   in Legacy: United” or “Generations-styled.” Incidental references such as
   “Generation 1-style” do not identify the modern Generations toyline.
7. After the continuity-specific host page is resolved, treat that page as the
   evidence for the fictional property. Do not let the property label outrank
   the requested product line when selecting among entries on that page.
   Normalize release aliases such as `ROTF` and `Revenge of the Fallen` to the
   same toyline label.
8. Rank the entries primarily against the user's toyline, then subline or
   edition, then size class and character evidence. For size class, an
   explicit product metadata value or a dedicated heading such as `Voyager
   Class toys`, `Deluxe Class toys`, `Leader Class toys`, or `Legends Class
   toys` is strong evidence. A description that says a toy is similar to,
   comparable to, or related to another size class is weak evidence and must
   not classify the toy as that size. An explicit statement that a toy is a
   redeco, repaint, recolor, remold, or retool of another toy normally carries
   over the source toy's size class when no conflicting size metadata exists;
   rare exceptions require evidence. Size evidence raises or lowers ranking
   confidence but does not hard-exclude an entry when the field is missing.
   After Portkey ranks the candidates, a deterministic size-evidence guard
   preserves this rule: supported exact matches remain ahead of known
   conflicting size classes while records with missing size data remain
   eligible.
   An explicit toyline match must beat a same-character entry from a different
   toyline; return the selected entry with its own image and first complete
   descriptive sentence.

This is a general rule for every searched character. It is not a special case
for Bumblebee, Prowl, or any other individual character.

## Instruction-source handoff

After Card 2 confirmation, the selected TFWiki record remains in frontend
state while Card 3 is shown. `Find my instructions` sends the original search
fields and that confirmed TFWiki record to the backend. The backend retrieves
Unicron.com's series catalog, identifies the relevant instruction series, and
checks its finite year pages. It keeps each instruction name, image, and
detail link together before Card 4 displays the best source match. Years
support discovery but are not a hard requirement. The post-confirmation
instruction source is Unicron.com's Transformers
Instructions Database. The configured starting catalog is
`https://www.unicron.com/tfitem/itemimage_db.php?mode=instructions&seriesID=23`.
The backend uses that catalog's series links to select the requested toyline,
then checks its finite year pages and keeps each instruction name, image, and
instruction-detail link together. The confirmed TFWiki entry and the user's
fields guide character matching. Unicron is the active instruction source;
Transformersland and Hasbro are not used in this workflow.
When multiple Unicron records share a character name, Card 4 ranks them in
this order: character alignment with the confirmed TFWiki entry, toyline or
subline alignment, then size class. Size remains important but cannot
compensate for a weaker character or toyline match. Card 4 also ranks them
using the requested property plus the confirmed TFWiki product context.
The confirmed TFWiki size class is also carried into this handoff. An explicit
size in the Unicron instruction title, such as `Starscream (Voyager)`, outranks
a same-character title from another class, such as `Legends Starscream`, even
when the selected TFWiki toy is a redeco whose exact name is not present in
Unicron.
This prevents a G1 Studio Series record such as `Grimlock w/ Wheelie (1986
TFTM)` from being displaced by an unrelated movie-era Grimlock record.
For multipacks, names after `with`, `vs.`, or `&` are secondary characters;
the requested character must match the primary name. Thus a TFWiki record
named `Sunstorm VS Autobot Ratchet` selects the Sunstorm multipack instruction
record and its linked Sunstorm-vs-Ratchet toy page, not Ratchet's separate
instruction record.

If Unicron has no direct instruction match—or only returns character-level
records whose titles do not identify the confirmed toy—the backend makes one
bounded Portkey interpretation call over the confirmed TFWiki toy entry. Portkey must
identify explicit redeco, recolor, repaint, retool, or remold language and a
nearby linked comparison toy. The returned TFWiki URL is validated, then the
related character name is searched in Unicron. If that succeeds, Card 4 names
the confirmed toy and says, for example, `I couldn't find the instructions for
Nebular Starscream so I found the instructions for a redeco of it!` The
relationship word is taken from the TFWiki/Portkey evidence (`repaint`,
`retool`, `recolor`, `remold`, or `redeco`). If Portkey is unavailable, the local
parser may use the same strict nearby-link rule as a fallback; it never treats
a generic mention as a relationship.

### Step-by-step instruction interpretation

The implemented instruction flow sends the full Unicron instruction record and
its instruction images, the confirmed TFWiki entry, and the matched Unicron
toy entry to Portkey. Each numbered instruction box is one bounded step. Before
writing steps, interpretation must identify the toy's alternate mode from the
instruction imagery and the accompanying Unicron entry, determine whether the
first box starts in robot or alternate mode, and tell the user which mode is
the starting point. Each step must describe the physical orientation shown at
the bottom of the box, then explain the highlighted movement and arrows in
relation to the previous step when applicable. The target is no more than 70
words per step, with additional words allowed when needed for clear, safe,
accessible guidance. Each step must compare its perspective with the
immediately preceding panel rather than assuming the figure stayed oriented
the same way. It must identify front, rear, side, top-down, underside, or
other views and state where the head and feet, or nose and tail, point relative
to the user. Steps must be self-contained for blind or low-vision
users: they must name parts, locations, directions, surfaces, alignments, and
rotations rather than saying “as shown,” “as illustrated,” or “move this
part.” Before the first numbered step, Portkey also checks
the TFWiki entry and matched Unicron toy page for source-supported handling
notes, including fragile or commonly broken parts, degrading plastics, rubber,
paint, water or liquid features, and force warnings. Only supported notes are
shown; an empty note list is valid. Card 5 presents one interpreted step at a
time and does not fabricate steps when multimodal interpretation fails. Card 5
supports backward navigation with `Go back` and the left arrow key, and
forward navigation with the confirmation button or right arrow key.
Card 5's browser text-to-speech reads the voice controls once when the card
opens, then reads the current step as the user advances. The spacebar pauses
or resumes speech; a double-tap repeats the current instruction. Speech reads
the starting mode together with the correct destination mode: alternate mode
converts to robot mode, while robot mode converts to the identified alternate
mode, followed by the step
number and step content, not the safety briefing or interface labels.
The opening controls announcement is intended to be spoken once when Card 5
opens. Browsers may restrict speech started after an asynchronous request; the
user can use the spacebar to start or resume speech.

The safety output is a bounded `safety_notes` list returned with the
interpretation. Portkey must distinguish source-supported warnings from visual
observations, identify the basis when useful, and avoid claiming a material or
hazard that the supplied TFWiki entry, Unicron page, or images do not support.
Relevant notes appear before the transformation sequence and may include
fragility, breakage, degrading plastics, rubber or other texture/material
observations, paint or clear parts, water/liquid features, small-parts
hazards, and force warnings. A resistant joint must be treated as a reason to
stop rather than apply more force.

### Accessory-aware instruction interpretation

Transformers commonly include weapons, tools, armor, missiles, companions, or
other accessories. The instruction prompt asks Portkey to compare TFWiki and
Unicron accessory information, return an `accessories` list, and display that
list before Step 1. If a piece leaves a hand or the figure and is absent for
several panels, the interpreter treats it as a possible accessory and tracks
it across the sequence. It must not label the piece missing or instruct the
user to attach or remove it unless the images support that conclusion.

### Assistive scope and collaboration

The generated sequence is an aid, not a definitive transformation guide or a
guarantee of success. Text alone may not take a blind or low-vision user from
one mode to another. The output should instead explain critical movements and
provide useful starting language for a friend or family member—whether
sighted or non-sighted—to discuss and coach the transformation. Working with
another person is encouraged as part of play; users should stop when a move is
unclear, resisted, or unsafe.

### External-resource collaboration

The app cannot provide this experience independently of the people and
organizations that upload, preserve, and make instruction scans accessible.
TFWiki, Unicron, Hasbro, and other Transformers resources are collaborators in
the practical sense that their availability and source quality determine what
the app can identify and interpret. A full launch should seek formal or
explicit collaboration with Hasbro and/or established fan-resource maintainers
to address permissions, attribution, stable access, preservation, and
accessibility.

### Prime context disambiguation

`Prime` in the property/universe field means *Transformers: Prime*, the
television continuity. `Prime` in the toyline field means the separate Prime
toyline. Its recognized sublines are `Robots in Disguise`, `First Edition`, and
`Beast Hunters`. Because “prime” is common language throughout Transformers
descriptions, an isolated occurrence in a product name or description is not
enough to identify either the TV continuity or the toyline; the field and
surrounding TFWiki context must determine its meaning.

The property list also includes `Transformers: One (2024)`, which normalizes to
the relevant TFWiki identity label rather than being confused with Prime.
`Masterpiece Movie Series` is an alternate, more formal name for the
`Masterpiece Movie` subline. The search normalizes both names to the same
Masterpiece Movie subline.

`ROTF`, `Revenge of the Fallen`, and `Revenge of Fallen` are equivalent
property inputs for TFWiki page resolution. TFWiki commonly uses the compact
`(ROTF)` article suffix even when the toy section itself is headed `Revenge of
the Fallen`. The same page-variant rule applies to `DOTM`/`Dark of the Moon`,
`AOE`/`Age of Extinction`, and `TLK`/`The Last Knight`; these commonly resolve
through a character's `(Movie)` page, where the film-specific toy heading
disambiguates the entry. `Bumblebee Movie` also normalizes to the applicable
Movie page while retaining its distinct film context in the search fields.

### Unicron catalog normalization and fallback

Unicron's catalog does not always use the same labels as the user's toyline
field. When `Titans Return` is entered as the toyline, the search preserves it
as the requested subline and also searches its parent `Generations` catalog.
The same parent-series approach applies to the other recognized sublines and
aliases documented in the backend. `G1` remains distinct from modern
`Generations` throughout this handoff.

The instruction search checks all finite year pages exposed by the selected
Unicron series; years help discover records but are not a hard requirement for
a match. If the normal instruction listings do not expose a usable record, a
bounded legacy catalog fallback may inspect the relevant catalog page and its
toy-page links. For example, the Titans Return Optimus Prime record can resolve
to:

`https://www2.unicron.com/2017-transformers/581-2017-generations/4440-optimus-prime-titans-return-voyager.html`

The exact matched toy page, rather than only the general catalog or image
parent, is retained as the Card 4 source link. Character matching is also
preserved for multipacks: when a record names multiple figures, the user's
character selects the corresponding primary figure and instruction page.

## Local Toybox memory

When a user saves a Card 3 result, the frontend stores a JSON-serialized
Toybox record in browser `localStorage` on that device. It contains the toy
identity and confirmed search fields. The Card 1 Toybox picker can recall that
record, and Card 3 disables saving when the same source or product identity is
already present. This is device-local memory, not a shared training database,
and it is not uploaded to the backend.

Formal-name fallbacks are limited to toy-entry matching: the product name or
the opening identity context of its description may use the shorter character
name. A later, unrelated mention elsewhere in the description cannot qualify
the toy. The resolved host page retains its formal TFWiki identity.

### Current frontend implementation note

The current V2 frontend stores Toybox records locally in browser `localStorage`.
It does not currently cache Unicron matches or Portkey interpretations, and it
does not include a separate `Read aloud` button. The documented voice controls
are the left/right arrow keys and the spacebar behavior described above.

### Orientation continuity rule

Every numbered instruction panel must be compared with the panel immediately
before it. The interpretation must identify front, rear, side, top-down,
underside, or another perspective, and state where the head and feet or nose
and tail point relative to the user. It must describe perspective changes
instead of assuming the toy remains front-facing. If the perspective is
ambiguous, the result must say so rather than assert that the prior orientation
continued.

### Connection-aware movement interpretation

The interpreter tracks where parts connect, not only what each part is called.
For example, a wing connected to an arm must be described and moved through
that arm connection. Pin and ratchet joints are useful models for constrained
single-plane rotation around a fixed center; ball joints can permit movement
across multiple planes. These are interpretive constraints, not facts to guess:
the output should name a joint type only when the sources or images support it.

For rotations, the interpreter must identify the fixed pivot and axis before
choosing words such as outward, inward, up, or down. It must distinguish a
piece rotating around an existing shoulder-to-arm, hip, or panel-hinge axis
from a piece moving outward into a new plane, and identify which part stays
fixed while the other sweeps around it.

### User-facing visual references

Arrows, panel markings, and neighboring images are valid evidence for the
interpreter, but they must not appear as unexplained references in the output.
Generated steps must translate them into physical actions. The output must not
say “as indicated,” “as shown,” “follow the arrows,” “in the next box,” or
refer the user back to the instructions or image.
