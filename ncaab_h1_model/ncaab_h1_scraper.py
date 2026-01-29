"""
NCAAB H1/H2 Data Scraper
Fetches play-by-play data from ESPN to build team first-half profiles.
"""

import requests
import json
import time
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

class NCAAB_H1_Scraper:
    def __init__(self):
        self.base_url = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball"
        self.team_stats = defaultdict(lambda: {
            'h1_scores': [], 'h2_scores': [],
            'h1_possessions': [], 'h2_possessions': [],
            'h1_tempo': [], 'h2_tempo': [],
            'games_played': 0
        })

    def fetch_schedule(self, date_range_days=None, season_start_date=None):
        """
        Fetch games for all teams.

        Args:
            date_range_days: Number of days back from today (if specified)
            season_start_date: Specific start date (YYYY-MM-DD format)
            If both None: defaults to full season starting Nov 1
        """
        games = []
        end_date = datetime.now()

        if season_start_date:
            # Use provided season start date
            start_date = datetime.strptime(season_start_date, '%Y-%m-%d')
        elif date_range_days:
            # Use date range
            start_date = end_date - timedelta(days=date_range_days)
        else:
            # Default: Start of current NCAAB season (November 1st)
            current_year = end_date.year
            # If we're in Jan-July, season started previous year; otherwise this year
            season_year = current_year - 1 if end_date.month <= 7 else current_year
            start_date = datetime(season_year, 11, 1)

        current = start_date
        while current <= end_date:
            date_str = current.strftime('%Y%m%d')
            url = f"{self.base_url}/scoreboard?dates={date_str}&groups=50&limit=1000"

            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()

                    if 'events' in data:
                        for event in data['events']:
                            game_id = event['id']
                            games.append({
                                'id': game_id,
                                'date': date_str,
                                'status': event['status']['type']['state']
                            })

                    print(f"✓ Fetched {date_str}: {len(data.get('events', []))} games")
                else:
                    print(f"✗ Failed {date_str}: HTTP {response.status_code}")

            except Exception as e:
                print(f"✗ Error fetching {date_str}: {e}")

            current += timedelta(days=1)
            time.sleep(0.5)  # Rate limiting

        return games

    def fetch_game_details(self, game_id, game_date=None):
        """Fetch detailed stats including H1/H2 splits for a specific game."""
        url = f"{self.base_url}/summary?event={game_id}"

        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                return None

            data = response.json()

            # Extract from header -> competitions -> competitors
            if 'header' not in data or 'competitions' not in data['header']:
                return None

            competitions = data['header']['competitions']
            if not competitions or 'competitors' not in competitions[0]:
                return None

            competitors = competitions[0]['competitors']
            if len(competitors) != 2:
                return None

            # Determine home/away (homeAway field)
            home_competitor = None
            away_competitor = None

            for comp in competitors:
                if comp.get('homeAway') == 'home':
                    home_competitor = comp
                elif comp.get('homeAway') == 'away':
                    away_competitor = comp

            if not home_competitor or not away_competitor:
                # Fallback: first is home, second is away
                home_competitor = competitors[0]
                away_competitor = competitors[1]

            home_team = home_competitor['team']['displayName']
            away_team = away_competitor['team']['displayName']

            # Extract linescores (H1, H2, OT...)
            home_h1, home_h2 = self._extract_half_scores(home_competitor)
            away_h1, away_h2 = self._extract_half_scores(away_competitor)

            if home_h1 is None or away_h1 is None:
                return None

            return {
                'game_id': game_id,
                'date': game_date, # Persist the date
                'home_team': home_team,
                'away_team': away_team,
                'home_h1': home_h1,
                'home_h2': home_h2,
                'home_full': home_h1 + home_h2,
                'away_h1': away_h1,
                'away_h2': away_h2,
                'away_full': away_h1 + away_h2,
                'h1_total': home_h1 + away_h1,
                'h2_total': home_h2 + away_h2,
                'full_total': home_h1 + home_h2 + away_h1 + away_h2
            }

        except Exception as e:
            print(f"Error fetching game {game_id}: {e}")
            return None

    def _extract_half_scores(self, competitor_data):
        """Extract H1 and H2 scores from competitor linescore."""
        # Get from linescores array
        if 'linescores' not in competitor_data:
            return None, None

        linescores = competitor_data['linescores']

        # NCAAB has 2 halves minimum
        if len(linescores) < 2:
            return None, None

        # H1 is first period
        h1_str = linescores[0].get('displayValue', linescores[0].get('value', '0'))
        h1 = int(h1_str)

        # H2 is sum of all remaining periods (handles OT)
        h2 = 0
        for ls in linescores[1:]:
            h2_str = ls.get('displayValue', ls.get('value', '0'))
            h2 += int(h2_str)

        return h1, h2

    def build_team_profiles(self, games_data):
        """Build H1/H2 statistical profiles for each team."""
        for game in games_data:
            if game is None:
                continue

            home = game['home_team']
            away = game['away_team']

            # Home team H1/H2 stats
            self.team_stats[home]['h1_scores'].append(game['home_h1'])
            self.team_stats[home]['h2_scores'].append(game['home_h2'])
            self.team_stats[home]['games_played'] += 1

            # Away team H1/H2 stats
            self.team_stats[away]['h1_scores'].append(game['away_h1'])
            self.team_stats[away]['h2_scores'].append(game['away_h2'])
            self.team_stats[away]['games_played'] += 1

        # Calculate averages and ratios
        profiles = {}
        for team, stats in self.team_stats.items():
            if stats['games_played'] < 3:  # Minimum sample size (reduced from 5 for faster testing)
                continue

            h1_avg = statistics.mean(stats['h1_scores'])
            h2_avg = statistics.mean(stats['h2_scores'])
            full_avg = h1_avg + h2_avg

            profiles[team] = {
                'games_played': stats['games_played'],
                'h1_avg_score': round(h1_avg, 2),
                'h2_avg_score': round(h2_avg, 2),
                'full_avg_score': round(full_avg, 2),
                'h1_ratio': round(h1_avg / full_avg, 3) if full_avg > 0 else 0.500,
                'h2_ratio': round(h2_avg / full_avg, 3) if full_avg > 0 else 0.500,
                'h1_std': round(statistics.stdev(stats['h1_scores']), 2) if len(stats['h1_scores']) > 1 else 0,
                'h2_std': round(statistics.stdev(stats['h2_scores']), 2) if len(stats['h2_scores']) > 1 else 0,
                'consistency_score': self._calculate_consistency(stats['h1_scores'], stats['h2_scores'])
            }

        return profiles

    def _calculate_consistency(self, h1_scores, h2_scores):
        """
        Calculate how consistent a team's H1/H2 split is.
        Lower variance = more predictable.
        """
        if len(h1_scores) < 2:
            return 0

        ratios = []
        for h1, h2 in zip(h1_scores, h2_scores):
            full = h1 + h2
            if full > 0:
                ratios.append(h1 / full)

        if len(ratios) < 2:
            return 0

        # Lower std = more consistent
        std = statistics.stdev(ratios)
        # Normalize to 0-100 scale (lower std = higher score)
        consistency = max(0, 100 - (std * 200))

        return round(consistency, 2)

    def run(self, save_path='data/'):
        """Full pipeline: fetch games, build profiles, save."""
        print("🏀 Starting NCAAB H1/H2 Data Collection...")
        print("=" * 60)

        # Step 1: Fetch entire season schedule
        print("\n1️⃣ Fetching schedule (entire season since Nov 1)...")
        games = self.fetch_schedule()  # Defaults to full season
        completed_games = [g for g in games if g['status'] == 'post']
        print(f"   Found {len(completed_games)} completed games this season")

        # Step 2: Fetch game details for ALL completed games
        print("\n2️⃣ Fetching game details for all games...")
        print(f"   This will take approximately {len(completed_games) * 0.15 / 60:.0f}-{len(completed_games) * 0.15 / 60 + 5:.0f} minutes")
        games_data = []

        for i, game in enumerate(completed_games, 1):
            if i % 100 == 0 or i == len(completed_games):
                print(f"   Progress: {i}/{len(completed_games)} ({i/len(completed_games)*100:.1f}%)")

            # Pass the date!
            game_details = self.fetch_game_details(game['id'], game['date'])
            if game_details:
                games_data.append(game_details)

            time.sleep(0.15)  # Rate limiting (0.15s = ~400 games/min)

        print(f"   ✓ Successfully fetched {len(games_data)} games with H1/H2 data")

        # Step 3: Build team profiles
        print("\n3️⃣ Building team H1/H2 profiles...")
        profiles = self.build_team_profiles(games_data)
        print(f"   ✓ Built profiles for {len(profiles)} teams")

        # Step 4: Save data
        print("\n4️⃣ Saving data...")
        import os
        os.makedirs(save_path, exist_ok=True)

        with open(f'{save_path}team_h1_profiles.json', 'w') as f:
            json.dump(profiles, f, indent=2)

        with open(f'{save_path}historical_games.json', 'w') as f:
            json.dump(games_data, f, indent=2)

        print(f"   ✓ Saved to {save_path}")

        # Step 5: Summary stats
        print("\n" + "=" * 60)
        print("📊 SUMMARY STATISTICS")
        print("=" * 60)

        # Find teams with most extreme H1 ratios
        sorted_teams = sorted(profiles.items(), key=lambda x: x[1]['h1_ratio'], reverse=True)

        print("\n🚀 Top 5 FAST STARTERS (High H1 ratio):")
        for team, stats in sorted_teams[:5]:
            print(f"   {team:30s} | H1: {stats['h1_ratio']:.1%} | Avg H1: {stats['h1_avg_score']:.1f}")

        print("\n🐌 Top 5 SLOW STARTERS (Low H1 ratio):")
        for team, stats in sorted_teams[-5:]:
            print(f"   {team:30s} | H1: {stats['h1_ratio']:.1%} | Avg H1: {stats['h1_avg_score']:.1f}")

        print("\n✅ Data collection complete!")

        return profiles, games

if __name__ == "__main__":
    scraper = NCAAB_H1_Scraper()
    profiles, games = scraper.run()
