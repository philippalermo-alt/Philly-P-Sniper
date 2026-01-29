# NHL Phase 2 Join Audit & Normalization

## 1. Discrepancy Analysis

| Team | Odds API | MoneyPuck | NHL Reference | Canonical ID (Target) |
|------|----------|-----------|---------------|-----------------------|
| **Montreal** | Montréal Canadiens | MTL | Montreal Canadiens | **MTL** |
| **St. Louis** | St Louis Blues | STL | St. Louis Blues | **STL** |
| **Tampa Bay** | Tampa Bay Lightning | T.B, TBL | Tampa Bay Lightning | **TBL** |
| **Los Angeles** | Los Angeles Kings | L.A, LAK | Los Angeles Kings | **LAK** |
| **New Jersey** | New Jersey Devils | N.J, NJD | New Jersey Devils | **NJD** |
| **San Jose** | San Jose Sharks | S.J, SJS | San Jose Sharks | **SJS** |
| **Vegas** | Vegas Golden Knights | VGK | Vegas Golden Knights | **VGK** |
| **Utah** | Utah Hockey Club | UTA | Utah Mammoth | **UTA** |

*Note: MoneyPuck appears to use legacy abbreviations (T.B, L.A, S.J, N.J) alongside standard ones. We will normalize all to the standard 3-letter code.*

## 2. Mapping Strategy
We will implement a central mapping function `get_canonical_team_id(raw_name)` that resolves all inputs to the **Canonical ID**.

### Canonical IDs (3-Letter Standard)
`ANA, BOS, BUF, CAR, CBJ, CGY, CHI, COL, DAL, DET, EDM, FLA, LAK, MIN, MTL, NJD, NSH, NYI, NYR, OTT, PHI, PIT, SEA, SJS, STL, TBL, TOR, UTA, VAN, VGK, WPG, WSH`

### Mapping Rules
1. **Odds API (Full Names)** -> Map to Canonical ID.
   - Handle "Montréal" (accent).
   - Handle "St Louis" (no dot).
2. **MoneyPuck (Abbr)** -> Map "T.B"->"TBL", "L.A"->"LAK", "S.J"->"SJS", "N.J"->"NJD". Pass others through.
3. **Ref Logs (Full Names)** -> Map "St. Louis" (dot), "Montreal" (no accent).

## 3. Join Keys
The join will use:
- **Game Date** (Corrected to proper Game Day)
- **Home Team Canonical ID**
- **Away Team Canonical ID**

## 4. Edge Case Handling
- **Double Headers/Neutral Sites**: Rare in NHL regular season (Global Series exists, handled by Date+Team).
- **Postponements**: If date shifts, join might fail. Will be flagged in Join Audit.
