# Database Schema Source of Truth

**Warning**: This directory contains the **Single Source of Truth (SST)** for the PhillyEdge Database.

## `schema.sql`
- **Purpose**: Defines the authoritative structure of the PostgreSQL database.
- **Origin**: Snapshot taken on 2026-01-25 (Post-Audit).
- **Usage**: Use this file to initialize new environments or verify schema integrity.

## Rules
1. **No Hidden Changes**: All schema modifications (migrations) must be reflected here or in applied migration scripts.
2. **Backup Priority**: In case of total failure, restore from `backups/` but verify against this structure.
