import faiss
import numpy as np


class FaissKNN:
    def __init__(self, k=5, nlist=50, nprobe=5):
        """
        k = מספר שכנים
        nlist = מספר clusters (חלוקה של הדאטה)
        nprobe = כמה clusters לבדוק בזמן חיפוש
        """
        self.k = k
        self.nlist = nlist
        self.nprobe = nprobe

    # -------------------------
    # normalize (cosine similarity)
    # -------------------------
    def _normalize(self, X):
        norms = np.linalg.norm(X, axis=1, keepdims=True) + 1e-8
        return X / norms

    # -------------------------
    # fit
    # -------------------------
    def fit(self, X, y):
        X = X.astype("float32")
        X = self._normalize(X)

        self.y = np.array(y)

        dim = X.shape[1]

        # 🔥 יצירת אינדקס מהיר (ANN)
        quantizer = faiss.IndexFlatIP(dim)
        self.index = faiss.IndexIVFFlat(
            quantizer,
            dim,
            self.nlist,
            faiss.METRIC_INNER_PRODUCT
        )

        # train (חובה לפני add)
        self.index.train(X)

        # הכנסת הדאטה
        self.index.add(X)

        # כמה clusters לבדוק בזמן חיפוש
        self.index.nprobe = self.nprobe

        return self

    # -------------------------
    # predict (BATCH SEARCH!)
    # -------------------------
    def predict(self, X):
        X = X.astype("float32")
        X = self._normalize(X)

        # 🔥 חיפוש על כל הדאטה בבת אחת
        D, I = self.index.search(X, self.k)

        preds = []

        for i in range(len(X)):
            labels = self.y[I[i]]
            weights = D[i]

            # weighted voting
            score = {}
            for label, w in zip(labels, weights):
                score[label] = score.get(label, 0) + w

            pred = max(score, key=score.get)
            preds.append(pred)

        return np.array(preds)