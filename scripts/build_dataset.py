"""Build the phase-1 dataset: 37 Iraqi public institutions x ranking indicators.
Values for the original 20 come from the app snapshot (data/raw/compare_snapshot.json);
values for the 17 added institutions and all national scores were collected on 2026-10-02.
"""
import csv, json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
snap = json.loads((ROOT/"data/raw/compare_snapshot.json").read_text(encoding="utf-8"))

EN = {"mosul":"University of Mosul","baghdad":"University of Baghdad","must":"Mustansiriyah University",
"basrah":"University of Basrah","kufa":"University of Kufa","ntu":"Northern Technical University",
"mtu":"Middle Technical University","atu":"Al-Furat Al-Awsat Technical University",
"tech":"University of Technology, Iraq","babylon":"University of Babylon","anbar":"University of Anbar",
"tikrit":"Tikrit University","kirkuk":"University of Kirkuk","diyala":"University of Diyala",
"kerbala":"University of Kerbala","misan":"University of Misan","qadis":"University of Al-Qadisiyah",
"ninevah":"University of Ninevah","hamdaniya":"University of Al-Hamdaniya","telafer":"University of Telafer"}
AR = {u["id"]:u["n"] for u in snap["unis"]}
NEW = {  # id: (english, arabic)
"nahrain":("Al-Nahrain University","جامعة النهرين"),
"muthanna":("Al-Muthanna University","جامعة المثنى"),
"thiqar":("University of Thi-Qar","جامعة ذي قار"),
"wasit":("Wasit University","جامعة واسط"),
"uoitc":("University of Information Technology and Communications","جامعة تكنولوجيا المعلومات والاتصالات"),
"karkh":("Al-Karkh University of Science","جامعة الكرخ للعلوم"),
"iraqia":("Al-Iraqia University","الجامعة العراقية"),
"stu":("Southern Technical University","الجامعة التقنية الجنوبية"),
"qasim":("Al-Qasim Green University","جامعة القاسم الخضراء"),
"fallujah":("University of Fallujah","جامعة الفلوجة"),
"sumer":("University of Sumer","جامعة سومر"),
"jabir":("Jabir ibn Hayyan University for Medical and Pharmaceutical Sciences","جامعة جابر بن حيان الطبية"),
"buog":("Basrah University for Oil and Gas","جامعة البصرة للنفط والغاز"),
"kadhim":("Imam Al-Kadhim University College","كلية الإمام الكاظم (ع)"),
"samarra":("University of Samarra","جامعة سامراء"),
"ibnsina":("Ibn Sina University of Medical and Pharmaceutical Sciences","جامعة ابن سينا للعلوم الطبية والصيدلانية"),
"adham":("Imam Al-Adham University College","كلية الإمام الأعظم الجامعة"),
}
# National ranking (IRU), public institutions: id -> (rank, score). Source: iru.mohesr.gov.iq/result (2025), iru.asse-gate.gov.iq (2024)
IRU25 = {"baghdad":(1,60.079828651604),"tech":(2,53.996857764223),"basrah":(3,52.167136948566),"anbar":(4,52.051528218299),
"mosul":(5,51.313521631231),"diyala":(6,49.628862028003),"babylon":(7,46.878112611093),"nahrain":(8,45.320889204265),
"must":(9,45.09882581132),"mtu":(10,44.402721441538),"ntu":(11,43.135559891759),"kerbala":(12,40.157750012607),
"kufa":(13,39.748265806443),"muthanna":(14,37.702344492909),"qadis":(15,37.245451257016),"atu":(16,35.166810991596),
"tikrit":(17,33.173854209326),"thiqar":(18,30.267447778093),"wasit":(19,28.160598115782),"uoitc":(20,27.988005546765),
"karkh":(21,27.749542559665),"iraqia":(22,27.549829369596),"stu":(23,27.20796750383),"qasim":(24,27.199340919636),
"kirkuk":(25,26.863951167507),"fallujah":(26,25.001705609602),"ninevah":(27,24.017887192713),"sumer":(28,24.000341652138),
"misan":(29,23.596897785069),"jabir":(30,18.555164265371),"buog":(31,18.222577363446),"kadhim":(32,17.563514772445),
"samarra":(33,14.233745942182),"telafer":(34,13.257041718313),"ibnsina":(35,12.093486685836),"adham":(36,11.745694687017),
"hamdaniya":(37,11.053172633965)}
IRU24 = {"tech":(1,61.614443873674),"anbar":(2,54.51862846155),"must":(3,51.039979672175),"baghdad":(4,48.653413332505),
"kufa":(5,47.932523232815),"kerbala":(6,47.787544716453),"babylon":(7,46.230012836738),"muthanna":(8,45.966271692139),
"diyala":(9,44.529722286403),"basrah":(10,44.202278506433),"mosul":(11,43.180143105961),"qadis":(12,43.112240086741),
"nahrain":(13,42.310915208713),"tikrit":(14,41.683846066823),"mtu":(15,39.950906133476),"ntu":(16,39.349110364332),
"atu":(17,38.348779674456),"iraqia":(18,37.087234460913),"thiqar":(19,37.04676925996),"wasit":(20,36.397230648438),
"kirkuk":(21,33.493242721987),"stu":(22,33.488721340217),"uoitc":(23,32.104319957836),"qasim":(24,30.635388786042),
"ninevah":(25,30.293878925386),"misan":(26,29.366107015465),"karkh":(27,28.629475962945),"jabir":(28,28.463874372445),
"fallujah":(29,28.402848930234),"sumer":(30,27.844922147134),"samarra":(31,26.907530556076),"buog":(32,24.760721948935),
"kadhim":(33,23.517433427711),"adham":(34,20.950752289087),"ibnsina":(35,20.865812972121),"telafer":(36,19.066160590455),
"hamdaniya":(37,19.004514882603)}
NR = "NR"          # not ranked / not listed
REP = "Reporter"   # THE: submitted data but did not meet ranking criteria
NEWV = {  # values for the 17 added institutions
"the":{"qasim":"1601–1800","muthanna":"1801–2000","nahrain":"1801–2000","stu":"1801–2000","wasit":"1801–2000","thiqar":"2001+",
       "iraqia":REP,"karkh":REP,"kadhim":REP,"jabir":REP,"fallujah":REP,"uoitc":REP},
"qs":{"nahrain":"1001–1200"},
"sir":{"uoitc":6795,"nahrain":8189,"wasit":9276,"muthanna":9295,"qasim":9328,"stu":9486,"thiqar":9841,"iraqia":9899,"karkh":10157,"fallujah":10475,"samarra":10612},
"sirr":{"nahrain":5761,"wasit":6479,"muthanna":8192,"qasim":4919,"stu":6114,"thiqar":7758,"iraqia":8497,"karkh":6497,"fallujah":8940,"samarra":9364,"uoitc":2788},
"siri":{"nahrain":7197,"wasit":8666,"muthanna":7418,"qasim":9291,"stu":8416,"thiqar":8827,"iraqia":7900,"karkh":10505,"fallujah":9032,"samarra":10136,"uoitc":7688},
"sirs":{"nahrain":8607,"wasit":8815,"muthanna":8391,"qasim":9482,"stu":9395,"thiqar":8957,"iraqia":9033,"karkh":9300,"fallujah":9720,"samarra":9637,"uoitc":8922},
"impact":{"iraqia":"1001–1500","kadhim":"1001–1500","stu":"1001–1500","fallujah":"1001–1500"},
"stud":{"qasim":3761,"nahrain":8018,"stu":16157,"wasit":20558,"thiqar":20043,"muthanna":11412},
"sps":{"qasim":6.1,"nahrain":5.1,"stu":20.6,"wasit":10.3,"thiqar":12.3,"muthanna":10.4},
}
old = snap["ind"]
def oldval(ind, u):
    v = old[ind].get(u)
    if v is None: return None
    return NR if v == "غير مدرجة" else v
def get(ind, u):
    if u in EN:
        v = oldval(ind, u)
        if ind == "the" and u == "telafer": return REP   # finer status found in THE 2027 table
        return v if v is not None else (NR if ind in ("the","qs","sir","sirr","siri","sirs","impact") else "")
    v = NEWV[ind].get(u)
    if v is not None: return v
    return NR if ind in ("the","qs","sir","sirr","siri","sirs","impact") else ""

ids = sorted(IRU25, key=lambda k: IRU25[k][0])
cols = ["id","name_en","name_ar","type","in_app_v1","iru2025_rank","iru2025_score","iru2024_rank","iru2024_score",
        "the_wur_2027","qs_wur_2027","sir2026_overall","sir2026_research","sir2026_innovation","sir2026_societal",
        "the_impact_2026","students_the2027","students_per_staff_the2027"]
rows = []
for u in ids:
    s24 = IRU24[u][1]
    if s24 is None: s24 = float(old["iru24"][u])     # 2-decimal value from the app snapshot
    rows.append({"id":u,"name_en":EN.get(u) or NEW[u][0],"name_ar":AR.get(u) or NEW[u][1],
      "type":"university college" if u in ("kadhim","adham") else "university","in_app_v1":int(u in EN),
      "iru2025_rank":IRU25[u][0],"iru2025_score":round(IRU25[u][1],4),"iru2024_rank":IRU24[u][0],"iru2024_score":round(s24,4),
      "the_wur_2027":get("the",u),"qs_wur_2027":get("qs",u),"sir2026_overall":get("sir",u),"sir2026_research":get("sirr",u),
      "sir2026_innovation":get("siri",u),"sir2026_societal":get("sirs",u),"the_impact_2026":get("impact",u),
      "students_the2027":get("stud",u),"students_per_staff_the2027":get("sps",u)})
with open(ROOT/"data/universities.csv","w",newline="",encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)

# consistency checks against the app snapshot
bad = []
for u in EN:
    if abs(float(old["iru25"][u]) - IRU25[u][1]) > 0.006: bad.append(("iru25",u))
    if int(old["iru25r"][u]) != IRU25[u][0]: bad.append(("iru25r",u))
    if IRU24[u][1] is not None and abs(float(old["iru24"][u]) - IRU24[u][1]) > 0.006: bad.append(("iru24",u))
print("rows:",len(rows),"| mismatches vs app:",bad or "none")
for c in cols[9:]:
    vals=[r[c] for r in rows]
    print(f"{c:28s} ranked/has value: {sum(v not in (NR,REP,'') for v in vals):2d}  Reporter: {vals.count(REP)}  NR: {vals.count(NR)}  blank: {vals.count('')}")
