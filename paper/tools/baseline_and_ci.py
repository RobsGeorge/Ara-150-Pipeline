"""Baseline contrast (dialect rule set vs MSA rule set, same engine) and Wilson CIs for Table 5.
Usage: python baseline_and_ci.py <g2p dir> <test_split.csv>"""
import csv, sys, math
sys.path.insert(0, sys.argv[1])
from arabic_g2p_rules import transcribe_protected as T

MSA = "Modern Standard Arabic (MSA)"
N = {"Egyptian": ("EGY", "Egyptian"), "Levantine": ("LEV", "Levantine Arabic"), "Khaliji": ("GLF", "Khaliji Arabic")}
tok, diff, sent, sdiff = {}, {}, {}, {}
for r in csv.DictReader(open(sys.argv[2], encoding="utf-8")):
    if r["Main Dialect"] not in N or not r["Transcript"].strip(): continue
    tag, d = N[r["Main Dialect"]]
    a, b = T(r["Transcript"], d).split(), T(r["Transcript"], MSA).split()
    assert len(a) == len(b)
    k = sum(x != y for x, y in zip(a, b))
    tok[tag] = tok.get(tag, 0) + len(a); diff[tag] = diff.get(tag, 0) + k
    sent[tag] = sent.get(tag, 0) + 1; sdiff[tag] = sdiff.get(tag, 0) + (k > 0)
for t in ("EGY", "LEV", "GLF"):
    print(f"{t}: tokens differing {diff[t]:,}/{tok[t]:,} = {100*diff[t]/tok[t]:.1f}%; sentences differing {sdiff[t]:,}/{sent[t]:,} = {100*sdiff[t]/sent[t]:.1f}%")

def wilson(k, n, z=1.96):
    p = k / n; c = (p + z*z/(2*n)) / (1 + z*z/n); h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / (1 + z*z/n)
    return 100*(c-h), 100*(c+h)
for name, k, n in (("EGY", 49, 50), ("LEV", 46, 50), ("GLF", 47, 50), ("All", 142, 150)):
    lo, hi = wilson(k, n); print(f"{name}: {k}/{n} 95% Wilson CI [{lo:.1f}, {hi:.1f}]")
