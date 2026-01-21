# Test Strategy (Mutation‑Proof, Integration‑First)

## Prinzipien
- Integration-first mit realistischen Fixtures
- Negative Fälle verpflichtend
- Dry-run darf nie schreiben oder Tools starten
- UNKNOWN ist besser als falsch

## Pflichtfälle (Core)
- DAT exact match → confidence=1000, is_exact=true
- CRC32+size fallback nur wenn SHA1 fehlt
- Heuristik: unter threshold → Unknown
- Ambiguität (top1-top2 < delta) → Unknown
- Mixed archive → Unknown
- ZIP Entry Hashing → deterministischer Match
- Trackset missing file → Fail + reason
- Folderset missing manifest → Fail + reason
- Dry-run: keine Writes, kein Subprocess
- Cancel: stoppt Hashing/IGIR, konsistente Reports

## Index Tests
- Incremental ingest: skip unverändert
- Changed DAT: replace rows
- Removed DAT: deactivate + remove hashes
- CRC32+SHA1 correctness
- Lockfile: parallel block, stale recovery, PID reuse

## IGIR Tests
- Plan required before execute
- Execute nur nach explizitem User Action
- Dest-root enforcement
- Diff export CSV/JSON
- Cancel/timeout kills process tree

## Mutation-Proof Beispiele
1) SHA1 Treffer ignoriert → Test muss rot
2) Dry-run startet Tool → Test muss rot
3) Dest-root check entfernt → Test muss rot

## Coverage Ziel
- >=70% für controller/detection/security/indexing/normalization
