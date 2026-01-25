from scipy.stats import nbinom

def test_prob():
    mu = 6.053786
    line = 6.5
    k_under = 6 # floor(6.5) or ceil(6.5)-1 -> 6
    
    alphas = [0.001, 0.0502, 0.0808, 0.1992, 0.30, 0.50]
    labels = ["Poisson", "Starter", "Short", "Volatile", "Bumped", "Huge"]
    
    print(f"🔎 MICRO-TEST: Under {line} (K<={k_under}) | Mu={mu:.4f}")
    print("-" * 50)
    print(f"{'Regime':<10} | {'Alpha':<8} | {'Prob(Under)':<12} | {'Diff vs 0.5997'}")
    
    for label, alpha in zip(labels, alphas):
        n = 1.0 / alpha
        p = n / (n + mu)
        prob = nbinom.cdf(k_under, n, p)
        diff = prob - 0.599674
        print(f"{label:<10} | {alpha:<8.4f} | {prob:<12.6f} | {diff:+.6f}")

if __name__ == "__main__":
    test_prob()
