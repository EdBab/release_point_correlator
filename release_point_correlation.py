#!/usr/bin/env python3
import re
import matplotlib.pyplot as plt
import seaborn as sns
import argparse
import math
import pandas as pd
import numpy as np
from pybaseball import cache, pitching_stats, statcast_pitcher, playerid_lookup
import sys

cache.enable()


def enforce_years(argument):
    pattern = re.compile("^([0-9]{4})(-[0-9]{4})?$")
    if pattern.match(argument):
        return argument
    else:
        raise argparse.ArgumentTypeError(
            "You must either supply a single season, or multiple, consecutive"
            " seasons separated by a hyphen.\nEx. 2015-2018"
        )


def get_release_variance(pitcher, season):
    player_id = playerid_lookup(pitcher["Name"].split()[1], pitcher["Name"].split()[0])
    if len(player_id) == 0:
        return -1
    try:
        true_player_id = (
            player_id[player_id["key_fangraphs"] == pitcher["IDfg"]]["key_mlbam"].item()
            if len(player_id) > 1
            else player_id["key_mlbam"].item()
        )
        if is_multiple_seasons:
            year_pitch_data = statcast_pitcher(
                f"{str(season)[0:4]}-01-01",
                f"{str(season)[5:9]}-12-31",
                player_id=true_player_id,
            )
        else:
            year_pitch_data = statcast_pitcher(
                f"{str(season)}-01-01",
                f"{str(season + 1)}-01-01",
                player_id=true_player_id,
            )
        x_series = (
            year_pitch_data["release_pos_x"] - year_pitch_data["release_pos_x"].mean()
        ) ** 2
        y_series = (
            year_pitch_data["release_pos_y"] - year_pitch_data["release_pos_y"].mean()
        ) ** 2
        year_pitch_data["distance_from_avg_pitch"] = np.sqrt((x_series) + (y_series))
    except Exception:
        return -1

    return year_pitch_data["distance_from_avg_pitch"].mean()


parser = argparse.ArgumentParser(
    description=(
        "A utility that examines the release position of pitchers and seeks to"
        " predict high and low performers based off of consistency"
    )
)

parser.add_argument(
    "--test_seasons",
    help=(
        "The future season(s) you want to use to examine a pitcher's release"
        " point data ex. 2021 or 2015-2022"
    ),
    type=enforce_years,
    required=True,
)

parser.add_argument(
    "--plate_appearances",
    help=(
        "The minimum number of batters a pitcher needs to have faced to be"
        " considered"
    ),
    type=int,
    required=True,
)

parser.add_argument(
    "--stat",
    help="The stat you want to compare release point variance to",
    choices=["ERA", "FIP", "WAR", "SO", "K/9"],
    required=True,
)

args = parser.parse_args()
is_multiple_seasons = False
if "-" in args.test_seasons:
    is_multiple_seasons = True
first_year = (
    args.test_seasons if "-" not in args.test_seasons else int(args.test_seasons[0:4])
)
if int(first_year) < 2015:
    print(
        "ERROR: Statcast data was introduced in 2015, you cannot search for"
        " data before this point\n"
    )
    sys.exit(1)

try:
    test_data = (
        pitching_stats(args.test_seasons, qual=args.plate_appearances)
        if not is_multiple_seasons
        else pitching_stats(
            args.test_seasons[0:4],
            end_season=args.test_seasons[5:9],
            qual=args.plate_appearances,
            ind=0,
        )
    )
except Exception:
    print(
        f"ERROR: Cannot fetch Statcast data for {args.test_seasons}. Has data"
        " been published for this year yet?\n"
    )
    sys.exit(1)


for index, row in test_data.iterrows():
    variance = get_release_variance(row, args.test_seasons)
    test_data.at[index, "release_variance"] = variance


test_data = test_data[test_data.release_variance != -1]

test_data["release_variance"] = test_data["release_variance"].apply(lambda x: x * 100)
fig_ba, ax_ba = plt.subplots(1, 1, figsize=(10, 5))

for i in range(0, 39):
    print("hey")
fig_ba.suptitle(f"Release point variance v. {args.stat} in {args.test_seasons}")
sns.regplot(
    test_data,
    x="release_variance",
    y=f"{args.stat}",
    fit_reg=True,
    scatter=True,
    ax=ax_ba,
)
ax_ba.set_title(
    "Pearson coefficient:"
    f" {str(round(pd.concat([test_data['release_variance'], test_data[f'{args.stat}']], axis=1).corr().iloc[0,1],2))}"
)
plt.show()
