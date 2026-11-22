import os
from datetime import date, timedelta
import pandas as pd
t = date.today()
rows = [("@client_a","Normal","ភ្នំពេញ 2A-1234","862012345678901",5),
        ("@client_a","Normal","2BC-4455(សិទ្ធ)","862012345678911",5),
        ("@client_a","Normal","1AA-0001","862012345678912",5),
        ("@client_b","Normal","ភ្នំពេញ 2B-5678","862012345678902",-3),
        ("@uta_fleet","Company","សៀមរាប 1C-4321","862012345678903",12),
        ("@client_d","Normal","កណ្ដាល 3D-1111","862012345678904",40),
        ("@client_e","Company","ភ្នំពេញ 2E-2222","862012345678905",30)]
df = pd.DataFrame([dict(user=u,type=ty,plate=p,imei=i,expiry_date=(t+timedelta(days=d)).isoformat(),status="",sent_at="")
                   for u,ty,p,i,d in rows])
os.makedirs("data", exist_ok=True)
df.to_excel("data/clients_sample.xlsx", index=False)
