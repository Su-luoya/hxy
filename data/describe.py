# -*- coding: utf-8 -*-
# @Author: 昵称有六个字
# @Date:   2023-02-28 20:59:12
# @Last Modified by:   昵称有六个字
# @Last Modified time: 2023-03-02 21:28:13
import math
import pandas as pd
from icecream import ic
from ydata_profiling import ProfileReport

df = pd.read_csv("data/test.csv")
y = ["bank_loan_restrict_rate"]
x = ["DFH"]
controls = [
    "size",
    "age",
    "age^2",
    "asset",
    "tax_tolerance",
    "employee_number",
    "gdp_2_proportion",
    "reserve_rate",
    "loan_rate_annual",
]
others = ["company", "region"]
i_list = ["industry", "company_ownership", "bank_type"]
interesting_list = (
    ["is_bank_loan", "is_need_bank_loan", "is_need_bank_loan_pro"]
    + [f"no_apply_bank_loan_reason_{i}" for i in range(1, 9)]
    + [f"no_receive_bank_loan_reason_{i}" for i in range(1, 9)]
    + ["is_private_loan", "is_need_private_loan"]
)
miss_group = ["miss_group", "missing_number", "repayment_capacity"]
df = df[y + x + controls + i_list + others + miss_group].dropna(
    subset=controls + i_list + others + miss_group
)
ic(df)
# df.to_csv("data/describe.csv", index=False)
# profile = ProfileReport(df)
# profile.to_file("data/describe.html")
df['missing_number'] = df['missing_number'].map(lambda x:math.exp(x)-1)
df[miss_group].to_excel("describe.xlsx", index=0)
