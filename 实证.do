**# 导入数据 
// import delimited "D:\github\hxy\data\test.csv", clear
import delimited "C:\Users\19319\iCloudDrive\Desktop\hxy\data\test.csv", clear

**# 控制变量
global restrict_control "size age age2 asset tax_tolerance employee_number gdp_2_proportion reserve_rate loan_rate_annual"
// 固定效应: i.industry i.company_ownership i.bank_type
// 被遗弃: company_type manage_system gdp_index_per

**# 描述性统计
outreg2 using Table1.xls, sum(log) bdec(3) tdec(2) keep(dfh  bank_loan_restrict_rate internet_penetration isi repayment_capacity  $restrict_control) title(Decriptive statistics) replace
* is_inno is_inno_product_output is_inno_tech_output is_buy_internet buy_internet_amount buy_internet_rate buy_internet_rate is_sell_internet private_loan_restrict_rate treat_cost loan_preference_2
**********************************************************************

**# 基准回归: b=-0.580,p=0.000 
reg bank_loan_restrict_rate dfh $restrict_control i.industry i.company_ownership i.bank_type [aweight=weight], r
estat vif // 共线性诊断
**# 输出
outreg2 using table2.doc, keep(dfh $restrict_control) tstat bdec(3) e(F) adec(3) tdec(2) ctitle("ols") replace


**********************************************************************

**# 稳健性检验
**# 1.替换估计方法: b=-4.276,p=0.000 
tobit bank_loan_restrict_rate dfh $restrict_control i.industry i.company_ownership i.bank_type [aweight=weight], ll ul
**# 输出
outreg2 using table2.xls, keep(dfh $restrict_control) tstat bdec(3) e(F) adec(3) tdec(2) ctitle("tobit") replace
**# 2.替换解释变量 
// coverage_breadth usage_depth credit digitization_level
qui reg bank_loan_restrict_rate coverage_breadth $restrict_control i.industry i.company_ownership i.bank_type [aweight=weight], r
estimates store coverage_breadth
qui reg bank_loan_restrict_rate usage_depth $restrict_control i.industry i.company_ownership i.bank_type [aweight=weight], r
estimates store usage_depth
qui reg bank_loan_restrict_rate credit $restrict_control i.industry i.company_ownership i.bank_type [aweight=weight], r
estimates store credit
qui reg bank_loan_restrict_rate digitization_level $restrict_control i.industry i.company_ownership i.bank_type [aweight=weight], r
estimates store digitization_level // 符号反了
estimates table coverage_breadth usage_depth credit digitization_level
**# 输出
outreg2 using table2.xls, append keep(dfh $restrict_control) tstat bdec(3) e(F) adec(3) tdec(2) ctitle("tobit") addtext(Year,Yes,Industry,Yes) replace
**# 3.替换被解释变量: b=-6.842,p=0.000
reg bank_loan_restrict dfh $restrict_control i.industry i.company_ownership i.bank_type [aweight=weight], r
outreg2 using table2.xls, keep(dfh $restrict_control) tstat bdec(3) e(F) adec(3) tdec(2) ctitle("ols") replace
**# 4.加入遗漏变量: gdp_index_per i.company_type i.manage_system
// b=-0.561,p=0.000
reg bank_loan_restrict_rate dfh gdp_index_per $restrict_control i.industry i.company_ownership i.bank_type i.company_type i.manage_system [aweight=weight], r

**********************************************************************

**# 样本自选择问题：b=-0.577,p=0.000
// miss_group missing_number repayment_capacity
preserve
probit miss_group missing_number repayment_capacity $restrict_control i.industry i.company_ownership i.bank_type, r
predict z if e(sample), xb
generate phi=normalden(z)
generate PHI=normal(z)
generate lambda=phi/(1-PHI)
reg bank_loan_restrict_rate dfh lambda $restrict_control i.industry i.company_ownership i.bank_type, r
restore

**********************************************************************

**# 遗漏变量+测量误差 (工具变量:internet_penetration, isi)
**# 1.排他性检验: Y=IV+C → Y=IV+X+C
reg bank_loan_restrict_rate internet_penetration_1 $restrict_control i.industry i.company_ownership i.bank_type [aweight=weight], r
estimates store withoutX 
reg bank_loan_restrict_rate dfh internet_penetration_1 $restrict_control i.industry i.company_ownership i.bank_type [aweight=weight], r
estimates store withX 
estimates table withoutX withX, star (0.05 0.01 0.001)

reg bank_loan_restrict_rate phone_rural $restrict_control i.industry i.company_ownership i.bank_type [aweight=weight], r
estimates store withoutX 
reg bank_loan_restrict_rate dfh phone_rural $restrict_control i.industry i.company_ownership i.bank_type [aweight=weight], r
estimates store withX 
estimates table withoutX withX, star (0.05 0.01 0.001)

**# 2.两阶段最小二乘: user_number_1 internet_penetration_1 user_size_growth_rate_1 distance_metres distance_miles distance_sphere phone_sum phone_urban phone_rural phone_mobile
// b=-0.579>-0.580(主要为解释变量的测量误差导致向下偏差),p=0.000
**# 2.1 第一阶段: b=1.033,-0.064 p=0.000,0.000
replace phone_rural = phone_rural*0.001
ivregress 2sls bank_loan_restrict_rate $restrict_control i.industry i.company_ownership i.bank_type (dfh=phone_rural internet_penetration_1), r first

**# 2.2豪斯曼检验: p=0.0597,0.0618
estat endogenous
**# 2.3弱工具变量检验: F=13878.3>19.93
estat firststage, all forcenonrobust
**# 2.4过度识别约束检验: p=0.9590
estat overid

**# 3.Heckman-IV：b=-0.622,p=0.000
preserve
qui probit miss_group missing_number repayment_capacity $restrict_control i.industry i.company_ownership i.bank_type, r
predict z if e(sample), xb
generate phi=normalden(z)
generate PHI=normal(z)
generate lambda=phi/(1-PHI)
ivregress 2sls bank_loan_restrict_rate lambda $restrict_control i.industry i.company_ownership i.bank_type (dfh=phone_rural internet_penetration_1), r first
restore

**********************************************************************

**# 创新
**# 1.is_inno
bdiff,group(is_inno) model(reg bank_loan_restrict_rate dfh $restrict_control, r) reps(1000) bsample // b0-b1=-0.252,p=0.030
qui reg bank_loan_restrict_rate dfh $restrict_control if is_inno==0, r
estimates store is_inno_0
qui reg bank_loan_restrict_rate dfh $restrict_control if is_inno==1, r
estimates store is_inno_1
estimates table is_inno_0 is_inno_1

**# 2.is_inno_product_output
bdiff,group(is_inno_product_output) model(reg bank_loan_restrict_rate dfh $restrict_control, r) reps(1000) bsample // b0-b1=-0.308,p=0.004
qui reg bank_loan_restrict_rate dfh $restrict_control if is_inno_product_output==0, r
estimates store is_inno_product_output_0
qui reg bank_loan_restrict_rate dfh $restrict_control if is_inno_product_output==1, r
estimates store is_inno_product_output_1
estimates table is_inno_product_output_0 is_inno_product_output_1

**# 3.is_inno_tech_output
bdiff,group(is_inno_tech_output) model(reg bank_loan_restrict_rate dfh $restrict_control, r) reps(1000) bsample // b0-b1=-0.366,p=0.008
qui reg bank_loan_restrict_rate dfh $restrict_control if is_inno_tech_output==0, r
estimates store is_inno_tech_output_0
qui reg bank_loan_restrict_rate dfh $restrict_control if is_inno_tech_output==1, r
estimates store is_inno_tech_output_1
estimates table is_inno_tech_output_0 is_inno_tech_output_1

**********************************************************************

**# 数字足迹 industry_class==0 零售行业

**# 1.1 is_buy_internet（核心1）
**# 总体
bdiff,group(is_buy_internet) model(reg bank_loan_restrict_rate dfh $restrict_control, r) reps(500) bsample // 全样本: p=0.246 n=1086
**# 分行业
preserve
keep if industry_class==0 // 零售行业: p=0.000 n=709
bdiff,group(is_buy_internet) model(reg bank_loan_restrict_rate dfh $restrict_control, r) reps(500) bsample 
restore
preserve
keep if industry_class==1 // 其他行业: p=0.412 n=278
bdiff,group(is_buy_internet) model(reg bank_loan_restrict_rate dfh $restrict_control, r) reps(500) bsample 
restore

**# 1.2 buy_internet_amount_group buy_internet_rate_group（核心2）
**# 总体
bdiff,group(buy_internet_amount_group) model(reg bank_loan_restrict_rate dfh $restrict_control, r) reps(500) bsample // 全样本: p=0.298 n=1151
**# 分行业
preserve
keep if industry_class==0 // 零售行业: p=0.016 n=760
bdiff,group(buy_internet_amount_group) model(reg bank_loan_restrict_rate dfh $restrict_control, r) reps(500) bsample
restore
preserve
keep if industry_class==1 // 其他行业: p=0.278 n=343
bdiff,group(buy_internet_amount_group) model(reg bank_loan_restrict_rate dfh $restrict_control, r) reps(500) bsample 
restore

**# 1.3 buy_internet_rate_group（核心3）
**# 总体
bdiff,group(buy_internet_rate_group) model(reg bank_loan_restrict_rate dfh $restrict_control, r) reps(500) bsample // 全样本: p=0.030 n=1050
**# 分行业
preserve
keep if industry_class==0 // 零售行业: p=0.026 n=701
bdiff,group(buy_internet_amount_group) model(reg bank_loan_restrict_rate dfh $restrict_control, r) reps(500) bsample
restore
preserve
keep if industry_class==1 // 其他行业: p=0.142 n=288
bdiff,group(buy_internet_rate_group) model(reg bank_loan_restrict_rate dfh $restrict_control, r) reps(500) bsample 
restore


**# 2.is_sell_internet（用于额外讨论）
// 样本分布存在问题 → 集中在零售行业，且仅有106个0
// → 导致sell_internet amount仅有80个值大于0
**# 总体
bdiff,group(is_sell_internet) model(reg bank_loan_restrict_rate dfh $restrict_control, r) reps(500) bsample // 全样本: p=0.000 n=1391
* is_sell_internet==0 → p=0.000 n=1312
reg bank_loan_restrict_rate dfh $restrict_control if is_sell_internet==0, r 
* is_sell_internet==1 → p=0.001 n=79
reg bank_loan_restrict_rate dfh $restrict_control if is_sell_internet==1, r 
**# 分行业
preserve
keep if industry_class==0 // 零售业行: p=0.012 n=397
bdiff,group(is_sell_internet) model(reg bank_loan_restrict_rate dfh $restrict_control, r) reps(500) bsample 
restore
preserve
keep if industry_class==1 // 其他行业: n=0
bdiff,group(is_sell_internet) model(reg bank_loan_restrict_rate dfh $restrict_control, r) reps(500) bsample 
restore

**********************************************************************

**# 民间借贷 → 挤出效应
center dfh private_loan_restrict_rate 
**# 1.总体: b=-0.329, p=0.000, n=2466
reg bank_loan_restrict_rate dfh private_loan_restrict_rate c.c_private_loan_restrict_rate#c.c_dfh $restrict_control i.industry i.company_ownership i.bank_type [aweight=weight], r
**# 2.1分招待费
reg bank_loan_restrict_rate dfh private_loan_restrict_rate c.c_private_loan_restrict_rate#c.c_dfh $restrict_control i.industry i.company_ownership i.bank_type [aweight=weight] if treat_cost_group==1, r // p=0.000,0.000, n=1263
reg bank_loan_restrict_rate dfh private_loan_restrict_rate c.c_private_loan_restrict_rate#c.c_dfh $restrict_control i.province i.industry i.company_ownership i.bank_type [aweight=weight] if treat_cost_group==0, r // p=0.024,0.022, n=1162
**# 2.2分融资偏好
reg bank_loan_restrict_rate dfh private_loan_restrict_rate c.c_private_loan_restrict_rate#c.c_dfh $restrict_control i.industry i.company_ownership i.bank_type [aweight=weight] if loan_preference_2==1, r // p=0.014,0.157, n=1263
reg bank_loan_restrict_rate dfh private_loan_restrict_rate c.c_private_loan_restrict_rate#c.c_dfh $restrict_control i.industry i.company_ownership i.bank_type [aweight=weight] if loan_preference_2!=1, r // p=0.002,0.001, n=1229

**********************************************************************