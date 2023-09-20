"""
feature_store.py
    This script contains all supporting functions to connect to Hopsworks.
"""

import pandas as pd
from hsfs.feature_store import FeatureStore
from hsfs.feature_group import FeatureGroup
from hsfs.feature_view import FeatureView
import hopsworks
from config import Config


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


def get_feature_store_data_r1(feature_group: FeatureGroup) -> pd.DataFrame:
    """
    Pulls data from the feature store.

    Args:
        feature_group: FeatureGroup used to pull the data.

    Returns:
        dataframe: pd.DataFrame with data pulled from the feature store.
    """

    dataframe = feature_group.read(online=True)
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
