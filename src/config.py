"""
config.py
    Load Hopsworks-related info stored in environment variables, a JSON file or a
    streamlit secrets file.
"""

import os
import json
import streamlit as st
from dotenv import load_dotenv


class Config:
    """
    Hopsworks-related info.
    """

    def __init__(self):
        self.hostname = None
        self.hopsworks_project_name = None
        self.hopsworks_api_key = None
        self.feature_group_name = None
        self.feature_view_name = None

    def update_attributes_env(self) -> None:
        """
        Update instance attributes.
        """

        # Workaround I was trying to bypass the path issues in Streamlit
        # dotenv_path = ""
        # Path for local development
        # if "DS_Projects" in os.getcwd():
        #     dotenv_path += os.getcwd() + "/.env"
        # Path for streamlit deployment
        # else:
        #     dotenv_path += os.getcwd() + "/src/.env"

        dotenv_path = ".env"
        load_dotenv(dotenv_path=dotenv_path)

        self.hostname = os.environ.get("HOSTNAME")
        self.hopsworks_project_name = os.environ.get("HOPSWORKS_PROJECT_NAME")
        self.hopsworks_api_key = os.environ.get("HOPSWORKS_API_KEY")
        self.feature_group_name = os.environ.get("FEATURE_GROUP_NAME")
        self.feature_view_name = os.environ.get("FEATURE_VIEW_NAME")

    def update_attributes_json(self) -> None:
        """
        Update instance attributes.
        """

        # Workaround I was trying to bypass the path issues in Streamlit
        # json_file_path = ""
        # Path for local development
        # if "DS_Projects" in os.getcwd():
        #     json_file_path += os.getcwd() + "/metadata.json"
        # Path for stremlit deployment
        # else:
        #     json_file_path += os.getcwd() + "/src/metadata.json"

        json_file_path = "metadata.json"

        # Open and read the JSON file
        with open(json_file_path, "r") as json_file:
            # Load the JSON data into a Python dictionary
            data = json.load(json_file)

        self.hostname = data["HOSTNAME"]
        self.hopsworks_project_name = data["HOPSWORKS_PROJECT_NAME"]
        self.hopsworks_api_key = data["HOPSWORKS_API_KEY"]
        self.feature_group_name = data["FEATURE_GROUP_NAME"]
        self.feature_view_name = data["FEATURE_VIEW_NAME"]

    def update_attributes_st(self) -> None:
        """
        Update instance attributes. This is the method used in the final implementation.
        """

        self.hostname = st.secrets["HOSTNAME"]
        self.hopsworks_project_name = st.secrets["HOPSWORKS_PROJECT_NAME"]
        self.hopsworks_api_key = st.secrets["HOPSWORKS_API_KEY"]
        self.feature_group_name = st.secrets["FEATURE_GROUP_NAME"]
        self.feature_view_name = st.secrets["FEATURE_VIEW_NAME"]
