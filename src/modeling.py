"""
modeling.py
    This script contains the modeling work.
"""

import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import scipy.stats
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
import statsmodels.api as sm
import shap
from utils import log_odds_to_prob, odds_to_prob


def prepare_data(games_data: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    This function standardize the predictors and returns both these standardized
    predictors and the dependent variable.

    Args:
        games_data: pd.DataFrame that contains the team's games data.
    Returns:
        X_train: pd.DataFrame with predictors.
        y_train: pd.DataFrame with the games' result (1: win, 0: loss).
    """

    # Columns for the analysis
    columns = [
        "jokic_pts",
        "jokic_reb",
        "jokic_ast",
        "murray_pts",
        "murray_reb",
        "murray_ast",
        "rest_pts",
        "rest_reb",
        "rest_ast",
    ]

    x_train = games_data[columns].copy()
    scaler = StandardScaler()
    x_train = pd.DataFrame(scaler.fit_transform(x_train), columns=x_train.columns)
    y_train = games_data.iloc[:, -1]

    return x_train, y_train


def log_reg_results(
    x_train: pd.DataFrame, y_train: pd.DataFrame
) -> tuple[list, list, list, Figure]:
    """
    This function fits a logistic regression model to the standardized games data and
    returns a bar plot of the coefficients with 95% CI.

    Args:
        X_train: pd.DataFrame with the predictors.
        y_train: pd.DataFrame with the games' result (1: win, 0: loss).
    Returns:
        jokic: list with Jokic's assists coefficient, probability equivalent and its
            p-value.
        murray: list with Murray's points coefficient, probability equivalent and its
            p-value.
        diff_test: list with results from test evaluating differences between Jokic and
            Murray regression coefficients.
        fig: Figure bar plot of the regression coefficients.
    """

    x_train["Intercept"] = 1
    log_reg = sm.Logit(y_train, x_train).fit()

    # Extract all coefficients but the Intercept
    summary = log_reg.summary2().tables[1].iloc[:-1, :]
    summary.sort_values(by="Coef.", inplace=True)

    # Extract the coefficients for the interpretation
    jokic_coeff = summary.loc["jokic_ast", "Coef."]
    jokic_assists = round((math.exp(jokic_coeff) - 1) * 100, 2)
    jokic_prob = round(odds_to_prob(math.exp(jokic_coeff) - 1) * 100, 2)
    jokic_assists_p = round(summary.loc["jokic_ast", "P>|z|"], 2)
    jokic = [jokic_assists, jokic_prob, jokic_assists_p]

    murray_coeff = summary.loc["murray_pts", "Coef."]
    murray_points = round((math.exp(murray_coeff) - 1) * 100, 2)
    murray_prob = round(odds_to_prob(math.exp(murray_coeff) - 1) * 100, 2)
    murray_points_p = round(summary.loc["murray_pts", "P>|z|"], 2)
    murray = [murray_points, murray_prob, murray_points_p]

    # Extract additional information to test differences between Jokic and Murray
    # coefficients
    jokic_var = log_reg.cov_params().loc["jokic_ast", "jokic_ast"]
    murray_var = log_reg.cov_params().loc["murray_pts", "murray_pts"]
    covar = log_reg.cov_params().loc["jokic_ast", "murray_pts"]
    # Run test
    diff = (
        jokic_coeff - murray_coeff
        if jokic_coeff >= murray_coeff
        else murray_coeff - jokic_coeff
    )
    z_score = diff / ((jokic_var + murray_var - 2 * covar) ** (1 / 2))
    p_value = scipy.stats.norm.sf(z_score) * 2
    diff_test = [round(z_score, 2), round(p_value, 2)]

    # Extract the names, the estimates and the values for the error bars
    coef_names = summary.index
    coef_estimates = summary["Coef."]
    coef_error = summary["Coef."] - summary["[0.025"]
    # Create a bar plot with error bars
    fig, axis = plt.subplots()
    fig.set_figheight(4)
    axis.barh(coef_names, coef_estimates, xerr=coef_error, capsize=4)
    axis.set_xlabel("Value")
    axis.set_ylabel("Coefficient")
    axis.set_title("Standardized logistic regression coefficients with 95% CI")
    axis.axvline(
        x=0, color="black", linewidth=0.8, linestyle="--"
    )  # Add vertical line at zero

    return jokic, murray, diff_test, fig


def shap_values_results(
    x_train: pd.DataFrame, y_train: pd.DataFrame
) -> tuple[np.ndarray, float, float, float, float]:
    """
    This function computes the SHAP values of the games data and returns them together
    with the SHAP values of Jokic's assists and Murray's points.

    Args:
        X_train: pd.DataFrame with the predictors.
        y_train: pd.DataFrame with the games' result (1: win, 0: loss).
    Returns:
        shap_values: np.ndarray with SHAP values.
        jokic_shap_value: float with Jokic's assists SHAP value.
        jokic_prob: float with the increased probability of winning a game associated
            with Jokic's assists SHAP value.
        murray_shap_value: float with Murray's points SHAP value.
        murray_prob: float with the increased probability of winning a game associated
            with Murray's points SHAP value.
    """

    log_reg = LogisticRegression(max_iter=200)
    log_reg.fit(x_train, y_train)
    explainer = shap.Explainer(log_reg, x_train)
    shap_values = explainer.shap_values(x_train)

    # Bring the SHAP values to a DataFrame
    shap_values_df = pd.DataFrame(shap_values, columns=x_train.columns)
    jokic_shap_value = round(shap_values_df["jokic_ast"].abs().mean(), 2)
    jokic_prob = round(
        log_odds_to_prob(shap_values_df["jokic_ast"].abs().mean()) * 100, 2
    )
    murray_shap_value = round(shap_values_df["murray_pts"].abs().mean(), 2)
    murray_prob = round(
        log_odds_to_prob(shap_values_df["murray_pts"].abs().mean()) * 100, 2
    )

    return shap_values, jokic_shap_value, jokic_prob, murray_shap_value, murray_prob


def shap_values_plot(shap_values: np.ndarray, x_train: pd.DataFrame):
    """
    This function plots a bar plot of the SHAP values.

    Args:
        shap_values: np.ndarray with SHAP values.
        X_train: pd.DataFrame with the predictors.
    """

    shap.summary_plot(shap_values, x_train, plot_type="bar")
