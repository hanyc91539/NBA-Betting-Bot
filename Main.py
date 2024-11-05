from selenium import webdriver
from selenium.common.exceptions import *
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from datetime import datetime
from unidecode import unidecode
from threading import Thread
import requests
from time import sleep
import json

USER = 'manadr'
SECRET = '2b090e1f62fd593a1676acff0445d108'
USERNAME = 'nathansiaw@gmail.com'
PASSWORD = 'fr0zenrain'

TRIGGER = {
    "Rain": {"id" : 0, "odd" : "under"},
    "Better Rain": {"id" : 1, "odd" : "under"},
    "Drought": {"id" : 2, "odd" : "over"},
    "Better Drought": {"id" : 3, "odd" : "over"}
}

FILTER_MARKET = {
    "1" : {"filter" : "Quarters", "market" : "1st Quarter - Total"},
    "2" : {"filter" : "Half"    , "market" : "1st Half - Asian Total"},
    "3" : {"filter" : "Quarters", "market" : "3rd Quarter - Total"},
    "4" : {"filter" : "Quarters", "market" : "4th Quarter - Total"}
}

LIVE_SCRAPING_URLS = [
    "https://stake.ac/sports/live/basketball",
    "https://stake.ac/sports/basketball/usa/ncaa-regular"
]

LIMIT_TIME_QUARTER_TOTAL = 240
LIMIT_TIME_QUARTER_ML = 120
LIMIT_PING = 2
EMPTY = '--@--'

QUARTER_TOTAL = "QuarterTotal"
HALFTIME = "Halftime"
QUARTER_ML = "QuarterML"

is_scrapping_now = False
Odds_QuarterML = {}

service = Service(executable_path="C:\chromedriver-win64\chromedriver.exe")   
options = Options()
options.add_experimental_option("debuggerAddress", "127.0.0.1:9015")
options.add_argument("user-agent=Chrome/120.0.6099.200")
driver = webdriver.Chrome(service=service, options=options)

def scrap_odds(url, filter_name, market_title):
    global is_scrapping_now
    is_scrapping_now = True
    result = {"over" : EMPTY, "under" : EMPTY, "home" : 0.0, "away" : 0.0}

    driver.get(url)
    is_ok = False
    timeout = 0.0
    while not is_ok:
        menus = driver.find_elements(By.CLASS_NAME, 'variant-tabmenu')
        for menu in menus:
            if menu.text == filter_name:
                driver.execute_script("arguments[0].click();", menu)
                is_ok = True
                break
        if menus:
            timeout += 0.1
            if timeout > 5:
                break
        sleep(0.1)
    timeout = 0.0
    while is_ok:
        markets = driver.find_elements(By.CLASS_NAME, 'secondary-accordion')
        for market in markets:
            try:
                title = market.find_element(By.CLASS_NAME, 'weight-semibold').text
                odds = market.find_elements(By.CLASS_NAME, 'outcome')
                if title == market_title:
                    if "Quarter - 1x2" in market_title:
                        result["home"] = odds[0].text.split("\n")[-1]
                        result["away"] = odds[2].text.split("\n")[-1]
                    else:
                        result["over"] = odds[0].text.replace("\n", "@")
                        result["under"] = odds[1].text.replace("\n", "@")
                    break
            except:
                pass
        if markets:
            timeout += 0.1
            if timeout > 5:
                break
        if ("Quarter - 1x2" in market_title and result["home"] != 0.0) or ("Quarter - 1x2" not in market_title and result["over"] != EMPTY):
            break
        sleep(0.1)
    is_scrapping_now = False
    driver.get("https://stake.ac/sports/live/basketball")

    return result

def scrap_odds_for_QuarterML():
    global Odds_QuarterML
    while True:
        if driver.current_url == "https://stake.ac/sports/live/basketball":
            odds_to_name_map = {}
            match_elements = driver.find_elements(By.CLASS_NAME, 'fixture-preview')
            for match_element in match_elements:
                try:
                    teams = match_element.find_element(By.CLASS_NAME, 'teams').text.split('\n')
                    home_team, away_team = teams[0], teams[1]

                    live_odds = match_element.find_elements(By.CLASS_NAME, 'weight-bold')
                    underdog = "xxxx"
                    try:
                        odds_home, odds_away = float(live_odds[0].text), float(live_odds[1].text)
                        if odds_home > odds_away:
                            underdog = "home"
                        if odds_home < odds_away:
                            underdog = "away"
                    except:
                        pass
                    odds_to_name_map[f'{home_team} vs {away_team}'] = underdog
                    # print(f'{datetime.now().strftime("%H:%M:%S")} {" ".ljust(10)} [{home_team.center(30)}] vs [{away_team.center(30)}], underdog: {underdog}({odds_home}, {odds_away})\n')
                except:
                    pass
            if odds_to_name_map:
                Odds_QuarterML = odds_to_name_map
        sleep(0.1)

def fetch_live(schedules):
    print('-'*50, 'fetching live'.center(50), '-'*50, '\n')
    live_matchs = {}

    timecount = 0
    driver.get("https://stake.ac/sports/live/basketball")
    while schedules[QUARTER_TOTAL] or schedules[HALFTIME] or schedules[QUARTER_ML]:
        if schedules[QUARTER_ML]: # This includes schedules[QUARTER_TOTAL]
            response = requests.get('https://api.thesports.com/v1/basketball/match/detail_live', params={"user":USER, "secret":SECRET})        
            if response.status_code == 200:
                results = response.json().get('results')
                updates = [obj for obj in results for key, element in schedules[QUARTER_ML].items() if key == obj["id"]]
                for update in updates:
                    id = update["id"]
                    updated_remain = update["timer"][3]
                    scores = {"home" : update["score"][3], "away" : update["score"][4]}

                    match = schedules[QUARTER_ML][id]
                    match_league = match["league"]
                    scrap_url = match["url"]

                    print_league_teams = f'{match_league["short_name"].ljust(10)} [{match["home"].center(30)}] vs [{match["away"].center(30)}]'

                    q_no_api = sum(1 for x, y in zip(scores["home"], scores["away"]) if x + y > 0)
                    q_no = max(match["q_no"], q_no_api)
                    schedules[QUARTER_ML][id]["q_no"] = q_no

                    curr_quarter_home_score = scores["home"][q_no - 1]
                    curr_quarter_away_score = scores["away"][q_no - 1]
                    diff_scores = curr_quarter_home_score - curr_quarter_away_score
                    q_ml_match_data = match[str(q_no)]
                    if q_no <= match_league["round"]:
                        if updated_remain >= LIMIT_TIME_QUARTER_ML:
                            if q_ml_match_data["status"]:
                                if q_ml_match_data["ping"] == 0:
                                    criteria = match_league[QUARTER_ML]["score"]
                                    underdog = q_ml_match_data["underdog"]
                                    if (underdog == "home" and diff_scores >= criteria) or (underdog == "away" and -diff_scores >= criteria):
                                        quarters = ["1st", "2nd", "3rd", "4th"]
                                        scrap_result = scrap_odds(scrap_url, "Quarters", f"{quarters[q_no - 1]} Quarter - 1x2")
                                        message = {
                                            "league" : match_league["name"],
                                            "short_name" : match_league["short_name"],
                                            "time" : match_league["time"],
                                            "q_no" : q_no,
                                            "remain" : updated_remain,
                                            "home" : match["home"],
                                            "away" : match["away"],
                                            "url" : scrap_url,
                                            "odds" : scrap_result[underdog],
                                            "underdog" : match[underdog],
                                            "scores" : f"{sum(scores['home'])}:{sum(scores['away'])}",
                                            "algorithm" : QUARTER_ML
                                            }
                                        with open('json files/message_to_be_pinged.json', 'w') as file:
                                            json.dump(message, file)
                                        schedules[QUARTER_ML][id][str(q_no)]["ping"] = 1
                                        if q_no == match_league["round"]:
                                            schedules[QUARTER_ML][id]["q_no"] = q_no + 1
                            else:
                                key = f'{match["home"]} vs {match["away"]}'
                                if key in Odds_QuarterML: # match_league["time"] * 60
                                    schedules[QUARTER_ML][id][str(q_no)]["status"] = True
                                    underdog = Odds_QuarterML[key]
                                    if underdog == "xxxx":                                    
                                        if sum(scores["home"]) > sum(scores["away"]):
                                            underdog = "away"
                                        elif sum(scores["home"]) < sum(scores["away"]):
                                            underdog = "home"
                                        else:
                                            pass
                                    schedules[QUARTER_ML][id][str(q_no)]["underdog"] = underdog
                            print_out = f'{print_league_teams} : Q{q_no}, underdog-{q_ml_match_data["underdog"]}, Ping {q_ml_match_data["ping"]}, scores {curr_quarter_home_score}:{curr_quarter_away_score}, {updated_remain} remains'
                            print(f'{datetime.now().strftime("%H:%M:%S")} {print_out}', '\n')
                        else:
                            if q_ml_match_data["status"]:
                                schedules[QUARTER_ML][id]["q_no"] = q_no + 1
                                print(f'{datetime.now().strftime("%H:%M:%S")} {print_league_teams} : Moved To Q{q_no + 1} - {QUARTER_ML}', '\n')
                    else:
                        del schedules[QUARTER_ML][id]
                        print(f'{datetime.now().strftime("%H:%M:%S")} {print_league_teams} : Deleted - {QUARTER_ML}', '\n')

                    if id in schedules[QUARTER_TOTAL]:
                        match = schedules[QUARTER_TOTAL][id]
                        q_no = max(match["q_no"], q_no_api)
                        schedules[QUARTER_TOTAL][id]["q_no"] = q_no

                        updated_scores = sum(scores["home"]) + sum(scores["away"])

                        if q_no_api == 0 and match["1"]["over"] == EMPTY and match["start"] - int(datetime.now().timestamp()) < 60:
                            while is_scrapping_now:
                                sleep(0.1)
                            result = scrap_odds(scrap_url, FILTER_MARKET["1"]["filter"], FILTER_MARKET["1"]["market"])
                            schedules[QUARTER_TOTAL][id]["1"]["over"] = result["over"]
                            schedules[QUARTER_TOTAL][id]["1"]["under"] = result["under"]
                            print_out = f'{print_league_teams} : over {result["over"]} | under {result["under"]}'
                            print(f'{datetime.now().strftime("%H:%M:%S")} {print_out}', FILTER_MARKET["1"]["market"], '\n')
                            
                        output = f'updated time: {updated_remain}'

                        if q_no < match_league["round"] or (match_league["short_name"] == "CBA" and q_no == match_league["round"]):                    
                            if updated_remain > LIMIT_TIME_QUARTER_TOTAL:
                                remain_last = -1
                                if id not in live_matchs:
                                    live_matchs[id] = []
                                if live_matchs[id]:
                                    remain_last = live_matchs[id][-1]["remain"]
                                if updated_remain != remain_last:
                                    live_matchs[id].append({"scores" : updated_scores, "remain" : updated_remain})

                                    while len(live_matchs[id]) > 100:
                                        del live_matchs[id][0]
                                    
                                    result = "Don't Trigger"
                                    if abs(sum(scores["home"]) - sum(scores["away"])) < 30:
                                        for data in live_matchs[id]:
                                            if data["remain"] - updated_remain <= 50:
                                                diff = updated_scores - data["scores"]
                                                if diff >= match_league[QUARTER_TOTAL][str(q_no)]["rain"] and schedules[QUARTER_TOTAL][id]["trigger"] != "Rain":
                                                    result = 'Rain'
                                                if diff >= match_league[QUARTER_TOTAL][str(q_no)]["rain better"] and schedules[QUARTER_TOTAL][id]["trigger"] != "Better Rain":
                                                    result = 'Better Rain'
                                        if result == "Don't Trigger":
                                            length = len(live_matchs[id])
                                            for index in range(length, 0, -1):
                                                data = live_matchs[id][index-1]
                                                diff = updated_scores - data["scores"]
                                                time_interval = data["remain"] - updated_remain
                                                time_drought = match_league[QUARTER_TOTAL][str(q_no)]["drought"]
                                                time_better_dought = match_league[QUARTER_TOTAL][str(q_no)]["drought better"]
                                                if time_interval >= time_drought and time_interval < time_better_dought and diff <= 1 and schedules[QUARTER_TOTAL][id]["trigger"] != "Drought":
                                                    result = 'Drought'
                                                if time_interval >= time_better_dought and diff <= 1 and schedules[QUARTER_TOTAL][id]["trigger"] != "Better Drought":
                                                    result = 'Better Drought'

                                    if result != "Don't Trigger":
                                        schedules[QUARTER_TOTAL][id]["trigger"] = result
                                        if "Rain" in result:
                                            type = "ping_rain"
                                        if "Drought" in result:
                                            type = "ping_drought"
                                        if match[f'{q_no}'][type] < LIMIT_PING:
                                            if match[f'{q_no + 1}']['over'] == EMPTY:
                                                while is_scrapping_now:
                                                    sleep(0.1)
                                                scrap_result = scrap_odds(scrap_url, FILTER_MARKET[str(q_no)]["filter"], FILTER_MARKET[str(q_no)]["market"])
                                                print_out = f'{print_league_teams} : over {scrap_result["over"]} | under {scrap_result["under"]}'
                                                print(f'{datetime.now().strftime("%H:%M:%S")} {print_out}', FILTER_MARKET[str(q_no)]["market"], '\n')
                                                live = scrap_result[TRIGGER[result]["odd"]]
                                                prematch = match[f'{q_no}'][TRIGGER[result]["odd"]]

                                                emoji = ""
                                                if live != EMPTY:
                                                    if  prematch != EMPTY:
                                                        if "Rain" in result and float(live.split('@')[0]) < float(prematch.split('@')[0]):
                                                            emoji = "⛔⛔⛔"
                                                        if "Drought" in result and float(live.split('@')[0]) > float(prematch.split('@')[0]):    
                                                            emoji = "⛔⛔⛔"
                                                    else:
                                                        live_line = float(live.split('@')[0])
                                                        live_odds = live.split('@')[1]
                                                        if "Rain" in result:
                                                            live_line -= 1
                                                        if "Drought" in result:
                                                            live_line += 1 
                                                        try:
                                                            live_odds = float(live.split('@')[1])
                                                            if "Rain" in result:
                                                                live_odds -= 0.5
                                                            if "Drought" in result:
                                                                live_odds += 0.5
                                                        except:
                                                            pass
                                                        prematch = f"{live_line}@{live_odds}"
                                                        schedules[QUARTER_TOTAL][id][f'{q_no}'][TRIGGER[result]["odd"]] = prematch
                                                else:
                                                    emoji = "⛔⛔⛔"

                                                message = {
                                                    "league" : match_league["name"],
                                                    "short_name" : match_league["short_name"],
                                                    "time" : match_league["time"],
                                                    "id" : TRIGGER[result]["id"],
                                                    "q_no" : q_no,
                                                    "title" : FILTER_MARKET[str(q_no)]["market"],
                                                    "remain" : updated_remain,
                                                    "home" : match["home"],
                                                    "away" : match["away"],
                                                    "prematch" : prematch,
                                                    "live" : live,
                                                    "url" : scrap_url,
                                                    "emoji" : emoji,
                                                    "algorithm" : QUARTER_TOTAL
                                                    }
                                                with open('json files/message_to_be_pinged.json', 'w') as file:
                                                    json.dump(message, file)
                                                schedules[QUARTER_TOTAL][id][f'{q_no}'][type] += 1

                                    seconds = 60 * match_league["time"] * q_no - updated_remain
                                    game_time = f'{str(int(seconds / 60)).zfill(2)}:{str(int(seconds % 60)).zfill(2)}'
                                    curr_prematch = f'Q{q_no}({(match[str(q_no)]["over"]).center(9)}, {(match[str(q_no)]["under"]).center(9)})'
                                    next_prematch = f'Q{q_no + 1}({(match[f"{q_no + 1}"]["over"]).center(9)}, {(match[f"{q_no + 1}"]["under"]).center(9)})'
                                    ping_rain = schedules[QUARTER_TOTAL][id][str(q_no)]["ping_rain"]
                                    ping_drought = schedules[QUARTER_TOTAL][id][str(q_no)]["ping_drought"]
                                    output = f'rain: {ping_rain}, drought: {ping_drought}, {result}\n\n{" "*92}{curr_prematch}, {next_prematch}, Time {game_time}'                                                                                                                        
                                else:
                                    output = f'remain equal({updated_remain})'    
                            else:
                                if q_no == q_no_api:
                                    if schedules[QUARTER_TOTAL][id][str(q_no)]["timeout_count"] >= 5:
                                        if updated_remain < 10 or (match_league["short_name"] == "CBA" and q_no == 4) or (match_league["short_name"] != "CBA" and q_no == 3):
                                            schedules[QUARTER_TOTAL][id]["q_no"] = q_no + 1

                                        if id not in live_matchs or live_matchs[id]:
                                            live_matchs[id] = []
                                            schedules[QUARTER_TOTAL][id]["trigger"] = "Don't Trigger"

                                        if updated_remain < 60 and match[f"{q_no + 1}"]["over"] == EMPTY:
                                            while is_scrapping_now:
                                                sleep(0.1)
                                            result = scrap_odds(scrap_url, FILTER_MARKET[f"{q_no + 1}"]["filter"], FILTER_MARKET[f"{q_no + 1}"]["market"])
                                            print_out = f'{print_league_teams} : over {result["over"]} | under {result["under"]}'
                                            print(f'{datetime.now().strftime("%H:%M:%S")} {print_out}', FILTER_MARKET[f"{q_no + 1}"]["market"], '\n')
                                            schedules[QUARTER_TOTAL][id][f"{q_no + 1}"]["over"] = result["over"]
                                            schedules[QUARTER_TOTAL][id][f"{q_no + 1}"]["under"] = result["under"]
                                    else:
                                        schedules[QUARTER_TOTAL][id][str(q_no)]["timeout_count"] += 1
                                output = f'Time Exceed({updated_remain})'
                        else:
                            if id in schedules[QUARTER_TOTAL]:
                                del schedules[QUARTER_TOTAL][id]
                                print(f'{datetime.now().strftime("%H:%M:%S")} {print_league_teams} : Deleted - {QUARTER_TOTAL}', '\n')
                            if id in live_matchs:
                                del live_matchs[id]
                            output = 'Ended'
                        print(f'{datetime.now().strftime("%H:%M:%S")} {print_league_teams} : Q{q_no}, {output}\n')
                    
        if schedules[HALFTIME]:
            timecount += 1
            if timecount % 150 == 0:
                dest_url = LIVE_SCRAPING_URLS[0] # int(timecount / 150)%2
                if driver.current_url != dest_url:
                    driver.get(dest_url)
                if timecount == 300:
                    timecount = 0

                print('-'*50, f'{datetime.now().strftime("%H:%M:%S")} Halftime Schedule({len(schedules[HALFTIME])})'.center(50), '-'*50, '\n')
                match_elements = []
                while not match_elements:
                    try:
                        empty = driver.find_element(By.ID, 'main-content').find_element(By.CLASS_NAME, 'sports-empty-list').text
                        match_elements.append(empty)
                    except:
                        pass
                    
                    # buttons = driver.find_elements(By.CLASS_NAME, 'x-flex-start')
                    # if len(buttons) == 2:
                    #     load_more = buttons[1].find_element(By.TAG_NAME, 'button')
                    #     print(load_more.text, "clicked")
                    #     driver.execute_script("arguments[0].click();", load_more)
                    #     sleep(0.5)
                    # if len(buttons) == 1:
                    match_elements = driver.find_elements(By.CLASS_NAME, 'fixture-preview')
                    for index, match_element in enumerate(match_elements):
                        try:
                            teams = match_element.find_element(By.CLASS_NAME, 'teams').text.split('\n')
                            home_team, away_team = teams[0], teams[1]
                            if f"{home_team} vs {away_team}" in schedules[HALFTIME]:
                                message = schedules[HALFTIME][f"{home_team} vs {away_team}"]
                                favourite_team = message["favourite"]
                                criteria_score = message["criteria"]
                                quarter = match_element.find_element(By.CLASS_NAME, 'fixture-details').text.replace('\n', ' ')
                                if "Second Break" in quarter or "Halftime" in quarter:
                                    temp = match_element.find_elements(By.CLASS_NAME, "weight-semibold")
                                    scores_home, scores_away = int(temp[0].text), int(temp[1].text)
                                    live_odds = match_element.find_elements(By.CLASS_NAME, 'weight-bold')
                                    print_league_teams = f'{" ".ljust(10)} [{home_team.center(30)}] vs [{away_team.center(30)}]'
                                    if favourite_team == "home" and scores_away - scores_home >= criteria_score:
                                        try:
                                            message["live"] = float(live_odds[0].text)
                                            message["scores"] = f"{scores_home}:{scores_away}"
                                            message["algorithm"] = HALFTIME
                                            with open('json files/message_to_be_pinged.json', 'w') as file:
                                                json.dump(message, file)
                                            del schedules[HALFTIME][f"{home_team} vs {away_team}"]
                                            print(f'{datetime.now().strftime("%H:%M:%S")} {print_league_teams} : Deleted - {HALFTIME}', '\n')
                                        except:
                                            pass
                                    if favourite_team == "away" and scores_home - scores_away >= criteria_score:
                                        try:
                                            message["live"] = float(live_odds[1].text)
                                            message["scores"] = f"{scores_away}:{scores_home}"
                                            message["algorithm"] = HALFTIME
                                            with open('json files/message_to_be_pinged.json', 'w') as file:
                                                json.dump(message, file)
                                            del schedules[HALFTIME][f"{home_team} vs {away_team}"]
                                            print(f'{datetime.now().strftime("%H:%M:%S")} {print_league_teams} : Deleted - {HALFTIME}', '\n')
                                        except:
                                            pass
                        except:
                            pass
                    sleep(0.1)
                if driver.current_url != LIVE_SCRAPING_URLS[0]:
                    driver.get(LIVE_SCRAPING_URLS[0])
        sleep(0.5)
    print('', '-'*50, 'fetching live End'.center(50), '-'*50, '\n')

def fetch_schedule():
    schedules = {
        QUARTER_TOTAL : {},
        HALFTIME : {},
        QUARTER_ML : {}
    }

    rankings = {}
    with open("json files/rankings.json", 'r') as file:
        rankings = json.load(file)

    print('\n')
    response = input("Are you sure you want to receive new ranking data? (y/n) ")
    print('\n')
    if response == "y":
        print('-'*50, 'Scrapping Rankings of NBA '.center(50), '-'*50, '\n')
        team_ranking_to_stake_map = {}
        with open("json files/team_ranking_to_stake_map.json", 'r') as file:
            team_ranking_to_stake_map = json.load(file)
        driver.get("https://www.teamrankings.com/nba/ranking/last-5-games-by-other")
        count = 0
        while True:
            try:
                rows = driver.find_element(By.ID, 'DataTables_Table_0').find_element(By.TAG_NAME, 'tbody').find_elements(By.TAG_NAME, 'tr')
                for row in rows:
                    cols = row.find_elements(By.TAG_NAME, 'td')
                    rank = int(cols[0].text)
                    name = " (".join(cols[1].text.split(" (")[:-1])
                    score = cols[1].text.split(" (")[-1].replace(")", "").split("-")
                    home_win = int(score[0])
                    away_win = int(score[1])
                    if team_ranking_to_stake_map["NBA"][name] == "":
                        count += 1
                        team_ranking_to_stake_map["NBA"][name] = f"{count}"
                    rankings[team_ranking_to_stake_map["NBA"][name]]  = {"ranking" : rank, "win" : home_win >= 2}
                if rows:
                    break
            except:
                pass
            try:
                empty = driver.find_element(By.CLASS_NAME, 'dataTables_empty').text
                break
            except:
                pass
            sleep(0.1)
        
        print('-'*50, 'Scrapping Rankings of NCAA'.center(50), '-'*50, '\n')
        driver.get("https://www.teamrankings.com/ncaa-basketball/ranking/last-5-games-by-other")
        while True:
            try:
                rows = driver.find_element(By.ID, 'DataTables_Table_0').find_element(By.TAG_NAME, 'tbody').find_elements(By.TAG_NAME, 'tr')
                results = {}
                for row in rows:
                    cols = row.find_elements(By.TAG_NAME, 'td')
                    rank = int(cols[0].text)
                    name = " (".join(cols[1].text.split(" (")[:-1])
                    score = cols[1].text.split(" (")[-1].replace(")", "").split("-")
                    home_win = int(score[0])
                    away_win = int(score[1])
                    if team_ranking_to_stake_map["NCAA"][name] == "":
                        count += 1
                        team_ranking_to_stake_map["NCAA"][name] = f"{count}"
                    rankings[team_ranking_to_stake_map["NCAA"][name]]  = {"ranking" : rank, "win" : home_win >= 2}
                if rows:
                    break
            except:
                pass
            try:
                empty = driver.find_element(By.CLASS_NAME, 'dataTables_empty').text
                break
            except:
                pass
            sleep(0.1)
        
        print('-'*50, 'Scrapping Rankings of CBA '.center(50), '-'*50, '\n')
        driver.get("https://www.flashscore.com/basketball/china/cba/standings/#/G2EAP5n6/form/overall/5")
        while True:
            try:
                rows = driver.find_elements(By.CLASS_NAME, 'ui-table__row')
                results = {}
                for row in rows:
                    cols = row.text.split("\n")
                    rank = int(cols[0].replace(".", ""))
                    name = cols[1]
                    home_win = int(cols[3])
                    away_win = int(cols[4])
                    if team_ranking_to_stake_map["CBA"][name] == "":
                        count += 1
                        team_ranking_to_stake_map["CBA"][name] = f"{count}"
                    rankings[team_ranking_to_stake_map["CBA"][name]]  = {"ranking" : rank, "win" : home_win >= 2}
                if rows:
                    break
            except:
                pass
            sleep(0.1)
        
        with open("json files/rankings.json", 'w') as file:
            json.dump(rankings, file)

    response = requests.get('https://api.thesports.com/v1/basketball/match/diary', params={"user":USER,"secret":SECRET,"date":datetime.now().strftime("%Y%m%d")})
    if response.status_code == 200:
        data = response.json()
    team_id_to_name_map = {team['id']: team['name'] for team in data['results_extra']['team']}

    leagues = []
    with open("json files/leagues.json", 'r') as file:
        leagues = json.load(file)
    for league in leagues:
        print('-'*50, league["name"].center(50), '-'*50, '\n')
        driver.get(league['url'])
        sleep(1)
        league_matchs = []
        while True:
            try:
                buttons = driver.find_elements(By.CLASS_NAME, 'x-flex-start')
                if len(buttons) == 2:
                    load_more = buttons[1].find_element(By.TAG_NAME, 'button')
                    driver.execute_script("arguments[0].click();", load_more)
                    sleep(0.5)
                if len(buttons) == 1:
                    match_elements = driver.find_elements(By.CLASS_NAME, 'fixture-preview')
                    for index, match_element in enumerate(match_elements):
                        url = match_element.find_element(By.TAG_NAME, 'a').get_attribute('href')
                        teams = match_element.find_element(By.CLASS_NAME, 'teams').text.split('\n')
                        home_team, away_team = teams[0], teams[1]
                        quarter = match_element.find_element(By.CLASS_NAME, 'fixture-details').text.replace('\n', ' ')
                        odds = match_element.find_elements(By.CLASS_NAME, 'weight-bold')
                        odds_home = 0
                        odds_away = 0
                        try:
                            odds_home = float(odds[0].text)
                        except:
                            pass
                        try:
                            odds_away = float(odds[1].text)
                        except:
                            pass
                        output = ", Favourite : None"
                        if league[HALFTIME]["status"]:
                            if league["short_name"] == "NBA" or league["short_name"] == "NCAA" or league["short_name"] == "CBA":
                                # try:
                                if ":" in quarter or "1st" in quarter or "Start" in quarter or (league["round"] == 4 and ("First Break" in quarter or "2nd" in quarter)): 
                                    ranking_home, ranking_away = 0, 0
                                    try:
                                        ranking_home, ranking_away = rankings[home_team]['ranking'], rankings[away_team]['ranking']
                                    except:
                                        pass
                                    if odds_home <= league[HALFTIME]["odds"] and odds_home < odds_away and ranking_home < ranking_away and rankings[home_team]['win']:
                                        schedules[HALFTIME][f"{home_team} vs {away_team}"] = {
                                            "league" : league["name"],
                                            "short_name" : league["short_name"],
                                            "winner" : home_team,
                                            "prematch" : odds_home,
                                            "live" : 0,
                                            "scores" : "0:0",
                                            "url" : url,
                                            "criteria" : league[HALFTIME]['score'],
                                            "favourite" : "home",
                                            "algorithm" : ""
                                            }
                                        output = f", Favourite : home@{odds_home}"
                                    if odds_away <= league[HALFTIME]["odds"] and odds_away < odds_home and ranking_home > ranking_away and rankings[away_team]['win']:
                                        schedules[HALFTIME][f"{home_team} vs {away_team}"] = {
                                            "league" : league["name"],
                                            "short_name" : league["short_name"],
                                            "winner" : away_team,
                                            "prematch" : odds_away,
                                            "live" : 0,
                                            "scores" : "0:0",
                                            "url" : url,
                                            "criteria" : league[HALFTIME]['score'],
                                            "favourite" : "away",
                                            "algorithm" : ""
                                            }
                                        output = f", Favourite : away@{odds_away}"
                                # except:
                                #     pass
                        
                        if league[QUARTER_ML]["status"]:
                            schedules[QUARTER_ML][f"{home_team} vs {away_team}"] = {
                                "league" : league,
                                "home" : home_team, 
                                "away" : away_team,
                                "url" : url,
                                "q_no" : 1,
                                "1" : {"ping" : 0, "underdog" : "", "status" : False},
                                "2" : {"ping" : 0, "underdog" : "", "status" : False},
                                "3" : {"ping" : 0, "underdog" : "", "status" : False},
                                "4" : {"ping" : 0, "underdog" : "", "status" : False},
                                "5" : {"ping" : 0, "underdog" : "", "status" : False},
                                "status" : False
                                }
                        
                        league_matchs.append({
                            "home" : home_team,
                            "away" : away_team,
                            "quarter" : quarter,
                            "url" : url,
                            "odds" : {"home" : odds_home, "away" : odds_away}
                            })
                        
                        print(f'{index + 1}. [{home_team.center(30)}] vs [{away_team.center(30)}] : {quarter.ljust(10)}{output}\n')
                    break
            except Exception as e:
                print(e)
            try:
                empty = driver.find_element(By.ID, 'main-content').find_element(By.CLASS_NAME, 'sports-empty-list').text
                break
            except:
                pass
            sleep(0.1)

        
        if league["short_name"] == "NCAA":
            continue
        
        results = [obj for obj in data['results'] if obj.get('competition_id') == league['id']]
        for obj in results:
            home_id = obj['home_team_id']
            away_id = obj['away_team_id']
            home = unidecode(team_id_to_name_map.get(home_id))
            away = unidecode(team_id_to_name_map.get(away_id))
            start = obj['match_time']

            if obj['id'] not in schedules[QUARTER_TOTAL]:
                output = 'Quarter Total - x'
                for match in league_matchs:
                    match_home = unidecode(match["home"]).replace('-', ' ').split(' ')
                    match_away = unidecode(match["away"]).replace('-', ' ').split(' ')
                    is_same_names = any(word in home.split(' ') for word in match_home) and any(word in away.split(' ') for word in match_away)
                    if 'End' not in match["quarter"] and is_same_names:
                        q_no = 1
                        if '2nd' in match["quarter"] or "First Break" in match["quarter"]:
                            q_no = 2
                        if '3rd' in match["quarter"] or "Second Break" in match["quarter"]:
                            q_no = 3
                        if '4th' in match["quarter"] or "Third Break" in match["quarter"]:
                            q_no = 4

                        key = f"{match['home']} vs {match['away']}"
                        if key in schedules[QUARTER_ML]:
                            q_ml_data = schedules[QUARTER_ML][key]
                            q_ml_data["q_no"] = q_no
                            q_ml_data["status"] = True
                            schedules[QUARTER_ML][obj['id']] = q_ml_data
                            del schedules[QUARTER_ML][key]

                        if '4th' not in match["quarter"] and 'Third Break' not in match["quarter"]:                        
                            output = f'Quarter Total - o' 
                            
                            if league[QUARTER_TOTAL]["status"]:                                
                                schedules[QUARTER_TOTAL][obj['id']] = {
                                    "home" : match["home"], 
                                    "away" : match["away"], 
                                    "start" : start,
                                    "q_no" : q_no, 
                                    "trigger" : "Don't trigger",
                                    "1" : {"over" : EMPTY, "under" : EMPTY, "ping_rain" : 0, "ping_drought" : 0, "timeout_count" : 0},
                                    "2" : {"over" : EMPTY, "under" : EMPTY, "ping_rain" : 0, "ping_drought" : 0, "timeout_count" : 0},
                                    "3" : {"over" : EMPTY, "under" : EMPTY, "ping_rain" : 0, "ping_drought" : 0, "timeout_count" : 0},
                                    "4" : {"over" : EMPTY, "under" : EMPTY, "ping_rain" : 0, "ping_drought" : 0, "timeout_count" : 0},
                                    "5" : {"over" : EMPTY, "under" : EMPTY, "ping_rain" : 0, "ping_drought" : 0, "timeout_count" : 0}
                                    }
                                output += f", Q{q_no}"

                            if league[HALFTIME]["status"]:
                                if league["short_name"] != "NBA" and league["short_name"] != "NCAA" and league["short_name"] != "CBA":
                                    favourite_team = None
                                    if match["odds"]["home"] <= league[HALFTIME]["odds"] and match["odds"]["home"] < match["odds"]["away"]:
                                        favourite_team = "home"
                                    if match["odds"]["away"] <= league[HALFTIME]["odds"] and match["odds"]["away"] < match["odds"]["home"]:
                                        favourite_team = "away"                                
                                    if favourite_team != None:
                                        h2h_response = requests.get('https://api.thesports.com/v1/basketball/match/analysis', params={"user":USER, "secret":SECRET, "uuid": obj['id']})
                                        h2h_data = h2h_response.json()["results"]
                                        try:
                                            home_index, away_index, home_key, away_key = 6, 7, "home", "away"
                                            if h2h_data["info"][7][0] == home_id and h2h_data["info"][6][0] == away_id:
                                                home_index, away_index, home_key, away_key = 7, 6, "away", "home"
                                            rank_home = int(h2h_data["info"][home_index][1])
                                            rank_away = int(h2h_data["info"][away_index][1])
                                            history_home = h2h_data["history"][home_key]
                                            history_away = h2h_data["history"][away_key]

                                            if (favourite_team == "home" and rank_home < rank_away) or (favourite_team == "away" and rank_home > rank_away):
                                                wins_home = 0
                                                wins_away = 0
                                                for index in range(league[HALFTIME]["history_count"]):
                                                    if history_home[index][6][0] == home_id and sum(history_home[index][6][2:]) > sum(history_home[index][7][2:]):
                                                        wins_home += 1
                                                    if history_home[index][7][0] == home_id and sum(history_home[index][7][2:]) > sum(history_home[index][6][2:]):
                                                        wins_home += 1
                                                    if history_away[index][6][0] == away_id and sum(history_away[index][6][2:]) > sum(history_away[index][7][2:]):
                                                        wins_away += 1
                                                    if history_away[index][7][0] == away_id and sum(history_away[index][7][2:]) > sum(history_away[index][6][2:]):
                                                        wins_away += 1
                                                # criteria = int(league[HALFTIME]["history_count"]/2)
                                                criteria = 2
                                                if (favourite_team == "home" and wins_home >= criteria) or (favourite_team == "away" and wins_away >= criteria):
                                                    odds = match[f"odds_{favourite_team}"]
                                                    schedules[HALFTIME][f"{match['home']} vs {match['away']}"] = {
                                                        "league" : league["name"],
                                                        "short_name" : league["short_name"],
                                                        "winner" : match[f"{favourite_team}"],
                                                        "prematch" : odds,
                                                        "live" : 0,
                                                        "scores" : "0:0",
                                                        "url" : url,
                                                        "criteria" : league[HALFTIME]['score'],
                                                        "favourite" : favourite_team
                                                        }
                                                    output += f", Favourite : {favourite_team}@{odds}"
                                        except:
                                            pass
                            break
                        else:
                            if league["short_name"] == "CBA" and league[QUARTER_TOTAL]["status"]:
                                schedules[QUARTER_TOTAL][obj['id']] = {
                                    "home" : match["home"], 
                                    "away" : match["away"], 
                                    "start" : start,
                                    "q_no" : q_no, 
                                    "trigger" : "Don't trigger",
                                    "1" : {"over" : EMPTY, "under" : EMPTY, "ping_rain" : 0, "ping_drought" : 0, "timeout_count" : 0},
                                    "2" : {"over" : EMPTY, "under" : EMPTY, "ping_rain" : 0, "ping_drought" : 0, "timeout_count" : 0},
                                    "3" : {"over" : EMPTY, "under" : EMPTY, "ping_rain" : 0, "ping_drought" : 0, "timeout_count" : 0},
                                    "4" : {"over" : EMPTY, "under" : EMPTY, "ping_rain" : 0, "ping_drought" : 0, "timeout_count" : 0},
                                    "5" : {"over" : EMPTY, "under" : EMPTY, "ping_rain" : 0, "ping_drought" : 0, "timeout_count" : 0}
                                    }
                                output += f", Q{q_no}"

                print(f'{results.index(obj) + 1}. [{home.center(30)}] vs [{away.center(30)}] : {datetime.fromtimestamp(start)}, {output}\n')   

    keys = []
    for key, val in schedules[QUARTER_ML].items():
        keys.append(key)
    for key in keys:
        if not schedules[QUARTER_ML][key]["status"]:
            del schedules[QUARTER_ML][key]
    return schedules

if __name__ == "__main__":
    while True:
        schedules = fetch_schedule()
        with open("json files/schedules.json", 'w') as file:
            json.dump(schedules, file)

        curr_hour = datetime.now().hour
        curr_minute = datetime.now().minute
        curr_second = datetime.now().second
        waitingTime = 86400 - curr_hour * 3600  - curr_minute * 60 - curr_second

        hour = int(waitingTime / 3600)
        minute = int((waitingTime % 3600) / 60)
        second = int((waitingTime % 3600) % 60)
        print('-'*50, f'sleeping for {hour}:{minute}:{second}'.center(50), '-'*50, '\n')

        thread_live = Thread(target=fetch_live, args=(schedules,))
        thread_live.start()
        thread_QuarterML = Thread(target=scrap_odds_for_QuarterML)
        thread_QuarterML.start()

        sleep(waitingTime)
