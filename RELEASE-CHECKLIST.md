# Open DPC JP 0.1.0 release gate

The maintainer confirmed publication rights and reviewed the candidate on 2026-09-26. The repository remains private until the final release steps below are performed.

## Owner decisions and external setup

- [x] Maintainer attested on 2026-09-26 that institutional and contributor permission for the extracted Python core, extraction scripts, DPC/CCI definitions, and synthetic fixtures under MIT has been confirmed. This is the maintainer's attestation, not an independent legal opinion.
- [x] Set citation author to Shoya Wada, ORCID 0000-0001-7055-1009, and intended repository owner to `sy-wada` as confirmed by the maintainer.
- [x] Maintainer confirmed the candidate files and third-party source terms; `NOTICE.md` records the distribution scope.
- [x] Set the author, ORCID, and repository URL in `CITATION.cff`.
- [ ] Add `date-released` to `CITATION.cff` on the actual release date, then rebuild and recheck the distributions before tagging.
- [x] Create private `sy-wada/open-dpc-jp` without importing the private `casecurator-research` Git history.
- [x] Use the `testpypi` environment and Trusted Publisher to upload `0.1.0`, then verify a clean TestPyPI install. Do not try to upload that version to TestPyPI again.
- [ ] Confirm the production PyPI Trusted Publisher uses owner `sy-wada`, repository `open-dpc-jp`, workflow `release.yml`, and GitHub environment `pypi`. No repository token or environment secret is needed for OIDC.
- [x] Configure Cloudflare Pages with build command `python -m pip install zensical==0.0.63 && python build_site.py`, output `site`, holding production branch `pages-hold`, and `main` previews. The maintainer confirmed the candidate preview, including the CSP and CSV download.

## Technical checks before release

- [x] Run Python 3.12/3.13/3.14 on Windows, macOS and Linux, plus the browser CSV and Windows PowerShell extraction tests. The maintainer confirmed the corrected Actions run passed.
- [x] Build the documentation and inspect the `main` preview, browser utility, scoped CSP, and CSV download. Record the exact preview URL in the private handoff log if available.
- [x] Build and check wheel/sdist, run conformance, and verify a clean TestPyPI install of `0.1.0`.
- [x] Add the repository and documentation URLs to README and package metadata.
- [ ] Review the final `PUBLICATION-MANIFEST.json` and distribution hashes after the release-date edit.
- [ ] Compare release tag `v0.1.0`, package metadata, CHANGELOG, CITATION, GitHub Release and deployed docs version. Make the repository public and publish only after the owner confirms the final release commit.
- [ ] After publishing, install from production PyPI in a clean environment, import `open_dpc_jp`, run a minimal API call, and verify README rendering and links.

The [official Zensical build instructions](https://zensical.org/docs/usage/build/), [PyPI Trusted Publishing guide](https://docs.pypi.org/trusted-publishers/using-a-publisher/), and [Cloudflare Pages build configuration](https://developers.cloudflare.com/pages/configuration/build-configuration/) should be rechecked at the time of release.
