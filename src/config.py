"""
config.py
    Load Hopsworks-related info stored in environment variables or a JSON file.
"""

import os
import json
from dotenv import load_dotenv

class Config:
    """
    Hopsworks-related info
    """

    def __init__(self):
        self.hopsworks_project_name = None
        self.hopsworks_api_key = None
        self.feature_group_name = None
        self.feature_view_name = None


    def update_attributes_env(self) -> None:
        """
        Update instance attributes
        """

        
        dotenv_path = os.getcwd() + '/.env'
        load_dotenv(dotenv_path = dotenv_path)

        self.hopsworks_project_name = os.environ.get('HOPSWORKS_PROJECT_NAME')
        self.hopsworks_api_key = os.environ.get('HOPSWORKS_API_KEY')
        self.feature_group_name = os.environ.get('FEATURE_GROUP_NAME')
        self.feature_view_name = os.environ.get('FEATURE_VIEW_NAME')


    def update_attributes_json(self) -> None:
        """
        Update instance attributes
        """
        
        json_file_path = ''
        if 'DS_Projects' in os.getcwd():
            json_file_path += os.getcwd() + '/metadata.json'
        else:
            json_file_path += os.getcwd() + '/src/metadata.json'

        # Open and read the JSON file
        with open(json_file_path, 'r') as json_file:
            # Load the JSON data into a Python dictionary
            data = json.load(json_file)

        self.hopsworks_project_name = data['HOPSWORKS_PROJECT_NAME']
        self.hopsworks_api_key = data['HOPSWORKS_API_KEY']
        self.feature_group_name = data['FEATURE_GROUP_NAME']
        self.feature_view_name = data['FEATURE_VIEW_NAME']
