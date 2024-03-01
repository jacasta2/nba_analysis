"""
data.py
    This script contains all supporting functions to pull NBA data.
"""

import os
import time
import hsfs
import numpy as np
import pandas as pd
from streamlit.delta_generator import DeltaGenerator
from nba_api.stats.endpoints import boxscoretraditionalv2, leaguegamefinder
from feature_store import (
    feature_group_connection_r1,
    get_feature_store_data_r1,
    get_feature_store_data_r2,
)

# from feature_store import (
#     feature_view_connection,
#     get_feature_store_data,
#     first_feature_group_connection,
# )


def pull_team_games(team_id: int, season_init: int, season_end: int) -> pd.DataFrame:
    """
    This function returns all regular season and playoff games info from a given team
    and seasons.

    An update that automatizes the process of fetching data from the nba_api and the
    Hopsworks feature store makes this function unnecessary. I leave it for the sake of
    learning.

    Args:
        team_id: int that contains the team id.
        season_init: int that contains the starting season from which the games info
            will be pulled.
        season_end: int that contains the ending season from which the games info will
            be pulled.

    Returns:
        pd.DataFrame that contains the games info from the given team and seasons.
    """

    # We create a list to store DataFrames, each containing a team's either regular
    # season or playoff games info from individual seasons
    seasons_list = []

    # We loop through each season
    for i in range(season_init, season_end + 1):
        # We create the season id needed by the nba_api. A season id has the form
        # 'yyyy-yy'. For example, the 2022-2023 season id is '2022-23'
        season = str(i) + "-" + str(i + 1)[-2:]

        # We pull regular season games by calling the nba_api
        games = leaguegamefinder.LeagueGameFinder(
            team_id_nullable=team_id,
            season_nullable=season,
            season_type_nullable="Regular Season",
        ).get_data_frames()[0]
        # We add a column to identify regular season games
        games["PLAYOFFS"] = 0
        seasons_list.append(games)

        # We pull playoff games by calling the nba_api
        games = leaguegamefinder.LeagueGameFinder(
            team_id_nullable=team_id,
            season_nullable=season,
            season_type_nullable="Playoffs",
        ).get_data_frames()[0]
        # We add a column to identify playoff games
        games["PLAYOFFS"] = 1

        # We update the list
        seasons_list.append(games)

    # We prepare the DataFrames to concatenate them
    for games in seasons_list:
        games.reset_index(drop=True, inplace=True)

    # We concatenate the DataFrames vertically and then sort the resulting DataFrame by
    # the games dates
    games = pd.concat(seasons_list, axis=0, ignore_index=True)
    return games.sort_values(by="GAME_DATE", ascending=True).reset_index(drop=True)


def append_players_stats_season(
    players_list: list, team_games: pd.DataFrame
) -> pd.DataFrame:
    """
    This function appends to a team's games info DataFrame from a single season the
    three main stats (points, rebounds and assists) from a given set of its players.
    The function also appends info on whether the players were starters in the games.
    This function is called within another function that loops through seasons.

    An update that automatizes the process of fetching data from the nba_api and the
    Hopsworks feature store makes this function unnecessary. I leave it for the sake of
    learning.

    Args:
        players_list: list that contains the players' ids.
        team_games: pd.DataFrame that contains the team's games data from a single
            season.

    Returns:
        pd.DataFrame that contains the team's games data from a single season,
        including the main stats from the given set of players.
    """

    # We load the nba_players info
    players_path = ""
    # Path for local development
    if "DS_Projects" in os.getcwd():
        players_path += "../data/nba_players.csv"
    # Path for streamlit deployment
    else:
        players_path += os.getcwd() + "/data/nba_players.csv"

    nba_players = pd.read_csv(players_path)

    # We create a list to store DataFrames, each containing a player's main stats
    players_df_list = []

    # We loop through each player
    for player_id in players_list:
        # For each player, we create an empty DataFrame that will store his main stats.
        # We use his last name (loaded from the nba_players DataFrame) to name the
        # columns
        last_name = (
            nba_players.loc[nba_players["id"] == player_id, "last_name"]
            .values[0]
            .upper()
        )
        players_df_list.append(
            pd.DataFrame(
                columns=[
                    last_name + "_PTS",
                    last_name + "_REB",
                    last_name + "_AST",
                    last_name + "_STARTER",
                ]
            )
        )

    # We loop through each game in a season
    for game in team_games.itertuples():
        # We get the box score for the game by calling the nba_api
        game_id = getattr(game, "GAME_ID")
        box_score = boxscoretraditionalv2.BoxScoreTraditionalV2(game_id=game_id)
        players_stats = box_score.player_stats.get_data_frame()

        # We loop through each player
        for i, player in enumerate(players_list):
            # If the player was part of the team roster for the game, we extract his
            # stats from the box score. If he wasn't, we fill the stats with 0s. We
            # append the stats at the end of the player stats DataFrame. This ensures
            # that the games' info DataFrame and each player's stats DataFrame have the
            # same length
            if player in players_stats["PLAYER_ID"].to_list():
                # We create the condition to pull the player's info from the box score
                player_condition = players_stats["PLAYER_ID"] == player

                # The 'START_POSITION' of non-starters is an empty string
                starter = (
                    1
                    if players_stats.loc[player_condition, "START_POSITION"].values[0]
                    != ""
                    else 0
                )
                # We pull the player's stats
                stats_list = [
                    players_stats.loc[player_condition, "PTS"].values[0],
                    players_stats.loc[player_condition, "REB"].values[0],
                    players_stats.loc[player_condition, "AST"].values[0],
                    starter,
                ]

                # We update his DataFrame
                players_df_list[i].loc[len(players_df_list[i])] = stats_list
            else:
                # We update his DataFrame
                players_df_list[i].loc[len(players_df_list[i])] = [0, 0, 0, 0]

    # We insert the games info DataFrame at the beginning of the list containing the
    # players' stats DataFrames to ease the concatenation
    players_df_list.insert(0, team_games)

    # We prepare the DataFrames to concatenate them
    for dataframe in players_df_list:
        dataframe.reset_index(drop=True, inplace=True)

    # We concatenate the DataFrames horizontally
    return pd.concat(players_df_list, axis=1)


def append_players_stats(players_list: list, team_games: pd.DataFrame) -> pd.DataFrame:
    """
    This function appends to a team's games info DataFrame the three main stats (points,
    rebounds and assists) from a given set of its players. The team's games info
    DataFrame may contain info from several seasons. The function takes this into
    consideration and appends the stats one season at a time. To avoid being blocked by
    the nba_api, the function adds a five-second sleep between seasons. The function
    also appends info on whether the players were starters in the games. This
    function's main purpose is controlling the append season by season since the actual
    append operation is performed by a function call.

    An update that automatizes the process of fetching data from the nba_api and the
    Hopsworks feature store makes this function unnecessary. I leave it for the sake of
    learning.

    Args:
        players_list: list that contains the players' ids.
        team_games: pd.DataFrame that contains the team's games data.

    Returns:
        pd.DataFrame that contains the team's games data, including the main stats from
            the given set of players.
    """

    # We create a list to store DataFrames, each containing the team's games info from
    # an individual season
    games_list = []

    # We extract the seasons and loop through them
    seasons = [i for i in team_games["SEASON_ID"].str[1:].unique().tolist()]
    for season in seasons:
        # We pull the games info from an individual season and append to it the players'
        # stats
        dataframe = team_games[team_games["SEASON_ID"].str[1:] == season].copy()
        dataframe = append_players_stats_season(players_list, dataframe)

        # We update the list
        games_list.append(dataframe)

        # We add a five-second sleep to avoid being blocked by the nba_api
        time.sleep(5)

    # We prepare the DataFrames to concatenate them
    for games in games_list:
        games.reset_index(drop=True, inplace=True)

    # We concatenate the DataFrames vertically
    return pd.concat(games_list, axis=0, ignore_index=True)


def teammates_stats(team_games: pd.DataFrame) -> pd.DataFrame:
    """
    This function compute the main stats (PTS, REB and AST) from the rest of the
    teammates, i.e., from the teammates whose stats weren't appended to the games data.
    It takes advantage of the name codification of the players stats columns. For
    example, for each player whose stats were appended to the games data, the points
    column's name is 'NAME_PTS'. Thus, the function pulls all columns whose names
    contain '_PTS', adds these points up and substracts them from the whole team points.

    An update that automatizes the process of fetching data from the nba_api and the
    Hopsworks feature store makes this function unnecessary. I leave it for the sake of
    learning.

    Args:
        team_games: pd.DataFrame that contains the team's games data.

    Returns:
        team_games = pd.DataFrame that contains the team's games data, including the
            main stats from the rest of the teammates.
    """

    # Some player stats could be filled with NaN values. Fill them with 0
    cols = [
        col
        for col in team_games.columns
        if "_PTS" in col or "_REB" in col or "_AST" in col or "_STARTER" in col
    ]
    col_dict = {col: 0 for col in cols}
    team_games.fillna(value=col_dict, inplace=True)

    # Pull points from the players, add them up and substract the sum from the whole
    # team points
    cols = [col for col in team_games.columns if "_PTS" in col]
    team_games["REST_PTS"] = team_games["PTS"] - team_games[cols].sum(axis=1)

    # Pull rebounds from the players, add them up and substract the sum from the whole
    # team rebounds
    cols = [col for col in team_games.columns if "_REB" in col]
    team_games["REST_REB"] = team_games["REB"] - team_games[cols].sum(axis=1)

    # Pull assists from the players, add them up and substract the sum from the whole
    # team assists
    cols = [col for col in team_games.columns if "_AST" in col]
    team_games["REST_AST"] = team_games["AST"] - team_games[cols].sum(axis=1)

    return team_games


def stats_to_int(team_games: pd.DataFrame) -> pd.DataFrame:
    """
    This function converts the stats columns from (i) the players whose stats were
    appended to the games data and (ii) the rest of their teammates to 'int'.

    An update that automatizes the process of fetching data from the nba_api and the
    Hopsworks feature store makes this function unnecessary. I leave it for the sake of
    learning.

    Args:
        team_games: pd.DataFrame that contains the team's games data.

    Returns:
        team_games: pd.DataFrame where all stats columns are of type 'int'.
    """

    cols = [
        col
        for col in team_games.columns
        if "_PTS" in col or "_REB" in col or "_AST" in col or "_STARTER" in col
    ]
    for col in cols:
        team_games[col] = team_games[col].astype(int)

    return team_games


def final_preparation(team_games: pd.DataFrame) -> pd.DataFrame:
    """
    This function performs some final processing steps to the DataFrame games.

    An update that automatizes the process of fetching data from the nba_api and the
    Hopsworks feature store makes this function unnecessary. I leave it for the sake of
    learning.

    Args:
        team_games: pd.DataFrame that contains the team's games data.

    Returns:
        team_games = pd.DataFrame prepared.
    """

    team_games["WIN"] = np.where(team_games["WL"] == "W", 1, 0)
    cols = [
        col
        for col in team_games.columns
        if "_PTS" in col or "_REB" in col or "_AST" in col or "_STARTER" in col
    ]
    cols.append("GAME_ID")
    cols.append("GAME_DATE")
    cols.append("SEASON_ID")
    cols.append("PLAYOFFS")
    cols.append("WIN")
    team_games = team_games[cols].copy()

    for col in team_games.columns:
        team_games.rename(columns={col: col.lower()}, inplace=True)

    return team_games


def pull_data(
    team_id: int, season_init: int, season_end: int, status_message
) -> tuple[pd.DataFrame, int, int]:
    """
    This function returns all regular season and playoff games info from a given team
    and seasons together with its main player stats.

    An update that automatizes the process of fetching data from the nba_api and the
    Hopsworks feature store makes this function unnecessary. I leave it for the sake of
    learning.

    Args:
        team_id: int that contains the team id.
        season_init: int that contains the starting season from which the games info
            will be pulled.
        season_end: int that contains the ending season from which the games info will
            be pulled.

    Returns:
        pd.DataFrame that contains the games info from the given team and seasons.
        int with the number of rows from data in the feature store.
        int with the number of rows from data pulled from the nba_api.
    """

    ### An update that simplifies reading from the feature store makes this commented
    ### code unnecesary. I leave it commented for the sake of learning
    # # Pull games info
    # games = pull_team_games(
    #     team_id=team_id, season_init=season_init, season_end=season_end
    # )

    # # Extract the game ids to check against the info stored in the feature store
    # game_id_list = games["GAME_ID"].to_list()

    # # Columns in the feature store
    # columns = [
    #     "jokic_pts",
    #     "jokic_reb",
    #     "jokic_ast",
    #     "jokic_starter",
    #     "murray_pts",
    #     "murray_reb",
    #     "murray_ast",
    #     "murray_starter",
    #     "rest_pts",
    #     "rest_reb",
    #     "rest_ast",
    #     "game_id",
    #     "game_date",
    #     "season_id",
    #     "playoffs",
    #     "win",
    # ]

    # Extract the seasons (e.g., 2016, 2017, etc.) from the seasons range
    list_1 = list(range(season_init, season_end + 1, 1))
    list_1 = [str(season) for season in list_1]

    ### This reflects the update mentioned above
    # Get the feature group
    feature_group = feature_group_connection_r1()

    # try-except to handle the first time data is inserted into the feature store. This
    # is hanlded within the except
    except_code = 0
    try:
        ### This reflects the update mentioned above
        # Get the feature view
        # feature_group, feature_view = feature_view_connection()

        # Get the data in the feature store
        # feature_store_data = get_feature_store_data(
        #     feature_view=feature_view, game_id_list=game_id_list, columns=columns
        # )
        feature_store_data = get_feature_store_data_r1(
            feature_group=feature_group, season_init=season_init, season_end=season_end
        )

        # Extract the seasons (e.g., 2016, 2017, etc.) from the feature store data
        list_2 = feature_store_data["season_id"].str[1:].unique().tolist()
        # Extract number of seasons not in the feature store
        seasons_not_in_feature_store = [
            element for element in list_1 if element not in list_2
        ]
    except hsfs.client.exceptions.RestAPIError:
        except_code += 1

        ### This reflects the update mentioned above
        # Get the feature group
        # feature_group = first_feature_group_connection()

        seasons_not_in_feature_store = list_1

    # If there're seasons not in the feature store...
    if len(seasons_not_in_feature_store) > 0:
        seasons = ""
        for season in seasons_not_in_feature_store:
            seasons += season + ", "
        message = "Seasons not in the feature store: " + seasons[:-2] + ".\n"
        message += "Pulling and preparing the data..."
        status_message.text(message)

        ### This reflects the update mentioned above
        # season_init_range = min(seasons_not_in_feature_store)
        # season_end_range = max(seasons_not_in_feature_store)
        season_init_range = int(min(seasons_not_in_feature_store))
        season_end_range = int(max(seasons_not_in_feature_store))

        ### This reflects the update mentioned above
        # Pull games info
        # games = games[
        #     (games["SEASON_ID"].str[1:] >= season_init_range)
        #     & (games["SEASON_ID"].str[1:] <= season_end_range)
        # ].copy()
        games = pull_team_games(
            team_id=team_id, season_init=season_init_range, season_end=season_end_range
        )
        # Prepare games data
        games = append_players_stats(players_list=[203999, 1627750], team_games=games)
        games = teammates_stats(team_games=games)
        games = stats_to_int(team_games=games)
        games = final_preparation(team_games=games)

        message = "Data pulling and preparation finished!" + "\n"
        message += "Updating the feature store with new data..."
        status_message.text(message)
        time.sleep(2)

        # Update feature store
        feature_group.insert(games, write_options={"start_offline_backfill": False})
        status_message.text("Feature store updated!")
        time.sleep(2)

        rows_nba = games.shape[0]

        # if-then-else added to handle the first time data is inserted into the feature
        # store. This is handled within the else
        if except_code == 0:
            rows_fs = feature_store_data.shape[0]

            # We prepare the DataFrames to concatenate them
            games_list = [feature_store_data, games]
            for games in games_list:
                games.reset_index(drop=True, inplace=True)

            # We concatenate the DataFrames vertically
            return pd.concat(games_list, axis=0, ignore_index=True), rows_fs, rows_nba
        else:
            return games, 0, rows_nba

    # If the requested data is all in the feature store...
    else:
        message = "All requested data is in the feature store."
        status_message.text(message)
        time.sleep(2)

        return feature_store_data, feature_store_data.shape[0], 0


def pull_games_starters(team_games: pd.DataFrame, date_range: tuple) -> pd.DataFrame:
    """
    This function filters the games data to extract only those games where the players
    whose stats were appended were starters. It takes advantage of the name codification
    of the players starter columns. For each player whose stats were appended to the
    games data, the starter column's name is 'NAME_STARTER'. Thus, the function pulls
    all columns whose names contain '_STARTER', adds them up and filters the data based
    on the result of the sum. Note that the column stores 1 if a player was a starter
    and stores 0 otherwise. Thus, when the sum is equal to the number of players, it
    means all these players were starters.

    Args:
        team_games: pd.DataFrame that contains the team's games data.
        date_range: tuple that contains the selected start and end date of the games
            data to run the analysis.

    Returns:
        filtered_team_games: pd.DataFrame that contains the team's games data from games
            where the players whose stats were appended were starters.
    """

    team_games = team_games[
        (team_games["game_date"] >= date_range[0])
        & (team_games["game_date"] <= date_range[1])
    ].copy()

    # Pull starters info
    cols = [col for col in team_games.columns if "_starter" in col]

    # Add this info up
    team_games["starters"] = team_games[cols].sum(axis=1)

    # Filter the games where the players of interest were starters
    filtered_team_games = team_games[team_games["starters"] == len(cols)].copy()

    # Cleaning and preparation
    team_games.drop("starters", axis=1, inplace=True)
    filtered_team_games.drop("starters", axis=1, inplace=True)
    filtered_team_games.drop(cols, axis=1, inplace=True)
    filtered_team_games.reset_index(drop=True, inplace=True)

    return filtered_team_games


def pull_games_feature_store(
    status_message: DeltaGenerator,
) -> tuple[pd.DataFrame, int]:
    """
    This function pulls the games data from the Hopsworks feature store.

    Args:
        status_message: DeltaGenerator that contains informative messages about the
            process.

    Returns:
        pd.DataFrame that contains the games data.
        int that contains the number of rows (games) in the feature store.
    """

    status_message.text("Connecting to Hopsworks...")
    hsfs_connection, feature_group = feature_group_connection_r1()
    status_message.text("Connected to Hopsworks! Pulling data...")

    games = get_feature_store_data_r2(feature_group=feature_group)
    status_message.text("Data pulled from the feature store!")
    time.sleep(1)

    hsfs_connection.close()
    status_message.text("Hopsworks connection closed!")
    time.sleep(1)

    return games, games.shape[0]
