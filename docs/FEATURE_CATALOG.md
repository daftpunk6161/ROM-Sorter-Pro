# Feature Catalog

Ideensammlung mit Priorisierungs-Hinweisen. Bewertungsskala: Risiko/Komplexität = Niedrig/Mittel/Hoch.

## Detection
| Feature | Ziel | Nutzerwert | Risiko | Komplexität | Status |
| --- | --- | --- | --- | --- | --- |
| DAT-Source Manager | Mehrere DAT-Profile verwalten | Bessere Abdeckung & Kontrolle | Mittel | Mittel | 🟢 Implementiert (MVP) |
| DAT-Integrity + Analytics | Integrität & Coverage messen | Vertrauen & Debuggability | Niedrig | Mittel | 🟢 Implementiert (MVP) |
| Unknown-Reduktion (Why Unknown) | Ursachen anzeigen + Vorschläge | Schnellere Korrektur | Mittel | Mittel | 🟢 Implementiert (MVP) |
| Lokale Mapping-Regeln | User Overrides ohne globale Änderungen | Präzise Ergebnisse | Mittel | Mittel | 🟢 Implementiert (MVP) |

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
| Plugin-System (später) | Erweiterbarkeit | Flexibilität | Hoch | Hoch | 🟡 In Planung |
