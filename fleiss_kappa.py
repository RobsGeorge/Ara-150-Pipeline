"""
Fleiss' kappa per dialect for the Phonemization human evaluation.

WHAT YOU NEED (the "rough per-annotator numbers" you mentioned):
For each dialect, a table where every row is one evaluated SENTENCE and every
column is one ANNOTATOR, with a binary judgment per cell:
    1 = correct (dialect-authentic & morphologically correct), 0 = incorrect.
Different annotators per dialect is fine; the count of raters PER ITEM must be
constant within a dialect (Fleiss' assumption). If raters-per-item varies, use
the weighted variant noted at the bottom.

If you only have per-annotator TOTALS (e.g., "annotator A: 47/50 correct") you
CANNOT compute kappa — report percentage agreement + number of raters instead.
"""
import numpy as np

def fleiss_kappa(ratings):
    """
    ratings: list of rows; each row = [count_category0, count_category1, ...]
             i.e. how many raters chose each category for that item.
             Row sums must all equal the (constant) number of raters n.
    Returns Fleiss' kappa (float).
    """
    M = np.asarray(ratings, dtype=float)
    N, k = M.shape
    n = M.sum(axis=1)
    assert np.all(n == n[0]), "raters-per-item must be constant; got %s" % set(n.tolist())
    n = n[0]
    p_j = M.sum(axis=0) / (N * n)                       # category marginals
    P_i = (np.sum(M * M, axis=1) - n) / (n * (n - 1))   # per-item agreement
    P_bar = P_i.mean()
    P_e = np.sum(p_j ** 2)
    if np.isclose(P_e, 1.0): return 1.0
    return (P_bar - P_e) / (1 - P_e)

def from_binary_matrix(judgments):
    """
    judgments: items x raters binary array (1 correct / 0 incorrect).
    Converts to the [n_incorrect, n_correct] count form Fleiss needs.
    """
    J = np.asarray(judgments, dtype=int)
    correct = J.sum(axis=1)
    n = J.shape[1]
    return np.stack([n - correct, correct], axis=1)

def interpret(k):
    # Landis & Koch (1977) benchmarks
    bins = [(-1,0.0,"poor"),(0.0,0.20,"slight"),(0.20,0.40,"fair"),
            (0.40,0.60,"moderate"),(0.60,0.80,"substantial"),(0.80,1.01,"almost perfect")]
    for lo,hi,lab in bins:
        if lo < k <= hi: return lab
    return "n/a"

if __name__ == "__main__":
    # ---- DEMO with synthetic data; replace each block with YOUR judgments ----
    rng = np.random.default_rng(0)
    demo = {
        # dialect: items x raters binary matrix (here 50 sentences x 3 raters)
        "Egyptian (EGY)":  (rng.random((50,3)) < 0.98).astype(int),
        "Levantine (LEV)": (rng.random((50,3)) < 0.92).astype(int),
        "Gulf (GLF)":      (rng.random((50,3)) < 0.94).astype(int),
    }
    print(f"{'Dialect':<18}{'Raters':<8}{'% agree':<10}{'Fleiss kappa':<14}{'Interpretation'}")
    for d, J in demo.items():
        counts = from_binary_matrix(J)
        k = fleiss_kappa(counts)
        pct = 100*np.mean(J.mean(axis=1).round()==J.mean(axis=1)) if False else 100*np.mean((J.sum(1)==J.shape[1])|(J.sum(1)==0))
        print(f"{d:<18}{J.shape[1]:<8}{pct:<10.1f}{k:<14.3f}{interpret(k)}")
    print("\nReplace the `demo` matrices with your real items x raters 0/1 judgments.")
    print("Unequal raters-per-item -> use statsmodels: "
          "statsmodels.stats.inter_rater.fleiss_kappa(aggregate_raters(data)[0]).")
