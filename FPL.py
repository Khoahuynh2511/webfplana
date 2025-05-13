import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
from datetime import datetime
import io

# Set page configuration
st.set_page_config(page_title="Football Analysis Dashboard", layout="wide")

# Initialize session state for navigation
if 'page' not in st.session_state:
    st.session_state.page = 'Home'

# CSS for equal-sized buttons and centering elements
st.markdown("""
    <style>
    .stButton button {
        width: 100%;
        padding: 10px 0px;
        color: black;
        font-size: 16px;
        border-radius: 5px;
    }
    .centered {
        display: flex;
        justify-content: center;
        align-items: center;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# Function to fetch data from Football-Data.org with error handling and caching
@st.cache_data(ttl=300, show_spinner=False)
def fetch_data_from_football_data(api_key, endpoint):
    url = f"https://api.football-data.org/v4/{endpoint}"
    headers = {'X-Auth-Token': api_key}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as err:
        st.error(f"API Error: {err}")
        return {}

# Function to fetch data from API-Sports with error handling and caching
@st.cache_data(ttl=300, show_spinner=False)
def fetch_data_from_api_sports(api_key, endpoint):
    url = f"https://v3.football.api-sports.io/{endpoint}"
    headers = {'x-apisports-key': api_key}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as err:
        st.error(f"API Error: {err}")
        return {}

# Function to fetch data from OddsAPI with error handling and caching
@st.cache_data(ttl=300, show_spinner=False)
def fetch_odds_data(api_key, sport, region, market):
    url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds/?regions={region}&markets={market}&apiKey={api_key}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as err:
        st.error(f"API Error: {err}")
        return {}

# Function to prepare team data from Football-Data.org
def prepare_team_data(api_key, league_id):
    data = fetch_data_from_football_data(api_key, f"competitions/{league_id}/teams")
    teams = data.get('teams', [])
    if not teams:
        return pd.DataFrame()
    
    # Chuẩn bị dữ liệu với cột coach và area
    team_list = [{'name': team.get('name'), 
                  'founded': team.get('founded'),
                  'venue': team.get('venue'), 
                  'website': team.get('website'),
                  'coach_name': f"{team.get('coach', {}).get('firstName', '')} {team.get('coach', {}).get('lastName', '')}".strip(),
                  'coach_nationality': team.get('coach', {}).get('nationality', 'N/A'),
                  'contract_start': team.get('coach', {}).get('contract', {}).get('start', 'N/A'),
                  'contract_until': team.get('coach', {}).get('contract', {}).get('until', 'N/A'),
                  'area_name': team.get('area', {}).get('name', 'N/A'),
                  'area_code': team.get('area', {}).get('code', 'N/A'),
                  'area_flag': team.get('area', {}).get('flag', ''),
                  'area_id': team.get('area', {}).get('id', 'N/A')}  # Thêm cột area chi tiết
                 for team in teams]
    
    # Tạo DataFrame
    df_teams = pd.DataFrame(team_list)
    
    # Chuẩn hóa dữ liệu coach_name, coach_nationality, và area_name
    df_teams['coach_name'] = df_teams['coach_name'].replace("", "Unknown").str.title()
    df_teams['coach_nationality'] = df_teams['coach_nationality'].fillna('Unknown').str.title()
    df_teams['area_name'] = df_teams['area_name'].fillna('Unknown').str.title()
    
    return df_teams
# Function to prepare standings data from Football-Data.org
def prepare_standings_data(api_key, league_id):
    data = fetch_data_from_football_data(api_key, f"competitions/{league_id}/standings")
    standings = data.get('standings', [])[0].get('table', [])
    if not standings:
        return pd.DataFrame()
    standings_list = [{'position': team.get('position'), 'team': team.get('team', {}).get('name'),
                       'playedGames': team.get('playedGames'), 'won': team.get('won'),
                       'draw': team.get('draw'), 'lost': team.get('lost'), 'points': team.get('points')} 
                      for team in standings]
    return pd.DataFrame(standings_list)

# Function to prepare match data from Football-Data.org
def prepare_match_data(api_key, league_id):
    data = fetch_data_from_football_data(api_key, f"competitions/{league_id}/matches")
    matches = data.get('matches', [])
    if not matches:
        return pd.DataFrame()
    match_list = [{'home_team': match.get('homeTeam', {}).get('name'),
                   'away_team': match.get('awayTeam', {}).get('name'),
                   'score_home': match.get('score', {}).get('fullTime', {}).get('homeTeam'),
                   'score_away': match.get('score', {}).get('fullTime', {}).get('awayTeam'),
                   'status': match.get('status'), 'date': match.get('utcDate')} 
                  for match in matches]
    return pd.DataFrame(match_list)

# Function to prepare player data from Football-Data.org
def prepare_player_data(api_key, team_id):
    data = fetch_data_from_football_data(api_key, f"teams/{team_id}")
    squad = data.get('squad', [])
    if not squad:
        return pd.DataFrame()
    player_list = [{'name': player.get('name'), 'position': player.get('position'),
                    'dateOfBirth': player.get('dateOfBirth'), 'nationality': player.get('nationality')} 
                   for player in squad]
    return pd.DataFrame(player_list)

# Function to prepare player performance data from API-Sports
def prepare_player_performance(api_key, player_name):
    data = fetch_data_from_api_sports(api_key, f"players?search={player_name}")
    if not data.get('response'):
        return {}
    
    player_info = data['response'][0]
    stats = player_info['statistics'][0]
    
    return {
        'name': player_info.get('player', {}).get('name'),
        'age': player_info.get('player', {}).get('age'),
        'nationality': player_info.get('player', {}).get('nationality'),
        'team': stats.get('team', {}).get('name'),
        'position': stats.get('games', {}).get('position'),
        'appearances': stats.get('games', {}).get('appearances', 0),
        'minutes_played': stats.get('games', {}).get('minutes', 0),
        'goals': stats.get('goals', {}).get('total', 0),
        'assists': stats.get('goals', {}).get('assists', 0),
        'shots_total': stats.get('shots', {}).get('total', 0),
        'passes_total': stats.get('passes', {}).get('total', 0),
        'yellow_cards': stats.get('cards', {}).get('yellow', 0),
        'red_cards': stats.get('cards', {}).get('red', 0)
    }

# Function to display a bar chart for team statistics
def display_team_statistics(standings_data):
    st.title("Team Statistics")
    fig, ax = plt.subplots()
    sns.barplot(x='team', y='points', data=standings_data, ax=ax)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    st.pyplot(fig)

# Function to display upcoming matches
def display_upcoming_matches(match_data):
    st.title("Upcoming Matches")
    upcoming_matches = match_data[match_data['status'] == 'SCHEDULED']
    upcoming_matches.loc[:, 'date'] = pd.to_datetime(upcoming_matches['date']).dt.strftime('%Y-%m-%d %H:%M:%S')
    st.dataframe(upcoming_matches[['home_team', 'away_team', 'date']])

    # Visualization: Upcoming matches schedule using Plotly
    st.subheader("Upcoming Matches Schedule")
    match_data['date'] = pd.to_datetime(match_data['date'])
    fig = px.histogram(match_data, x='date', nbins=20, title="Distribution of Upcoming Match Dates")
    st.plotly_chart(fig)

# OddsAPI integration with match and bookmaker selection
# OddsAPI integration with match and bookmaker selection with data analysis
def display_odds_data(api_key):
    st.title("Tỷ lệ cược bóng đá")
    sport = "soccer"  # Loại thể thao
    region = "eu"  # Khu vực (EU)
    market = "h2h"  # Loại thị trường (Head to Head)

    odds_data = fetch_odds_data(api_key, sport, region, market)
    if odds_data:
        # Tạo danh sách các trận đấu để người dùng chọn
        match_options = {f"{game['home_team']} vs {game['away_team']}": game for game in odds_data}
        selected_match = st.selectbox("Chọn trận đấu", list(match_options.keys()))
        
        # Lấy thông tin về trận đấu đã chọn
        game = match_options[selected_match]
        st.subheader(f"{game['home_team']} vs {game['away_team']}")
        
        # Tạo danh sách các nhà cái để người dùng chọn
        bookmaker_options = {bookmaker['title']: bookmaker for bookmaker in game['bookmakers']}
        selected_bookmaker = st.selectbox("Chọn nhà cái", list(bookmaker_options.keys()))
        
        # Hiển thị tỷ lệ cược cho nhà cái đã chọn
        bookmaker = bookmaker_options[selected_bookmaker]
        st.write(f"Nhà cái: {bookmaker['title']}")
        odds_list = []
        for market in bookmaker['markets']:
            for outcome in market['outcomes']:
                st.write(f"{outcome['name']}: {outcome['price']}")
                odds_list.append({'Outcome': outcome['name'], 'Odds': outcome['price']})
        
        # Phân tích dữ liệu tỷ lệ cược
        if odds_list:
            odds_df = pd.DataFrame(odds_list)
            st.subheader("Phân tích tỷ lệ cược")
            
            # Biểu đồ thanh cho tỷ lệ cược
            fig, ax = plt.subplots()
            sns.barplot(x='Outcome', y='Odds', data=odds_df, ax=ax)
            ax.set_title(f"Tỷ lệ cược cho {game['home_team']} vs {game['away_team']}")
            plt.xticks(rotation=45, ha='right')
            st.pyplot(fig)
            
            # Thống kê cơ bản về tỷ lệ cược
            st.subheader("Thống kê cơ bản")
            st.write(odds_df.describe())
            
            # Biểu đồ phân phối tỷ lệ cược
            st.subheader("Phân phối tỷ lệ cược")
            fig = px.histogram(odds_df, x='Odds', title="Phân phối tỷ lệ cược")
            st.plotly_chart(fig)
    else:
        st.write("Không có dữ liệu tỷ lệ cược.")



# Sidebar for selecting league and team
# Sidebar for selecting league and team
st.sidebar.title("Select League and Team")
league_dict = {
    'Premier League': 'PL',
    'La Liga': 'PD',
    'Serie A': 'SA',
    'Bundesliga': 'BL1',
    'Ligue 1': 'FL1',
    'Eredivisie': 'DED',
    'Primeira Liga': 'PPL',
    'Brasileirão Série A': 'BSA',
}
league = st.sidebar.selectbox("League", list(league_dict.keys()))
league_id = league_dict[league]

# API Keys
football_data_api_key = "fc8b9a8f57794b898583b305a4cebd6d"  # Football-Data.org
api_sports_key = "fcd2323fcc1080e1868b86c89d4703ec"  # API-Sports
odds_api_key = "b95b6b63fd6ece2b4689076c781a1c74"  # OddsAPI


# Load and prepare team data from Football-Data.org
teams_data = fetch_data_from_football_data(football_data_api_key, f"competitions/{league_id}/teams")
teams = teams_data.get('teams', [])
team_options = {team['name']: team['id'] for team in teams}
selected_team = st.sidebar.selectbox("Select Team", list(team_options.keys()))

# Load and prepare player data from Football-Data.org
player_data = prepare_player_data(football_data_api_key, team_options[selected_team])

standings_data = prepare_standings_data(football_data_api_key, league_id)
match_data = prepare_match_data(football_data_api_key, league_id)

# Sidebar navigation
st.sidebar.title("Navigation")
st.sidebar.button("Home", on_click=lambda: st.session_state.update({'page': 'Home'}))
st.sidebar.button("Team Data", on_click=lambda: st.session_state.update({'page': 'Team Data'}))
st.sidebar.button("Standings", on_click=lambda: st.session_state.update({'page': 'Standings'}))
st.sidebar.button("Matches", on_click=lambda: st.session_state.update({'page': 'Matches'}))
st.sidebar.button("Player Data", on_click=lambda: st.session_state.update({'page': 'Player Data'}))
st.sidebar.button("Player Performance", on_click=lambda: st.session_state.update({'page': 'Player Performance'}))
st.sidebar.button("Upcoming Matches", on_click=lambda: st.session_state.update({'page': 'Upcoming Matches'}))
st.sidebar.button("Odds Data", on_click=lambda: st.session_state.update({'page': 'Odds Data'}))

# Page content based on navigation state
if st.session_state.page == 'Home':
    st.title(f"Football Analysis Dashboard - {league}")
    st.write("Use the navigation menu to explore team data, standings, matches, and player statistics.")

elif st.session_state.page == 'Team Data':
    st.title(f"Team Data - {league}")
    if not teams_data:
        st.write("No team data available.")
    else:
        df_teams = pd.DataFrame(teams)
        st.dataframe(df_teams)

        # Visualize founded year of teams
        if not df_teams.empty and 'founded' in df_teams.columns:
            st.subheader("Distribution of Team Founded Years")
            fig, ax = plt.subplots()
            sns.histplot(df_teams['founded'].dropna(), bins=20, kde=True, ax=ax)
            ax.set_title("Distribution of Team Founded Years")
            plt.xticks(rotation=45)
            st.pyplot(fig)

elif st.session_state.page == 'Standings':
    st.title(f"Standings - {league}")
    if not standings_data.empty:
        st.dataframe(standings_data)
        display_team_statistics(standings_data)
    else:
        st.write("No standings data available.")

elif st.session_state.page == 'Matches':
    st.title(f"Matches - {league}")
    if not match_data.empty:
        st.dataframe(match_data)

        # Visualization: Goals distribution in matches using Plotly
        st.subheader("Goals Distribution in Matches")
        fig = px.histogram(match_data[['score_home', 'score_away']].stack(), title="Distribution of Goals in Matches")
        st.plotly_chart(fig)
    else:
        st.write("No match data available.")

elif st.session_state.page == 'Player Data':
    st.title(f"Player Data - {selected_team}")
    if not player_data.empty:
        st.dataframe(player_data)

        # Visualization: Player positions
        st.subheader("Player Positions Distribution")
        fig, ax = plt.subplots()
        sns.countplot(y='position', data=player_data, ax=ax)
        ax.set_title("Distribution of Player Positions")
        st.pyplot(fig)

        # Convert 'dateOfBirth' to datetime format
        player_data['dateOfBirth'] = pd.to_datetime(player_data['dateOfBirth'], errors='coerce')

        # Calculate age from date of birth
        current_year = datetime.now().year
        player_data['age'] = current_year - player_data['dateOfBirth'].dt.year

        # Visualization: Player ages
        st.subheader("Player Age Distribution")
        fig, ax = plt.subplots()
        sns.histplot(player_data['age'].dropna(), bins=20, kde=True, ax=ax)
        ax.set_title("Distribution of Player Ages")
        plt.xticks(rotation=45)
        st.pyplot(fig)
        
        # Visualization: Player nationality distribution
        st.subheader("Player Nationalities Distribution")
        fig, ax = plt.subplots()
        sns.countplot(y='nationality', data=player_data, ax=ax, order=player_data['nationality'].value_counts().index)
        ax.set_title("Distribution of Player Nationalities")
        plt.xticks(rotation=45)
        st.pyplot(fig)

    else:
        st.write("No player data available.")

elif st.session_state.page == 'Player Performance':
    st.title(f"Player Performance - {selected_team}")
    selected_player = st.selectbox("Select Player", player_data['name'])
    player_performance = prepare_player_performance(api_sports_key, selected_player)
    
    if player_performance:
        st.write(f"**Name:** {player_performance['name']}")
        st.write(f"**Age:** {player_performance['age']}")
        st.write(f"**Nationality:** {player_performance['nationality']}")
        st.write(f"**Team:** {player_performance['team']}")
        st.write(f"**Position:** {player_performance['position']}")
        st.write(f"**Appearances:** {player_performance['appearances']}")
        st.write(f"**Minutes Played:** {player_performance['minutes_played']}")
        st.write(f"**Goals:** {player_performance['goals']}")
        st.write(f"**Assists:** {player_performance['assists']}")
        st.write(f"**Shots Total:** {player_performance['shots_total']}")
        st.write(f"**Passes Total:** {player_performance['passes_total']}")
        st.write(f"**Yellow Cards:** {player_performance['yellow_cards']}")
        st.write(f"**Red Cards:** {player_performance['red_cards']}")
    else:
        st.write("No performance data available for this player.")

elif st.session_state.page == 'Upcoming Matches':
    if not match_data.empty:
        display_upcoming_matches(match_data)

elif st.session_state.page == 'Odds Data':
    display_odds_data(odds_api_key)

# Function to export data to CSV
def export_data_to_csv(dataframe, filename):
    buffer = io.StringIO()
    dataframe.to_csv(buffer, index=False)
    buffer.seek(0)
    st.download_button(label="Download CSV", data=buffer, file_name=f"{filename}.csv", mime='text/csv')

# Adding download option for dataframes
if st.session_state.page in ['Team Data', 'Standings', 'Matches', 'Player Data']:
    if 'dataframe' in locals():
        export_data_to_csv(dataframe, f"{st.session_state.page.lower()}_data")
