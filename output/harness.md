# V2 verification harness

This project currently uses manual verification alongside the compiler checks.
The harness scope covers the complete local flow:

- Card 1 validates character, property or universe, toyline, subline, and size class inputs.
- Search sends the entered fields to the FastAPI backend and displays the best TFWiki candidate.
- TFWiki resolution checks the general toys section, the character page fallback, and dynamically discovered same-character branches whose URLs contain `toys`.
- Toyline and subline fields are interpreted contextually. Recognized sublines are normalized to their parent toyline, including `Titans Return` to `Generations`.
- After a continuity-specific page is found, verify that an explicit toyline match outranks the page's broad property context; for example, `ROTF` must select the `Revenge of the Fallen` section on a Movie Starscream page.
- Verify size ranking across classes: explicit product metadata or headings such as Voyager, Deluxe, Leader, and Legends must outrank a description that only compares a toy to another size class, without excluding entries that lack size evidence.
- Verify that this size ordering remains in place after the Portkey ranking response; a known Legends entry must not displace a supported Voyager entry when Voyager is requested.
- Verify that explicit redeco, repaint, recolor, remold, and retool relationships inherit the source size only when the entry lacks stronger contradictory metadata.
- For Card 4, verify that the confirmed TFWiki size is carried into Unicron ranking; a `Voyager` title must outrank a conflicting `Legends` title for a Voyager redeco.
- Verify the initial Unicron priority order: confirmed character, toyline/subline, then size class. A character-level result without the confirmed toy identity must trigger the TFWiki related-toy fallback instead of being treated as a direct match.
- Card 2 always supports the three-position experience: best candidate, second candidate, and third candidate before search refinement.
- Card 3 supports Toybox save, duplicate prevention, and local recall.
- Card 4 displays the matched Unicron source and blocks interpretation without a source match.
- Unicron matching checks parent-series aliases, all finite year pages, and the bounded legacy catalog fallback; Card 4 preserves the exact matched toy-page link.
- Card 5 displays safety and accessory context, the starting and destination modes, and one step at a time.
- Card 5 supports the Go back button, left/right arrow navigation, and spacebar speech controls.

Run the static checks from the project folder:

```powershell
python -c "import ast,pathlib; [ast.parse(path.read_text(encoding='utf-8')) for path in pathlib.Path('backend').glob('*.py')]; print('PYTHON_OK')"
frontend\node_modules\.bin\tsc.cmd --noEmit --project frontend\tsconfig.json
```

Manual source verification should confirm that the selected TFWiki product,
its image, heading, metadata, and description remain attached to one another;
that Unicron source links point to the matched toy page; and that generated
steps do not use visual-only phrases such as “as shown.”
