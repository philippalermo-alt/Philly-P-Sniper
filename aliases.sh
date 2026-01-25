alias sniper='ssh -i secrets/philly_key.pem ubuntu@100.48.72.44'
alias sniper_deploy='bash deploy_fast.sh'
alias deploy_full='bash deploy_aws.sh'
alias run_sniper_aws='sniper "cd Philly-P-Sniper && sudo docker-compose exec api python3 hard_rock_model.py"'
alias sniper_logs='sniper "cd Philly-P-Sniper && sudo docker-compose logs -f api"'
alias run_ncaab_1h='sniper "cd Philly-P-Sniper && sudo docker-compose exec api python3 ncaab_h1_model/ncaab_h1_edge_finder.py"'
alias run_ncaab_loose='sniper "cd Philly-P-Sniper && sudo docker-compose exec -T api env NCAAB_MIN_EDGE=0.03 NCAAB_MIN_CONF=65 python3 ncaab_h1_model/ncaab_h1_edge_finder.py"'
alias run_soccer_v6='sniper "cd Philly-P-Sniper && sudo docker-compose exec api python3 soccer_sniper.py"'
alias run_soccer_v5='sniper "cd Philly-P-Sniper && sudo docker-compose exec api python3 soccer_sentinel.py"'
# New Isolated Deployment Shortcut
alias deploy_stream='bash deploy_streamlit_isolated.sh'

# Soccer Props Shortcuts
alias run_soccer_props='sniper "cd Philly-P-Sniper && sudo docker-compose exec -T api python3 prop_sniper.py"'
alias run_soccer_props_diag='sniper "cd Philly-P-Sniper && sudo docker-compose exec -T api env DIAGNOSTIC_MODE=true python3 prop_sniper.py"'
