# Hermes Agent Windows Workstation - Multilingual Showcase Site

A high-performance showcase website celebrating the **Hermes Agent Windows Workstation**, based on the Zenn publication [「IDEにAIを足す」のをやめた。AIエージェントを中心にWindows環境を再構築した話](https://zenn.dev/zapabob/articles/hermes-agent-windows-workstation).

## Features
- **Trilingual Support (Zero Reload)**:
  - 🇬🇧 **King's English (`en-GB`)**: Sophisticated British English orthography and technical terminology.
  - 🇯🇵 **Japanese (`ja`)**: Punchy, passionate manifesto directly reflecting the original Zenn article.
  - 🇨🇳 **Simplified Chinese (`zh-CN`)**: Native, idiomatic terminology for the global AI and OSS community.
- **Modern Glassmorphism & Cyber Obsidian Aesthetic**: Tailored CSS design system with fluid typography, responsive layout, and contrast bubble overlays.
- **Interactive Capabilities**:
  - Full-screen Lightbox zoom for high-resolution inspection of workstation UI panes.
  - One-click copy for `git clone` command with animated toast confirmation.
  - Live metric stat cards (9,808+ clones, 237+ unique developers, 723+ composed upstream commits).
- **Zero Third-Party Dependencies**: Pure HTML5, CSS3, and JavaScript, running completely offline and statically deployable to GitHub Pages.

## Local Preview
```bash
py -3 -m http.server 8085 --directory docs/workstation-site
```
Then visit `http://localhost:8085`.

## GitHub Pages Deployment
- Automated via `.github/workflows/deploy-workstation-pages.yml` on push to `main`.
- Can also be served directly from a dedicated `gh-pages` branch.
