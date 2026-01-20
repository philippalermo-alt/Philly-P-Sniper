from models.base_model import BaseModel

class NBA_Model(BaseModel):
    def __init__(self):
        features = [
            'implied_prob', 'true_prob', 'ticket_pct', 
            'minutes_to_kickoff', 'dvp_rank'
        ]
        super().__init__('nba', features, 'models/nba_model.pkl')

class Soccer_Model(BaseModel):
    def __init__(self):
        features = [
            'implied_prob', 'true_prob', 'ticket_pct', 
            'minutes_to_kickoff', 'xg_diff'
        ]
        super().__init__('soccer', features, 'models/soccer_model.pkl')
    
    def load_data(self):
        df = super().load_data()
        if not df.empty:
            df['xg_diff'] = df['home_xg'] - df['away_xg']
        return df

class NCAAB_Model(BaseModel):
    def __init__(self):
        features = [
            'implied_prob', 'true_prob', 'ticket_pct', 
            'minutes_to_kickoff', 'kenpom_diff'
        ]
        super().__init__('ncaab', features, 'models/ncaab_model.pkl')
    
    def load_data(self):
        df = super().load_data()
        if not df.empty:
            df['kenpom_diff'] = df['home_adj_em'] - df['away_adj_em']
        return df

class Generic_Model(BaseModel):
    def __init__(self, sport_name):
        features = [
            'implied_prob', 'true_prob', 'ticket_pct', 
            'minutes_to_kickoff'
        ]
        super().__init__(sport_name, features, f'models/{sport_name}_model.pkl')
