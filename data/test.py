# -*- coding: utf-8 -*-
# @Author: 昵称有六个字
# @Date:   2023-02-22 23:37:51
# @Last Modified by:   昵称有六个字
# @Last Modified time: 2023-03-02 23:40:48
import numpy as np
import pandas as pd
from icecream import ic

ic.configureOutput("")


df_class = pd.read_excel("data/origin/class.xlsx")
df_internet = pd.read_csv("data/controls/phone.csv")
df_class = pd.merge(df_class, df_internet, on="province", how="left")

df_class.to_excel("data/origin/class.xlsx", index=False)
ic(df_internet)
