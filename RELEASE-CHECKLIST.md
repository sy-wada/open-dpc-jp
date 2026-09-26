# Open DPC JP 0.1.0 release gate

This candidate is not publication-authorized. Do not make the repository public, upload a distribution, or deploy the site until the owner records the rights and privacy review below.

## Owner decisions and external setup

- [x] Maintainer attested on 2026-09-26 that institutional and contributor permission for the extracted Python core, extraction scripts, DPC/CCI definitions, and synthetic fixtures under MIT has been confirmed. This is the maintainer's attestation, not an independent legal opinion.
- [x] Set citation author to Shoya Wada, ORCID 0000-0001-7055-1009, and intended repository owner to `sy-wada` as confirmed by the maintainer.
- [ ] Before release, review `NOTICE.md` and the exact third-party source terms against the candidate files; record the result and update any release-candidate wording in `NOTICE.md`.
- [ ] Add the actual repository URL and release date to `CITATION.cff`, and approve its final wording.
- [ ] Confirm `sy-wada/open-dpc-jp` and `open-dpc-jp` are available immediately before creating the repository/project.
- [ ] Create a new repository from this candidate without importing the private `casecurator-research` Git history. Audit the first commit and GitHub visibility before public access.
- [ ] Create or access TestPyPI and PyPI accounts with 2FA. Configure pending Trusted Publishers matching owner and repository: TestPyPI workflow `testpypi.yml`, environment `testpypi`; PyPI workflow `release.yml`, environment `pypi`.
- [ ] Create the Cloudflare account, then plan Pages branch deployment before connecting GitHub: Git integration automatically deploys the selected production branch. To preview before publication, use a holding production branch and a separate candidate preview branch; switch production to `main` only at release. Build command: `python -m pip install zensical==0.0.63 && python build_site.py`; output directory: `site`.

## Technical checks before release

- [ ] Run Python 3.12/3.13/3.14 on Windows, macOS and Linux via `test.yml`. Run PowerShell extraction parity on Windows; local Windows execution was blocked by script-signing policy.
- [ ] Run `python build_site.py`, inspect all required pages and the interactive tool in desktop and mobile browsers, and verify the scoped CSP response header from Cloudflare preview.
- [ ] Run `python -m build`, `python -m twine check dist/*`, clean wheel install and conformance. Upload to TestPyPI and verify an install from TestPyPI before production PyPI.
- [ ] Update README documentation URL and `pyproject.toml` project URLs to the actual deployed site/repository. Fill release date in `CITATION.cff`, then rebuild and recheck artifact hashes.
- [ ] Review `PUBLICATION-MANIFEST.json` and its `publication_authorized: false` gate. Set the final release authorization record only after all reviews are complete; never publish the unchecked candidate verbatim.
- [ ] Compare release tag `v0.1.0`, package metadata, CHANGELOG, CITATION, GitHub Release and deployed docs version. Publish only after all rights gates and preview checks pass.
- [ ] After publishing, install from production PyPI in a clean environment, import `open_dpc_jp`, run a minimal API call, and verify README rendering and links.

The [official Zensical build instructions](https://zensical.org/docs/usage/build/), [PyPI Trusted Publishing guide](https://docs.pypi.org/trusted-publishers/using-a-publisher/), and [Cloudflare Pages build configuration](https://developers.cloudflare.com/pages/configuration/build-configuration/) should be rechecked at the time of release.
