# Feature Catalog

> **Aktualisiert:** 2026-01-31  
> **Status:** MVP Feature-Complete

Ideensammlung mit Priorisierungs-Hinweisen. Bewertungsskala: Risiko/Komplexität = Niedrig/Mittel/Hoch.

## Detection
| Feature | Ziel | Nutzerwert | Risiko | Komplexität | Status |
| --- | --- | --- | --- | --- | --- |
| DAT-Source Manager | Mehrere DAT-Profile verwalten | Bessere Abdeckung & Kontrolle | Mittel | Mittel | 🟢 Implementiert (MVP) |
| DAT-Integrity + Analytics | Integrität & Coverage messen | Vertrauen & Debuggability | Niedrig | Mittel | 🟢 Implementiert (MVP) |
| Unknown-Reduktion (Why Unknown) | Ursachen anzeigen + Vorschläge | Schnellere Korrektur | Mittel | Mittel | 🟢 Implementiert (MVP) |
| Lokale Mapping-Regeln | User Overrides ohne globale Änderungen | Präzise Ergebnisse | Mittel | Mittel | 🟢 Implementiert (MVP) |
| Confidence-Tuner (Slider) | Mindest-Confidence einstellbar | Precision/Recall Balance | Niedrig | Niedrig | 🟡 Geplant (v1.1) |
| Collection-Completeness | Fortschritt pro System anzeigen | Sammler-Motivation | Niedrig | Mittel | 🟡 Geplant (v1.1) |

## Conversion / Normalization
| Feature | Ziel | Nutzerwert | Risiko | Komplexität | Status |
| --- | --- | --- | --- | --- | --- |
| Plattform-Format-Registry v1 | Formate & Regeln zentral | Konsistenz | Niedrig | Mittel | 🟢 Implementiert (MVP) |
| Track-Set Validator (cue/gdi) | Vollständigkeit prüfen | Weniger defekte Sets | Niedrig | Mittel | 🟢 Implementiert (MVP) |
| Folder-Set Validator (PS3 etc.) | Komplettheitschecks | Qualität & Sicherheit | Mittel | Hoch | 🟢 Implementiert (MVP) |
| Pro-Plattform Output Targets | Zielprofile (CHD/RVZ/etc.) | Flexible Workflows | Mittel | Mittel | 🟢 Implementiert (MVP) |

## IGIR
| Feature | Ziel | Nutzerwert | Risiko | Komplexität | Status |
| --- | --- | --- | --- | --- | --- |
| Plan/Diff/Execute Flow | Safety diff vor Ausführung | Höhere Sicherheit | Mittel | Mittel | 🟢 Implementiert (MVP) |
| Profile pro Plattform | Args-Templates je Kategorie | Power-User Effizienz | Niedrig | Mittel | 🟢 Implementiert (MVP, active_profile) |
| Rollback-Strategie | Copy-first oder Copy-only | Fehlerprävention | Niedrig | Mittel | 🟢 Implementiert (MVP, Copy-first) |
| Report-Viewer | Filter/Export der Ergebnisse | Transparenz | Niedrig | Mittel | 🟡 In Planung |

## GUI / UX
| Feature | Ziel | Nutzerwert | Risiko | Komplexität | Status |
| --- | --- | --- | --- | --- | --- |
| Job-Queue (Pause/Resume) | Mehrere Tasks sequenziell | Stabilere Abläufe | Mittel | Hoch | 🟢 Implementiert (MVP) |
| Log-Viewer mit Filtern | Schnelles Debugging | Besseres Troubleshooting | Niedrig | Mittel | 🟢 Implementiert (MVP) |
| Presets + Bulk-Actions | Wiederholbare Flows | Zeitersparnis | Niedrig | Mittel | 🟢 Implementiert |
| Tk-Minimalparität | Kernflows stabil | Fallback nutzbar | Niedrig | Mittel | 🟢 Implementiert |

## DB / Daten
| Feature | Ziel | Nutzerwert | Risiko | Komplexität | Status |
| --- | --- | --- | --- | --- | --- |
| Hash-Cache (path+mtime+size) | Wiederholte Scans beschleunigen | Performance | Niedrig | Mittel | 🟢 Implementiert (MVP) |
| Index-Sharding (optional) | Skalierung bei sehr großen Sets | Performance | Hoch | Hoch | 🟡 In Planung |
| Library-Reports | Bestandsanalyse | Transparenz | Niedrig | Mittel | 🟢 Implementiert |

## Performance
| Feature | Ziel | Nutzerwert | Risiko | Komplexität | Status |
| --- | --- | --- | --- | --- | --- |
| IO-aware Hashing | IO-Engpässe vermeiden | Stabilität | Mittel | Mittel | 🟢 Implementiert (MVP) |
| SQLite-Tuning | Indexing schneller | Performance | Niedrig | Mittel | 🟢 Implementiert (MVP) |
| Bench/Profiling Tools | Bottlenecks sichtbar | Wartbarkeit | Niedrig | Mittel | 🟡 In Planung |

## Qualität & Maintainability
| Feature | Ziel | Nutzerwert | Risiko | Komplexität | Status |
| --- | --- | --- | --- | --- | --- |
| Golden Fixtures | Regressionen verhindern | Stabilität | Niedrig | Mittel | 🟢 Implementiert (MVP) |
| Mutation-Tests (kritisch) | Testqualität erhöhen | Sicherheit | Mittel | Hoch | 🟡 In Planung |
| Strukturierte Logs (JSON) | Bessere Debuggability | Mittel | Mittel | 🟢 Implementiert (MVP) |

## Integrationen
| Feature | Ziel | Nutzerwert | Risiko | Komplexität | Status |
| --- | --- | --- | --- | --- | --- |
| Rebuilder-Mode | Sichere Rebuilds | Datenqualität | Mittel | Hoch | 🟢 Implementiert (MVP) |
| Frontend-Exporte | ES/LaunchBox Mapping | Komfort | Mittel | Mittel | 🟢 Implementiert (MVP) |
| MiSTer-FPGA-Export | MiSTer-Ordnerformat | Community Request | Niedrig | Mittel | 🟡 Geplant (v1.1) |
| Flash-Cart-Export | EverDrive/SD2SNES | Hardware-User | Niedrig | Mittel | 🟡 Geplant (v1.1) |
| Analogue-Pocket-Export | OpenFPGA Format | Hardware-User | Niedrig | Mittel | 🟡 Geplant (v1.1) |
| Steam-ROM-Manager | Steam Deck Integration | Komfort | Niedrig | Mittel | 🟡 Geplant (v1.2) |
| Plugin-System (später) | Erweiterbarkeit | Flexibilität | Hoch | Hoch | 🟡 In Planung |

## ROM-Verifizierung & Audit (NEU)
| Feature | Ziel | Nutzerwert | Risiko | Komplexität | Status |
| --- | --- | --- | --- | --- | --- |
| Bad-Dump-Scanner | [b]/[!]/[o] erkennen | Qualitätskontrolle | Niedrig | Niedrig | 🟡 Geplant (v1.1) |
| Intro/Trainer-Erkennung | [t]/[f] ROMs finden | Saubere Sammlung | Niedrig | Niedrig | 🟡 Geplant (v1.1) |
| Overdump-Erkennung | Größer als DAT | Speicher sparen | Niedrig | Mittel | 🟡 Geplant (v1.1) |
| Integritäts-Report | Vollständiger Audit | Dokumentation | Niedrig | Mittel | 🟡 Geplant (v1.1) |

## Duplikat-Management (NEU)
| Feature | Ziel | Nutzerwert | Risiko | Komplexität | Status |
| --- | --- | --- | --- | --- | --- |
| Hash-Duplikat-Finder | Identische finden | Speicher sparen | Niedrig | Niedrig | 🟡 Geplant (v1.1) |
| Fuzzy-Duplikat-Finder | Rev A vs B | 1G1R-Sets | Niedrig | Mittel | 🟡 Geplant (v1.1) |
| Duplikat-Merge-Wizard | Intelligent mergen | Aufgeräumt | Mittel | Mittel | 🟡 Geplant (v1.2) |

## Patch-Management (NEU)
| Feature | Ziel | Nutzerwert | Risiko | Komplexität | Status |
| --- | --- | --- | --- | --- | --- |
| IPS/BPS/UPS-Patcher | Patches anwenden | Fan-Translations | Mittel | Mittel | 🟡 Geplant (v1.1) |
| Patch-Bibliothek | Patches verwalten | Organisation | Niedrig | Mittel | 🟡 Geplant (v1.2) |
| Auto-Patch-Matching | Patches finden | Komfort | Mittel | Mittel | 🟡 Geplant (v1.2) |

## Emulator-Integration (NEU)
| Feature | Ziel | Nutzerwert | Risiko | Komplexität | Status |
| --- | --- | --- | --- | --- | --- |
| ROM-Direkt-Start | Quick-Test | Workflow | Niedrig | Niedrig | 🟡 Geplant (v1.1) |
| Core-Zuordnung | RetroArch-Cores | Power-User | Niedrig | Niedrig | 🟡 Geplant (v1.1) |
| Per-Game-Settings | Individuelle Config | Kompatibilität | Niedrig | Mittel | 🟡 Geplant (v1.2) |

## Collection-Analytics (NEU)
| Feature | Ziel | Nutzerwert | Risiko | Komplexität | Status |
| --- | --- | --- | --- | --- | --- |
| Sammlungs-Dashboard | Statistiken | Übersicht | Niedrig | Mittel | 🟡 Geplant (v1.1) |
| Wunschlisten-Manager | Fehlende tracken | Sammler-Ziele | Niedrig | Niedrig | 🟡 Geplant (v1.1) |
| Inkrementelles Backup | Nur geänderte | Effizienz | Niedrig | Mittel | 🟡 Geplant (v1.2) |

## Deployment
| Feature | Ziel | Nutzerwert | Risiko | Komplexität | Status |
| --- | --- | --- | --- | --- | --- |
| Portable-Mode | USB-Stick-kompatibel | Flexibilität | Niedrig | Niedrig | 🟡 Geplant (v1.1) |
| Auto-Updater | Einfache Updates | Komfort | Mittel | Mittel | 🟡 In Planung |
