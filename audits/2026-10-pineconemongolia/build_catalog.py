import csv, json, statistics as st, sys
src = sys.argv[1]  # dir with info.json + sheets/metrics.csv
rows = [  # id, views, format, ai_gen_pct (est. share of runtime AI could generate), ai_scenes
 ("DddNgjrDfHv",3144,"Podcast clip",0,"captions, reframe"),
 ("Ddah1P4DJWN",3958,"Podcast clip",0,"captions, reframe"),
 ("DdYiEQok8oS",7606,"Presenter / program promo",30,"listicle type cards, Morphosis end card"),
 ("DdYeKGyCcjY",10000,"Podcast clip",0,"captions, reframe"),
 ("DdWISo9lfw7",12800,"Podcast clip",0,"captions, reframe"),
 ("DdV-aBJAkvY",3221,"Presenter / program promo",35,"REC viewfinder overlay, coding b-roll"),
 ("DdTTKPxHP_q",155000,"Cinematic brand film",65,"Sisyphus painting, rock-head people, data globe, Earth"),
 ("DdQA52OiqGh",6215,"Podcast clip",0,"captions, reframe"),
 ("DdNwtIoiPzN",4137,"Podcast clip",0,"captions, reframe"),
 ("DdLL9dqDUT9",4922,"Podcast clip",0,"captions, reframe"),
 ("DdJdvJoBe7P",85300,"Creator collab",5,"list title cards"),
 ("DdIvbNqjtfz",26400,"Podcast clip",0,"captions, YouTube end card"),
 ("DdIipF8yn6i",149000,"Creator collab",0,"logo sting"),
 ("DdIeokvDfsB",11100,"Cinematic brand film",55,"Earth sunrise, constellation, server room"),
 ("DdGbVDQDQHP",13400,"Podcast clip",0,"captions, reframe"),
 ("DdCpl1jTswR",6331,"Presenter / program promo",15,"screen-record zooms, photo collage"),
 ("DdBrhUlyQkQ",30400,"Creator collab",10,"app-demo insert"),
 ("Dc--se1sS7e",36500,"Creator collab",15,"archive-photo overlay, kinetic text, profile mockup"),
 ("Dc3WEeziWJ5",126000,"Event / partnership film",5,"co-brand lockup, film-frame look"),
 ("Dcz20KEJwRL",7511,"Creator collab",30,"GAP-year poster, logo-on-hook, PiP inserts"),
 ("Dczx6zpCG5F",16900,"Creator collab",5,"handle sticker"),
 ("DciHlCSmyY4",9686,"Event / partnership film",5,"logo animation, split-screen"),
 ("Dcgf9h7DeU9",15800,"Motion / CGI teaser",90,"3D esports operators, CHAMPIONSHIP title, guest card"),
 ("DcdeGEAii9l",13200,"Cinematic brand film",40,"N/10K counter, Earth outro"),
 ("DcS54TXCJsv",11800,"Event / partnership film",5,"question title chips"),
 ("DcLvDl1zBgu",9113,"Event / partnership film",0,"-"),
 ("Db5IVR2k8xI",9045,"Motion / CGI teaser",100,"3D kinetic '26', typewriter, starfield"),
 ("DbvQMInxjkJ",9496,"Creator collab",10,"sticker gifs, post mockups"),
 ("Dbut2BXBeIb",10900,"Creator collab",0,"-"),
 ("DbswhuzuC0T",62000,"Creator collab",0,"-"),
 ("DbsnFNOhmSx",18400,"Presenter / program promo",35,"UI mockups, aurora CTA card, coding b-roll"),
 ("DbqFv2Fzd1L",31100,"Podcast clip",0,"captions, title bar"),
]
met = {r["id"]: r for r in csv.DictReader(open(f"{src}/sheets/metrics.csv"))}
out = []
for i, v, fmt, ai, sc in rows:
    j = json.load(open(f"{src}/reels/{i}.info.json"))
    m = met[i]
    out.append(dict(id=i, date=j["upload_date"], views=v, likes=j.get("like_count") or 0,
        comments=j.get("comment_count") or 0, duration_s=float(m["duration_s"]),
        cuts_per_min=float(m["cuts_per_min"]), format=fmt, ai_gen_pct=ai, ai_scenes=sc,
        url=f"https://www.instagram.com/reel/{i}/"))
with open("catalog.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
V = [r["views"] for r in out]
print("reels", len(out), "total views", sum(V), "median", st.median(V), "mean", round(st.mean(V)))
print("dates", min(r["date"] for r in out), max(r["date"] for r in out))
print("median dur", st.median(r["duration_s"] for r in out), "median cpm", st.median(r["cuts_per_min"] for r in out))
print("likes total", sum(r["likes"] for r in out))
fmts = {}
for r in out: fmts.setdefault(r["format"], []).append(r)
print("\nformat|n|share|views|view_share|median|max|like_rate|med_dur|med_cpm|ai_gen_wavg")
for k, rs in sorted(fmts.items(), key=lambda x: -sum(r["views"] for r in x[1])):
    vs = [r["views"] for r in rs]
    lr = sum(r["likes"] for r in rs) / sum(vs) * 100
    ai = sum(r["ai_gen_pct"] * r["duration_s"] for r in rs) / sum(r["duration_s"] for r in rs)
    print(f'{k}|{len(rs)}|{len(rs)/len(out)*100:.0f}%|{sum(vs)}|{sum(vs)/sum(V)*100:.0f}%|{st.median(vs):.0f}|{max(vs)}|{lr:.2f}%|{st.median(r["duration_s"] for r in rs):.0f}|{st.median(r["cuts_per_min"] for r in rs):.1f}|{ai:.0f}%')
tot_ai = sum(r["ai_gen_pct"] * r["duration_s"] for r in out) / sum(r["duration_s"] for r in out)
print("\nruntime-weighted AI-generatable share:", round(tot_ai), "%; total runtime min", round(sum(r['duration_s'] for r in out)/60,1))
print("reels with >=30% AI-generatable:", sum(1 for r in out if r["ai_gen_pct"] >= 30))
print("top5:", [(r['id'], r['views'], r['format']) for r in sorted(out, key=lambda r: -r['views'])[:5]])
print("bottom5:", [(r['id'], r['views'], r['format']) for r in sorted(out, key=lambda r: r['views'])[:5]])
