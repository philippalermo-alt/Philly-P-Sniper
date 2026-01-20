from models.sport_models import NBA_Model, Soccer_Model, NCAAB_Model, Generic_Model

def main():
    print("🚀 Starting Model V2 Training Pipeline...")

    # 1. NBA
    print("\n🏀 Training NBA Model...")
    nba = NBA_Model()
    nba.train()

    # 2. Soccer
    print("\n⚽ Training Soccer Model...")
    soccer = Soccer_Model()
    soccer.train()
    
    # 3. NCAAB
    print("\n🎓 Training NCAAB Model...")
    ncaab = NCAAB_Model()
    ncaab.train()

    # 4. Others (NHL, NFL)
    other_sports = ['icehockey_nhl', 'americanfootball_nfl']
    for sport in other_sports:
        print(f"\nTraining {sport} Model...")
        model = Generic_Model(sport)
        model.train()

    print("\n✨ Training Complete.")

if __name__ == "__main__":
    main()
