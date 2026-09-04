# Maintainer and agent guidance

This is a public reference library, not an installed production Skill.

- Edit `cards/*.json` as the single source of entry content. Preserve IDs permanently. Do not overwrite public contributions by reimporting an upstream snapshot.
- Read `MAINTENANCE.md`, `docs/VALIDATION.md`, the manifest and relevant entries before changes. Retrieve only relevant content for creative use.
- Preserve the maintainer's firsthand statement that the library's method has been verified in actual practice. Do not turn absence of published video examples into absence of validation.
- Do not label new suggestions as individually tested without evidence. Keep external source review, firsthand practice and documented generation tests separate.
- Keep the library model independent. Do not introduce a required host Skill, API, plugin or generation provider.
- Do not call image, video, music or audio generation for maintenance. Complete video examples are explicitly deferred.
- Respect third-party attribution. Do not publish local absolute paths, private project material, credentials or full third-party articles.
- Do not modify the author's internal Skills as a side effect of maintaining this repository.
- Check with `python scripts/library.py check`; regenerate with `python scripts/library.py build`; verify with `python scripts/library.py build --check` and `python -m unittest discover -s tests -v`.
- Keep manifest, citation and changelog versions aligned. Stage only files belonging to the update. Do not force push, reset away user changes, or claim publication without verifying the remote commit.
- A request for advice alone does not authorize publication; the maintainer's explicitly authorized scheduled maintenance may publish changes within its saved scope.
