import numpy as np
import matplotlib.pyplot as plt
from scipy.linalg import eigh

def simulate_spectral_bias(n_nodes=100, noise_level=0.5):
    print(f"--- Spectral Bias Simulation (Path c) ---")
    print(f"Analyzing Regualrization Bias on Graph Laplacian Eigenbasis (n={n_nodes})")

    # 1. Create a simple 1D lattice (ring graph)
    L = np.zeros((n_nodes, n_nodes))
    for i in range(n_nodes):
        L[i, i] = 2
        L[i, (i+1)%n_nodes] = -1
        L[i, (i-1)%n_nodes] = -1

    # 2. Compute Eigenvalues and Eigenvectors
    evals, evecs = eigh(L)

    # 3. Define a "true" smooth signal (low-frequency) and add white noise
    t = np.linspace(0, 2*np.pi, n_nodes)
    true_signal = np.sin(t)
    noisy_signal = true_signal + noise_level * np.random.randn(n_nodes)

    # 4. Project noisy signal onto the spectral basis
    coeffs = evecs.T @ noisy_signal

    # 5. Reconstruction with varying spectral cutoffs (Regularization)
    # Simulation: spectral bias means we tend to keep only low-frequency modes
    cutoff = n_nodes // 5
    filtered_coeffs = coeffs.copy()
    filtered_coeffs[cutoff:] = 0
    reconstructed_signal = evecs @ filtered_coeffs

    # 6. Metrics
    mse_noisy = np.mean((noisy_signal - true_signal)**2)
    mse_recon = np.mean((reconstructed_signal - true_signal)**2)

    print(f"MSE Noisy: {mse_noisy:.6f}")
    print(f"MSE Reconstructed (top 20% modes): {mse_recon:.6f}")
    
    if mse_recon < mse_noisy:
        print("VERIFICATION: SUCCESS. Spectral projection acts as a natural denoising regularizer.")
    else:
        print("VERIFICATION: FAILED. Regularization bias not observed.")

    # 7. Visualization (Save as artifact)
    plt.figure(figsize=(10, 6))
    plt.plot(true_signal, 'k--', label="True Signal (Low-Freq)")
    plt.plot(noisy_signal, 'r.', alpha=0.3, label="Noisy Signal")
    plt.plot(reconstructed_signal, 'g-', linewidth=2, label=f"Spectral Recon (Cutoff={cutoff})")
    plt.title("Path c: Spectral Regularization Bias (Low-Pass Filter)")
    plt.legend()
    plt.savefig("_docs/resonance/spectral_bias_plot.png")
    print("Plot saved to _docs/resonance/spectral_bias_plot.png")

if __name__ == "__main__":
    simulate_spectral_bias()
