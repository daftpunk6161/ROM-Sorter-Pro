# Identifikation — DAT/Hash-first (RomVault/IGIR Style)

## Leitprinzipien
- **DAT/Hash Hit ist Wahrheit**: confidence=1000, is_exact=true
- **UNKNOWN > WRONG**: False Positives sind Release-Blocker
- **Dry-run**: niemals externe Tools, niemals Writes

## Zielpipeline (Strict Order)
1) **Exact Match (DAT/Hash)**
   - Primär: SHA1 exact
   - Fallback: CRC32 + size nur wenn SHA1 in DAT fehlt
   - Treffer → sofort akzeptieren, Heuristik stoppt

2) **Signaturen/Struktur**
   - Magic/Header
   - Disc Track Sets (CUE/GDI) Validierung
   - Folder Sets (Manifeste/required_paths)

3) **Heuristik (letzter Weg)**
   - Datei-/Ordner-Tokens, Extension
   - Unknown-Regeln:
     - < threshold → Unknown
     - Top1–Top2 < delta → Unknown
     - Konfliktgruppe/Mixed Signals → Unknown

## Output Model (Unified)
- platform_id
- confidence
- is_exact
- signals[]
- candidates[]
- reason
- input_kind
- normalized_artifact (optional)

## Lokale Overrides (Mapping)
Für manuelle Korrekturen gibt es eine lokale Override-Datei.

- Standardpfad: [config/identify_overrides.yaml](../config/identify_overrides.yaml)
- Aktivierung: `identification_overrides.enabled=true`
- Pfad-Override: `identification_overrides.path` (YAML oder JSON)

Minimal-Schema pro Regel:
- `name`: eindeutiger Name
- `platform_id`: Zielplattform (z.B. "PS2")
- Match-Keys (kombinierbar, **alle** müssen matchen):
   - `path_regex`
   - `name_regex`
   - `path_glob`
   - `contains` (String oder Liste)
   - `extension`
   - `starts_with`
   - `ends_with`

Regeln werden top‑down ausgewertet (first match wins). Overrides erzeugen das Signal `OVERRIDE_RULE`.

## Archive Awareness
- ZIP: Entries einzeln hashen (Stream, kein Extract by default)
- 7z/rar: optional (wenn Tool vorhanden), sonst Unknown
- Mixed Content: Unknown (außer deterministischer Entry-Consensus)

## Ist-Zustand (Gap)
- Heuristik/DB/ML existiert parallel zur DAT-Logik
- DAT-Index ist in-memory/pickle, nicht sqlite-basiert
- Archive erkennt nur Dateinamen, keine Entry-Hashes

## Ziel-Metriken
- False Positive Rate: ~0
- Unknown Rate: akzeptiert bei Ambiguität
- deterministischer Output (gleiche Inputs => gleiche Outputs)
