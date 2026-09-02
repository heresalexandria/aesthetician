# Finding the right preset

The library is large, and a preset's name says what the artifact *is*
("Tokyo Spectacle Print") rather than what you are looking for ("a sixties
kaiju film"). Four things bridge that gap, in the app and on the command line.

## Search that understands what you type

Every word you type has to land somewhere in a preset: its name, tagline,
tags, keywords, facets, description or variant names. A word matches a whole
word or the start of one, so `adventur` already finds adventure. Some
expansions happen automatically:

| you type | also tried |
|---|---|
| `80s`, `1980s`, `80's` | `eighties` and each other |
| `black and white`, `b&w` | `bw` |
| `monster movie`, `giant monster` | `kaiju` |
| `sci fi`, `science fiction` | `scifi` |
| `super 8`, `16 mm`, `hong kong` | `super8`, `16mm`, `hong-kong` |
| `tape` | `vhs`, `videotape`, `cassette` |
| `spooky` | `horror`, `creepy`, `eerie`, `haunted` |

The full phrase and synonym tables live in `aesthetician/taxonomy.py`; the
app reads them from the engine's schema, so the two never disagree.

Results come back ranked: a hit in the name outweighs one in the tagline,
which outweighs the keywords, tags, facets, id and era; the description is the
tie-breaker. While a query is active the list is a ranked **RESULTS** group
with the family named on each row, instead of a tour of the families.

Answers come in two tiers. **Results** are presets the typed words themselves
landed in (a decade counts in all its spellings). **Related**, folded under
its own label, holds presets that only a synonym reached, and a synonym only
counts as a whole word in something a person wrote (name, tagline, keywords,
tags, id), never in facet labels or prose. So `witch` is the two folk-horror
looks, with the rest of horror one click away, and `scifi` cannot reach the
sound-only shelf through the words "playback space". A word that lands
nowhere directly (`spooky`) shows its related presets unfolded.

From the CLI, `aesthetician info <id>` prints a preset's tags, keywords and
facets, and the `search()` helper in `aesthetician.taxonomy` runs the same
scorer against the registry.

## Keywords

Every preset carries a short list of search keywords: the genre and mood
words a person actually types, format aliases, and one or two canonical
touchstones (`godzilla`, `miami-vice`). They are searched, never shown as
labels. New presets declare them inline (`keywords=(...)`); the presets that
predate the field get theirs from `aesthetician/presets/_keywords.py`.

## Facets

Five facets are **derived** from each preset, so nothing has to be tagged by
hand and the vocabulary can be tightened in one place:

| facet | decided by |
|---|---|
| **Medium** | effects in the chain (`vhs` means videotape, `halftone` means print, `pixel_era` means computer graphics) plus format words in the vocabulary. Sound-only presets get audio media: disc, tape, radio, telephone, PA, film soundtrack, digital, playback space. |
| **Genre** | program and picture words: adventure, action, horror, kaiju, western, crime, comedy, drama, music, war, fantasy, documentary, news, sports, commercial, kids, anime, educational, home movie, surveillance, talk and variety, game show, reality, experimental, internet aesthetic, utility |
| **Region** | country and tradition words: usa, uk, japan, italy, france, germany, hong-kong, india, latin-america, soviet, eastern-europe, scandinavia, spain, benelux, australia, canada, china, korea, southeast-asia, middle-east, africa |
| **Condition** | clean, worn, damaged, copy-of-a-copy, weak signal, crushed by compression |
| **Color** | the chain itself: a `mono` effect at full amount is black and white, a strong non-neutral tint is tinted, everything else is color |

In the app the facets are the dropdown row under the family chips. Each
dropdown only lists values that still have presets under everything else you
have selected, with counts, so a choice never empties the list. Facets
combine with the family chips, the era dropdown, the ★ and ♪ chips and the
search box.

`scripts/validate_presets.py` refuses a picture preset with no medium or no
genre facet, which is how the vocabulary is kept honest as presets are added.

## The Guide

The **✦ Guide** chip swaps the library for curated starting points: "make it
look like…" collections (a sixties kaiju film, security-camera footage,
somebody's home movies), a particular medium, an era of television, a
particular sound. Each collection lists its best answers first and, where one
preset cannot do it alone, **recipes**: ready-made stacks such as an eighties
adventure feature seen through a rental tape. Clicking a recipe applies its
layers bottom to top, exactly like a saved stack, and asks first if the tab
already carries work.

Collections are data (`aesthetician/collections.py`) and validated with the
presets, so a renamed preset can never leave a dangling recommendation.

## Sorting

The dropdown beside the era filter orders the library: by **family** (the
shelf order the app has always used), **A to Z**, **year**, or by when a
preset **arrived** in the library, newest or oldest first. The arrival date and
first release version come from git history, generated into
`aesthetician/presets/_introduced.py` by `scripts/gen_introduced.py` (re-run
it after adding presets); the packaged app has no git to ask. The flat sorts
name the family on each row, and the two "added" sorts also show the release
each preset first shipped in. `aesthetician info <id>` prints the same date.

## Recents

An unfiltered list starts with **◷ RECENT**: the last eight aesthetics picked
by hand (arrow-key auditioning does not count). It is stored with favorites in
the app's local settings.
