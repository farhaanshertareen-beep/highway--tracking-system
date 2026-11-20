# Balochistan Smart Highway & Weather Intelligence System (Hardened Edition)

## Key Hardening & Improvements
- **Password Security**: Uses salted `PBKDF2-HMAC-SHA256` (120,000 iterations) with constant-time comparison and automatic upgrade of legacy hashes.
- **Input Validation & Data Integrity**: Validates usernames, Pakistani mobile numbers, vehicle plate numbers, and prevents duplicate driver pass IDs or empty directives.
- **Map & Telemetry Resilience**: Escapes embedded JSON payloads (`</`), includes automatic OpenStreetMap tile fallback if Carto fails, updates the active HUD readout when clicking any marker, and safely handles `None`/offline weather fields.
- **Database Stability**: Uses WAL mode, foreign keys, `UNIQUE` constraints, and single-run initialization per session.
