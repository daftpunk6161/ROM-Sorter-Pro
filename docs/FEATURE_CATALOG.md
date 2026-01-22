# Feature Catalog

Ideensammlung mit Priorisierungs-Hinweisen. Bewertungsskala: Risiko/Komplexität = Niedrig/Mittel/Hoch.

## Detection
| Feature | Ziel | Nutzerwert | Risiko | Komplexität |
| --- | --- | --- | --- | --- |
| DAT-Source Manager | Mehrere DAT-Profile verwalten | Bessere Abdeckung & Kontrolle | Mittel | Mittel |
| DAT-Integrity + Analytics | Integrität & Coverage messen | Vertrauen & Debuggability | Niedrig | Mittel |
| Unknown-Reduktion (Why Unknown) | Ursachen anzeigen + Vorschläge | Schnellere Korrektur | Mittel | Mittel |
| Lokale Mapping-Regeln | User Overrides ohne globale Änderungen | Präzise Ergebnisse | Mittel | Mittel |

## Conversion / Normalization
| Feature | Ziel | Nutzerwert | Risiko | Komplexität |
| --- | --- | --- | --- | --- |
| Plattform-Format-Registry v1 | Formate & Regeln zentral | Konsistenz | Niedrig | Mittel |
| Track-Set Validator (cue/gdi) | Vollständigkeit prüfen | Weniger defekte Sets | Niedrig | Mittel |
| Folder-Set Validator (PS3 etc.) | Komplettheitschecks | Qualität & Sicherheit | Mittel | Hoch |
| Pro-Plattform Output Targets | Zielprofile (CHD/RVZ/etc.) | Flexible Workflows | Mittel | Mittel |

## IGIR
| Feature | Ziel | Nutzerwert | Risiko | Komplexität |
| --- | --- | --- | --- | --- |
| Plan/Diff/Execute Flow | Safety diff vor Ausführung | Höhere Sicherheit | Mittel | Mittel |
| Profile pro Plattform | Args-Templates je Kategorie | Power-User Effizienz | Niedrig | Mittel |
| Rollback-Strategie | Copy-first oder Copy-only | Fehlerprävention | Niedrig | Mittel |
| Report-Viewer | Filter/Export der Ergebnisse | Transparenz | Niedrig | Mittel |

## GUI / UX
| Feature | Ziel | Nutzerwert | Risiko | Komplexität |
| --- | --- | --- | --- | --- |
| Job-Queue (Pause/Resume) | Mehrere Tasks sequenziell | Stabilere Abläufe | Mittel | Hoch |
| Log-Viewer mit Filtern | Schnelles Debugging | Besseres Troubleshooting | Niedrig | Mittel |
| Presets + Bulk-Actions | Wiederholbare Flows | Zeitersparnis | Niedrig | Mittel |
| Tk-Minimalparität | Kernflows stabil | Fallback nutzbar | Niedrig | Mittel |

## DB / Daten
| Feature | Ziel | Nutzerwert | Risiko | Komplexität |
| --- | --- | --- | --- | --- |
| Hash-Cache (path+mtime+size) | Wiederholte Scans beschleunigen | Performance | Niedrig | Mittel |
| Index-Sharding (optional) | Skalierung bei sehr großen Sets | Performance | Hoch | Hoch |
| Library-Reports | Bestandsanalyse | Transparenz | Niedrig | Mittel |

## Performance
| Feature | Ziel | Nutzerwert | Risiko | Komplexität |
| --- | --- | --- | --- | --- |
| IO-aware Hashing | IO-Engpässe vermeiden | Stabilität | Mittel | Mittel |
| SQLite-Tuning | Indexing schneller | Performance | Niedrig | Mittel |
| Bench/Profiling Tools | Bottlenecks sichtbar | Wartbarkeit | Niedrig | Mittel |

## Qualität & Maintainability
| Feature | Ziel | Nutzerwert | Risiko | Komplexität |
| --- | --- | --- | --- | --- |
| Golden Fixtures | Regressionen verhindern | Stabilität | Niedrig | Mittel |
| Mutation-Tests (kritisch) | Testqualität erhöhen | Sicherheit | Mittel | Hoch |
| Strukturierte Logs (JSON) | Bessere Debuggability | Mittel | Mittel |

## Integrationen
| Feature | Ziel | Nutzerwert | Risiko | Komplexität |
| --- | --- | --- | --- | --- |
| Rebuilder-Mode | Sichere Rebuilds | Datenqualität | Mittel | Hoch |
| Frontend-Exporte | ES/LaunchBox Mapping | Komfort | Mittel | Mittel |
| Plugin-System (später) | Erweiterbarkeit | Flexibilität | Hoch | Hoch |
