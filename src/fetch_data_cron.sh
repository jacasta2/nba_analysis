#!/bin/bash
function fetch_data {
  cd /mnt/c/Users/USER/DS_Projects/nba_analysis/src
}
fetch_data
source /home/jacasta2/.cache/pypoetry/virtualenvs/nba-analysis-QLTyKPT2-py3.10/bin/activate /home/jacasta2/.cache/pypoetry/virtualenvs/nba-analysis-QLTyKPT2-py3.10
/home/jacasta2/.local/bin/poetry run python /mnt/c/Users/USER/DS_Projects/nba_analysis/src/fetch_data_cron.py