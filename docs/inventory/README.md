# Inventory of installed skills, plugins and MCP tools

Purpose: decide what `twwa-growth` distils, what it calls as an optional integration, and what it ignores.
The research dossier in `../research/` is the factual basis; where an installed tool disagrees with it, the dossier wins unless the tool cites a newer primary source.

## Workflow phases used for mapping

| ID | Phase | What happens |
|---|---|---|
| P0 | Onboard | canonical business facts (NAP, services, service area, prices), access, config |
| P1 | Check | read-only audit: tracking, GBP, geo-grid, site (Astro/Vercel technical + on-page + CRO), citations, AI panel baseline |
| P2 | Plan | at most 5 actions per cycle with hypothesis, metric, window, effort, risk; fixed priority order |
| P3 | Ship | branch, Vercel preview, gate scripts, approval bound to exact version, merge, live verification, IndexNow, action log |
| P4 | Pages and content | German page types and copy, evidence requirements, gates A to H (demand, service relationship, local evidence, town swap, similarity, ramp, pilot, prune) |
| P5 | Reviews | review engine compliant with German law (UWG, consent), reply drafts, velocity targets |
| P6 | Off-site | citations (German tiers), membership and partner listings, local press, roundup pitches, drafts only |
| P7 | AI visibility | prompt panel, multi-run mention rate with intervals, cited-domain analysis |
| P8 | Measure and attribute | GSC, Bing, GBP, Vercel events, lead records, per-action verdicts vs control pages |
| P9 | Weekly loop | scheduled run, health alerts, opportunity detection, owner request |
| P10 | Report | one-page German monthly report led by qualified Anfragen vs lead-portal cost |
| P11 | Prospect check | free "Sichtbarkeits-Check" on any URL without repo access |

## File format (one file per group)

1. **Scope**: what was read (paths, versions, licence of each source) and what was skipped and why.
2. **Per source table**: skill or tool, what it actually does (one line, verified by reading it), phases it helps (IDs above), how `twwa-growth` should use it: `distil` (take a rule or checklist, restated in our words), `call` (optional integration: "if installed, use X for Y; otherwise do Z"), or `ignore` (with reason).
3. **Rules and checklists worth distilling**: concrete, with thresholds and the source skill named. No verbatim copying of third-party text; restate.
4. **Scripts and data access worth knowing**: CLI interface, auth, cost, whether it works without credentials.
5. **Contradictions with the dossier**: claim in the tool, dossier position (cite the dossier file and finding), which side the evidence supports.
6. **Harmful or banned for our use**: anything that amounts to link schemes, review incentives or gating, fake reviews, astroturfing, mass doorway pages, manipulating AI answers.
7. **Gaps**: things our workflow needs that none of the sources in this group covers (German law, German citation sources, Astro/Vercel specifics, cookieless attribution, action log with measurement windows, and so on).

Keep each file under about 1,800 words. Tables over prose. Every claim about a tool must come from reading its files, not from its name.
