from discord import Intents, Embed, Color
from discord.ext import tasks, commands
from datetime import datetime
from time import sleep
import json

TOKEN = 'MTE3ODY2MDQyNzYwNjAxMTk4NA.Ge-O86.wZDmVi6ZkghqQRO6E8J8dNLl5ujYoWPH6JKr_w'

QUARTER_TOTAL = "QuarterTotal"
HALFTIME = "Halftime"
QUARTER_ML = "QuarterML"
WINRATE = "Winrate"

CHANNEL_ID = {
    QUARTER_TOTAL : 1173581589758869576,
    HALFTIME      : 1194789659297976412,
    QUARTER_ML    : 1203940818449203200,
    WINRATE       : 1201792075209646100
}

ADMIN_1 = "elssfz" 
ADMIN_2 = "codestar007" 
ICON_WIN = "✅"
ICON_LOSS = "❌"

winrates = {}
with open("json files/winrates.json", 'r') as file:
    winrates = json.load(file)

latest_message_id = ""

winrate_data = {}

# *Rain*    : **{rain_win}** Wins **{rain_loss}** Loss - {rain_percent}%

# *Drought* : **{drought_win}** Wins **{drought_loss}** Loss - {drought_percent}%

# *Halftime*: **{halftime_win}** Wins **{halftime_loss}** Loss - {halftime_percent}%

winrate_template = '''
*Quarter ML*: **{quarter_ml_win}** Wins **{quarter_ml_loss}** Loss - {quarter_ml_percent}%
'''

template = [["Rain          ", "☔     ", "Over/Under", "For Rain", "Both teams have scored 11 or more in a 50s window"],
            ["Better_Rain   ", "☔☔☔", "Over/Under", "For Better Rain", "Both teams have scored 13 or more in a 50s window"],
            ["Drought       ", "🏜️     ", "Over", "For Drought", "Both teams have not scored for a while, recommended to take the OVER bet. Do not take lines higher than what is recommended."],
            ["Better_Drought", "🏜️🏜️🏜️", "Over/Under", "For Better Drought", "Both teams have not scored more than 1 in a 90s window"]]

intents = Intents.default()
intents.messages = True
intents.reactions = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    send_signal_message.start()
    send_winrate_message.start()

@bot.event
async def on_message(message):
    global latest_message_id
    global winrate_data
    global winrates

    if str(message.author) == "SportsMate#6498":
        if winrate_data:
            algorithm_type = winrate_data["algo"]
            league = winrate_data["league"]
            short_name = winrate_data["short_name"]
            createdAt = winrate_data["createdAt"]
            if algorithm_type == QUARTER_ML:
                winrates[algorithm_type.split(" - ")[0]][message.id] = {"league" : league, "short_name" : short_name, "algo" : algorithm_type, "createdAt" : createdAt}
                with open("json files/winrates.json", 'w') as file:
                    json.dump(winrates, file)
            winrate_data = {}
            latest_message_id = ""
        else:
            latest_message_id = message.id

@tasks.loop(seconds=1.0)
async def send_winrate_message():
    global winrates
    
    for algorithm in [QUARTER_ML]: # QUARTER_TOTAL, HALFTIME, 
        if winrates[algorithm]:
            channel_Q = bot.get_channel(CHANNEL_ID[algorithm])
            if channel_Q:
                id_batch = []
                for id, value in winrates[algorithm].items():
                    id_batch.append(id)
                for id in id_batch:
                    try:
                        fetched_message = await channel_Q.fetch_message(id)
                        for reaction in fetched_message.reactions:
                            async for user in reaction.users():
                                name = winrates[algorithm][id]["league"]
                                short_name = winrates[algorithm][id]["short_name"]
                                algo = winrates[algorithm][id]["algo"]
                                if str(reaction.emoji) == ICON_WIN and (user.name == ADMIN_1 or user.name == ADMIN_2):
                                    winrates_league = {}
                                    with open("json files/winrates_league.json", 'r') as file:
                                        winrates_league = json.load(file)
                                    
                                    winrates_league[name][algo]["win"] += 1

                                    channel = bot.get_channel(CHANNEL_ID[WINRATE])
                                    if channel:
                                        embed = Embed(color=Color.blue())
                                        embed.title = f'**{short_name}** ({name})'

                                        result = {
                                            "Rain" :{},
                                            "Drought" :{},
                                            "Halftime" :{},
                                            "QuarterML" :{},
                                        }
                                        for index in ["Rain", "Drought", "Halftime", "QuarterML"]:
                                            win =winrates_league[name][index]["win"]
                                            loss =winrates_league[name][index]["loss"]
                                            percent = 0.00
                                            if win + loss != 0:
                                                percent = round(win * 100 / (win + loss), 2)
                                            result[index] = {"win" : win, "loss" : loss, "percent" : percent}

                                        embed.description = winrate_template.format(
                                            rain_win = result["Rain"]["win"], rain_loss = result["Rain"]["loss"], rain_percent = result["Rain"]["percent"], 
                                            drought_win = result["Drought"]["win"], drought_loss = result["Drought"]["loss"], drought_percent = result["Drought"]["percent"],
                                            halftime_win = result["Halftime"]["win"], halftime_loss = result["Halftime"]["loss"], halftime_percent = result["Halftime"]["percent"],
                                            quarter_ml_win = result["QuarterML"]["win"], quarter_ml_loss = result["QuarterML"]["loss"], quarter_ml_percent = result["QuarterML"]["percent"]
                                        )
                                        await channel.send(embed=embed)

                                        if winrates_league[name]["id"] != "":
                                            fetched_message = await channel.fetch_message(winrates_league[name]["id"])
                                            await fetched_message.delete()
                                        while latest_message_id == "":
                                            sleep(0.1)
                                        winrates_league[name]["id"] = latest_message_id
                                        with open("json files/winrates_league.json", 'w') as file:
                                            json.dump(winrates_league, file)
                                        print(f'{datetime.now().strftime("%H:%M:%S")}, reacted on message created at {winrates[algorithm][id]["createdAt"]} - {latest_message_id}, Win')
                                        del winrates[algorithm][id]
                                        with open("json files/winrates.json", 'w') as file:
                                            json.dump(winrates, file)

                                if str(reaction.emoji) == ICON_LOSS and (user.name == ADMIN_1 or user.name == ADMIN_2):
                                    winrates_league = {}
                                    with open("json files/winrates_league.json", 'r') as file:
                                        winrates_league = json.load(file)

                                    winrates_league[name][algo]["loss"] += 1

                                    channel = bot.get_channel(CHANNEL_ID[WINRATE])
                                    if channel:
                                        embed = Embed(color=Color.blue())
                                        embed.title = f'**{short_name}** ({name})'
                                        
                                        result = {
                                            "Rain" :{},
                                            "Drought" :{},
                                            "Halftime" :{},
                                            "QuarterML" :{},
                                        }
                                        for index in ["Rain", "Drought", "Halftime", "QuarterML"]:
                                            win =winrates_league[name][index]["win"]
                                            loss =winrates_league[name][index]["loss"]
                                            percent = 0.00
                                            if win + loss != 0:
                                                percent = round(win * 100 / (win + loss), 2)
                                            result[index] = {"win" : win, "loss" : loss, "percent" : percent}

                                        embed.description = winrate_template.format(
                                            rain_win = result["Rain"]["win"], rain_loss = result["Rain"]["loss"], rain_percent = result["Rain"]["percent"], 
                                            drought_win = result["Drought"]["win"], drought_loss = result["Drought"]["loss"], drought_percent = result["Drought"]["percent"],
                                            halftime_win = result["Halftime"]["win"], halftime_loss = result["Halftime"]["loss"], halftime_percent = result["Halftime"]["percent"],
                                            quarter_ml_win = result["QuarterML"]["win"], quarter_ml_loss = result["QuarterML"]["loss"], quarter_ml_percent = result["QuarterML"]["percent"]
                                        )
                                        await channel.send(embed=embed)

                                        if winrates_league[name]["id"] != "":
                                            fetched_message = await channel.fetch_message(winrates_league[name]["id"])
                                            await fetched_message.delete()
                                        while latest_message_id == "":
                                            sleep(0.1)
                                        winrates_league[name]["id"] = latest_message_id
                                        with open("json files/winrates_league.json", 'w') as file:
                                            json.dump(winrates_league, file)      
                                        print(f'{datetime.now().strftime("%H:%M:%S")}, reacted on message created at {winrates[algorithm][id]["createdAt"]} - {latest_message_id}, Loss')
                                        del winrates[algorithm][id]
                                        with open("json files/winrates.json", 'w') as file:
                                            json.dump(winrates, file)
                    except:
                        print(f'{datetime.now().strftime("%H:%M:%S")}, Not Exists Message with ID: {id}')

@tasks.loop(seconds=0.1)
async def send_signal_message():
    global winrate_data

    message = {}
    try:
        with open("json files/message_to_be_pinged.json", 'r') as file:
            message = json.load(file)
    except:
        pass
    
    if message:
        with open("json files/message_to_be_pinged.json", 'w') as file:
            json.dump({}, file)

        if message["algorithm"] == QUARTER_TOTAL:
            channel = bot.get_channel(CHANNEL_ID[QUARTER_TOTAL])
            if channel:
                text = '''__**{name}**__   {icon}                   {emoji}

                [{home}  vs.  {away}]({url})      [{q_no} Quarter - {time}]

                🔥   __**Live**__   🔥
                {sub_title} point total line and odds: __**{type} {live} odds**__

                *{sub_title} Pre game: {type} {prematch} odds*
                
                {title}
                ```{description}```'''

                name = message["league"]
                short_name = message["short_name"]
                id = message["id"]
                q_no = message["q_no"]
                sub_title = message["title"]
                remain = message["remain"]
                home = message["home"]
                away = message["away"]
                live = message["live"]
                prematch = message["prematch"]
                url = message["url"]
                emoji = message["emoji"]
                league_time = message["time"]
                
                seconds = 60 * league_time * q_no - remain
                min = int(seconds / 60)
                second = int(seconds % 60)
                time = f'{str(min).zfill(2)}:{str(second).zfill(2)}'
                quarter = ['1st', '2nd', '3rd', '4th']

                embed = Embed(color=Color.blue())
                embed.title = f'**{short_name}** ({name})'
                embed.description = text.format(
                                        name=template[id][0], icon=template[id][1], type=template[id][2], title=template[id][3], description=template[id][4], 
                                        live=live, prematch=prematch,q_no=quarter[q_no-1], time=time, home=home, away=away, url=url, sub_title=sub_title, emoji=emoji
                                        )
                
                algo = "Rain"
                if "Drought" in template[id][0]:
                    algo = "Drought"
                winrate_data = {"league" : name, "short_name" : short_name, "algo" : algo, "createdAt" : datetime.now().strftime("%Y/%m/%d, %H:%M:%S")}
                
                await channel.send(embed=embed)
                print(f'{datetime.now().strftime("%H:%M:%S")}, sent a message - Quarter Total Algorithm')
            else:
                print(f'{datetime.now().strftime("%H:%M:%S")}, channel not found')

        if message["algorithm"] == HALFTIME:
            channel = bot.get_channel(CHANNEL_ID[HALFTIME])
            if channel:
                text = '''
                __*Currently favourite team is down by 7 or more points at the half*__

                League: **{short_name}** ({name})

                *Pre game: [{winner}]({url}) @ {prematch} odds*

                Current odds:  [{winner}]({url}) @ __**{live} odds**__

                Current Score **{scores}**
                ```Possible comeback, consider taking the team who is losing at half-time on Money Line.
Exception: if the odd is higher than 2.40 at half time, you can take the handicap! Good luck!  ⏰```'''

                name = message["league"]
                short_name = message["short_name"]
                winner = message["winner"]
                prematch = message["prematch"]
                live = message["live"]
                scores = message["scores"]
                url = message["url"]
                
                embed = Embed(color=Color.blue())
                embed.title = f'⏰   Favorite value bet alert!   ⏰'
                embed.description = text.format(winner=winner, url=url, scores=scores, prematch=prematch, live=live, name=name,short_name=short_name)

                winrate_data = {"league" : name, "short_name" : short_name, "algo" : "Halftime", "createdAt" : datetime.now().strftime("%Y/%m/%d, %H:%M:%S")}
                
                await channel.send(embed=embed)
                print(f'{datetime.now().strftime("%H:%M:%S")}, sent a message - Halftime Algorithm')
            else:
                print(f'{datetime.now().strftime("%H:%M:%S")}, channel not found')

        if message["algorithm"] == QUARTER_ML:
            channel = bot.get_channel(CHANNEL_ID[QUARTER_ML])
            if channel:
                text = '''
                LIVE (Quarter ML Signal)

                [{home}  vs.  {away}]({url})
                [{quarter} Quarter - {time}]
                
                Model Recommendation:
                *Bet on [{underdog}]({url}) Quarter {q_no} MoneyLine*
                
                *Current Odds*: **{odds}**
                (Draw no bet)

                *Current Score*: **{scores}**
                '''

                name = message["league"]
                short_name = message["short_name"]
                q_no = message["q_no"]
                home = message["home"]
                away = message["away"]
                url = message["url"]
                odds = message["odds"]
                underdog = message["underdog"]
                scores = message["scores"]
                league_time = message["time"]
                remain = message["remain"]

                seconds = 60 * league_time * q_no - remain
                min = int(seconds / 60)
                second = int(seconds % 60)
                time = f'{str(min).zfill(2)}:{str(second).zfill(2)}'
                
                quarter = ['1st', '2nd', '3rd', '4th']

                embed = Embed(color=Color.blue())
                embed.title = f'**{short_name}** ({name})'
                embed.description = text.format(q_no=q_no, underdog=underdog, url=url, odds=odds, quarter=quarter[q_no-1], time=time, scores=scores, home=home, away=away)

                winrate_data = {"league" : name, "short_name" : short_name, "algo" : "QuarterML", "createdAt" : datetime.now().strftime("%Y/%m/%d, %H:%M:%S")}
                
                await channel.send(embed=embed)
                print(f'{datetime.now().strftime("%H:%M:%S")}, sent a message - Quarter ML Algorithm')
            else:
                print(f'{datetime.now().strftime("%H:%M:%S")}, channel not found')

if __name__ == "__main__":
    response = input("Are you sure you want to reset your win rate data? (y/n) ")
    if response == "y":
        winrates_league = {}
        with open("json files/winrates_league.json", 'r') as file:
            winrates_league = json.load(file)
        for league, data in winrates_league.items():
            for algorithm in ["Rain", "Drought", "Halftime", "QuarterML"]:
                data[algorithm]["win"] = 0
                data[algorithm]["loss"] = 0
            data["id"] = ""
        with open("json files/winrates_league.json", 'w') as file:
            json.dump(winrates_league, file)
    bot.run(TOKEN)
