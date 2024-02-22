"""
feature_store.py
    This script contains all supporting functions to connect to Hopsworks.
"""

import hopsworks
import pandas as pd
from hsfs.feature_group import FeatureGroup
from hsfs.feature_store import FeatureStore
from hsfs.feature_view import FeatureView
from config import Config
from utils import add_one_day


def feature_store_connection(my_config: Config) -> FeatureStore:
    """
    Connects to Hopsworks and returns a pointer to the feature store.

    Returns:
        feature_store: FeatureStore pointer to the feature store.
    """

    project = hopsworks.login(
        project=my_config.hopsworks_project_name,
        api_key_value=my_config.hopsworks_api_key,
    )
    feature_store = project.get_feature_store()
    return feature_store


def feature_group_connection(my_config: Config) -> tuple[FeatureStore, FeatureGroup]:
    """
    Connects to the feature store and returns a pointer to the feature store and feature
    group. An update that simplifies reading from the feature store makes this function
    unnecessary. I replace it with the function feature_group_connection_r1 below. I
    leave this function for the sake of learning.

    Returns:
        feature_store: FeatureStore pointer to the feature store.
        feature_group: FeatureGroup pointer to the feature group.
    """

    feature_store = feature_store_connection(my_config)
    feature_group = feature_store.get_or_create_feature_group(
        name=my_config.feature_group_name,
        version=1,
        description="Games data from Denver Nuggets",
        primary_key=["game_id"],
        online_enabled=True,
    )
    return feature_store, feature_group


def feature_view_connection() -> tuple[FeatureGroup, FeatureView]:
    """
    Connects to the feature group and returns a pointer to the feature view. An update
    that simplifies reading from the feature store makes this function unnecessary. I
    replace it with the function feature_group_connection_r1 below. I leave this
    function for the sake of learning.

    Returns:
        feature_group: FeatureGroup pointer to the feature group.
        feature_view: FeatureView pointer to the feature view.
    """

    my_config = Config()
    # my_config.update_attributes_env() # Use if working with metadata stored in env
    # variables
    # my_config.update_attributes_json() # Use if working with metadata stored in a
    # json file
    my_config.update_attributes_st()

    feature_store, feature_group = feature_group_connection(my_config)
    feature_view = feature_store.get_or_create_feature_view(
        name=my_config.feature_view_name, version=1, query=feature_group.select_all()
    )
    return feature_group, feature_view


def get_feature_store_data(
    feature_view: FeatureView, game_id_list: list, columns: list
) -> pd.DataFrame:
    """
    Pulls data from the feature store. An update that simplifies reading from the
    feature store makes this function unnecessary. I replace it with the function
    get_feature_store_data_r1 below. I leave this function for the sake of learning.

    Args:
        feature_view: FeatureView used to pull the data.
        game_id_list: list that contains game ids, which are used to pull the data from
            the feature store.
        columns: list that contains the column names.

    Returns:
        dataframe: pd.DataFrame with data pulled from the feature store.
    """

    dataframe = feature_view.get_feature_vectors(
        entry=[{"game_id": game_id} for game_id in game_id_list]
    )
    dataframe = pd.DataFrame(dataframe, columns=columns)
    return dataframe


def first_feature_group_connection() -> FeatureGroup:
    """
    Connects to the feature store and returns a pointer to the feature group the first
    time data is going to be inserted into the feature store. An update that simplifies
    reading from the feature store makes this function unnecessary. I replace it with
    the function feature_group_connection_r1 below. I leave this function for the sake
    of learning.

    Returns:
        feature_group: FeatureGroup pointer to the feature group.
    """

    my_config = Config()
    # my_config.update_attributes_env() # Use if working with metadata stored in env
    # variables
    # my_config.update_attributes_json() # Use if working with metadata stored in a
    # json file
    my_config.update_attributes_st()

    feature_store = feature_store_connection(my_config)
    feature_group = feature_store.get_or_create_feature_group(
        name=my_config.feature_group_name,
        version=1,
        description="Games data from Denver Nuggets",
        primary_key=["game_id"],
        online_enabled=True,
    )
    return feature_group


def get_feature_store_data_r1(
    feature_group: FeatureGroup, season_init: int, season_end: int
) -> pd.DataFrame:
    """
    Pulls data from the feature store.

    Args:
        feature_group: FeatureGroup used to pull the data.
        season_init: int that contains the starting season from which the games info
            will be pulled.
        season_end: int that contains the ending season from which the games info will
            be pulled.

    Returns:
        dataframe: pd.DataFrame with data pulled from the feature store.
    """

    # Pull data from feature store
    dataframe = feature_group.read(online=True)

    # Filter data according to selected seasons range
    dataframe = dataframe[
        (dataframe["season_id"].str[1:] >= str(season_init))
        & (dataframe["season_id"].str[1:] <= str(season_end))
    ].copy()

    # Some processing
    dataframe.sort_values(by="game_date", ascending=True, inplace=True)
    dataframe.reset_index(drop=True, inplace=True)

    return dataframe


def feature_group_connection_r1() -> FeatureGroup:
    """
    Connects to the feature store and returns a pointer to the feature group.

    Returns:
        feature_group: FeatureGroup pointer to the feature group.
    """

    my_config = Config()
    my_config.update_attributes_st()

    feature_store = feature_store_connection(my_config)

    feature_group = feature_store.get_or_create_feature_group(
        name=my_config.feature_group_name,
        version=1,
        description="Games data from Denver Nuggets",
        primary_key=["game_id"],
        online_enabled=True,
    )

    return feature_group


def feature_group_connection_r2(params_list: list) -> FeatureGroup:
    """
    Connects to the feature store and returns a pointer to the feature group. This
    connection is used to fetch recent games data and push it into the feature store
    using GitHub actions.

    Args:
        params_list: list that contains the parameters needed to connect to the feature
        store (Hopsworks API key, project name and feature group name).

    Returns:
        feature_group: FeatureGroup pointer to the feature group.
    """

    project = hopsworks.login(
        project=params_list[1],
        api_key_value=params_list[0],
    )

    feature_store = project.get_feature_store()

    feature_group = feature_store.get_or_create_feature_group(
        name=params_list[2],
        version=1,
        description="Games data from Denver Nuggets",
        primary_key=["game_id"],
        online_enabled=True,
    )

    return feature_group


def get_date_most_recent_game_fs(feature_group: FeatureGroup) -> str:
    """
    Pulls date from most recent game available in the feature store. It's used to fetch
    recent games data and push it into the feature store using GitHub actions.

    Args:
        feature_group: FeatureGroup used to pull the data.

    Returns:
        recent_date: string with the date from the most recent game available in the
            feature store. The format is yyyy-mm-dd.
    """

    # Pull data from feature store
    dataframe = feature_group.read(online=True)

    # Some processing
    dataframe.sort_values(by="game_date", ascending=False, inplace=True)
    dataframe.reset_index(drop=True, inplace=True)

    recent_date = dataframe.loc[0, "game_date"]
    del dataframe
    recent_date = add_one_day(recent_date)

    return recent_date
