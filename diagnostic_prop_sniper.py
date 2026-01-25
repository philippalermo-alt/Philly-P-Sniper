from prop_sniper import PropSniper
import pandas as pd
from utils import log

class DiagnosticSniper(PropSniper):
    def __init__(self):
        super().__init__()
        self.min_edge = -10.0 # Capture EVERYTHING
        self.found_props = []

    def log_opportunity(self, league, player, matchup, market, selection, price, edge, book, model_prob):
        # Override to NOT write to DB, just store in memory
        self.found_props.append({
            "League": league,
            "Player": player,
            "Matchup": matchup,
            "Market": market,
            "BookPrice": price,
            "ModelProb": f"{model_prob:.1f}%",
            "ImpliedProb": f"{(100/(price+100) if price>0 else abs(price)/(abs(price)+100))*100:.1f}%",
            "Edge": edge,
            "Book": book
        })
        # Optional: Print real-time so we see progress
        # print(f"   👉 {player}: Edge {edge*100:.1f}%")

    def print_report(self):
        if not self.found_props:
            print("\n❌ No props found. Check API quota or schedule.")
            return

        df = pd.DataFrame(self.found_props)
        df_sorted = df.sort_values("Edge", ascending=False)
        
        print(f"\n📊 DIAGNOSTIC REPORT: Found {len(df)} Props")
        print("🔝 TOP 10 HIGHEST EDGES (Independent of Threshold):")
        print("-" * 60)
        # Format for display
        print(df_sorted[['Player', 'Matchup', 'BookPrice', 'ModelProb', 'Edge']].head(15).to_string(index=False))
        print("-" * 60)
        print("📉 BOTTOM 5 (Worst Edges):")
        print(df_sorted[['Player', 'Matchup', 'BookPrice', 'ModelProb', 'Edge']].tail(5).to_string(index=False))

if __name__ == "__main__":
    print("🚀 Starting Diagnostic Sniper (No Filters)...")
    diag = DiagnosticSniper()
    diag.run()
    diag.print_report()
