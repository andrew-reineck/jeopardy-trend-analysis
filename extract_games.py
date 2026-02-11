import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import sqlite3 as sql
import random

def scrape_game(game_id):
    url = f"https://www.j-archive.com/showgame.php?game_id={game_id}"
    r = requests.get(url)
    if r.status_code != 200:
        return None
    
    soup = BeautifulSoup(r.text, "html.parser")
    
    # Air date
    air_date_tag = soup.find("title")
    if not air_date_tag:
        return None
    
    # Extract date format from title - "Show #1234, aired 2004-05-12"
    title = air_date_tag.text
    if "aired" not in title or "Show #" not in title:
        return None
    air_date = title.split("aired")[1].strip()
    show_num = int(title.split("Show #")[1].split(",")[0].strip())
    
    # Extract categories (6 Jeopardy + 6 Double + 1 Final)
    category_tags = soup.find_all("td", {"class": "category_name"})
    categories = [c.text.strip() for c in category_tags]
    
    # Structure into records
    records = []
    rounds = ["Jeopardy"]*6 + ["Double Jeopardy"]*6 + ["Final Jeopardy"]*1
    
    for rnd, cat in zip(rounds, categories):
        records.append({
            "game_id": game_id,
            "show_num": show_num,
            "air_date": air_date,
            "round": rnd,
            "category": cat
        })

    return records

def all_games(conn_path, final_file_name):
    conn = sql.connect(conn_path)

all_data = []
for game_id in range(1, 9263):
    game = scrape_game(game_id)
    if game:
        all_data.extend(game)
    print(game_id)
    time.sleep(6*random.random())

df = pd.DataFrame(all_data)
df.sort_values(by="show_num")
# df.to_csv("jeopardy_data.csv")