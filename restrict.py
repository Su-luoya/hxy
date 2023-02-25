# -*- coding: utf-8 -*-
# @Author: 昵称有六个字
# @Date:   2023-02-22 23:49:06
# @Last Modified by:   昵称有六个字
# @Last Modified time: 2023-02-25 21:52:12
# -- coding: utf-8 --
import warnings
from pprint import pprint

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from icecream import ic
from scipy.stats.mstats import winsorize

warnings.filterwarnings("ignore")
ic.configureOutput(prefix="")


class Data(object):
    """
    原始数据(df+df_class)初步处理:
    1.将'.d'和'.r'替换为缺失值
    2.删除金融行业
    """

    __instance = None
    __first_init = False

    def __new__(cls, df, df_class):
        if not cls.__instance:
            cls.__instance = object.__new__(cls)
        return cls.__instance

    def __init__(self, df, df_class):
        if not self.__first_init:
            Data.__first_init = True
            # 初始化
            self.df = df
            self.df_class = df_class
            # 将'.d'和'.r'替换为缺失值
            self.df = self.df.replace([".d", ".r"], np.nan).fillna(np.nan)
            # 删除金融行业
            self.delete_finance_industry()

    def delete_finance_industry(self):
        """删除金融行业:a1004(实际经营业务),a1005(主营业务)"""
        ic("Delete the finance industry")
        print(f"original sample:{len(self.df)}")
        # 去除实际经营业务范围属于金融业
        self.df = self.df[self.df["a1004_18_mc"] == 0]
        # 去除主营业务属于金融业
        self.df = self.df[self.df["a1005"] != 18]
        # a1004ex1和a1005ex1中不包含金融
        self.df = self.df[
            self.df["a1004ex1"].fillna("hxy").map(lambda x: "金融" not in x)
        ]
        self.df = self.df[
            self.df["a1005ex1"].fillna("hxy").map(lambda x: "金融" not in x)
        ]
        print(f"processed sample:{len(self.df)}")


class Pre(object):
    """预处理"""

    # 读取原始数据
    df = pd.read_csv("origin/data.csv", encoding="unicode_escape", low_memory=False)
    df_class = pd.read_excel("origin/class.xlsx")
    # 原始数据初步处理
    data = Data(df, df_class)
    df = data.df
    df_class = data.df_class
    # 创建结果文件
    df_result = pd.DataFrame()
    df_result["company"] = df["cmesid_2015"]  # 生成企业序号

    def reset_result(self):
        self.df_result = pd.DataFrame()
        self.df_result["company"] = self.df["cmesid_2015"]  # 生成企业序号

    def extreme(self, series, columns, rate=0.01):
        """
        The extreme function is a helper function that replaces missing values with
        the winsorized value of the column. The default rate is 0.01, which means that
        the lowest and highest 1% of values are replaced.

        :param self: Access the attributes and methods in the same class
        :param series: Specify the dataframe that we want to apply the function on
        :param columns: Specify the columns to be winsorized
        :param rate: Determine how much of the data to replace with the winsorized value
        :return: A dataframe with the winsorized values
        """
        return pd.DataFrame(
            np.where(
                series.isnull(),
                np.nan,
                winsorize(np.ma.masked_invalid(series), limits=(rate, rate)),
            ),
            columns=columns,
        )

    def merge_it(self, name, position_list):
        """
        The merge_it function takes a DataFrame and a list of integers.
        It then creates an average position for each stock in the DataFrame,
        where the average is weighted by both the preceding and following positions.
        For example, if there are three positions per stock (e.g., 1, 2, 3), then:

        :param self: Access the attributes and methods of the class in python
        :param name: Specify the name of the new column, and position_list is used to specify which columns are combined
        :param position_list: Specify the position of the data to be merged
        """
        position_list = [0] + position_list
        position_list_1 = np.roll(position_list, -1)
        position_list_1[-1] = position_list[-1] * 2 - position_list[-2]
        ave_list = (position_list + position_list_1) / 2
        return (
            self.df[name]
            .astype(float)
            .fillna(
                self.df[f"{name}it"].map(
                    dict(
                        zip(
                            map(
                                lambda x: str(x), list(range(1, len(position_list) + 2))
                            ),
                            map(lambda x: x * 10000, ave_list),
                        )
                    )
                )
            )
        )

    def delete_pc(self, series):
        '''去除某列的"省"&"市"'''
        return series.replace({"省": "", "市": ""}, regex=True)

    def merge_province(self, df):
        df["province"] = self.delete_pc(df["province"])
        df = df[df["province"] != "中国"]
        for year in [2013, 2014]:
            df_temp = (
                df[df["year"].astype(int) == year]
                .set_index("province")
                .drop(columns="year")
            )
            df_temp.columns = [
                column + ("_lag" if year == 2013 else "") for column in df_temp.columns
            ]
            self.df_class = pd.merge(
                self.df_class.set_index("province"),
                df_temp,
                how="left",
                left_index=True,
                right_index=True,
            ).reset_index(drop=False)

    @property
    def region_dict(self) -> dict:
        """{province:region}"""
        return (
            pd.read_excel("class/region.xlsx").set_index("province")["region"].to_dict()
        )

    @property
    def industry_dict(self) -> dict:
        """
        {
        industry_financial_loan:{industry_code:industry_name},
        industry_sme_work:{industry_code:industry_name}
        }
        """
        return (
            pd.read_excel("class/industry.xlsx")
            .set_index("industry")[
                [
                    "industry_question",
                    "industry_class",
                    "industry_financial_loan",
                    "industry_sme_work",
                ]
            ]
            .to_dict()
        )

    @property
    def bank_dict(self) -> dict:  # todo//
        df_bank = pd.read_excel("class/banktype.xlsx")
        df_bank["bank_type"] = df_bank["bank_type"].astype(int)
        return df_bank.set_index("bank_type")[
            ["bank_type_dfh", "bank_type_bfi", "bank_type_bflpi"]
        ].to_dict()


class Equity(Pre):
    """股权融资"""

    def __init__(self):
        self.reset_result()

    def initial_investment(self):
        """初期投入的资金 & 范围"""
        self.df_result["initial_investment"] = self.merge_it(
            name="e1001", position_list=[5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000]
        )

    def government_subsidy(self):
        """政府补贴"""
        self.df["e1002a"] = self.df["e1002a"].map({"1": 1, "2": 0})
        self.df.loc[self.df["e1002a"] == 1, "e1002a"] = self.merge_it(
            name="e1002b", position_list=[1, 2, 5, 10, 20, 30, 50, 100, 200, 500]
        )
        self.df_result["government_subsidy"] = self.df["e1002a"]

    def add_investment(self):
        """增加注册资本金"""
        self.df["e1006"] = self.df["e1006"].map({"1": 1, "2": 0})
        self.df.loc[self.df["e1006"] == 1, "e1006"] = self.merge_it(
            name="e1008", position_list=[2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000]
        )
        self.df_result["add_investment"] = self.df["e1006"]

    def all(self):
        """合并"""
        self.initial_investment()
        self.government_subsidy()
        self.add_investment()


class Private(Pre):
    """民间融资"""

    def __init__(self):
        self.reset_result()

    def is_private_loan(self):
        """是否有尚未还清的银行贷款"""
        self.df_result["is_private_loan"] = self.df["e1045"].map({"1": 1, "2": 0})

    def is_need_private_loan(self):
        """是否需要民间贷款"""
        self.df_result["is_need_private_loan"] = self.df["e1046"].map(
            {"1": 0, "2": 1, "3": 1, "4": 1}
        )

    def private_loan_need(self):
        """需要多少民间贷款"""
        self.df_result["private_loan_need"] = self.merge_it(
            name="e1047", position_list=[5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000]
        )

    def private_loan_number(self):
        """几笔尚未还清的民间贷款"""
        self.df_result["private_loan_number"] = (
            self.df["e1048"].astype(float)
            # .map(lambda x: float(x) if x is not np.nan else x)
        )

    def max_private_loan(self):
        """最大笔民间贷款: 一共贷了多少+还剩多少没还"""
        # 还剩多少没还
        self.df.loc[self.df["e1045"] == "2", "e1051"] = self.df["e1045"].replace("2", 0)
        self.df_result["max_rest_private_loan"] = self.merge_it(
            name="e1051", position_list=[1, 2, 5, 10, 20, 30, 50, 100, 200, 500]
        )
        # 一共贷了多少
        self.df.loc[self.df["e1045"] == "2", "e1052"] = self.df["e1045"].replace("2", 0)
        self.df_result["max_private_loan"] = self.merge_it(
            name="e1052", position_list=[0.5, 2, 5, 10, 20, 50, 100, 200, 500, 1000]
        )

    def all_private_loan(self):
        """所有民间贷款: 一共贷了多少+还剩多少没还"""
        # 还剩多少没还
        self.df.loc[self.df["e1045"] == "2", "e1049"] = self.df["e1045"].replace("2", 0)
        position_list = [2, 5, 10, 20, 30, 50, 100, 200, 500, 1000, 2000]
        self.df_result["all_rest_private_loan"] = self.merge_it(
            name="e1049", position_list=position_list
        ).fillna(self.merge_it(name="e1051", position_list=position_list))
        # 一共贷了多少
        self.df.loc[self.df["e1045"] == "2", "e1050"] = self.df["e1045"].replace("2", 0)
        position_list = [5, 10, 20, 30, 50, 100, 200, 500, 1000, 2000, 5000]
        self.df_result["all_private_loan"] = self.merge_it(
            name="e1050", position_list=position_list
        ).fillna(self.merge_it(name="e1052", position_list=position_list))

    def bank_loan_use_method(self):
        """Debt类中调用的方法"""
        # self.all_private_loan()
        # self.is_need_private_loan()
        self.All()

    """NO USE"""

    def private_loan(self):
        """民间贷款情况"""
        self.is_private_loan()  # 是否有尚未还清的民间贷款
        self.private_loan_number()  # 几笔尚未还清的民间贷款
        self.max_private_loan()  # 最大笔民间贷款：一共贷了多少+还剩多少没还
        self.all_private_loan()  # 所有民间贷款：一共贷了多少+还剩多少没还

    def private_loan_dissatisfaction(self):
        """民间贷款需求没有得到满足的金额"""
        self.df.loc[self.df["e1063"] == "1", "e1064"] = 0
        self.df.loc[self.df["e1063"] == "4", "e1064"] = self.df_result[
            "all_private_loan"
        ]
        self.df.loc[self.df["e1063"] == "2", "e1064"] = self.df["e1045"].replace("2", 0)
        self.df_result["private_loan_dissatisfaction"] = self.merge_it(
            name="e1064", position_list=[2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000]
        )

    def private_loan_satisfaction_rate(self):
        """民间贷款需求满足率"""
        self.df_result["private_loan_satisfaction_rate"] = np.nan
        # 有贷款&是否需要贷款
        self.df_result.loc[
            self.df_result["is_private_loan"] == 1, "private_loan_satisfaction_rate"
        ] = (
            1
            - self.df_result["private_loan_dissatisfaction"]
            / (
                self.df_result["all_private_loan"]
                + self.df_result["private_loan_dissatisfaction"]
                + 0.0000001
            )
        ).astype(
            float
        )
        # 没贷款&需要贷款
        self.df_result.loc[
            (self.df_result["is_private_loan"] == 0)
            * (self.df_result["private_loan_need"].isnull() == False),
            "private_loan_satisfaction_rate",
        ] = 0
        # 没贷款&不需要贷款
        self.df_result.loc[
            self.df_result["is_need_private_loan"] == 0,
            "private_loan_satisfaction_rate",
        ] = 1
        self.df_result["private_loan_satisfaction_rate"] = np.where(
            self.df_result["private_loan_satisfaction_rate"].isnull(),
            np.nan,
            winsorize(
                np.ma.masked_invalid(self.df_result["private_loan_satisfaction_rate"]),
                limits=(0.01, 0.01),
            ),
        )

    def private_loan_restrict(self):
        """民间贷款融资约束"""
        self.is_need_private_loan()  # 是否需要民间贷款
        self.private_loan_need()  # 需要多少民间贷款
        self.private_loan_dissatisfaction()  # 民间贷款需求没有得到满足的金额
        self.private_loan_satisfaction_rate()  # 民间贷款需求满足率
        # 融资约束
        self.df_result["private_loan_restrict"] = np.nan
        self.df_result.loc[
            self.df_result["is_private_loan"] == 1, "private_loan_restrict"
        ] = self.df_result["private_loan_dissatisfaction"]
        self.df_result.loc[
            self.df_result["is_private_loan"] == 0, "private_loan_restrict"
        ] = (self.df_result["private_loan_need"] + 1)
        # 融资约束百分比
        self.df_result["private_loan_restrict_rate"] = (
            1 - self.df_result["private_loan_satisfaction_rate"]
        )

    def All(self):
        self.private_loan()  # 民间贷款情况
        self.private_loan_restrict()  # 民间贷款融资约束

    """NO USE"""


class Debt(Private):
    """银行融资"""

    def __init__(self):
        self.reset_result()

    def is_bank_loan(self):
        """是否有尚未还清的银行贷款"""
        self.df_result["is_bank_loan"] = self.df["e1014"].map({"1": 1, "2": 0})

    def is_need_bank_loan(self):
        """是否需要银行贷款"""
        self.df_result["is_need_bank_loan"] = self.df["e1015"].map(
            {"1": 0, "2": 1, "3": 1, "4": 1}
        )

    def bank_loan_need(self):
        """需要多少银行贷款"""
        self.df_result["bank_loan_need"] = self.merge_it(
            name="e1016", position_list=[5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000]
        )

    def bank_loan_number(self):
        """几笔尚未还清的银行贷款"""
        self.df_result["bank_loan_number"] = (
            self.df["e1019"]
            .replace("5.5", "6")
            .astype(float)
            # .map(lambda x: float(x) if x is not np.nan else x)
        )

    def max_bank_loan(self):
        """最大笔银行贷款：一共贷了多少+还剩多少没还"""
        # 还剩多少没还
        self.df.loc[self.df["e1014"] == "2", "e1022"] = self.df["e1014"].replace("2", 0)
        self.df_result["max_rest_bank_loan"] = self.merge_it(
            name="e1022", position_list=[1, 2, 5, 10, 20, 30, 50, 100, 200, 500]
        )
        # 一共贷了多少
        self.df.loc[self.df["e1014"] == "2", "e1023"] = self.df["e1014"].replace("2", 0)
        self.df_result["max_bank_loan"] = self.merge_it(
            name="e1023", position_list=[0.5, 2, 5, 10, 20, 50, 100, 200, 500, 1000]
        )

    def all_bank_loan(self):
        """所有银行贷款：一共贷了多少+还剩多少没还"""
        # 还剩多少没还
        self.df.loc[self.df["e1014"] == "2", "e1020"] = self.df["e1014"].replace("2", 0)
        position_list = [2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000]
        self.df_result["all_rest_bank_loan"] = self.merge_it(
            name="e1020", position_list=position_list
        ).fillna(self.merge_it(name="e1022", position_list=position_list))

        # 一共贷了多少
        self.df.loc[self.df["e1014"] == "2", "e1021"] = self.df["e1014"].replace("2", 0)
        position_list = [5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000]
        self.df_result["all_bank_loan"] = self.merge_it(
            name="e1021", position_list=position_list
        ).fillna(self.merge_it(name="e1023", position_list=position_list))

    def max_bank_loan_year(self):
        """最大笔贷款的贷款年份"""
        self.df_result["max_bank_loan_year"] = (
            self.df["e1024"].astype(float)
            # .map(lambda x: int(x) if x is not np.nan else np.nan)
        )

    def bank_loan(self):
        """银行贷款情况"""
        self.is_bank_loan()  # 是否有尚未还清的银行贷款
        self.bank_loan_number()  # 几笔尚未还清的银行贷款
        self.max_bank_loan()  # 最大笔银行贷款：一共贷了多少+还剩多少没还
        self.all_bank_loan()  # 所有银行贷款：一共贷了多少+还剩多少没还
        self.max_bank_loan_year()  # 最大笔贷款的贷款年份

    def bank_loan_dissatisfaction(self):
        """银行贷款需求没有得到满足的金额"""
        self.df.loc[self.df["e1041"] == "1", "e1042"] = 0
        self.df.loc[self.df["e1041"] == "4", "e1042"] = self.df_result["all_bank_loan"]
        self.df.loc[self.df["e1014"] == "2", "e1042"] = self.df["e1014"].replace("2", 0)
        self.df_result["bank_loan_dissatisfaction"] = self.merge_it(
            name="e1042", position_list=[2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000]
        )

    def bank_loan_satisfaction_rate(self):
        """银行贷款需求满足率"""
        self.df_result["bank_loan_satisfaction_rate"] = np.nan
        # 有贷款&无论是否需要贷款
        self.df_result.loc[
            self.df_result["is_bank_loan"] == 1, "bank_loan_satisfaction_rate"
        ] = (
            1
            - self.df_result["bank_loan_dissatisfaction"]
            / (
                self.df_result["all_bank_loan"]
                + self.df_result["bank_loan_dissatisfaction"]
                + 0.0000001
            )
        ).astype(
            float
        )
        # 没贷款&需要贷款
        self.df_result.loc[
            (self.df_result["is_bank_loan"] == 0)
            * (self.df_result["bank_loan_need"].isnull() == False),
            "bank_loan_satisfaction_rate",
        ] = 0
        # 没贷款&不需要贷款
        self.df_result.loc[
            self.df_result["is_need_bank_loan"] == 0, "bank_loan_satisfaction_rate"
        ] = 1

    def is_card_loan(self):
        """是否有尚未还清的信用卡融资"""
        self.df_result["is_card_loan"] = self.df["e1043"].map({"1": 1, "2": 0})

    def all_card_loan(self):
        """信用卡融资金额"""
        self.df_result["all_card_loan"] = self.merge_it(
            name="e1044", position_list=[0.5, 2, 5, 10, 20, 50, 100, 200, 500, 1000]
        )

    def delete_fake(self):
        """删除不需要信用贷款但需要其他类型贷款的“没有融资约束”的企业"""
        # 不需要银行贷款:all_private_loan>0 （前提：is_bank_loan=0）
        # self.is_need_bank_loan() # 测试用，需删除
        # 有尚未还清的民间借款:'is_need_private_loan'==1 & 'all_private_loan'>0
        self.bank_loan_use_method()  # self.all_private_loan()+self.is_need_private_loan()
        # 有尚未还清的信用卡贷款
        # self.is_card_loan()
        # self.all_card_loan()
        # condition_card = (self.df_result["all_card_loan"] > 0) | (
        #     self.df_result["is_card_loan"] == 0
        # )
        condition_bank = self.df_result["is_need_bank_loan"] == 0
        condition_private = (self.df_result["all_private_loan"] > 0) | (
            self.df_result["is_need_private_loan"] == 1
        )
        index = (
            condition_bank
            & condition_private
            # condition_bank & (condition_private | condition_card)
        )
        self.df_result.loc[index, "bank_loan_satisfaction_rate"] = np.nan
        self.df_result["miss_group"] = (
            self.df_result["bank_loan_satisfaction_rate"].isnull().map(lambda x: 1 - x)
        )
        self.df_result.loc[index, "miss_group"] = np.nan

    def bank_loan_restrict(self):
        """银行贷款融资约束"""
        self.is_need_bank_loan()  # 是否需要银行贷款
        self.bank_loan_need()  # 需要多少银行贷款
        self.bank_loan_dissatisfaction()  # 银行贷款需求没有得到满足的金额
        self.bank_loan_satisfaction_rate()  # 银行贷款需求满足率
        # 删除不需要信用贷款但需要其他类型贷款的“没有融资约束”的企业
        self.delete_fake()
        # 融资约束
        self.df_result["bank_loan_restrict"] = np.nan
        self.df_result.loc[
            self.df_result["is_bank_loan"] == 1, "bank_loan_restrict"
        ] = self.df_result["bank_loan_dissatisfaction"]
        self.df_result.loc[
            self.df_result["is_bank_loan"] == 0, "bank_loan_restrict"
        ] = (
            self.df_result["bank_loan_need"] + 1
        )  #! ?????为什么+1
        # 融资约束百分比
        self.df_result["bank_loan_restrict_rate"] = (
            1 - self.df_result["bank_loan_satisfaction_rate"]
        )

    def all(self):
        self.bank_loan()  # 银行贷款情况
        self.bank_loan_restrict()  # 银行贷款融资约束
        self.df_result["bank_loan_restrict"] = self.df_result["bank_loan_restrict"].map(
            lambda x: np.log(x + 1)
        )
        # 融资偏好
        self.df_result["loan_preference_4"] = (
            self.df["e1065"].astype(float)
            # .map(lambda x: float(x) if x is not np.nan else x)
        )
        self.df_result["loan_preference_2"] = self.df_result["loan_preference_4"].map(
            {1: 1, 2: 0, 3: 0, 4: 0}
        )
        self.df_result["loan_preference_2_nan"] = self.df_result[
            "loan_preference_4"
        ].map({1: 1, 2: 0, 3: np.nan, 4: np.nan})


class DigitalFoot(Pre):
    """🔢👣"""

    def __init__(self):
        self.reset_result()

    def temp1(self, x):
        if x == 0:
            return 0
        elif x > 0:
            return 1
        else:
            return np.nan

    def temp2(self, x):
        if x == "6":
            return 1
        elif x is np.nan:
            return x
        else:
            return 0

    def temp3(self, name1, name2):
        return (
            (self.df_result[name1].fillna(2) + self.df_result[name2].fillna(2))
            .map(lambda x: np.nan if x == 4 else x)
            .map({2: 1, 3: 1})
        )

    def temp4(self, name1, name2):
        return (
            self.df_result[name1].fillna(10 ** (-6))
            + self.df_result[name2].fillna(10 ** (-6))
        ).map(lambda x: np.nan if x == 10 ** (-6) * 2 else x)

    def combine(self, columns, combine_name):
        """合并多列"""
        self.df_result[combine_name] = (
            self.df_result[columns].fillna(0).sum(axis=1)
        )  # type: ignore
        self.df_result.loc[
            self.df_result[columns].isnull().apply(lambda x: ~x).any(axis=1) == False,
            combine_name,  # type: ignore
        ] = np.nan

    def is_amount(
        self, industry, is_name, amount_name, position_list, label="", sb="sell"
    ):
        """是否+金额
        Args:
            sb (str, optional): sell or buy. Defaults to 'sell'.
        """
        # 互联网“sb”金额
        self.df.loc[self.df[is_name].replace("3", "2") != "2", amount_name] = self.df[
            is_name
        ].map({"1": 0, "4": 0, "5": 0})
        self.df_result[f"{industry}_{sb}_internet{label}_amount"] = self.merge_it(
            name=amount_name, position_list=position_list
        )
        # 是否互联网"sb"
        self.df_result[f"{industry}_is_{sb}_internet{label}"] = self.df_result[
            f"{industry}_{sb}_internet{label}_amount"
        ].map(self.temp1)

    def buy(self, industry, is_name, amount_name, position_list, label=""):
        """是否互联网购买+互联网购买金额"""
        sb = "buy"
        # 是否互联网购买+互联网购买金额
        self.is_amount(industry, is_name, amount_name, position_list, label, sb)

    def buy_pro(self, industry, is_pro_name, label=""):
        """互联网购买金额pro"""
        self.df_result.loc[
            self.df[is_pro_name] == "2", f"{industry}_buy_internet{label}_amount"
        ] = 0

    def adv_pro(self, industry, is_pro_name, amount_pro_name, label=""):
        """是否互联网宣传pro"""
        self.df_result.loc[
            self.df[is_pro_name] == "2", f"{industry}_is_adv_internet{label}"
        ] = 0
        self.df_result.loc[
            self.df[amount_pro_name] == "0", f"{industry}_is_adv_internet{label}"
        ] = 0

    def sell(
        self, industry, is_name, amount_name, future_name, position_list, label=""
    ):
        """是否互联网销售+互联网销售金额+未来是否互联网销售"""
        sb = "sell"
        # 是否互联网销售+互联网销售金额
        self.is_amount(industry, is_name, amount_name, position_list, label, sb)
        # 未来是否互联网销售
        self.df_result[f"{industry}_future_sell_internet{label}"] = self.df[
            future_name
        ].map({"1": 1, "2": 0})

    def adv(self, industry, is_name, future_name):
        """2014年是否互联网销售+未来是否互联网销售"""
        # 2014年是否互联网销售
        self.df_result[f"{industry}_is_adv_internet"] = self.df[is_name]
        # 未来是否互联网销售
        self.df_result[f"{industry}_future_adv_internet"] = self.df[future_name].map(
            {"1": 1, "2": 0}
        )

    def BA_buy(self):
        """零售业生产经营BA:是否互联网采购+互联网采购金额+互联网采购金额比例"""
        # 是否互联网采购+互联网采购金额
        self.buy(
            industry="BA",
            is_name="ba4002",
            amount_name="ba4005",
            position_list=[2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000],
        )
        # 传统采购
        self.df.loc[
            self.df["ba4002"].replace("3", "1") != "1", "ba4004"
        ] = self.df[  # "!='1'"是传统；"!='2'"是互联网
            "ba4002"
        ].map(
            {"2": 0, "4": 0, "5": 0}
        )
        self.df_result["BA_buy_tradition_amount"] = self.merge_it(
            name="ba4004", position_list=[2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000]
        )
        # 互联网采购/(传统采购+互联网采购)
        self.df_result["BA_buy_internet_rate"] = self.df_result[
            "BA_buy_internet_amount"
        ] / (
            self.df_result["BA_buy_tradition_amount"]
            + self.df_result["BA_buy_internet_amount"]
        )

    def BA_sell(self):
        """零售业生产经营BA:是否互联网销售+互联网销售金额+未来是否互联网销售"""
        self.sell(
            industry="BA",
            is_name="ba5001",
            amount_name="ba5003",
            future_name="ba5009",
            position_list=[0.5, 2, 5, 10, 20, 50, 100, 200, 500, 1000],
        )

    def BA_adv(self):
        """零售业生产经营BA:2014年是否互联网销售+未来是否互联网销售"""
        self.adv(industry="BA", is_name="ba5016_6_mc", future_name="ba5020")
        self.adv_pro(industry="BA", is_pro_name="ba5013", amount_pro_name="ba5014")

    def BA(self):
        """零售业生产经营BA:互联网采购+销售+宣传"""
        self.BA_buy()
        self.BA_sell()
        self.BA_adv()

    def BB_buy(self):
        """批发业生产经营BB:是否互联网采购+互联网采购金额+互联网采购金额比例"""
        # 采购总金额bb4002 - 传统采购金额bb4004 = 互联网采购金额 ➡️ 互联网采购金额比例
        self.df_result["BB_buy_all_amount"] = self.merge_it(
            name="bb4002a", position_list=[0.5, 2, 5, 10, 20, 50, 100, 200, 500, 1000]
        )
        self.df.loc[self.df["bb4001"].replace("3", "1") != "1", "bb4004"] = self.df[
            "bb4001"
        ].map({"2": 0})
        self.df_result["BB_buy_tradition_amount"] = self.merge_it(
            name="bb4004", position_list=[0.5, 2, 5, 10, 20, 50, 100, 200, 500, 1000]
        )
        self.df_result["BB_buy_internet_amount"] = (
            self.df_result["BB_buy_all_amount"]
            - self.df_result["BB_buy_tradition_amount"]
        )
        self.df_result["BB_buy_internet_rate"] = self.df_result[
            "BB_buy_internet_amount"
        ] / (self.df_result["BB_buy_all_amount"] + 0.00001)
        # 是否互联网采购
        self.df_result["BB_is_buy_internet"] = self.df["bb4001"].map(
            {"1": 0, "2": 1, "3": 1}
        )
        self.df_result.loc[
            self.df_result["BB_buy_internet_amount"] > 0, "BB_is_buy_internet"
        ] = (self.df_result["BB_buy_internet_amount"] > 0).astype(int)

    def BB_sell(self):
        """批发业生产经营BB:是否互联网销售+互联网销售金额+未来是否互联网销售"""
        self.sell(
            industry="BB",
            is_name="bb5001",
            amount_name="bb5003",
            future_name="bb5009",
            position_list=[2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000],
        )

    def BB_adv(self):
        """批发业生产经营BB:2014年是否互联网宣传+未来是否互联网宣传"""
        self.adv(industry="BB", is_name="bb5012_6_mc", future_name="bb5016")
        self.adv_pro(industry="BB", is_pro_name="bb5010", amount_pro_name="bb5011")

    def BB(self):
        """批发业生产经营BB:互联网采购+销售+宣传"""
        self.BB_buy()
        self.BB_sell()
        self.BB_adv()

    def BC_buy(self):
        """制造业生产经营BC:是否互联网采购(设备/原材料)+互联网采购金额+比例(原材料)"""
        # 互联网采购设备
        self.buy(
            industry="BC",
            is_name="bc4007",
            amount_name="bc4008",
            position_list=[0.5, 2, 5, 10, 20, 50, 100, 200, 500, 1000],
            label="_equipment",
        )
        self.buy_pro(industry="BC", is_pro_name="bc4003")
        # 互联网采购原材料
        self.buy(
            industry="BC",
            is_name="bc5005",
            amount_name="bc5006",
            position_list=[0.5, 2, 5, 10, 20, 50, 100, 200, 500, 1000],
            label="_material",
        )
        # 互联网采购原材料比例
        self.df_result["BC_buy_internet_material_rate"] = self.df_result[
            "BC_buy_internet_material_amount"
        ] / (
            self.merge_it(
                name="bc5004",
                position_list=[0.5, 2, 5, 10, 20, 50, 100, 200, 500, 1000],
            )
            + 0.00001
        )
        # 合并
        # 是否互联网采购
        self.df_result["BC_is_buy_internet"] = self.temp3(
            name1="BC_is_buy_internet_equipment", name2="BC_is_buy_internet_material"
        )
        # 互联网采购金额
        self.df_result["BC_buy_internet_amount"] = self.temp4(
            name1="BC_buy_internet_equipment_amount",
            name2="BC_buy_internet_material_amount",
        )
        # 互联网采购比例
        self.df_result["BC_buy_internet_rate"] = self.df_result[
            "BC_buy_internet_material_rate"
        ]

    def BC_sell(self):
        """制造业生产经营BC:是否互联网销售+互联网销售金额+未来是否互联网销售"""
        self.sell(
            industry="BC",
            is_name="bc6003",
            amount_name="bc6005",
            future_name="bc6010",
            position_list=[2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000],
        )

    def BC_adv(self):
        """制造业生产经营BC:2014年是否互联网宣传+未来是否互联网宣传"""
        self.adv(industry="BC", is_name="bc6013_6_mc", future_name="bc6017")
        self.adv_pro(industry="BC", is_pro_name="bc6011", amount_pro_name="bc6012")

    def BC(self):
        """制造业生产经营BC:互联网采购+销售+宣传"""
        self.BC_buy()
        self.BC_sell()
        self.BC_adv()

    def BD_buy(self):
        """交通运输业BD:客运/货运互联网采购/金额"""
        # 客运
        self.buy(
            industry="BD",
            is_name="bd2014",
            amount_name="bd2015",
            position_list=[2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000],
            label="_passenger",
        )
        # 货运
        self.buy(
            industry="BD",
            is_name="bd6018",
            amount_name="bd6019",
            position_list=[2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000],
            label="_transport",
        )
        # 合并
        # 是否互联网采购
        self.df_result["BD_is_buy_internet"] = self.temp3(
            name1="BD_is_buy_internet_passenger", name2="BD_is_buy_internet_transport"
        )
        # 互联网采购金额
        self.df_result["BD_buy_internet_amount"] = self.temp4(
            name1="BD_buy_internet_passenger_amount",
            name2="BD_buy_internet_transport_amount",
        )

    def BD_sell(self):
        """交通运输业BD:(客运/货运)是否互联网销售+互联网销售金额+未来是否互联网销售"""
        # 客运
        self.sell(
            industry="BD",
            is_name="bd4006",
            amount_name="bd4009",
            future_name="bd4008",
            position_list=[1, 3, 5, 7, 10, 30, 50, 100, 500, 1000],
            label="_passenger",
        )
        # 货运
        self.sell(
            industry="BD",
            is_name="bd8004",
            amount_name="bd8005b",
            future_name="bd8005a",
            position_list=[1, 3, 5, 7, 10, 30, 50, 100, 500, 1000],
            label="_transport",
        )
        # 合并
        # 是否互联网销售
        self.df_result["BD_is_sell_internet"] = self.temp3(
            name1="BD_is_sell_internet_passenger", name2="BD_is_sell_internet_transport"
        )
        # 互联网销售金额
        self.df_result["BD_sell_internet_amount"] = self.temp4(
            name1="BD_sell_internet_passenger_amount",
            name2="BD_sell_internet_transport_amount",
        )
        # 未来是否互联网销售
        self.df_result["BD_future_sell_internet"] = self.temp3(
            name1="BD_future_sell_internet_passenger",
            name2="BD_future_sell_internet_transport",
        )

    def BD(self):
        """交通运输业BD"""
        self.BD_buy()
        self.BD_sell()

    def BE_buy(self):
        """餐饮业BE:是否互联网采购+互联网采购金额+互联网采购比例"""
        # 是否互联网采购
        self.df_result["BE_is_buy_internet"] = self.df["be2016"].map({"1": 1, "2": 0})
        # 互联网采购金额
        self.df_result["BE_buy_internet_amount"] = self.merge_it(
            name="be2017", position_list=[1, 2, 5, 10, 20, 30, 50, 100, 200, 500]
        )
        self.df_result.loc[
            self.df_result["BE_is_buy_internet"] == 0, "BE_buy_internet_amount"
        ] = 0
        # 互联网采购比例
        self.df_result["BE_buy_internet_rate"] = self.df_result[
            "BE_buy_internet_amount"
        ] / (
            self.merge_it(
                name="be2015", position_list=[1, 2, 5, 10, 20, 30, 50, 100, 200, 500]
            )
            + 0.000001
        )

    def BE_sell(self):
        """餐饮业BE:是否互联网销售+互联网销售金额+未来是否互联网销售"""
        self.sell(
            industry="BE",
            is_name="be3009",
            amount_name="be3010",
            future_name="be3016",
            position_list=[1, 3, 5, 7, 10, 30, 50, 100, 500, 1000],
        )

    def BE_adv(self):
        """餐饮业BE:2014年是否互联网宣传+未来是否互联网宣传"""
        self.adv(industry="BE", is_name="be3003_6_mc", future_name="be3007")
        self.adv_pro(industry="BE", is_pro_name="be3001", amount_pro_name="be3002")

    def BE(self):
        """餐饮业BE:互联网采购+销售+宣传"""
        self.BE_buy()
        self.BE_sell()
        self.BE_adv()

    def BF_buy(self):
        """软件和信息技术服务业BF:是否互联网采购+互联网采购金额+互联网采购比例"""
        # 是否互联网采购 + 互联网采购金额
        self.buy(
            industry="BF",
            is_name="bf2020",
            amount_name="bf2021",
            position_list=[1, 2, 5, 10, 20, 30, 50, 100, 200, 500],
        )
        # 互联网采购比例
        self.df_result["BF_buy_internet_rate"] = self.df_result[
            "BF_buy_internet_amount"
        ] / (
            self.merge_it(
                name="bf2019", position_list=[1, 2, 5, 10, 20, 30, 50, 100, 200, 500]
            )
            + 0.000001
        )

    def BF_sell(self):
        """软件和信息技术服务业BF:是否互联网销售+互联网销售金额+未来是否互联网销售"""
        self.sell(
            industry="BF",
            is_name="bf3004",
            amount_name="bf3006",
            future_name="bf3009",
            position_list=[1, 3, 5, 7, 10, 30, 50, 100, 500, 1000],
        )

    def BF_adv(self):
        """软件和信息技术服务业BF:2014年是否互联网宣传+未来是否互联网宣传"""
        self.adv(industry="BF", is_name="bf3012_6_mc", future_name="bf3015a")
        self.adv_pro(industry="BF", is_pro_name="bf3010", amount_pro_name="bf3011")

    def BF(self):
        """软件和信息技术服务业BF:互联网采购+销售+宣传"""
        self.BF_buy()
        self.BF_sell()
        self.BF_adv()

    def BG_buy(self):
        """住宿BG:是否互联网采购+互联网采购金额+比例"""
        # 其他固定资产:是否互联网采购+互联网采购金额
        self.buy(
            industry="BG",
            is_name="bg2011",
            amount_name="bg2012",
            position_list=[1, 2, 5, 10, 20, 30, 50, 100, 200, 500],
            label="_asset",
        )
        # 易耗品
        # 是否互联网采购+互联网采购金额
        self.buy(
            industry="BG",
            is_name="bg2014",
            amount_name="bg2015",
            position_list=[0.2, 0.5, 1, 2, 5, 10, 15, 20, 30, 50],
            label="_consumable",
        )
        # 互联网采购金额比例
        self.df_result["BG_buy_internet_consumable_rate"] = self.df_result[
            "BG_buy_internet_consumable_amount"
        ] / (
            self.merge_it(
                name="bg2013", position_list=[0.5, 1, 2, 5, 10, 15, 20, 30, 50, 100]
            )
            + 0.00001
        )
        # 合并
        # 是否互联网采购
        self.df_result["BG_is_buy_internet"] = self.temp3(
            name1="BG_is_buy_internet_asset", name2="BG_is_buy_internet_consumable"
        )
        # 互联网采购金额
        self.df_result["BG_buy_internet_amount"] = self.temp4(
            name1="BG_buy_internet_asset_amount",
            name2="BG_buy_internet_consumable_amount",
        )
        # 互联网采购金额比例
        self.df_result["BG_buy_internet_rate"] = self.df_result[
            "BG_buy_internet_consumable_rate"
        ]

    def BG_sell(self):
        """住宿BG:是否互联网销售+互联网销售金额+未来是否互联网销售"""
        self.sell(
            industry="BG",
            is_name="bg3008",
            amount_name="bg3009",
            future_name="bg3015",
            position_list=[1, 3, 5, 7, 10, 30, 50, 100, 500, 1000],
        )

    def BG_adv(self):
        """住宿BG:2014年是否互联网宣传+未来是否互联网宣传"""
        self.adv(industry="BG", is_name="bg3003_6_mc", future_name="bg3007")
        self.adv_pro(industry="BG", is_pro_name="bg3001", amount_pro_name="bg3002")

    def BG(self):
        """住宿BG:互联网采购+销售+宣传"""
        self.BG_buy()
        self.BG_sell()
        self.BG_adv()

    def BH_buy(self):
        """建筑业企业生产经营BH:是否互联网采购+互联网采购金额"""
        # 是否互联网采购+互联网采购金额
        self.buy(
            industry="BH",
            is_name="bh2405",
            amount_name="bh2407",
            position_list=[0.5, 2, 5, 10, 20, 50, 100, 200, 500, 1000],
        )
        # 互联网采购金额比例
        self.df_result["BH_buy_internet_rate"] = self.df_result[
            "BH_buy_internet_amount"
        ] / (
            self.merge_it(
                name="bh2404",
                position_list=[2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000],
            )
            + 0.00001
        )

    def BH(self):
        """建筑业企业生产经营BH:互联网采购"""
        self.BH_buy()

    def BI_sell(self):
        """农业生产经营问卷BI:主要销售渠道是否互联网销售"""
        self.df_result["BI_is_sell_internet"] = self.df["bi3012_6_mc"]

    def BI(self):
        """农业生产经营问卷BI:互联网销售"""
        self.BI_sell()

    def TB_sell(self):
        """生产经营通用问卷TB:是否互联网销售+互联网销售金额+未来是否互联网销售"""
        self.sell(
            industry="TB",
            is_name="tb1001",
            amount_name="tb1002",
            future_name="tb1008",
            position_list=[1, 3, 5, 7, 10, 30, 50, 100, 500, 1000],
        )

    def TB_adv(self):
        """生产经营通用问卷TB:2014年是否互联网宣传+未来是否互联网宣传"""
        self.adv(industry="TB", is_name="tb1011_6_mc", future_name="tb1015")
        self.adv_pro(industry="TB", is_pro_name="tb1009", amount_pro_name="tb1010")

    def TB(self):
        """生产经营通用问卷TB:互联网销售+互联网宣传"""
        self.TB_sell()
        self.TB_adv()

    def all(self):  # sourcery skip: min-max-identity
        self.BA()
        self.BB()
        self.BC()
        self.BD()
        self.BE()
        self.BF()
        self.BG()
        self.BH()
        self.BI()
        self.TB()
        # 互联网采购
        # 是否互联网采购
        columns = [
            f"{industry}_is_buy_internet"
            for industry in ["BA", "BB", "BC", "BD", "BE", "BF", "BG", "BH"]
        ]
        self.combine(columns=columns, combine_name="is_buy_internet")
        # 互联网采购金额
        columns = [
            f"{industry}_buy_internet_amount"
            for industry in ["BA", "BB", "BC", "BD", "BE", "BF", "BG", "BH"]
        ]
        self.combine(columns=columns, combine_name="buy_internet_amount")
        # 互联网采购比例
        columns = [
            f"{industry}_buy_internet_rate"
            for industry in ["BA", "BB", "BC", "BE", "BF", "BG", "BH"]
        ]
        self.combine(columns=columns, combine_name="buy_internet_rate")
        # 互联网销售
        # 是否互联网销售
        columns = [
            f"{industry}_is_sell_internet"
            for industry in ["BA", "BB", "BC", "BD", "BE", "BF", "BG", "BI", "TB"]
        ]
        self.combine(columns=columns, combine_name="is_sell_internet")
        # 互联网销售金额
        columns = [
            f"{industry}_sell_internet_amount"
            for industry in ["BA", "BB", "BC", "BD", "BE", "BF", "BG", "TB"]
        ]
        self.combine(columns=columns, combine_name="sell_internet_amount")
        # 未来是否互联网销售
        columns = [
            f"{industry}_future_sell_internet"
            for industry in ["BA", "BB", "BC", "BD", "BE", "BF", "BG", "TB"]
        ]
        self.combine(columns=columns, combine_name="future_sell_internet")
        # 互联网宣传
        # 是否互联网宣传
        columns = [
            f"{industry}_is_adv_internet"
            for industry in ["BA", "BB", "BC", "BE", "BF", "BG", "TB"]
        ]
        self.combine(columns=columns, combine_name="is_adv_internet")
        # 未来是否互联网宣传
        columns = [
            f"{industry}_future_adv_internet"
            for industry in ["BA", "BB", "BC", "BE", "BF", "BG", "TB"]
        ]
        self.combine(columns=columns, combine_name="future_adv_internet")
        # 最终指标
        self.df_result = self.df_result[
            [
                "company",
                "is_buy_internet",
                "buy_internet_amount",
                "buy_internet_rate",
                "is_sell_internet",
                "sell_internet_amount",
                "future_sell_internet",
                "is_adv_internet",
                "future_adv_internet",
            ]
        ]
        # 是否互联网足迹
        columns = [f"is_{i}_internet" for i in ["buy", "sell", "adv"]]
        self.df_result["is_internet"] = self.df_result[columns].fillna(0).sum(axis=1)
        self.df_result.loc[
            self.df_result[columns].isnull().apply(lambda x: ~x).any(axis=1) == False,
            "is_internet",
        ] = np.nan
        self.df_result["is_internet"] = (
            self.df_result["is_internet"]
            .fillna(-1)
            .map(lambda x: np.nan if x == -1 else int(bool(x)))
        )
        # 未来是否互联网足迹
        columns = [f"future_{i}_internet" for i in ["sell", "adv"]]
        self.df_result["future_internet"] = (
            self.df_result[columns].fillna(0).sum(axis=1)
        )
        self.df_result.loc[
            self.df_result[columns].isnull().apply(lambda x: ~x).any(axis=1) == False,
            "future_internet",
        ] = np.nan
        self.df_result["future_internet"] = (
            self.df_result["future_internet"]
            .fillna(-1)
            .map(lambda x: np.nan if x == -1 else int(bool(x)))
        )
        # 分组
        self.df_result["buy_internet_amount_group"] = pd.qcut(
            self.df_result["buy_internet_amount"], 2, labels=[0, 1]
        )  # .map(lambda x: 1 if x not in [0, np.nan] else x)
        self.df_result["buy_internet_rate_group"] = pd.qcut(
            self.df_result["buy_internet_rate"], 2, labels=[0, 1]
        )  # .map(lambda x: 1 if x not in [0, np.nan] else x)
        log_list = ["buy_internet_amount", "sell_internet_amount"]
        self.df_result[log_list] = self.df_result[log_list].applymap(
            lambda x: np.log(x + 1)
        )


class Controls(Debt):
    """控制变量"""

    def __init__(self):
        self.reset_result()

    def open_year(self):
        """企业开立账户年份+预测最大笔贷款年份"""
        self.df_result["open_year"] = (
            self.df["e1011"].astype(float)
            # .map(lambda x: float(x) if x is not np.nan else x)
        )

    def industry(self):
        """行业分类:A1005(主营业务所属行业)"""
        self.df_result["industry"] = self.df["a1005"].replace(19, np.nan)
        self.df_result["industry_question"] = self.df_result["industry"].map(
            self.industry_dict["industry_question"]
        )
        self.df_result["industry_class"] = (
            self.df_result["industry"]
            .map(self.industry_dict["industry_class"])
            .map({"零售和批发业": 0, "制造业": 1})
        )

    """问卷内"""

    def size(self):
        """企业规模:F4001"""
        self.df_result["size"] = np.log(
            self.merge_it(
                name="f4001",
                position_list=[5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000],
            )
            + 1
        )

    def age(self):
        """企业年龄:2016-A1006"""
        self.df_result["age"] = (
            2015
            - self.df["a1006"].astype(float)
            # .map(lambda x: float(x) if x is not np.nan else x)
        ) * 12 + (
            12
            - self.df["a1006a"].map(
                lambda x: np.log(float(x) + 1) if x is not np.nan else x
            )
        )
        self.df_result["age^2"] = np.power(self.df_result["age"], 2)

    def asset(self):
        """企业资产:log(A1009)"""
        self.df_result["asset"] = np.log(
            self.merge_it(
                name="a1009",
                position_list=[
                    10,
                    20,
                    50,
                    100,
                    300,
                    500,
                    1000,
                    2000,
                    5000,
                    8000,
                    10000,
                    80000,
                    120000,
                ],
            )
            + 1
        )

    def is_profit(self):
        """经营情况:F4002"""
        self.df_result["is_profit"] = self.df["f4002"].map({"1": 1, "2": -1, "3": 0})

    def is_subsides(self):
        """政府补贴:F4004a"""
        self.df_result["is_subsides"] = self.df["f4004a"].map({"1": 1, "2": 0})

    def is_association(self):
        """行业协会:H2001"""
        self.df_result["is_association"] = self.df["h2001"].map({"1": 1, "2": 0})

    def working_fund(self):
        """日均流动资金:log(F2001)"""
        self.df_result["working_fund"] = np.log(
            self.merge_it(
                name="f2001", position_list=[1, 2, 5, 10, 20, 30, 50, 100, 200, 500]
            )
            + 1
        )

    def tax_tolerance(self):
        """税费负担程度:G1001"""
        self.df_result["tax_tolerance"] = (
            self.df["g1001"].astype(float)
            # .map(lambda x: float(x) if x is not np.nan else x)
        )

    # def bank_help(self):
    #     """金融服务帮助:H2012"""
    #     self.df_result["bank_help"] = (
    #         sum(self.df[f"h2012_{i}_mc"] for i in range(1, 10))
    #         .fillna(0)
    #         .map(lambda x: 1 if x > 0 else x)  # type: ignore
    #     )

    def manage_system(self):
        """企业管理制度:I1014"""
        self.df_result["manage_system"] = self.df["i1014"].map(
            lambda x: float(x) if x is not np.nan else x
        )

    def company_type(self):
        """企业组织形式:A1013"""
        self.df_result["company_type"] = self.df["a1013"].map(
            lambda x: float(x) if x is not np.nan else x
        )

    def company_ownership(self):
        """企业所有制形式:A1014"""
        self.df_result["company_ownership"] = self.df["a1014"].map(
            lambda x: float(x) if x is not np.nan else x
        )

    def employee_number(self):
        """企业人数:s(it)"""
        self.df_result["employee_number"] = np.log(
            self.merge_it(
                name="c1002",
                position_list=[
                    10,
                    20,
                    30,
                    40,
                    50,
                    60,
                    70,
                    80,
                    90,
                    100,
                    126,
                    150,
                    176,
                    200,
                    300,
                ],
            )
            + 1
        )

    def bank_type_match(self, x):
        """
        开户银行类型匹配:
        # 国有商业银行:55803
        # 城市商业银行:32076
        # 股份制商业银行:36435
        # 农村金融机构
        # 农村商业银行:33039
        # 外资银行:1973
        # 政策性银行
        """
        if 1 <= x <= 6:  # 中农工建交邮
            return "国有商业银行"
        elif x == 9:  # 城市商业银行
            return "城市商业银行"
        elif x == 10:  # 全国性股份制商业银行
            return "股份制商业银行"
        elif x in [7, 11]:  # 农村信用合作社+其他农村金融机构
            return "农村金融机构"
        elif x == 8:  # 农村商业银行
            return "农村商业银行"
        elif x == 15:  # 外资银行
            return "外资银行"
        elif x in [12, 13, 14]:  # 国家开发银行+中国进出口银行+中国农业发展银行
            return "政策性银行"
        else:
            return np.nan  # 其他

    def bank_type(self):
        """开户银行类型:E1010(int) -> bank_type:1-14;bank_name:国有商业银行···"""
        self.df_result["bank_type"] = (
            self.df["e1010"].fillna(0).astype(int).replace(0, np.nan)
        )
        self.df_result["bank_name"] = self.df_result["bank_type"].map(
            self.bank_type_match
        )

    """GDP"""

    def gdp(self):
        """GDP:三大产业+产业贡献度+指数"""
        self.merge_province(pd.read_csv("controls/gdp.csv"))

    """company"""

    def sme_operation_index_region(self):
        """小微企业运行指数(分地区)"""
        dic = (
            pd.read_csv("controls/company/小微企业运行指数(region+month).csv")
            .groupby("region")["sme_operation_index"]
            .mean()
            .to_dict()
        )
        self.df_class["sme_operation_index_region"] = (
            self.df_class["province"].map(self.region_dict).map(dic)
        )

    def sme_operation_index_industry(self):
        """小微企业运行指数(分行业)"""
        if "industry" not in self.df_result.columns:
            self.industry()
        dic = (
            pd.read_csv("controls/company/小微企业运行指数(industry+month).csv")
            .groupby("industry_sme_work")["sme_operation_index_industry"]
            .mean()
            .to_dict()
        )
        self.df_result["sme_operation_index_industry"] = (
            self.df_result["industry"]
            .map(self.industry_dict["industry_sme_work"])
            .map(dic)
        )

    def insurance_institution(self):
        """保险类金融机构分布（province+year）"""
        self.merge_province(
            pd.read_csv("controls/institution/保险类金融机构分布表（province+year）.csv")
        )

    def bank_institution(self):
        """银行金融机构分布（banktype+province+year）"""
        df = pd.read_csv("controls/institution/银行金融机构分布表（banktype+province+year）.csv")
        df["province"] = self.delete_pc(df["province"])
        columns = [
            "outlet_num",
            "outlet_employees",
            "outlet_assets",
            "corporate_ins_num",
            "outlet_pert",
        ]
        # 按省份匹配
        province_columns = [f"{column}_province" for column in columns]
        self.merge_province(
            df[df["bank_type_bfi"] == "合计"]
            .drop("bank_type_bfi", axis=1)
            .rename(columns=dict(zip(columns, province_columns)))
        )
        # 按银行类型匹配
        if "bank_type" not in self.df_result.columns:
            self.bank_type()
        bank_columns = [f"{column}_bank" for column in columns]
        bfi_dict = (
            df[df["year"].astype(int) == 2014]
            .rename(columns=dict(zip(columns, bank_columns)))
            .set_index(["province", "bank_type_bfi"])[bank_columns]
            .to_dict()
        )
        self.df_result["bank_type_bfi"] = self.df_result["bank_type"].map(
            self.bank_dict["bank_type_bfi"]
        )
        if "province" not in self.df_result.columns:
            self.df_result["province"] = pd.merge(
                self.df_result, self.df_class, on="company", how="left"
            )["province"]
        for bank_column in bank_columns:
            self.df_result[bank_column] = (
                self.df_result[["province", "bank_type_bfi"]]
                .apply(tuple, axis=1)
                .map(bfi_dict[bank_column])
            )
        self.df_result = self.df_result.drop(columns=["province"])

    def bank_worker(self):
        """银行业金融机构:法人机构+从业人员"""
        if "bank_type" not in self.df_result.columns:
            self.bank_type()
        df_worker = pd.read_csv(
            "controls/institution/银行业金融机构法人机构及从业人员表（banktype+year）.csv"
        )
        worker_dict = (
            df_worker[df_worker["year"].astype(int) == 2014]
            .drop(columns="year")
            .set_index("bank_type_bflpi")
            .to_dict()
        )
        for column in worker_dict.keys():
            self.df_result[column] = (
                self.df_result["bank_type"]
                .map(self.bank_dict["bank_type_bflpi"])
                .map(worker_dict[column])
            )

    def bank_index(self):
        """银行业景气与盈利指数表"""
        if "open_year" not in self.df_result.columns:
            self.open_year()
        columns = ["bank_bloomindex", "bank_profitindex"]
        self.df_result[columns] = pd.merge(
            self.df_result[["open_year"]],
            pd.read_csv("controls/institution/银行业景气与盈利指数表（year）.csv")
            .groupby("year")
            .mean()
            .reset_index(drop=False)
            .rename({"year": "open_year"}, axis=1),
            how="left",
            on="open_year",
        )[columns]

    """loan"""

    def industry_merge(self, df, columns, industry_name="industry_financial_loan"):
        """合并行业"""
        if "industry" not in self.df_result.columns:
            self.industry()
        for year in range(2013, 2015):
            dic = (
                df[df["year"].astype(int) == year]
                .drop(columns="year")
                .set_index(industry_name)
                .to_dict()
            )
            for column in columns:
                self.df_result[column + ("_lag" if year == 2013 else "")] = (
                    self.df_result["industry"]
                    .map(self.industry_dict[industry_name])
                    .map(dic[column])
                )

    def loan_balance(self):
        """金融机构贷款余额"""
        df_balance = pd.read_csv("controls/loan/金融机构贷款表（industry+year）.csv")
        columns = ["local_foreign_balance", "local_balance", "foreign_balance"]
        self.industry_merge(
            df=df_balance, columns=columns, industry_name="industry_financial_loan"
        )

    def loan_balance_small(self):
        """金融机构境内大中小微企业人民币贷款"""
        df_balance = pd.read_csv("controls/loan/金融机构境内大中小微企业人民币贷款（industry+year）.csv")
        df_balance = df_balance[df_balance["scale"] == "小型企业"]
        columns = ["fina_loan_balance"]
        self.industry_merge(
            df=df_balance, columns=columns, industry_name="industry_financial_loan"
        )

    def small_loan_balance(self):
        """小额贷款公司基本情况（province+quarter）"""
        self.merge_province(
            pd.read_csv("controls/loan/小额贷款公司基本情况表（province+quarter）.csv")
            .groupby(["year", "province"])
            .mean()
            .reset_index(drop=False)
        )

    def loan_approval(self):
        """银行业贷款审批指数"""
        if "max_bank_loan_year" not in self.df_result.columns:
            self.max_bank_loan_year()
        if "open_year" not in self.df_result.columns:
            self.open_year()
        approval_dict = (
            pd.read_csv("controls/loan/银行业贷款审批指数表（quarter）.csv")
            .groupby("year")
            .mean()["bank_loan_approval"]
            .to_dict()
        )
        self.df_result["bank_loan_approval(max_bank_loan_year)"] = self.df_result[
            "max_bank_loan_year"
        ].map(approval_dict)
        self.df_result["bank_loan_approval(open_year)"] = self.df_result[
            "open_year"
        ].map(approval_dict)

    def loan_demand(self):
        """银行业贷款需求指数"""
        if "max_bank_loan_year" not in self.df_result.columns:
            self.max_bank_loan_year()
        if "open_year" not in self.df_result.columns:
            self.open_year()
        columns = [
            "total_loan_demand",
            "large_loan_demand",
            "middle_loan_demand",
            "small_loan_demand",
        ]
        demand_dict = (
            pd.read_csv("controls/loan/银行业贷款需求指数表（quarter）.csv")
            .groupby("year")
            .mean()[columns]
            .to_dict()
        )
        for year_type in ["max_bank_loan_year", "open_year"]:
            for column in columns:
                self.df_result[f"{column}({year_type})"] = self.df_result[
                    year_type
                ].map(demand_dict[column])

    def loan_balance_dfh(self):
        """银行业金融机构普惠小微企业贷款余额"""
        if "bank_type" not in self.df_result.columns:
            self.bank_type()
        dfh_bank_dict = (
            pd.read_csv("controls/loan/银行业金融机构普惠小微企业贷款表（banktype+quarter）.csv")
            .set_index("bank_type_dfh")["sme_loan_balance"]
            .to_dict()
        )
        self.df_result["sme_loan_balance"] = (
            self.df_result["bank_type"]
            .map(self.bank_dict["bank_type_dfh"])
            .map(dfh_bank_dict)
        )

    def loan_balance_legal(self):
        if "bank_type" not in self.df_result.columns:
            self.bank_type()
        """银行用于法人小微企贷款余额"""
        legal_bank_dict = (
            pd.read_csv("controls/loan/银行用于法人小微企业贷款表（banktype+quarter）.csv")
            .groupby("bank_type_dfh")
            .mean()["legal_loan_balance"]
            .to_dict()
        )
        self.df_result["legal_loan_balance"] = (
            self.df_result["bank_type"]
            .map(self.bank_dict["bank_type_dfh"])
            .map(legal_bank_dict)
        )

    def treat_cost(self):
        self.df_result["treat_cost"] = np.log(
            self.merge_it(
                name="f4008",
                position_list=[0.5, 1, 2, 5, 10, 15, 20, 30, 500, 100],
            )
            + 1
        )
        self.df_result["treat_cost_group"] = pd.qcut(
            self.df_result["treat_cost"], 2, labels=[0, 1]
        )  # .map(lambda x: 1 if x not in [0, np.nan] else x)

    def all(self):
        """合并"""
        # 开户年份
        self.open_year()
        # 行业
        self.industry()
        # 问卷内
        self.size()
        self.age()
        self.asset()
        self.is_profit()
        self.is_subsides()
        self.is_association()
        self.working_fund()
        self.tax_tolerance()
        # self.bank_help()
        self.manage_system()
        self.company_type()
        self.company_ownership()
        self.employee_number()
        self.bank_type()
        # gdp
        self.gdp()
        # company
        self.sme_operation_index_region()
        self.sme_operation_index_industry()
        # institution
        self.insurance_institution()
        self.bank_institution()
        self.bank_worker()
        self.bank_index()
        # loan
        self.loan_balance()
        self.loan_balance_small()
        self.small_loan_balance()
        self.loan_approval()
        self.loan_demand()
        self.loan_balance_dfh()
        self.loan_balance_legal()
        # other
        self.treat_cost()


class Innovation(Controls):
    """创新"""

    def __init__(self):
        self.reset_result()

    def temp(self, x):
        """
        The temp function is used to create a new column in the dataframe.
        It takes an integer as input and returns 1 if it is 1 or 2, 0 if it is 0, and np.nan otherwise.

        :param self: Refer to the object itself
        :param x: Determine the value of the temperature at a specific time
        :return: A value of 1 if x is in the list [0, 1], a value of 0 if x is equal to 0 and np
        """

        if x in [1, 2]:
            return 1
        elif x == 0:
            return 0
        else:
            return np.nan

    def is_inno(self):
        """是否有创新"""
        # 是否有产品技术创新
        self.df_result["is_tech_inno"] = (
            self.df["d1001"].replace("1", 1).replace("2", 0)
        )
        # 是否有专职研发人员
        self.df_result["is_stuff_inno"] = (
            self.df["d1002"].replace("1", 1).replace("2", 0)
        )
        # 是否有其他创新
        self.df_result["is_else_inno"] = (
            self.df["d2001"].replace("1", 1).replace("2", 0)
        )
        # 是否有创新
        self.df_result["is_inno"] = self.df_result["is_tech_inno"].fillna(
            3
        ) + self.df_result["is_else_inno"].fillna(3)
        self.df_result["is_inno"] = self.df_result["is_inno"].map(self.temp)

    def inno_cost(self):
        """研发与创新活动经费总支出d1006a+自主研发的经费支出d1006b"""
        if "is_tech_inno" not in self.df_result.columns:
            self.is_inno()
        self.df_result["inno_total_cost"] = self.merge_it(
            name="d1006a", position_list=[1, 2, 5, 10, 20, 30, 50, 100, 200, 500]
        )
        self.df_result.loc[self.df_result["is_tech_inno"] == 0, "inno_total_cost"] = 0
        self.df_result["inno_self_cost"] = self.merge_it(
            name="d1006b", position_list=[1, 2, 5, 10, 20, 30, 50, 100, 200, 500]
        )
        self.df_result.loc[self.df_result["is_tech_inno"] == 0, "inno_self_cost"] = 0

    def inno_output(self):
        """研发创新活动产出：产品+技术"""
        if "is_tech_inno" not in self.df_result.columns:
            self.is_inno()
        # inno_product_output
        condition_type = self.df["d1007_1_mc"] == 1
        condition_work = self.df["d1008"].astype(float) == 1
        self.df_result.loc[
            condition_type & condition_work, "inno_product_output"
        ] = self.merge_it(
            name="d1009", position_list=[1, 2, 5, 10, 20, 30, 50, 100, 200, 500]
        )
        self.df_result.loc[
            self.df_result["is_tech_inno"] == 0, "inno_product_output"
        ] = 0
        # is_inno_product_output
        self.df_result["is_inno_product_output"] = (
            self.df_result["inno_product_output"]
            .fillna(-1)
            .map(lambda x: 1 if x > 0 else x)
            .replace(-1, np.nan)
            .map(lambda x: np.nan if x < 0 else x)
        )
        # is_inno_tech_output
        self.df_result["is_inno_tech_output"] = (
            self.df["d1011"].astype(float).map({1: 1, 2: 0})
        )
        self.df_result.loc[
            self.df_result["is_tech_inno"] == 0, "is_inno_tech_output"
        ] = 0
        # is_inno_output
        self.df_result["is_inno_output"] = (
            self.df_result["is_inno_product_output"].fillna(-2)
            + self.df_result["is_inno_tech_output"].fillna(-2)
        ).map({-4: np.nan, -1: 1, -2: 0, 0: 0, 0: 1, 2: 1})

    def inno_efficiency(self):  # TODO
        # if 'size' not in self.df_result.columns:
        #     self.size()
        self.inno_cost()
        self.inno_output()
        self.df_result["inno_total_efficiency"] = (
            self.df_result["inno_product_output"] / self.df_result["inno_total_cost"]
        )
        self.df_result["inno_self_efficiency"] = (
            self.df_result["inno_product_output"] / self.df_result["inno_self_cost"]
        )
        # print(self.df_result['inno_total_efficiency'].describe())

    def inno_consciousness(self):
        """创新意识"""
        # 创新风险
        self.df_result["inno_risk_consciousness"] = self.df["d3012"].astype(float)
        # 创新必要性
        self.df_result["inno_need_consciousness"] = (
            self.df["d3016_1_mc"].astype(float).fillna(-2)
            + self.df["d3016_2_mc"].astype(float).fillna(-2)
        ).map({-4: np.nan, -2: 0, -1: 1, 0: 0, 1: 1, 2: 1})
        # 员工创新重视程度
        self.df_result["inno_stuff_consciousness"] = self.df["i1010"].astype(float)

    def all(self):
        """合并"""
        self.is_inno()
        # self.inno_cost()
        # self.inno_output()
        self.inno_efficiency()
        self.inno_consciousness()
        log_list = ["inno_total_cost", "inno_self_cost", "inno_product_output"]
        self.df_result[log_list] = self.df_result[log_list].applymap(
            lambda x: np.log(x + 1) if x is not np.nan else np.nan
        )
        # self.df_result.to_csv('inno.csv')


class Interest(Controls):
    """融资贵:利率"""

    def __init__(self):
        self.reset_result()

    def rate(self):
        """利率大小:e1029(大小),e1030(单位)"""
        self.df_result["rate"] = self.df["e1029"].map(
            lambda x: float(x) if x is not np.nan else x
        ) * self.df["e1030"].map({"1": 0.01, "2": 0.001, "3": 0.01, "4": 0.1})

    def annual_rate(self):
        """年利率:e1028(结算频率)"""
        self.rate()
        frequency = self.df["e1028"].map(
            {"1": 1, "2": 12, "3": 360, "4": 2, "5": 4, "6": np.nan, "7": np.nan}
        )
        self.df_result["annual_rate"] = (
            1 + self.df_result["rate"] / frequency
        ) ** frequency - 1

    def loan_year(self):
        """贷款年份:e1024"""
        self.df_result["loan_year"] = self.df["e1024"].map(
            lambda x: float(x) if x is not np.nan else np.nan
        )
        # 预测max_bank_loan_year -> loan_year_predict
        if "max_bank_loan_year" not in self.df_result.columns:
            self.max_bank_loan_year()
        if "open_year" not in self.df_result.columns:
            self.open_year()
        model = smf.ols(
            formula="max_bank_loan_year ~ open_year", data=self.df_result
        ).fit()
        b, a = model.params
        self.df_result["loan_year_predict"] = (a * self.df_result["open_year"] + b).map(
            lambda x: round(x, 0)
        )
        self.df_result["loan_year_predict"] = self.df_result[
            "max_bank_loan_year"
        ].fillna(self.df_result["loan_year_predict"])

    def max_bank_loan_maturity(self):
        """最大笔贷款的还款期限:E1025"""
        self.df_result["max_bank_loan_maturity"] = (
            self.df["e1025"]
            .replace("0", np.nan)
            .replace("9999", np.nan)
            .map(lambda x: float(x) if x is not np.nan else np.nan)
        )

    def match_maturity(self, month):  # sourcery skip: remove-redundant-if
        """匹配期限"""
        if month <= 6:
            return "0.5"
        elif 6 < month <= 12:
            return "1"
        elif 12 < month <= 36:
            return "1-3"
        elif 36 < month <= 60:
            return "3-5"
        elif month > 60:
            return "5"
        else:
            return False

    def other_rate_cal(self, name):
        """利率加权计算"""
        self.df_other_rate[name] = (
            self.df_other_rate["date_diff"] * self.df_other_rate[name]
        )
        return (
            self.df_other_rate.groupby("year")[name].sum()
            / self.df_other_rate.groupby("year")["date_diff"].sum()
        )

    def other_rate(self):
        """其他宏观利率"""
        # 导入并合并（方式“outer”）
        self.df_other_rate = pd.merge(
            pd.read_csv("rate/reserve_rate.csv"),
            pd.read_csv("rate/loan_rate.csv"),
            how="outer",
        )
        # 添加每年的“1/1”和“12/31”
        df_new = pd.DataFrame(
            [f"{i}/1/1" for i in range(1989, 2016)]
            + [f"{i}/12/31" for i in range(1989, 2016)],
            columns=["date"],
        )
        self.df_other_rate = pd.merge(self.df_other_rate, df_new, how="outer")
        # 转换日期格式
        self.df_other_rate["date"] = pd.to_datetime(self.df_other_rate["date"])
        # 按照日期排序
        self.df_other_rate.sort_values("date", inplace=True)
        # 缺失值“向前”填充
        self.df_other_rate = self.df_other_rate.fillna(method="ffill").fillna(
            method="bfill"
        )
        # 获取年份
        self.df_other_rate["year"] = self.df_other_rate["date"].dt.year
        # 计算日期间天数差值
        self.df_other_rate["date(-1)"] = self.df_other_rate["date"].shift(-1)
        self.df_other_rate["date_diff"] = (
            (self.df_other_rate["date(-1)"] - self.df_other_rate["date"])
            .astype("timedelta64[D]")
            .fillna(0)
            .map(lambda x: int(x) if x != 0 else np.nan)
        )
        # 需要加权的利率变量
        reserve_list = [
            "reserve_rate",
            "excess_rate",
            "loan_rate_annual",
            "loan_rate_quarter",
            "loan_rate_20days",
        ]
        loan_list = [
            "loan_rate(0.5)",
            "loan_rate(1)",
            "loan_rate(1-3)",
            "loan_rate(3-5)",
            "loan_rate(5)",
        ]
        # 生成储存结果的数据框
        df = pd.DataFrame(range(1989, 2016), columns=["loan_year_predict"]).set_index(
            "loan_year_predict"
        )
        # 利率加权计算
        for name in reserve_list + loan_list:
            df[name] = self.other_rate_cal(name)
        self.df_other_rate = df
        # 匹配字典:loan_list
        df.loc[0] = np.nan  # type: ignore
        self.match_dict = df[loan_list].to_dict()
        self.match_dict[np.nan] = {0: np.nan, np.nan: np.nan}
        for i in self.match_dict:
            self.match_dict[i][np.nan] = np.nan
        # 合并剩余宏观数据:reserve_list
        if "loan_year_predict" not in self.df_result.columns:
            self.loan_year()
        self.df_result = pd.merge(
            self.df_result,
            df[reserve_list].reset_index(level=0),
            on="loan_year_predict",
            how="left",
        )
        # df = df.reset_index(drop=False).rename(
        #     {'loan_year': 'loan_year_predict'})
        # self.df_result = pd.merge(
        #     self.df_result, df[reserve_list], on='loan_year_predict', how='left')

    def match_func(self, x):
        """
        The match_func function is a helper function that takes in two arguments:
            1. self, which refers to the instance of the class
            2. x, which refers to a tuple containing (i) an index and (ii) a value from one of
            the columns in our dataset

        :param self: Reference the class itself
        :param x: Match the values in the dataframe to those in the dictionary
        :return: The match_dict value for the given x
        """
        return np.nan if np.nan in x else self.match_dict[x[1]][int(x[0])] * 0.01

    def match_rate(self):
        """匹配利率"""
        self.annual_rate()  # 年利率
        self.loan_year()  # 贷款年份
        self.max_bank_loan_maturity()  # 最大笔贷款的还款期限
        self.other_rate()  # 其他宏观利率
        # 匹配期限+年份
        self.df_result["max_bank_loan_maturity_type"] = (
            self.df_result["max_bank_loan_maturity"]
            .map(self.match_maturity)
            .map(lambda x: f"loan_rate({x})" if x else np.nan)
        )
        self.df_result["loan_year"] = self.df_result["loan_year"].fillna(0)
        self.df_result["other_rate"] = (
            self.df_result[["loan_year", "max_bank_loan_maturity_type"]]
            .apply(list, axis=1)
            .apply(self.match_func)
        )
        # 填充缺失贷款利率
        self.df_result["annual_rate"].fillna(self.df_result["other_rate"], inplace=True)
        del self.df_result["other_rate"]

    def all(self):
        self.match_rate()
        self.df_result["loan_year"].replace(0, np.nan, inplace=True)
        self.df_result["annual_rate"] = (
            self.df_result["rate"]
            .map(lambda x: min(x, 0.15))
            .map(lambda x: max(x, 0.01))
        )


class Knowledge(Controls):
    """企业主知识"""

    def __init__(self):
        self.reset_result()

    def financial_attention(self):
        """对金融经济知识关注程度+是否上过经济或金融类课程"""
        self.df_result["financial_attention"] = (
            self.df["i1023"]
            .astype(float)
            .map(lambda x: 6 - x if x is not np.nan else np.nan)
        )
        self.df_result["financial_course"] = (
            self.df["i1023a"].astype(float).map({1: 1, 2: 0})
        )

    def risk_preference(self):
        """风险偏好"""
        self.df_result["risk_preference"] = (
            self.df["i1024"]
            .astype(float)
            .map(lambda x: 6 - x if x is not np.nan else np.nan)
        )
        self.df_result["lottery_preference"] = self.df["i1025"].astype(float)

    def interest_rate(self):
        """利率计算"""
        self.df_result["answer_interest_rate"] = (
            self.df["i1024a"].astype(float).map({1: 0, 2: 1, 3: 0, 4: 0})
        )
        self.df_result["knowledge_interest_rate"] = (
            self.df["i1024a"].astype(float).map({1: 1, 2: 1, 3: 1, 4: 0})
        )

    def inflation_rate(self):
        """通胀率计算"""
        self.df_result["answer_inflation_rate"] = (
            self.df["i1024b"].astype(float).map({1: 1, 2: 0, 3: 0, 4: 0})
        )
        self.df_result["knowledge_inflation_rate"] = (
            self.df["i1024b"].astype(float).map({1: 1, 2: 1, 3: 0, 4: 0})
        )

    def stock_fund(self):
        """股票基金风险判断"""
        self.df_result["answer_stock_fund"] = (
            self.df["i1026"]
            .astype(float)
            .fillna(-1)
            .map(lambda x: 0 if x not in (1, -1) else x)
            .replace(-1, np.nan)
        )
        self.df_result["knowledge_stock_fund"] = (
            self.df["i1026"]
            .astype(float)
            .fillna(-1)
            .map(lambda x: 0 if x not in (1, 2, 3, -1) else min(x, 1))
            .replace(-1, np.nan)
        )

    def all(self):
        """合并"""
        self.financial_attention()
        self.risk_preference()
        self.interest_rate()
        self.inflation_rate()
        self.stock_fund()

    # def factor_analyze(self):
    #     self.all()
    #     df_factor = self.df_result.dropna().set_index("company")
    #     print(df_factor)


class Missing(Pre):
    """企业基本信息未答题数量"""

    def __init__(self):
        self.reset_result()

    def a1016(self):
        self.df.loc[self.df["a1013"] == "1", "a1016"] = 1

    def a1021(self):
        condition = (self.df["a1013"] == "1") | (
            (self.df["a1015"] == 1) & (self.df["a1016"] == "1")
        )
        self.df.loc[condition, "a1021"] = 100
        self.df.loc[~self.df["a1021it"].isnull(), "a1021"] = 0

    def a1022(self):
        self.df.loc[~self.df["a1022it"].isnull(), "a1022"] = 0

    def a1025(self):
        self.df.loc[~self.df["a1025it"].isnull(), "a1025"] = 0

    def a1026(self):
        self.df.loc[~self.df["a1026a"].isnull(), "a1026"] = 0

    def a1030(self):
        self.df["a1030a"] = (
            self.df[[f"a1030a_{i}_mc" for i in range(1, 10)]].isnull().any(axis=1)
        )

    def a1032(self):
        self.df.loc[self.df["a1015"] == 1, "a1032"] = 1

    def a1034(self):
        self.df.loc[self.df["a1015"] == 1, "a1034"] = 100
        self.df.loc[~self.df["a1034"].isnull(), "a1034"] = 100

    def a1035(self):
        self.df.loc[self.df["a1015"] == 1, "a1035"] = 1

    def repayment_capacity(self):
        self.df_result["repayment_capacity"] = (
            self.df["e1068"].astype(float).map({1: 1, 2: 0, 3: 0, 4: 0})
        )
        condition = (
            (self.df["e1014"].astype(float) == 2)
            & (self.df["e1043"].astype(float) == 2)
            & (self.df["e1045"].astype(float) == 2)
        )
        self.df_result.loc[condition, "repayment_capacity"] = 1
        self.df_result.loc[
            (self.df["e1068a_3_mc"].astype(float) == 1), "repayment_capacity"
        ] = 0
        # self.df_result['repayment_capacity'] = self.df_result['repayment_capacity'].fillna(1-self.df['e1068a_3_mc'].astype(float))
        # self.df_result["repayment_capacity"] = self.df['e1068a_3_mc'].astype(float)

    def all(self):
        self.repayment_capacity()
        self.a1016()
        self.a1021()
        self.a1022()
        self.a1025()
        self.a1026()
        self.a1030()
        self.a1032()
        self.a1034()
        self.a1035()

        info_columns = [
            "a1010",
            "a1011",
            "a1012",
            "a1013",
            "a1014",
            "a1015",
            "a1016",
            "a1018",
            "a1019",
            "a1020",
            "a1021",
            "a1022",
            "a1023",
            "a1024",
            "a1025",
            "a1026",
            "a1030a",
            "a1030b",
            "a1032",
            "a1034",
            "a1035",
            "a1036",
            "a1038",
        ]
        self.df_result["missing_number"] = np.log(
            self.df[info_columns].isnull().sum(axis=1) + 1
        )


class Result(Pre):
    """导出结果"""

    def factorize(self):
        """编码:省份+地区+开户银行类型+..."""
        self.df_result["province_code"] = pd.factorize(self.df_result["province"])[0]
        self.df_result["region"] = self.df_result["province"].map(self.region_dict)
        self.df_result["region_code"] = pd.factorize(self.df_result["region"])[0]
        self.df_result["bank_type"] = pd.Series(
            pd.factorize(self.df_result["bank_type"])[0]
        ).replace(-1, np.nan)

    def weight(self):
        """权重处理"""
        self.df_result["weight"] = (self.df_result["weight"] * 10000000).astype(int)

    def log_cal(self):
        """对df_class中指标进行对数处理"""
        log_list = [
            "distance_metres",
            "distance_miles",
            "distance_sphere",
            "coverage_breadth(-1)",
            "coverage_breadth",
            "usage_depth(-1)",
            "usage_depth",
            "credit(-1)",
            "credit",
            "digitization_level(-1)",
            "digitization_level",
            "DFH(-1)",
            "DFH",
        ]
        self.df_result[log_list] = self.df_result[log_list].applymap(
            lambda x: np.log(x + 1)
        )

    def get_data(self):
        """计算所有指标"""
        equity = Equity()
        equity.all()
        debt = Debt()
        debt.all()
        foot = DigitalFoot()
        foot.all()
        controls = Controls()
        controls.all()
        inno = Innovation()
        inno.all()
        interest = Interest()
        interest.all()
        missing = Missing()
        missing.all()
        df_factor = pd.read_csv("knowledge/factor.csv")
        weight_list = [27.714, 22.008, 16.713]
        weight_list = list(map(lambda x: x / sum(weight_list), weight_list))
        df_factor["knowledge"] = (
            df_factor["factor_calculate"] * weight_list[0]
            + df_factor["factor_judge"] * weight_list[1]
            + df_factor["factor_attention"] * weight_list[2]
        )
        df_factor["knowledge_group"] = pd.qcut(
            df_factor["knowledge"], 5, labels=range(5)
        ).map(lambda x: 1 if x not in [0, np.nan] else x)
        df_factor["factor_calculate_group"] = pd.qcut(
            df_factor["factor_calculate"], 5, labels=range(5)
        ).map(lambda x: 1 if x not in [0, np.nan] else x)
        df_factor["factor_judge_group"] = pd.qcut(
            df_factor["factor_judge"], 5, labels=range(5)
        ).map(lambda x: 1 if x not in [0, np.nan] else x)
        df_factor["factor_attention_group"] = pd.qcut(
            df_factor["factor_attention"], 5, labels=range(5)
        ).map(lambda x: 1 if x not in [0, np.nan] else x)

        result_list = [
            equity.df_result,
            debt.df_result,
            inno.df_result,
            foot.df_result,
            interest.df_result,
            controls.df_result,
            missing.df_result,
            df_factor,
        ]
        self.df_result = pd.concat(
            [df.set_index("company") for df in result_list], axis=1
        ).reset_index(drop=False)

        self.df_result = pd.merge(
            controls.df_class, self.df_result, how="outer", on="company"
        )

    def winsorize_vars(self):
        """缩尾处理(df_result)"""
        winsorize_columns = [
            "initial_investment",
            "government_subsidy",
            "add_investment",
            "bank_loan_number",
            "max_rest_bank_loan",
            "max_bank_loan",
            "all_rest_bank_loan",
            "all_bank_loan",
            "bank_loan_need",
            "bank_loan_dissatisfaction",
            "bank_loan_satisfaction_rate",
            "bank_loan_restrict",
            "bank_loan_restrict_rate",
            "buy_internet_amount",
            "buy_internet_rate",
            "sell_internet_amount",
            "size",
            "asset",
            "working_fund",
            "employee_number",
        ]
        self.df_result[winsorize_columns] = self.extreme(
            self.df_result[winsorize_columns], columns=winsorize_columns
        )

    def work(self):
        self.get_data()
        self.factorize()
        self.weight()
        self.log_cal()
        self.winsorize_vars()
        self.df_result.to_csv("test.csv", index=False)
        ic(self.df_result)


if __name__ == "__main__":
    # equity = Equity()
    # equity.all()
    # print(equity.df_result.head(20))

    # debt = Debt()
    # debt.all()
    # print(debt.df_result.head(60))

    # inno = Innovation()
    # inno.inno_consciousness()
    # inno.all()
    # print(inno.df_result.head(20))

    # foot = DigitalFoot()
    # foot.all()
    # print(foot.df_result.head(20))

    # controls = Controls()
    # controls.all()
    # controls.open_year()
    # print(controls.df_result.head(20))
    # print(controls.df_class.head(20))

    # interest = Interest()
    # interest.all()
    # print(interest.df_result.head(20))

    # knowledge = Knowledge()
    # knowledge.all()
    # print(knowledge.df_result.head(20))
    # knowledge.df_result.to_csv('knowledge/knowledge.csv',index=False)

    # missing = Missing()
    # missing.all()
    # pprint(missing.df_result.head(20))

    result = Result()
    result.work()
    ...
