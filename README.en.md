# Acting for AI

**Turn emotion, relationships and subtext into visible acting choices.**

[中文](README.md) · [Library](docs/INDEX.md) · [Integration guide](docs/INTEGRATION.md)

Acting for AI is an open reference library for AI video, animation and storyboarding. It translates creative intentions into gaze, breath, hand movement, posture, spatial relationships and action beats that creators and AI skills can retrieve and adapt.

The maintainer has verified and continuously used the library's approach in real creative practice. Full video examples are not included in this release. This firsthand experience is not a claim of per-entry testing, universal model compatibility or measured improvement in controlled experiments. See [validation scope](docs/VALIDATION.md).

## Contents

The initial release contains 45 emotion/state entries, 31 relationship entries and 31 movement/acting references, selected and structured from the maintainer's existing v0.1.10 reference library. Entry content is primarily Chinese; some searchable English aliases are provided.

Use one main action and a small number of supporting cues. Ground them in the character's situation, objective and trigger; preserve the response and end state. These are creative choices, not rules for diagnosing real people's emotions.

## Integrate without a model dependency

Any workflow capable of reading Markdown or JSON can use the material as reference context. The repository does not automatically install itself into skills, run generation or prescribe a model-specific prompt format.

1. Retrieve relevant entries using [data/index.json](data/index.json).
2. Read the selected `cards/ID.json` or rendered `docs/cards/ID.md` files.
3. Adapt the actions to the scene and the host skill's existing output format.
4. Keep source IDs and validation scope in your working notes, outside the final generation prompt.

Offline usage (Python 3.10+, standard library only):

```sh
python scripts/library.py search "restraint"
python scripts/library.py show REL-030
python scripts/library.py check
python scripts/library.py build --check
```

Maintenance runs every seven days in the maintainer's existing local scheduled task. GitHub CI checks consistency only; it does not generate video. See [maintenance](MAINTENANCE.md), [contributing](CONTRIBUTING.md), and [citation metadata](CITATION.cff).

Original documentation and entries: CC BY 4.0. Code: MIT. Linked third-party materials retain their own rights.
