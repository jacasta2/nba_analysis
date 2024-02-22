"""
fetch_data.py
    This script contains supporting functions to pull NBA data using a GitHub action. 
"""

import os
import numpy as np
import pandas as pd
from hsfs.feature_group import FeatureGroup
from nba_api.stats.endpoints import boxscoretraditionalv2, leaguegamefinder
from feature_store import feature_group_connection_r2, get_date_most_recent_game_fs

HOPSWORKS_API_KEY = os.environ.get("HOPSWORKS_API_KEY")
HOPSWORKS_PROJECT_NAME = os.environ.get("HOPSWORKS_PROJECT_NAME")
FEATURE_GROUP_NAME = os.environ.get("FEATURE_GROUP_NAME")


def append_players_stats(players_list: list, team_games: pd.DataFrame) -> pd.DataFrame:
    """
    This function appends to a team's games info DataFrame from a single season the
    three main stats (points, rebounds and assists) from a given set of its players.
    The function also appends info on whether the players were starters in the games.
    This function is called within another function that loops through seasons.

    Args:
        players_list: list that contains the players' ids.
        team_games: pd.DataFrame that contains the team's games data from a single
            season.

    Returns:
        pd.DataFrame that contains the team's games data from a single season,
        including the main stats from the given set of players.
    """

    # We load the nba_players info
    players_path = "../data/nba_players.csv"
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


def teammates_stats(team_games: pd.DataFrame) -> pd.DataFrame:
    """
    This function compute the main stats (PTS, REB and AST) from the rest of the
    teammates, i.e., from the teammates whose stats weren't appended to the games data.
    It takes advantage of the name codification of the players stats columns. For
    example, for each player whose stats were appended to the games data, the points
    column's name is 'NAME_PTS'. Thus, the function pulls all columns whose names
    contain '_PTS', adds these points up and substracts them from the whole team points.

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


def push_data_to_feature_store(
    feature_group: FeatureGroup, team_games: pd.DataFrame
) -> None:
    """
    This function pushes the DataFrame team_games to the feature store.

    Args:
        feature_group: FeatureGroup where the DataFrame team_games will be pushed.
        team_games: pd.DataFrame that contains the team's games data.
    """

    team_games = append_players_stats(
        players_list=[203999, 1627750], team_games=team_games
    )
    team_games = teammates_stats(team_games=team_games)
    team_games = stats_to_int(team_games=team_games)
    team_games = final_preparation(team_games=team_games)

    feature_group.insert(team_games, write_options={"start_offline_backfill": False})


def fetch_recent_games() -> None:
    """
    This function pulls the date from the most recent game available in the feature
    store and uses this date to pull games from the day after using the nba_api.
    """

    # We connect to the feature group
    feature_group = feature_group_connection_r2(
        params_list=[
            HOPSWORKS_API_KEY,
            HOPSWORKS_PROJECT_NAME,
            FEATURE_GROUP_NAME,
        ]
    )

    # We pull data from the feature store and we get the date from the most recent game
    # available in the data
    most_recent_date = get_date_most_recent_game_fs(feature_group=feature_group)

    # We split the date into its elements and create a new date variable with the format
    # required by the endpoint LeagueGameFinder
    date_elements = most_recent_date.split("-")
    year = date_elements[0]
    month = date_elements[1]
    day = date_elements[2]
    date_from = month + "/" + day + "/" + year

    # We pull regular season games by calling the endpoint LeagueGameFinder
    new_data_regular_season = leaguegamefinder.LeagueGameFinder(
        team_id_nullable=1610612743,
        date_from_nullable=date_from,
        date_to_nullable="01/31/2024",  # Testing
        season_type_nullable="Regular Season",
    ).get_data_frames()[0]

    # We drop summer league games, if any. They're played in July, so we drop games
    # whose date has July as the month
    summer_league_games = new_data_regular_season[
        new_data_regular_season["GAME_DATE"].str[5:7] == "07"
    ].index
    new_data_regular_season.drop(summer_league_games, inplace=True)

    # We pull playoff games by calling the endpoint LeagueGameFinder
    new_data_playoffs = leaguegamefinder.LeagueGameFinder(
        team_id_nullable=1610612743,
        date_from_nullable=date_from,
        season_type_nullable="Playoffs",
    ).get_data_frames()[0]

    # We concat regular season and playoff dataframes checking whether they're empty

    # Fetched data include both regular season and playoff games
    if len(new_data_regular_season) > 0 and len(new_data_playoffs) > 0:
        new_data_regular_season["PLAYOFFS"] = 0
        new_data_playoffs["PLAYOFFS"] = 1
        games = pd.concat(
            [new_data_regular_season, new_data_playoffs], axis=0, ignore_index=True
        )
        push_data_to_feature_store(feature_group=feature_group, team_games=games)
        print(
            "Data from recent games fetched, prepared and pushed into the feature \
            store."
        )

    # Fetched data include only regular season games
    elif len(new_data_regular_season) > 0 and len(new_data_playoffs) == 0:
        new_data_regular_season["PLAYOFFS"] = 0
        games = new_data_regular_season
        push_data_to_feature_store(feature_group=feature_group, team_games=games)
        print(
            "Data from recent games fetched, prepared and pushed into the feature \
            store."
        )

    # Fetched data include only playoff games
    elif len(new_data_regular_season) == 0 and len(new_data_playoffs) > 0:
        new_data_playoffs["PLAYOFFS"] = 1
        games = new_data_playoffs
        push_data_to_feature_store(feature_group=feature_group, team_games=games)
        print(
            "Data from recent games fetched, prepared and pushed into the feature \
            store."
        )

    # There's no data (off season)
    else:
        print(
            "There is no data from recent games to fetch, prepare and push into the \
            feature store."
        )
        # return pd.DataFrame()


if __name__ == "__main__":

    fetch_recent_games()
