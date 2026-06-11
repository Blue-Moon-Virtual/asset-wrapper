# Asset Master — Collectionize: Launch & Monetization Plan

*Blue Moon Virtual · prepared 2026-06-11*

## 1. The legal reality first (it shapes everything)

Any Blender add-on that imports `bpy` is a derivative of Blender and **must be
GPL-licensed**. This is not a problem — every paid add-on on Superhive
(formerly Blender Market) works this way — but it means:

- You sell **convenience, packaging, updates, and support**, not the code.
- A buyer may legally re-share the code. In practice almost nobody does, and
  paying customers want the update channel and support.
- Keep the GitHub repo public (good marketing, trust, bug reports) and sell
  the **packaged releases + support** on the stores.

## 2. Positioning

**One-liner:** *"Turn any selection or collection into a linked asset — in
one click."*

Differentiators to hammer in every description:
- Works with **collection instances** (the gap competitors leave open)
- **Dependency-safe**: curve/mirror/boolean/armature helpers travel with the
  asset — assets never come in deformed
- Per-project library that **syncs with the project folder** (GDrive/Dropbox
  team workflows) and auto-registers
- Zero-setup thumbnails

Target users: archviz studios, set-dressing/environment artists, small teams
sharing files over synced drives. Lead with the team workflow — that's the
story competitors don't tell.

## 3. Channels & pricing (recommendation)

Three-tier funnel, all from the same codebase:

| Channel | Price | Role |
| --- | --- | --- |
| **Blender Extensions** (extensions.blender.org) | Free | Distribution + discovery. Largest funnel; extension manifest is already prepared. Put "Support development on Gumroad" in the description. |
| **Gumroad** | $0+ pay-what-you-want (suggest $10) | Donations + mailing list. Gumroad gives you buyer emails = your update/launch channel. |
| **Superhive** (formerly Blender Market) | $14.99 launch price | The "real" revenue channel. Buyers there expect to pay; 30% commission feels expensive but the audience converts. |

Reasoning: a $10–15 utility add-on is an impulse buy for studios; underpricing
to $5 signals "toy". Free tier on extensions.blender.org is what gets you the
user base and GitHub stars that make the paid listing credible. If you'd
rather start pure-donation, launch Gumroad-only at $0+, but expect roughly
1–3% of downloaders to pay.

**Recommended path:** launch v1.0 on all three the same week. Same zip
everywhere.

## 4. Pre-launch checklist (1–2 weeks of evenings)

1. **Rename check** — "Asset Master" is generic; search Superhive/Gumroad for
   collisions before printing the name on artwork. Alternative candidates:
   *Collectionize*, *Asset Rounduo*, keep it if clear.
2. **GitHub org** — publish repo under a `bluemoonvirtual` org. Enable Issues
   and Discussions. Add 2–3 GIFs to the README (the before/after of a broken
   vs. correct curve-modifier asset is *the* money shot).
3. **Demo video, 60–90 s** — screen capture, no talking-head needed:
   furnished room → select sofa group → click Collection → Asset Browser
   shows thumbnail → drag 3 more sofas in → file size comparison. Post on
   YouTube; embed everywhere.
4. **5–8 screenshots/GIFs** for store pages (panel, thumbnail grid in Asset
   Browser, preferences, team-drive folder structure).
5. **Store copy** — reuse README "Why" section. First sentence must contain
   "linked collection assets in one click".
6. **Versioning & support promise** — state clearly: "Supports Blender 4.2+,
   updates free forever, support via GitHub Issues." Cheap to promise,
   builds trust.
7. **Test matrix** — run the headless test suite (`_test/run_tests.py`) on
   4.2 LTS and current stable before each release.

## 5. Launch week

- Day 1: GitHub public + tag v1.0.0 + release zip. Gumroad + Superhive live.
- Day 1: Submit to **extensions.blender.org** (review takes days–weeks; the
  manifest and GPL license are already compliant).
- Day 2: **BlenderArtists** "Released" thread — honest post: what it does,
  the GIFs, free/paid links. This thread becomes your support hub; link it
  from the store pages.
- Day 2–3: Reddit **r/blender** (show the workflow GIF, mention free version
  in comments, don't hard-sell), X/BlueSky post, LinkedIn (archviz audience —
  your studio network is exactly the target market).
- Day 3: Pitch **BlenderNation** (they cover new add-ons readily; email with
  video + 2 paragraphs). Biggest single traffic spike you can get for free.
- Week 2: Short workflow article ("How we share furniture assets over Google
  Drive at Blue Moon Virtual") — blog/LinkedIn; it markets both the studio
  and the add-on.

## 6. After launch

- **Respond fast for the first month** — early reviews decide store ranking.
- Collect the top 3 feature requests; ship a 1.1 within 4–6 weeks (momentum
  + "actively maintained" badge effect).
- Roadmap candidates already visible from the codebase: asset catalogs
  support, batch-collectionize multiple collections, "unpack/edit asset and
  re-export" round-trip, material-asset mode.
- Track: downloads (extensions.blender.org dashboard), Gumroad conversion,
  Superhive sales. If Superhive ≫ Gumroad after 3 months, consider making
  Gumroad paid-only too.

## 7. Realistic expectations

Niche utility add-ons on Superhive typically do **$100–600/month** after a
good launch, with a long tail; the free-tier funnel and a BlenderNation
feature are what push you to the upper end. The bigger strategic value:
portfolio credibility for Blue Moon Virtual and inbound contacts from
studios with the same pipeline pain.
