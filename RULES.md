# Rules for Documentation

## Rule: Document All Successful Scraping Processes
- **When** a scraping job completes successfully (i.e., data is written to the remote database or output file without errors), **immediately** add a detailed entry to the `SCRAPING_OPERATIONS_GUIDE.md` (or a new dedicated guide) describing:
  - The script name and version.
  - The data source and any API/website specifics.
  - Environment configuration (e.g., local Selenium setup, SSH tunnel details, database connection string).
  - Any special flags or parameters used.
  - Performance metrics (duration, records processed, any throttling adjustments).
  - Known pitfalls and how they were resolved.
- **Why**: Guarantees reproducibility, speeds up future debugging, and prevents repeat failures after server restarts.
- **Enforcement**: The assistant will automatically create or update the guide after each successful run.

## Rule: Database Integrity & Connections (STRICT)
- **Host**: `localhost` (Internal Cluster/Docker: `db`)
- **Port**: `5432`
- **User**: `user`
- **Password**: `password`
- **DB Name**: `philly_sniper` (NOT `philly_p_sniper`)
- **Action**: If `Connection refused`, prompt user to start DB; do not assume wrong creds first.

# 🚫 NEGATIVE CONSTRAINTS
- **NO "SNIPER" BRANDING:** The brand is **PhillyEdge** or **PhillyEdge.AI**. Never use the word "Sniper" in user-facing text, alerts, emails, or dashboards.
- AESTHETICS: Use "Emerald Green" and "Gold/Amber" accents.

## Rule: Dashboard Time Invariants (Strict)
- **Always** filter out selections that are past their start time (`kickoff < now`). No exceptions.
- **Never** display opportunities more than 36 hours in the future (`kickoff > now + 36h`).
