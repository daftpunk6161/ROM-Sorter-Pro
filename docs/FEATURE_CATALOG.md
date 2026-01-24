# Feature Catalog

Ideensammlung mit Priorisierungs-Hinweisen. Bewertungsskala: Risiko/Komplexität = Niedrig/Mittel/Hoch.

## Detection
| Feature | Ziel | Nutzerwert | Risiko | Komplexität |
| --- | --- | --- | --- | --- |
| DAT-Source Manager (MVP) | Mehrere DAT-Profile verwalten | Bessere Abdeckung & Kontrolle | Mittel | Mittel |
| DAT-Integrity + Analytics (MVP) | Integrität & Coverage messen | Vertrauen & Debuggability | Niedrig | Mittel |
| Unknown-Reduktion (Why Unknown) (MVP) | Ursachen anzeigen + Vorschläge | Schnellere Korrektur | Mittel | Mittel |
| Lokale Mapping-Regeln (MVP) | User Overrides ohne globale Änderungen | Präzise Ergebnisse | Mittel | Mittel |

## Conversion / Normalization
| Feature | Ziel | Nutzerwert | Risiko | Komplexität |
| --- | --- | --- | --- | --- |
| Plattform-Format-Registry v1 (MVP) | Formate & Regeln zentral | Konsistenz | Niedrig | Mittel |
| Track-Set Validator (cue/gdi) (MVP) | Vollständigkeit prüfen | Weniger defekte Sets | Niedrig | Mittel |
| Folder-Set Validator (PS3 etc.) (MVP) | Komplettheitschecks | Qualität & Sicherheit | Mittel | Hoch |
| Pro-Plattform Output Targets (MVP) | Zielprofile (CHD/RVZ/etc.) | Flexible Workflows | Mittel | Mittel |

## IGIR
| Feature | Ziel | Nutzerwert | Risiko | Komplexität |
| --- | --- | --- | --- | --- |
| Plan/Diff/Execute Flow (MVP) | Safety diff vor Ausführung | Höhere Sicherheit | Mittel | Mittel |
| Profile pro Plattform (MVP, active_profile) | Args-Templates je Kategorie | Power-User Effizienz | Niedrig | Mittel |
| Rollback-Strategie (MVP, Copy-first) | Copy-first oder Copy-only | Fehlerprävention | Niedrig | Mittel |
| Report-Viewer | Filter/Export der Ergebnisse | Transparenz | Niedrig | Mittel |

## GUI / UX
| Feature | Ziel | Nutzerwert | Risiko | Komplexität |
| --- | --- | --- | --- | --- |
| Job-Queue (Pause/Resume) (MVP) | Mehrere Tasks sequenziell | Stabilere Abläufe | Mittel | Hoch |
| Log-Viewer mit Filtern (MVP) | Schnelles Debugging | Besseres Troubleshooting | Niedrig | Mittel |
| Presets + Bulk-Actions | Wiederholbare Flows | Zeitersparnis | Niedrig | Mittel |
| Tk-Minimalparität | Kernflows stabil | Fallback nutzbar | Niedrig | Mittel |

## DB / Daten
| Feature | Ziel | Nutzerwert | Risiko | Komplexität |
| --- | --- | --- | --- | --- |
| Hash-Cache (path+mtime+size) (MVP) | Wiederholte Scans beschleunigen | Performance | Niedrig | Mittel |
| Index-Sharding (optional) | Skalierung bei sehr großen Sets | Performance | Hoch | Hoch |
| Library-Reports | Bestandsanalyse | Transparenz | Niedrig | Mittel |

## Performance
| Feature | Ziel | Nutzerwert | Risiko | Komplexität |
| --- | --- | --- | --- | --- |
| IO-aware Hashing (MVP) | IO-Engpässe vermeiden | Stabilität | Mittel | Mittel |
| SQLite-Tuning (MVP) | Indexing schneller | Performance | Niedrig | Mittel |
| Bench/Profiling Tools | Bottlenecks sichtbar | Wartbarkeit | Niedrig | Mittel |

## Qualität & Maintainability
| Feature | Ziel | Nutzerwert | Risiko | Komplexität |
| --- | --- | --- | --- | --- |
| Golden Fixtures (MVP) | Regressionen verhindern | Stabilität | Niedrig | Mittel |
| Mutation-Tests (kritisch) | Testqualität erhöhen | Sicherheit | Mittel | Hoch |
| Strukturierte Logs (JSON) (MVP) | Bessere Debuggability | Mittel | Mittel |

## Integrationen
| Feature | Ziel | Nutzerwert | Risiko | Komplexität |
| --- | --- | --- | --- | --- |
| Rebuilder-Mode (MVP) | Sichere Rebuilds | Datenqualität | Mittel | Hoch |
| Frontend-Exporte (MVP) | ES/LaunchBox Mapping | Komfort | Mittel | Mittel |
| Plugin-System (später) | Erweiterbarkeit | Flexibilität | Hoch | Hoch |
