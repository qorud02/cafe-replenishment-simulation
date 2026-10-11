import sys,math,json,itertools
from pathlib import Path
import numpy as np
D=Path(__file__).resolve().parent
sys.path.insert(0,str(D))
import study
P=study.P
def reference(path,pack,life,cv,penalty,z,adjusted,burn):
 s=[0.0]*life;pipe=0.0
 sums=dict.fromkeys(['purchased','served','unmet','expired','inventory','orders','demand'],0.)
 def mv(t):
  w=P['weekday_multipliers'][t%7];m=180*w
  return m,876*w+cv*cv*m*m
 def use(arr,req):
  rem=float(req)
  for a in range(len(arr)):
   take=min(arr[a],rem);arr[a]-=take;rem-=take
  return req-rem
 for t,req in enumerate(path):
  s[-1]+=pipe;before=sum(s)
  m0,v0=mv(t);m1,v1=mv(t+1)
  target=max(0,m0+m1+z*math.sqrt(v0+v1));correction=0.
  if adjusted:
   temp=list(s)
   for f in (m0,m1):
    use(temp,f);correction+=temp.pop(0);temp.append(0.)
  order=pack*math.ceil(max(0,target-before+correction)/pack)
  served=use(s,float(req));waste=s.pop(0);s.append(0.);closing=sum(s)
  assert abs(before-served-waste-closing)<1e-9
  pipe=order
  if t>=burn:
   for k,v in dict(purchased=order,served=served,unmet=req-served,expired=waste,inventory=closing,orders=float(order>0),demand=req).items():sums[k]+=v
 n=len(path)-burn
 ret={k+'_per_day':v/n for k,v in sums.items()}
 ret.update(cost_per_day=(sums['purchased']*100+sums['unmet']*100*penalty+sums['inventory']*.25)/n,fill_rate=sums['served']/sums['demand'] if sums['demand'] else 1.,final_inventory=sum(s),final_pipeline=pipe)
 return ret
paths=np.random.default_rng(812481).integers(0,601,size=(3,17))
configs=trajectories=metrics=0;maxdiff=0.
for life,pack,cv,penalty,adjusted in itertools.product([1,2,3,5],[1,20,60,120],[0,.35,.7],[3,10],[False,True]):
 zs=[-.5,0,1,2.5]
 o=study.simulate(paths,pack=pack,life=life,cv=cv,penalty_ratio=penalty,z_values=zs,expiry_adjusted=adjusted,burn_in=3)
 configs+=1
 for i,p in enumerate(paths):
  for j,z in enumerate(zs):
   trajectories+=1;r=reference(p,pack,life,cv,penalty,z,adjusted,3)
   for k,v in r.items():
    diff=abs(o[k][i,j]-v);maxdiff=max(maxdiff,diff);metrics+=1
    assert diff<1e-8,(configs,i,j,k,o[k][i,j],v)
o=study.simulate(np.zeros((1,3),int),pack=20,life=2,cv=0,penalty_ratio=3,z_values=[0],burn_in=0)
assert o['purchased_per_day'][0,0]*3==360
assert o['expired_per_day'][0,0]*3==320
assert o['final_inventory'][0,0]==20
assert o['final_pipeline'][0,0]==20
assert abs(o['cost_per_day'][0,0]-(36000+85)/3)<1e-8
moments=[]
for cv in [0,.35,.7]:
 mu=np.array([18,12,8.]);v=mu+cv*cv*mu*mu
 c=cv*cv*np.outer(mu,mu)/np.sqrt(np.outer(v,v))
 moments.append({'cv':cv,'aggregate_mean':180,'aggregate_sd':math.sqrt(876+cv*cv*180**2),'first_two_menu_correlation':float(c[0,1])})
print(json.dumps({'status':'passed','configs':configs,'trajectories':trajectories,'metric_comparisons':metrics,'max_absolute_difference':maxdiff,'hand_fixture':{k:v.tolist() for k,v in o.items()},'demand_moments_at_weekday_multiplier_one':moments},indent=2))
