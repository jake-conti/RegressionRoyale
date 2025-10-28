import requests
import json
import urllib.parse
import sys
import random

MY_BATTLES = "NOT_LOADED"
CR_API_TOKEN = "NOT_LOADED"
CR_API_HEADER = "NOT_LOADED"
DATA = dict()
ONE_HOT_TABLE = dict()   

def load_secrets():
    global CR_API_TOKEN
    global CR_API_HEADER
    try:
        # Initialize API token and header from secrets.json
        with open("SECRETS.json") as SEC_FILE:
            secrets = json.load(SEC_FILE)
            CR_API_TOKEN = secrets["TOKEN"]
            CR_API_HEADER = {"Authorization": f"Bearer {CR_API_TOKEN}"}
    
    # Exit if error occurs
    except Exception as e:
        print(f"An Error Occurred Loading Secrets: {e}")
        sys.exit()

def test():
    global MY_BATTLES
    
    player_tag = "#8PJ89JLJ" # Use my player tag
    encoded_tag = player_tag.replace("#", "%23")
    BASE_URL = "https://api.clashroyale.com/v1"
    endpoint = f"/players/{encoded_tag}/battlelog"
    url = BASE_URL + endpoint

    try:

        response = requests.get(url, headers=CR_API_HEADER, timeout=10)
        response.raise_for_status() 
        print("Test Request successful!")
       
        
        MY_BATTLES = response.json()
        print(get_ladder_battle("#8PJ89JLJ")) # Print output of get_ladder_battle 
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")

def load_data(dataName: str):
    global DATA
    
    # load data as .csv into the DATA dictionary
    try:
        with open(dataName, 'r', encoding='utf-8') as datafile:
            for line in datafile:
                line = line.strip().replace("\ufeff", "").split(',')
                if(line == ''):
                    break
                
                entry = dict()
                entry["trophies"] = int(line[1])
                entry["card1"] = line[2]
                entry["card2"] = line[3]
                entry["card3"] = line[4]
                entry["card4"] = line[5]
                entry["card5"] = line[6]
                entry["card6"] = line[7]
                entry["card7"] = line[8]
                entry["card8"] = line[9]
                # TODO: ADD TOWER TROOP
                DATA[line[0]] = entry
        
        print(f"Data successfully loaded. Number of entries: {len(DATA.keys())}")
                
    except Exception as e:
        print(f"Something went wrong parsing the data file: {e}")

def save_data(dataName: str):
    global DATA
    print("Saving data...")
    # Save data to csv
    try:
        with open(dataName, 'w', encoding='utf-8') as datafile:
            for key in DATA:
                
                entry = [key, 
                         str(DATA[key]['trophies']),
                         DATA[key]['card1'],
                         DATA[key]['card2'],
                         DATA[key]['card3'],
                         DATA[key]['card4'],
                         DATA[key]['card5'],
                         DATA[key]['card6'],
                         DATA[key]['card7'],
                         DATA[key]['card8']]
                        # TODO: ADD TOWER TROOP
                        
                entryStr = ",".join(entry) + '\n'
                datafile.write(entryStr)
            print(f"Data saved, size = {len(DATA.keys())}")
            
    except Exception as e:
        print(f"Error occurred while saving data: {e}")
           
def convert_to_one_hot(dataName: str):
    global ONE_HOT_TABLE
    
    card_list = get_cards_in_data()
    if len(ONE_HOT_TABLE.keys()) == 0:
        for i, card in enumerate(card_list):
            ONE_HOT_TABLE[card] = i
    
    with open(dataName, "w", encoding="utf-8") as OH_file:
        for key in DATA:
            zeros = ['0'] * len(card_list)
            for i in range(1, 9): zeros[ONE_HOT_TABLE[DATA[key][f"card{i}"]]] = '1'
            entry = [str(DATA[key]["trophies"])] + zeros
            entryStr = ",".join(entry) + '\n'
            OH_file.write(entryStr)
    
    print(f"Data saved, size = {len(DATA.keys())}")              
        
def request(endpoint: str):
    
    # Make an API call given an endpoint
    url = "https://api.clashroyale.com/v1" + endpoint
    try:
        response = requests.get(url, headers=CR_API_HEADER, timeout=10)
        response.raise_for_status()
        response = response.json()
        return response

    except Exception as e:
        print(f"An error occured making the request {endpoint}: {e}")

def find_players_in_trophy_range(min_trophies: int, max_trophies: int, num_players_to_return: int, max_clans_to_check: int = 50) -> list:

    found_players = []
    found_player_tags = set(DATA.keys())
    checked_clan_tags = set()

    print(f"Searching for {num_players_to_return} players between {min_trophies} and {max_trophies} trophies")

    # Query clans
    clan_search_params = {
        "minScore": max(501, min_trophies - 500),
        "limit": max_clans_to_check,
        "minMembers": 25
    }
    query_string = urllib.parse.urlencode(clan_search_params)
    clan_search_results = request(f"/clans?{query_string}")
    
    
    # If query fails, return nothing
    if not clan_search_results or 'items' not in clan_search_results:
        print("An error occured finding clans.")
        return found_players

    clans_to_check = clan_search_results['items']
    print(f"Found {len(clans_to_check)} clans to check.")

    # Randomize order of clans
    random.shuffle(clans_to_check)

    # Loop through clans
    for clan_info in clans_to_check:
        
        # Stop search if numplayers is matched
        if len(found_players) >= num_players_to_return:
            print("Found enough players!")
            break
        
        # skip already visited clans
        clan_tag = clan_info.get('tag')
        if not clan_tag or clan_tag in checked_clan_tags:
            continue

        # Get member list
        checked_clan_tags.add(clan_tag)
        encoded_clan_tag = urllib.parse.quote(clan_tag)
        member_list_response = request(f"/clans/{encoded_clan_tag}/members") 

        # Continue if error occurred getting the request
        if not member_list_response or 'items' not in member_list_response:
            continue
        
        # Loop through member list
        for member in member_list_response['items']:
            
            # Break if numplaters is matched
            if len(found_players) >= num_players_to_return:
                break

            member_trophies = member.get('trophies')
            member_tag = member.get('tag')

            # If tag is valid and not already found AND within trophy range, add it to found_players
            if member_tag and member_trophies is not None and min_trophies <= member_trophies <= max_trophies and member_tag not in found_player_tags:
                    
                found_players.append({
                    "tag": member_tag,
                    "trophies": member_trophies
                })
                found_player_tags.add(member_tag)

    # Print results
    print()
    if len(found_players) < num_players_to_return:
        print(f"Finished searching clans but only found {len(found_players)} good players.")
    else:
        print("Finished search. Found all players!")

    return found_players

def parse_battle_info(team_dict: dict):
    # Get all cards
    cards = team_dict["cards"]
    card_names = list()
    for card in cards:
        
        # Make EVO cards distinct
        name = ''
        if "evolutionLevel" in card.keys():
            name += "EVO-"
        name += card["name"]
        card_names.append(name)
        
        # TODO: Add tower troop to return
    
    return [team_dict["tag"], team_dict["startingTrophies"]] + card_names
    
def get_ladder_battle(player_tag: str):
    encoded_tag = player_tag.replace("#", "%23")
    results = request(f"/players/{encoded_tag}/battlelog")
    
    for entry in results:
        
        # Get first entry of a ladder battle
        if(entry["gameMode"]["name"] != "Ladder"):
            continue
        
        user_team = entry["team"][0]
        
        opponent_team = entry["opponent"][0]
        
        # Return false if the user or the opponent is already in DATA
        if(user_team['tag'] in DATA or opponent_team['tag'] in DATA):
            return False
        
        # Return the entries for the user and their opponent
        return parse_battle_info(user_team), parse_battle_info(opponent_team)

def get_cards_in_data():
    cards = set()
    for tag in DATA:
        for i in range(1, 9): cards.add(DATA[tag][f"card{i}"])
    return sorted(cards)

def get_data(points_per_bucket: int, bucket_size: int):
    for i in range(1, 10000, bucket_size):
        players = []
        try:
            players = find_players_in_trophy_range(i, i+bucket_size, points_per_bucket, 1000)
            for player in players:
                ladder_battle = get_ladder_battle(player["tag"])
                if(not ladder_battle):
                    print("Searching for ladder battle")
                    continue
                
                print("Ladder battle found!")
                for entry in ladder_battle:
                    
                    value = dict()
                    value["trophies"] = int(entry[1])
                    value["card1"] = entry[2]
                    value["card2"] = entry[3]
                    value["card3"] = entry[4]
                    value["card4"] = entry[5]
                    value["card5"] = entry[6]
                    value["card6"] = entry[7]
                    value["card7"] = entry[8]
                    value["card8"] = entry[9]
                    # TODO: Add tower troop to value
                    DATA[entry[0]] = value
                    
            save_data("Data.csv")
        
        except:
            print("Something went wrong...")
            
if __name__ == "__main__":
    load_secrets()
    load_data("Data.csv")
    
    while True:
        print("What do you want to do?")
        print("1. Get more data")
        print("2. Print all cards in DATA")
        print("3. Output number of datapoints")
        print("4. Create One-Hot Dataset")
        print("5. Run a Test API Call")
        print("6. Quit")
        prompt = int(input("Enter a number: "))
        print()
        
        if prompt == 1:
            range_size = int(input("Enter the size of your trophy range"))
            points_per_bucket = int(input("Enter the number of points per trophy range"))
            get_data(points_per_bucket, range_size)
            
        
        elif prompt == 2:     
            print(get_cards_in_data())
            
        elif prompt == 3:
            print(len(DATA.keys()))
            
        elif prompt == 4:
            convert_to_one_hot("Data_OH.csv")
            
        elif prompt == 5:
            test()
        elif prompt == 6:
            sys.exit()
        
        print("\n")

            
