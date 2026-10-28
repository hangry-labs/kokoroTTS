# Project website

The GitHub Pages overview is built directly from the root README. Translated
READMEs, Markdown documentation and the listening gallery at `/examples/` share
the same header and navigation. The gallery keeps its own player.

## Preview

With Docker, Git, Task, uv and PowerShell 7 available (see
[local development](../README.md#local-development)):

```powershell
task pages
```

Open <http://127.0.0.1:9006/kokoroTTS/>. Press Ctrl+C to stop the
preview. `task pages-build` builds without starting the server. These tasks use
a separate Ruby Docker image and do not start the speech engine or use a GPU.
The staged build includes local public-file edits and respects Git ignore rules.

`Gemfile.lock` pins GitHub Pages 232 and its dependencies. The container uses the
same Jekyll 3.10 build as GitHub Pages, with safe mode enabled. The existing
branch-based Pages deployment can build this configuration without a separate
Actions workflow.

## Configuration

Edit the root [`_config.yml`](../_config.yml) for the project title, public URL,
repository and navigation. `url` is the origin; `baseurl` is the repository path,
or an empty string for a domain-root site. Navigation paths are relative to that
base URL. `hangry.background: none` disables the animated background; reduced
motion preferences also disable it.

The root README supplies the overview content, including release history. Keep
relative Markdown links usable on GitHub; the website resolves them to rendered
pages. Source-file links open on GitHub when the file is excluded from the site.
Use `<details markdown="1">` for collapsible sections containing Markdown, so
commands and tables render correctly in both Jekyll and GitHub.

The gallery's `index.md` includes the content from its standalone `index.html`.
The latter is excluded only from Jekyll's output, so the website gets one shared
header while the downloaded galleries still open directly. Voice
definitions, media and player code remain shared between both presentations.
The SSML showcase follows the same pattern through `examples/ssml.md` and its
standalone `ssml.html`, with styles scoped to `.ssml-page`.
Rich pages can set `wide`, `sidebar: false`, `content_class`, `stylesheets` and
`scripts` in front matter to use the same theme with their own content.

## Languages

`hangry.languages` enables the six website languages. The header remembers the
choice and keeps it in `?lang=` links between the overview, documentation and
examples. Each overview uses the actual translated README. Pages without a
translation keep their original content and show a notice in the selected
language. Translated content comes from the committed Markdown files.

Add a translated guide alongside its original, for example `docs/API.nb.md`, to
have it selected automatically for Norwegian. Set `lang: nb` in its front matter
for the correct language in the initial HTML and metadata. Keep relative links to
the original guide names; the theme resolves available translations. Use an
explicit `?lang=en` when a link should always open the English version.

The README examples links open the public website directly with the relevant
language selected. On a local website preview, those links stay in the preview.

## Reusing the theme

[`theme/`](theme/) is a self-contained Apache-2.0 Jekyll theme package, containing
the layout, brand asset, CSS, JavaScript, license and gemspec. It has no
project-specific paths or product text. This repository points `layouts_dir` and
`hangry.asset_root` at that local package, so deployment works without a separate
theme repository.

To share it across projects, publish the contents of `theme/` as a theme
repository or gem. A consumer can then use a pinned `remote_theme` reference or
install the gem, remove the local `layouts_dir` override, and use
`hangry.asset_root: /assets/hangry-pages`. Keep the README rendering plugins and
project-specific navigation settings in each consuming repository. The remote
theme should be published before consumers switch to it.

The galleries are independent of the theme and remain usable from Pages or a
downloaded checkout. `task pages-test` also requires Node.js for the language
routing checks.
