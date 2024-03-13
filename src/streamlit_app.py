"""
streamlit_app.py
    This script contains the app's frontend. 
"""

import time
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from streamlit.delta_generator import DeltaGenerator
from data import pull_games_starters, pull_games_feature_store
from modeling import (
    prepare_data,
    log_reg_results,
    shap_values_results,
    shap_values_plot,
)


def pull_games_feature_store_(
    status_message: DeltaGenerator
) -> tuple[pd.DataFrame, int]:
    """
    This function pulls data from the Hopsworks feature store.

    Args:
        message: DeltaGenerator that contains informative messages about the process.

    Returns:
        pd.DataFrame with NBA data.
        int with number of rows (games) in DataFrame from feature store.
    """

    return pull_games_feature_store(status_message=status_message)


# Use all space in the layout
st.set_page_config(layout="wide")

# App's title (since all layout is used, we need to center-align the title)
st.markdown(
    "<h1 style='text-align: center'>Jokic's assists vs. Murray's points</h1>",
    unsafe_allow_html=True,
)
# App's description
DESCRIPTION = """
This app pulls Denver Nuggets' games data from a Hopsworks feature store and analizes
the importance of Jokic's assists and Murray's points to determine whether the Nuggets
win a game. You have to click **Pull data** to fetch the data from the feature store
(the data is already prepared). The feature store is automatically updated once every
week in the background with prepared data. Once the data is pulled, you have to select a
date range (by default, the app selects the oldest and most recent dates from the pulled
games). Then, by clicking **Run**, the app filters games within such range where both
Jokic and Murray were starters and runs the analysis. The app provides a graphical
analysis based on standardized logistic regression coefficients and SHAP values. The
analysis also considers Jokic's points and rebounds, Murray's assists and rebounds and
the points, rebounds and assists from the rest of their teammates, totaling 9 features.
"""
st.markdown(DESCRIPTION)
# Placeholder for informative messages
status_message = st.empty()


# Initialize the DataFrames that will contain the data used in the analysis
if "games" not in st.session_state:
    st.session_state.games = pd.DataFrame()
if "games_starters" not in st.session_state:
    st.session_state.games_starters = pd.DataFrame()


### Pull data from feature store
st.sidebar.header("Feature store")
# Games button
if st.sidebar.button("Pull data"):
    if st.session_state.games.empty:

        st.session_state.games, number_games = pull_games_feature_store_(
            status_message=status_message
        )

        MESSAGE = "Job finished!" + "\n"
        MESSAGE += (
            "We pulled " + str(number_games) + " observations from the feature store."
        )
        status_message.text(MESSAGE)

        # Display the first five rows of the DataFrame
        st.header("Games")
        st.dataframe(st.session_state.games.head())
    else:
        status_message.text("The data was already pulled from the feature store.")


### Run the analysis
# Run button
if st.session_state.games.empty:
    status_message.text("Pull the data from the feature store to run the analysis.")
else:
    st.sidebar.header("Analysis")
    min_date = pd.to_datetime(st.session_state.games["game_date"]).min()
    max_date = pd.to_datetime(st.session_state.games["game_date"]).max()
    selected_date_range = st.sidebar.date_input(
        label="Select date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    # Catch error associated with the selection of the end date. When selecting the
    # range, once the start date is selected, an error is raised because the end date
    # is not selected yet.
    try:
        start_date_str = selected_date_range[0].strftime("%Y-%m-%d")
        end_date_str = selected_date_range[1].strftime("%Y-%m-%d")
    except IndexError:
        status_message.text("Make sure to select a date range.")

    if st.sidebar.button("Run"):

        # Catch error associated with the selection of the end date. If no end date is
        # selected, the app still runs, so we need to control that the end date is
        # selected
        try:
            # Container with the two main plots from the analysis
            container_1 = st.container()
            container_1.col1, container_1.col2 = st.columns(2)

            # Extract the number of games where both Jokic and Murray were starters
            st.session_state.games_starters = pull_games_starters(
                team_games=st.session_state.games,
                date_range=(start_date_str, end_date_str),
            )
            number_of_games = st.session_state.games_starters.shape[0]
            status_message.text(
                "There're "
                + str(number_of_games)
                + " games where both Jokic and Murray were starters in the selected "
                + "date range."
            )
            time.sleep(2)

            if number_of_games < 180:
                NUMBER_OF_GAMES_STR = str(number_of_games)
                MESSAGE = """
                A common rule-of-thumb indicates we need at least 10-20 observations per
                predictor to run a regression. As a conservative measure, we should work
                with the upper bound. Thus, with 9 features, we would need at least 180
                observations to run the analysis. Currently, {0} observations were
                selected. Please revise the date range and try again.
                """
                MESSAGE = MESSAGE.format(NUMBER_OF_GAMES_STR)
                st.warning(MESSAGE)
            else:
                status_message.text("Running the logistic regression analysis...")
                # Split data into standardized independent variables and dependent
                # variable
                x_train, y_train = prepare_data(st.session_state.games_starters)
                # Fit a logistic regression (using statsmodels) and plot the
                # coefficients
                jokic, murray, diff_test, bar_plot = log_reg_results(
                    x_train=x_train, y_train=y_train
                )
                container_1.col1.pyplot(bar_plot)
                time.sleep(1)

                status_message.text("Running the SHAP values analysis...")
                fig, ax = plt.subplots()
                ax.set_title("SHAP values")
                # Compute the SHAP values. We remove the last column of the predictors
                # in the slicing since an intercept column is added to 'X_train' in
                # 'log_reg_plot()' and this column is no longer needed since
                # scikit-learn adds it by default when fitting a logistic regression
                (
                    shap_values,
                    jokic_shap_value,
                    jokic_prob,
                    murray_shap_value,
                    murray_prob,
                ) = shap_values_results(x_train=x_train.iloc[:, :-1], y_train=y_train)

                # Plot the SHAP values
                shap_values_plot(shap_values=shap_values, x_train=x_train.iloc[:, :-1])
                plt.figure().set_figheight(4)
                container_1.col2.pyplot(fig)
                time.sleep(1)

                status_message.text("Job finished! See the results below.")

                # Container describing Jokic's results
                container_2 = st.container()
                container_2.col1, container_2.col2 = st.columns(2)

                MESSAGE_1 = (
                    "A 1-standard deviation increase in Jokic's assists increases "
                    + "the odds of winning by "
                    + str(jokic[0])
                    + "%. This is a "
                    + str(jokic[1])
                    + "% increase in the chances of winning."
                )
                MESSAGE_2 = (
                    "The coefficient of Jokic's assists isn't statistically "
                    + "significant."
                )
                MESSAGE = MESSAGE_1 if jokic[2] <= 0.05 else MESSAGE_2
                container_2.col1.info(MESSAGE)

                MESSAGE = (
                    "Jokic's assists increase the log odds of winning by "
                    + str(jokic_shap_value)
                    + ". This is a "
                    + str(jokic_prob)
                    + "% increase in the chances of winning."
                )
                container_2.col2.info(MESSAGE)

                # Container describing Murray's results
                container_3 = st.container()
                container_3.col1, container_3.col2 = st.columns(2)

                MESSAGE_1 = (
                    "A 1-standard deviation increase in Murray's points increases the "
                    + "odds of winning by "
                    + str(murray[0])
                    + "%. This is a "
                    + str(murray[1])
                    + "% increase in the chances of winning."
                )
                MESSAGE_2 = (
                    "The coefficient of Murray's points isn't statistically "
                    + "significant."
                )
                MESSAGE = MESSAGE_1 if murray[2] <= 0.05 else MESSAGE_2
                container_3.col1.info(MESSAGE)

                MESSAGE = (
                    "Murray's points increase the log odds of winning by "
                    + str(murray_shap_value)
                    + ". This is a "
                    + str(murray_prob)
                    + "% increase in the chances of winning."
                )
                container_3.col2.info(MESSAGE)

                # Container comparing Jokic and Murray results from logistic regression
                container_4 = st.container()
                container_4.col1, container_4.col2 = st.columns(2)
                MESSAGE_1 = "The coefficients are statistically different"
                MESSAGE_2 = (
                    "We cannot statistically rule out the possibility that the "
                    + "coefficients are similar"
                )
                MESSAGE = MESSAGE_1 if diff_test[1] <= 0.05 else MESSAGE_2
                MESSAGE += (
                    " (z = " + str(diff_test[0]) + ", p = " + str(diff_test[1]) + ")."
                )
                container_4.col1.info(MESSAGE)

                container_5 = st.container()
                MESSAGE = """
                Caution is advised when interpreting the results. Even if there's a
                statistically significant difference between the standardized regression
                coefficients, such difference could be due to a difference between these
                features' standard deviations (if such difference exists). Nonetheless,
                this exercise can still provide an overall picture to understand how
                different stats contribute to a Nuggets' win.
                """
                container_5.warning(MESSAGE)
        except NameError:
            status_message.text("Make sure to select a date range.")
