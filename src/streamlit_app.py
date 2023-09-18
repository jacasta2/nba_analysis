"""
streamlit_app.py
    This script contains the app's frontend. 
"""

import time
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from data import pull_data, pull_games_starters
from modeling import (
    prepare_data,
    log_reg_results,
    shap_values_results,
    shap_values_plot,
)

# Use all space in the layout
st.set_page_config(layout="wide")

# App's title (since all layout is used, we need to center-align the title)
st.markdown(
    "<h1 style='text-align: center'>Jokic's assists vs. Murray's points</h1>",
    unsafe_allow_html=True,
)
# App's description
DESCRIPTION = """
This app pulls Denver Nuggets' games data, filters games where both Jokic and Murray
were starters and provides a graphical analysis on the importance of Jokic's assists and
Murray's points to determine whether the Nuggets win a game. The analysis also considers
Jokic's points and rebounds, Murray's assists and rebounds and the points, rebounds and
assists from the rest of their teammates, totaling 9 features. 
"""
st.markdown(DESCRIPTION)
# Placeholder for informative messages
status_message = st.empty()

# Initialize the DataFrames that will contain the data used in the analysis
if "games" not in st.session_state:
    st.session_state.games = pd.DataFrame()
if "games_starters" not in st.session_state:
    st.session_state.games_starters = pd.DataFrame()

### Pull games
# Seasons sliders
st.sidebar.header("Select season range")
MIN_SEASON = 2016
MAX_SEASON = 2022
start_year = st.sidebar.slider("Start season", MIN_SEASON, MAX_SEASON, MIN_SEASON)
end_year = st.sidebar.slider("End season", start_year, MAX_SEASON, start_year)
# Games button
if st.sidebar.button("Get games"):

    def pull_data_() -> tuple[pd.DataFrame, int, int]:
        """
        This function pulls NBA data.

        Returns:
            pd.DataFrame with NBA data.
            int with number of rows in DataFrame from feature store.
            int with number of rows in DataFrame pulled from the nba_api.
        """

        return pull_data(1610612743, start_year, end_year, status_message)

    status_message.text("Checking if requested data is in the feature store...")

    # Pull data
    st.session_state.games, rows_fs, rows_nba = pull_data_()
    # Extract the number of games from which data was pulled
    number_of_games = st.session_state.games.shape[0]

    MESSAGE = "Job finished!" + "\n"
    MESSAGE += (
        "We pulled " + str(rows_fs) + " observations from the feature store." + "\n"
    )
    MESSAGE += "We pulled " + str(rows_nba) + " observations from the nba_api."
    status_message.text(MESSAGE)

    # Display the last five rows of the DataFrame
    st.header("Games")
    st.dataframe(st.session_state.games.tail())

### Run the analysis
# Run button
st.sidebar.header("Run analysis")
if st.sidebar.button("Run"):
    if st.session_state.games.empty:
        status_message.text("There's no data to run the analysis.")
    else:
        # Container with the two main plots from the analysis
        container_1 = st.container()
        container_1.col1, container_1.col2 = st.columns(2)

        # Extract the number of games where both Jokic and Murray were starters
        st.session_state.games_starters = pull_games_starters(st.session_state.games)
        number_of_games = st.session_state.games_starters.shape[0]
        status_message.text(
            "There're "
            + str(number_of_games)
            + " games where both Jokic and Murray were starters."
        )
        time.sleep(2)

        if number_of_games < 180:
            NUMBER_OF_GAMES_STR = str(number_of_games)
            MESSAGE = """
            A common rule-of-thumb indicates one needs at least 10-20 observations per
            predictor to run a regression. As a conservative measure, one should work
            with the upper bound. Thus, with 9 features, one would need at least 180
            observations to run the analysis. Currently, {0} observations were pulled.
            Please pull more data.
            """
            MESSAGE = MESSAGE.format(NUMBER_OF_GAMES_STR)
            st.warning(MESSAGE)
        else:
            status_message.text("Running the logistic regression analysis...")
            # Split data into standardized independent variables and dependent variable
            x_train, y_train = prepare_data(st.session_state.games_starters)
            # Fit a logistic regression (using statsmodels) and plot the coefficients
            jokic, murray, diff_test, bar_plot = log_reg_results(
                x_train=x_train, y_train=y_train
            )
            container_1.col1.pyplot(bar_plot)

            status_message.text("Running the SHAP values analysis...")
            fig, ax = plt.subplots()
            ax.set_title("SHAP values")
            # Compute the SHAP values. We remove the last column of the predictors in
            # the slicing since an intercept column is added to 'X_train' in
            # 'log_reg_plot()' and this column is no longer needed since scikit-learn
            # adds it by default when fitting a logistic regression
            shap_values, jokic_shap_value, murray_shap_value = shap_values_results(
                x_train=x_train.iloc[:, :-1], y_train=y_train
            )
            # Plot the SHAP values
            shap_values_plot(shap_values=shap_values, x_train=x_train.iloc[:, :-1])
            plt.figure().set_figheight(4)
            container_1.col2.pyplot(fig)

            status_message.text("Job finished!")

            # Container describing Jokic's results
            container_2 = st.container()
            container_2.col1, container_2.col2 = st.columns(2)

            MESSAGE_1 = "A 1-standard deviation increase in Jokic's assists increases"
            MESSAGE_1 += " the odds of winning by " + str(jokic[0]) + "%."
            MESSAGE_2 = (
                "The coefficient of Jokic's assists isn't statistically significant."
            )
            MESSAGE = MESSAGE_1 if jokic[1] <= 0.05 else MESSAGE_2
            container_2.col1.info(MESSAGE)

            MESSAGE = (
                "Jokic's assists increase the log odds of winning by "
                + str(jokic_shap_value)
                + "."
            )
            container_2.col2.info(MESSAGE)

            # Container describing Murray's results
            container_3 = st.container()
            container_3.col1, container_3.col2 = st.columns(2)

            MESSAGE_1 = "A 1-standard deviation increase in Murray's points increases "
            MESSAGE_1 += "the odds of winning by " + str(murray[0]) + "%."
            MESSAGE_2 = (
                "The coefficient of Murray's points isn't statistically significant."
            )
            MESSAGE = MESSAGE_1 if murray[1] <= 0.05 else MESSAGE_2
            container_3.col1.info(MESSAGE)

            MESSAGE = (
                "Murray's points increase the log odds of winning by "
                + str(murray_shap_value)
                + "."
            )
            container_3.col2.info(MESSAGE)

            # Container comparing Jokic and Murray results from logistic regression
            container_4 = st.container()
            container_4.col1, container_4.col2 = st.columns(2)
            MESSAGE_1 = "The coefficients are statistically different"
            MESSAGE_2 = "We cannot statistically rule out the possibility that the "
            MESSAGE_2 += "coefficients are similar"
            MESSAGE = MESSAGE_1 if diff_test[1] <= 0.05 else MESSAGE_2
            MESSAGE += (
                " (z = " + str(diff_test[0]) + ", p = " + str(diff_test[1]) + ")."
            )
            container_4.col1.info(MESSAGE)
