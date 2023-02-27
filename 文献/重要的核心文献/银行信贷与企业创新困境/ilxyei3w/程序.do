
FIGURE 1:
sum   hrdvN  if   hrdvN==N  /N从1~10，表示持续N期rd高于行业基准数量,数据1
sum   hrdvN  if   hrdvN==0  /N从1~10，表示持续N期rd低于行业基准数量,数据1
sum   hrdvN  if   hrdcN==N  /N从1~10，表示持续N期rd高于地区基准数量,数据1
sum   hrdvN  if   hrdcN==0  /N从1~10，表示持续N期rd低于地区基准数量,数据1


Appendix 1:
tab hrdv5  if  ccer==N   /N位申万行业代码,数据1

TABEL 1:
tab  hrdvN if  hdtvN==N  /N从1~10，表示持续N期信贷高于行业平均公司中，hrdvN=0 和 hrdvN=N的企业数量和占比,数据1
tab  hrdcN if  hdtcN==N  /N从1~10，表示持续N期信贷高于地区平均公司中，hrdcN=0 和 hrdcN=N的企业数量和占比,数据1

Appendix 3:
sum  vbankcr   cbankcr hrdv5 hrdc5 rd    /数据1

Appendix 4:
pwcorr vbankcr   cbankcr hrdv5 hrdc5 rd ,sig   /数据1

TABEL 2:
xtreg   vbankcr         l.rd  l.opcash   l.ppe      l.size l.lev   l. hightec3    l.absnda    l.roa   i.year  if bank0==1, fe r /bank0==1 代表非银行金融业样本,数据1
xtreg   vshortcr     l.rd  l.opcash   l.ppe      l.size l.lev   l. hightec3    l.absnda    l.roa   i.year  if bank0==1, fe r  /数据1
xtreg    vlongcr      l.rd  l.opcash   l.ppe      l.size l.lev   l. hightec3    l.absnda    l.roa   i.year  if bank0==1, fe r  /数据1
xtreg    cbankcr     l.rd  l.opcash   l.ppe      l.size l.lev   l. hightec3    l.absnda    l.roa   i.year  if bank0==1, fe r  /数据1
xtreg    cshortcr      l.rd  l.opcash   l.ppe      l.size l.lev   l. hightec3    l.absnda    l.roa   i.year  if bank0==1, fe r  /数据1
xtreg    clongcr      l.rd  l.opcash   l.ppe      l.size l.lev   l. hightec3    l.absnda    l.roa   i.year  if bank0==1, fe r  /数据1

TABEL 3:
xtreg     rd      l.vbankcr    l.size      l.lev     l.absnda l.age   i.year  if bank0==1, fe r   /数据1
xtreg     rd      l.vshortcr    l.size      l.lev     l.absnda l.age   i.year  if bank0==1, fe r   /数据1
xtreg     rd      l. vlongcr   l.size      l.lev     l.absnda l.age   i.year  if bank0==1, fe r   /数据1
xtreg     rd      l.cbankcr    l.size      l.lev     l.absnda l.age   i.year  if bank0==1, fe r   /数据1
xtreg     rd      l. cshortcr     l.size      l.lev     l.absnda l.age   i.year  if bank0==1, fe r   /数据1
xtreg     rd      l. clongcr   l.size      l.lev     l.absnda l.age   i.year  if bank0==1, fe r   /数据1

TABEL 4:
ologit   hrdv3  l.vbankcr    l.size      l.lev     l.absnda l.age          i.year    if      bank0==1  ,r   nolog   /数据1
ologit   hrdv4   l.vbankcr    l.size      l.lev     l.absnda l.age          i.year   if      bank0==1  ,r   nolog   /数据1
ologit   hrdv5  l.vbankcr    l.size      l.lev     l.absnda l.age           i.year   if      bank0==1  ,r   nolog   /数据1
ologit   hrdc3   l.cbankcr    l.size      l.lev     l.absnda l.age         i.year   if      bank0==1  ,r   nolog   /数据1
ologit   hrdc4  l.cbankcr    l.size      l.lev     l.absnda l.age          i.year    if      bank0==1  ,r   nolog   /数据1
ologit   hrdc5   l.cbankcr    l.size      l.lev     l.absnda l.age           i.year    if      bank0==1  ,r   nolog   /数据1

PSM  
  ologit   hrdv5     l.size      l.lev     l.absnda l.age           i.year   if      bank0==1  ,r    /数据1
  ologit   hrdc5       l.size      l.lev     l.absnda l.age           i.year    if      bank0==1  ,r      /数据1

TABEL 5:
基于PSM匹配后的样本进行分组检验
ttest  ftvbankcr= fcvbankcr  if  thrdv5==T & chrdv5 ==C / 数据2
ttest  ftvshortcr= fcvshortcr  if  thrdv5==T & chrdv5 ==C / 数据2
ttest  ftvlongcr= fcvlongcr  if  thrdv5==T & chrdv5 ==C  / 数据2
ttest  ftcbankcr= fccbankcr  if  thrdc5==T & chrdc5 ==C / 数据3
ttest  ftcshortcr= fccshortcr  if  thrdc5==T & chrdc5 ==C / 数据3
ttest  ftclongcr= fcclongcr  if  thrdc5==T & chrdc5 ==C / 数据3

TABEL 6:
ttest  ftvbankcr= fcvbankcr  if  thrdv5-chrdv5 ==T-C / 数据2
ttest  ftvshortcr= fcvshortcr  if  thrdv5-chrdv5 ==T-C / 数据2
ttest  ftvlongcr= fcvlongcr  if  thrdv5-chrdv5 ==T-C  / 数据2
ttest  ftcbankcr= fccbankcr  if  thrdc5-chrdc5 ==T-C  / 数据3
ttest  ftcshortcr= fccshortcr  if  thrdc5-chrdc5 ==T-C   / 数据3
ttest  ftclongcr= fcclongcr  if  thrdc5-chrdc5 ==T-C   / 数据3

TABEL 7:
xtreg     vbankcr   l.rd  l.lnbrchrd   l.lnbrch  l.opcash   l.ppe        l.size l.lev   l. hightec3    l.absnda    l.roa            i.year    if      bank0==1,r fe /数据1
xtreg   vbankcr         l.rd   l.crrd   l.cr   l.opcash   l.ppe      l.size l.lev   l. hightec3    l.absnda    l.roa  i.year  if bank0==1  , fe r /数据1
xtreg     cbankcr   l.rd  l.lnbrchrd   l.lnbrch  l.opcash   l.ppe        l.size l.lev   l. hightec3    l.absnda    l.roa         i.year    if      bank0==1,r fe /数据1
xtreg   cbankcr         l.rd  l.crrd   l.cr    l.opcash   l.ppe      l.size l.lev   l. hightec3    l.absnda    l.roa   i.year  if bank0==1  , fe r /数据1

TABEL 8:
xtivreg2    vbankcr      l.opcash   l.ppe      l.size l.lev   l. hightec3    l.absnda    l.roa    (l.rd   =  l.dsnum       l.ivrd ) if bank0==1,   fe r   /数据1
xtivreg2   rd        l.size      l.lev     l.absnda l.age      ( l.vbankcr = l.syxy   l.state  l.lnbrch ) if bank0==1,  fe r  /数据1 
xtivreg2    cbankcr      l.opcash   l.ppe      l.size l.lev   l. hightec3    l.absnda    l.roa    (l.rd   =  l.dsnum       l.ivrd ) if bank0==1,   fe r  /数据1
xtivreg2   rd        l.size      l.lev     l.absnda l.age      ( l.cbankcr = l.syxy  l.state  l.lnbrch    ) if bank0==1,  fe r   /数据1
 
prob disrd  drev   share   size       lev       absnda      roa   age i.ccer  if bank0==1  /数据1
 predict gw , xb 
g lambda=normalden(gw)/normal(gw) if disrd==1

TABEL9:
reg   vbankcr      l.rd  l.opcash   l.ppe      l.size l.lev   l. hightec3    l.absnda    l.roa   l.lambda i.year i.ccer if bank0==1,   r   /数据1
reg   vshortcr     l.rd  l.opcash   l.ppe      l.size l.lev   l. hightec3    l.absnda    l.roa    l.lambda  i.year i.ccer if bank0==1,    r   /数据1
reg    vlongcr      l.rd  l.opcash   l.ppe      l.size l.lev   l. hightec3    l.absnda    l.roa   l.lambda  i.year i.ccer if bank0==1,    r  /数据1
reg    cbankcr     l.rd  l.opcash   l.ppe      l.size l.lev   l. hightec3    l.absnda    l.roa    l.lambda  i.year i.ccer if bank0==1,    r  /数据1
reg    cshortcr      l.rd  l.opcash   l.ppe      l.size l.lev   l. hightec3    l.absnda    l.roa   l.lambda  i.year i.ccer if bank0==1,   r  /数据1
reg    clongcr      l.rd  l.opcash   l.ppe      l.size l.lev   l. hightec3    l.absnda    l.roa     l.lambda  i.year i.ccer if bank0==1,    r  /数据1

TABEL 10:
reg     rd      l.vbankcr    l.size      l.lev     l.absnda l.age  l.lambda  i.year i.ccer if bank0==1,    r /数据1
reg     rd      l.vshortcr    l.size      l.lev     l.absnda l.age  l.lambda  i.year i.ccer if bank0==1,    r /数据1
reg     rd      l. vlongcr   l.size      l.lev     l.absnda l.age  l.lambda  i.year i.ccer if bank0==1,  r /数据1   
reg     rd      l.cbankcr    l.size      l.lev     l.absnda l.age  l.lambda  i.year i.ccer if bank0==1,    r /数据1
reg     rd      l. cshortcr     l.size      l.lev     l.absnda l.age l.lambda   i.year i.ccer if bank0==1,    r /数据1
reg     rd      l. clongcr   l.size      l.lev     l.absnda l.age  l.lambda  i.year i.ccer if bank0==1,    r /数据1
   




