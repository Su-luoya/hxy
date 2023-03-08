# -*- coding: utf-8 -*-
# @Author: 昵称有六个字
# @Date:   2023-02-22 23:37:51
# @Last Modified by:   昵称有六个字
# @Last Modified time: 2023-03-07 22:06:34
import numpy as np
import pandas as pd
from icecream import ic

ic.configureOutput("")


# df_class = pd.read_excel("data/origin/class.xlsx")
# df_internet = pd.read_csv("data/controls/phone.csv")
# df_class = pd.merge(df_class, df_internet, on="province", how="left")

# df_class.to_excel("data/origin/class.xlsx", index=False)
# ic(df_internet)


df = pd.read_csv("data/origin/data.csv", low_memory=False)
# columns = [f"e1053_{i}_mc" for i in range(1, 11)]

# df = df[columns]
# df["relation"] = 0
# for i in range(1, 6):
#     df["relation"] += df[f"e1053_{i}_mc"]


# df["relation"] = df["relation"].fillna(999).map(lambda x: x >= 1 if x !=999 else np.nan)

# ic(df[["relation"]].describe())
ic((df["e1045"] == "1").describe())
# ic(df)
