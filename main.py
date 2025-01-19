import re
import warnings
from os import getcwd, path
from tkinter import filedialog

import pandas as pd
import yaml

warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    message="Workbook contains no default style, apply openpyxl's default",
)


def get_clockify_data():
    clockify_file = filedialog.askopenfilename(
        filetypes=(("Excel files", "*.xlsx"),), initialdir=getcwd()
    )
    if not path.isfile(clockify_file):
        raise FileNotFoundError(f"File '{clockify_file}' does not exist.")
    clockify_df = pd.read_excel(clockify_file)
    return clockify_df


def generate_config(clockify_df):
    clockify_users = [
        user
        for user in clockify_df["User"].unique().tolist()
        if not pd.isna(user) and not re.match(r"Total \(.*", user)
    ]
    config = {
        "users": {
            user: {
                "ID": None,
                "SSN": None,
                "Pay Designation": None,
                "Worked WG2 Code": None,
                "Descriptions": {
                    "Example": {
                        "Pay Designation": None,
                        "Worked WG2 Code": None,
                    }
                },
            }
            for user in clockify_users
        }
    }
    with open("config.yml", "w") as file:
        yaml.dump(config, file, sort_keys=False)


def read_config(clockify_df: pd.DataFrame):
    config_file = "config.yml"
    if not path.isfile(config_file):
        print(
            f"File '{config_file}' does not exist. Creating a template based on clockify.xlsx."
        )
        generate_config(clockify_df)
        raise ValueError(f"Fill in {config_file} and try again.")
    with open(config_file, "r") as file:
        config = yaml.safe_load(file)
        if config is None:
            raise ValueError(
                "Invalid YAML: The file is empty or has incorrect formatting."
            )
        return config


def split_dates(string) -> tuple[str, ...]:
    dates = re.findall(r"\d{1,2}/\d{1,2}/\d{2,4}", string)
    return tuple(dates)


def clean_clockify_data(clockify_df: pd.DataFrame):
    clockify_df.iloc[:, 0] = clockify_df.iloc[:, 0].ffill()
    clockify_df = clockify_df.loc[
        ~clockify_df["User"].str.contains(r"Total \(", na=False)
    ]
    return clockify_df


def get_start_and_end_dates(clockify_df: pd.DataFrame) -> tuple[str, ...]:
    date_cell = clockify_df.loc[
        clockify_df["User"].str.contains(r"Total \(", na=False), "User"
    ]
    if date_cell is None:
        raise ValueError("No total (date) row found in Clockify data.")

    dates = date_cell.to_string(index=False, header=False)
    return split_dates(dates)


def validate_config(config, clockify):
    clockify_users = clockify["User"].unique().tolist()
    config_users = list(config["users"].keys())
    missing_users = [user for user in clockify_users if user not in config_users]
    if missing_users:
        raise ValueError(f"Missing users in config: {', '.join(missing_users)}")
    for user, user_data in config["users"].items():
        if not (user_data.get("ID") or user_data.get("SSN")):
            raise ValueError(
                f"User '{user}' is missing both ID and SSN, they need one or the other"
            )
        allowed_keys = [
            "ID",
            "SSN",
            "Pay Designation",
            "Worked WG2 Code",
            "Descriptions",
        ]
        if not all(key in allowed_keys for key in user_data.keys()):
            raise ValueError(
                f"User '{user}' contains extra keys: {', '.join([key for key in user_data.keys() if key not in allowed_keys])}"
            )

        if user_data.get("Descriptions"):
            user_clockify_descriptions = (
                clockify.loc[clockify["User"] == user, "Description"].dropna().unique()
            )
            config_descriptions = set(user_data["Descriptions"].keys())
            missing_descriptions = set(user_clockify_descriptions) - config_descriptions
            if missing_descriptions:
                raise ValueError(
                    f"Descriptions in Clockify spreadsheet but not found in config for {user}: {', '.join(missing_descriptions)}"
                )
            for desc_type, desc_data in user_data["Descriptions"].items():
                if not (
                    desc_data.get("Pay Designation")
                    and desc_data.get("Worked WG2 Code")
                ):
                    raise ValueError(
                        f"User '{user}' is missing either Pay Designation or Worked WG2 Code in '{desc_type}'"
                    )

        else:
            if not (
                user_data.get("Pay Designation") and user_data.get("Worked WG2 Code")
            ):
                raise ValueError(
                    f"User '{user}' is missing either Pay Designation or Worked WG2 Code"
                )


def create_user_data(config, clockify, start_date, end_date):
    user_data_list = []

    for user, user_data in config["users"].items():
        if user_data.get("Descriptions"):
            for desc_type, desc_data in user_data["Descriptions"].items():
                user_hours = clockify.loc[
                    clockify["User"].eq(user) & clockify["Description"].eq(desc_type)
                ].iloc[0]["Time (decimal)"]
                user_entry = {
                    "Name": user,
                    "Description": desc_type,
                    "ID": user_data.get("ID"),
                    "SSN": user_data.get("SSN"),
                    "Pay Designation": desc_data.get("Pay Designation"),
                    "Hours": user_hours,
                    "Worked WG2 Code": desc_data.get("Worked WG2 Code"),
                    "Period Start Date": start_date,
                    "Period End Date": end_date,
                }
                user_data_list.append(user_entry)
        else:
            user_hours = clockify.loc[clockify["User"].eq(user)].iloc[0][
                "Time (decimal)"
            ]
            user_entry = {
                "Name": user,
                "Description": "",
                "ID": user_data.get("ID"),
                "SSN": user_data.get("SSN"),
                "Pay Designation": user_data.get("Pay Designation"),
                "Hours": user_hours,
                "Worked WG2 Code": user_data.get("Worked WG2 Code"),
                "Period Start Date": start_date,
                "Period End Date": end_date,
            }
            user_data_list.append(user_entry)

    return pd.DataFrame(user_data_list)


def main():
    try:
        clockify_df = get_clockify_data()
        config = read_config(clockify_df)
        start_date, end_date = get_start_and_end_dates(clockify_df)
        clockify_df = clean_clockify_data(clockify_df)
        validate_config(config, clockify_df)
        user_data = create_user_data(config, clockify_df, start_date, end_date)
        try:
            user_data.to_excel("Payroll_to_Import.xlsx", index=False)
        finally:
            print("Payroll data saved to Payroll_to_Import.xlsx")
    except Exception as e:
        print(f"An error occurred: {e}")
        input("Press Enter to close...")


if __name__ == "__main__":
    main()
