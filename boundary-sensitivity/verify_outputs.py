import csv,json,math,statistics,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def betacf(a,b,x):
 qab=a+b;qap=a+1;qam=a-1;c=1.;d=1-qab*x/qap
 if abs(d)<1e-300:d=1e-300
 d=1/d;h=d
 for m in range(1,501):
  m2=2*m;aa=m*(b-m)*x/((qam+m2)*(a+m2));d=1+aa*d
  if abs(d)<1e-300:d=1e-300
  c=1+aa/c
  if abs(c)<1e-300:c=1e-300
  d=1/d;h*=d*c
  aa=-(a+m)*(qab+m)*x/((a+m2)*(qap+m2));d=1+aa*d
  if abs(d)<1e-300:d=1e-300
  c=1+aa/c
  if abs(c)<1e-300:c=1e-300
  d=1/d;factor=d*c;h*=factor
  if abs(factor-1)<3e-14:return h
 raise AssertionError('beta convergence')
def ibeta(a,b,x):
 if x<=0:return 0.
 if x>=1:return 1.
 bt=math.exp(math.lgamma(a+b)-math.lgamma(a)-math.lgamma(b)+a*math.log(x)+b*math.log1p(-x))
 if x<(a+1)/(a+b+2):return bt*betacf(a,b,x)/a
 return 1-bt*betacf(b,a,1-x)/b
def tcrit(df):
 lo=0.;hi=5.
 for _ in range(100):
  mid=(lo+hi)/2
  cdf=1-.5*ibeta(df/2,.5,df/(df+mid*mid))
  if cdf<.975:lo=mid
  else:hi=mid
 return (lo+hi)/2
CRIT=tcrit(199)
def intervals(xs):
 avg=statistics.mean(xs);se=statistics.stdev(xs)/math.sqrt(len(xs))
 return avg,avg-CRIT*se,avg+CRIT*se,se
errors=[];maxerr={}
def same(actual,expected,label,tol=1e-7):
 a=float(actual);d=abs(a-expected);maxerr[label]=max(maxerr.get(label,0),d)
 if d>tol:errors.append([label,a,expected,d])
def rows(folder,f):
 with (ROOT/folder/f).open(newline='',encoding='utf8') as h:return list(csv.DictReader(h))
summaries={}
for folder,nscenarios in [('boundary-sensitivity',11)]:
 sc=rows(folder,'scenario_results.csv');pa=rows(folder,'paired_comparisons.csv');raw=rows(folder,'replication_results.csv');cal=rows(folder,'calibration.csv')
 assert len(sc)==nscenarios*2
 assert len(pa)==nscenarios
 assert len(raw)==nscenarios*2*200
 groups={}
 for row in raw:
  key=(row['scenario'],row['policy']);r=int(row['replication'])
  group=groups.setdefault(key,{})
  assert r not in group
  group[r]={k:float(v) for k,v in row.items() if k not in ('scenario','policy','replication')}
 assert len(groups)==nscenarios*2
 for key,g in groups.items():
  assert set(g)==set(range(200))
  penalty=float(key[0].split('_P')[-1])
  for d in g.values():
   same(d['cost_per_day'],d['purchased_per_day']*100+d['unmet_per_day']*100*penalty+d['inventory_per_day']*.25,'rawcost')
   same(d['demand_per_day'],d['served_per_day']+d['unmet_per_day'],'rawserved+unmet',1e-10)
   same(d['fill_rate'],d['served_per_day']/d['demand_per_day'],'rawfill',1e-12)
 for r in sc:
  g=groups[(r['scenario'],r['policy'])];vec=lambda metric:[g[i][metric] for i in range(200)]
  a,l,h,se=intervals(vec('cost_per_day'))
  for field,x in [('daily_cost_krw',a),('cost_ci_low',l),('cost_ci_high',h),('cost_mc_se',se)]:same(r[field],x,'scenario_'+field)
  for field,rawfield,mult in [('fill_rate','fill_rate',1),('orders_per_day','orders_per_day',1),('purchased_liters_per_day','purchased_per_day',.05),('expired_liters_per_day','expired_per_day',.05),('unmet_liters_per_day','unmet_per_day',.05),('inventory_liters_per_day','inventory_per_day',.05)]:
   same(r[field],statistics.mean(vec(rawfield))*mult,'scenario_'+field,1e-9)
  if r['policy']=='mean_base_stock':
   assert float(r['selected_z'])==0.
  else:
   rc=[x for x in cal if x['scenario']==r['scenario'] and x['policy']==r['policy']]
   assert len(rc)==13
   selected=[x for x in rc if x['selected']=='True'];assert len(selected)==1
   best=min(rc,key=lambda q:(float(q['validation_daily_cost_krw']),float(q['z'])))
   assert selected[0]==best
   assert float(r['selected_z'])==float(best['z'])
 for r in pa:
  b=groups[(r['scenario'],'calibrated_base_stock')];a=groups[(r['scenario'],'expiry_adjusted_base_stock')]
  for i in range(200):
   for policy in ['expiry_adjusted_base_stock']:
    same(groups[(r['scenario'],policy)][i]['demand_per_day'],b[i]['demand_per_day'],'paired_demand',1e-12)
  delta=lambda k:[a[i][k]-b[i][k] for i in range(200)]
  mean,lo,hi,se=intervals(delta('cost_per_day'))
  for f,x in [('cost_difference_krw',mean),('ci_low',lo),('ci_high',hi),('mc_se',se)]:same(r[f],x,'paired_'+f)
  same(r['percent_difference'],100*mean/statistics.mean([b[i]['cost_per_day'] for i in range(200)]),'paired_percent',1e-9)
  mean,lo,hi,se=intervals(delta('fill_rate'))
  for f,x in [('fill_rate_difference',mean),('fill_ci_low',lo),('fill_ci_high',hi)]:same(r[f],x,'paired_'+f,1e-12)
  mean,lo,hi,se=intervals([v*.05 for v in delta('expired_per_day')])
  for f,x in [('expired_liters_difference',mean),('expired_ci_low',lo),('expired_ci_high',hi)]:same(r[f],x,'paired_'+f,1e-10)
 meta=json.loads((ROOT/folder/'run_metadata.json').read_text())
 neg=sum(float(r['cost_difference_krw'])<0 for r in pa);pos=sum(float(r['cost_difference_krw'])>0 for r in pa)
 assert neg==meta['negative_point_estimates']
 assert sum(float(r['ci_high'])<0 for r in pa)==meta['lower_pointwise_ci']
 assert sum(float(r['ci_low'])>0 for r in pa)==meta['higher_pointwise_ci']
 boundary=[r for r in sc if r['policy']!='mean_base_stock' and float(r['selected_z']) in (-1.,5.)]
 summaries[folder]={'scenario_rows':len(sc),'replicate_rows':len(raw),'pair_rows':len(pa),'calibration_rows':len(cal),'negative':neg,'positive':pos,'zero':nscenarios-neg-pos,'ci_below_zero':meta['lower_pointwise_ci'],'ci_above_zero':meta['higher_pointwise_ci'],'selected_grid_boundary':len(boundary),'boundary_cells':[r['scenario']+' '+r['policy']+' z='+r['selected_z'] for r in boundary]}

out={'status':'passed' if not errors else 'failed','t_critical_199':CRIT,'summaries':summaries,'maximum_absolute_differences':maxerr,'errors':errors}
(ROOT/'boundary-sensitivity'/'verification.json').write_text(json.dumps(out,indent=2),encoding='utf8')
print(json.dumps(out,indent=2))
sys.exit(bool(errors))
