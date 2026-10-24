"""Horse v3: smooth landmark warp (3-D thin-plate spline, kernel U(r) = r) from the modelling frame of the generator
to Rob's HX rig frame (HORSE_SKELETON_SPEC.md v1.2).  Pure numpy; used by horse_v3_config (inverse-warped sockets)
and horse_v3.py (final vertex positions)."""
import numpy as np

class TPS:
    def __init__(self, src, dst, reg=1e-6):
        src = np.asarray(src, float); dst = np.asarray(dst, float)
        n = len(src)
        K = np.linalg.norm(src[:, None] - src[None], axis=2) + reg * np.eye(n)
        P = np.concatenate([np.ones((n, 1)), src], 1)
        A = np.zeros((n + 4, n + 4)); A[:n, :n] = K; A[:n, n:] = P; A[n:, :n] = P.T
        b = np.zeros((n + 4, 3)); b[:n] = dst
        self.coef = np.linalg.solve(A, b)
        self.src = src

    def __call__(self, X):
        X = np.atleast_2d(np.asarray(X, float))
        out = np.empty_like(X)
        for i in range(0, len(X), 20000):
            x = X[i:i + 20000]
            K = np.linalg.norm(x[:, None] - self.src[None], axis=2)
            out[i:i + 20000] = K @ self.coef[:len(self.src)] + self.coef[len(self.src)] + x @ self.coef[len(self.src) + 1:]
        return out

    def inverse(self, Y, iters=60):
        Y = np.atleast_2d(np.asarray(Y, float))
        X = Y.copy()
        for _ in range(iters):
            X = X + 0.8 * (Y - self(X))
        return X
