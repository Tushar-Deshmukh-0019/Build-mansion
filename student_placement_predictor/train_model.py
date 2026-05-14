import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score, f1_score, precision_score, recall_score,
    roc_auc_score, confusion_matrix, classification_report
)
from imblearn.over_sampling import SMOTE
import joblib as _joblib

# ============================================================
# 1. LOAD & CLEAN
# ============================================================
df = pd.read_csv("collegePlace.csv")
print(f"Raw shape: {df.shape}")
print(f"Columns: {list(df.columns)}")

df.drop_duplicates(inplace=True)
df.dropna(subset=["PlacedOrNot"], inplace=True)
df.ffill(inplace=True)
print(f"After dedup/dropna: {df.shape}")

# ============================================================
# 2. OUTLIER REMOVAL — IQR with 2.5x fence
# ============================================================
for col in ["CGPA", "Internships", "Age"]:
    Q1  = df[col].quantile(0.25)
    Q3  = df[col].quantile(0.75)
    IQR = Q3 - Q1
    lo  = Q1 - 2.5 * IQR
    hi  = Q3 + 2.5 * IQR
    before = len(df)
    df = df[(df[col] >= lo) & (df[col] <= hi)]
    print(f"  Outlier [{col}]: {before} → {len(df)} rows  (fence: {lo:.1f} – {hi:.1f})")

print(f"\nFinal dataset: {df.shape}")
print(f"Class distribution:\n{df['PlacedOrNot'].value_counts()}\n")

# ============================================================
# 3. ENCODE CATEGORICALS
# ============================================================
le_gender = LabelEncoder()
le_stream  = LabelEncoder()

df["Gender"] = le_gender.fit_transform(df["Gender"])
df["Stream"]  = le_stream.fit_transform(df["Stream"])

print(f"Gender classes : {list(le_gender.classes_)}")
print(f"Stream classes : {list(le_stream.classes_)}")

# ============================================================
# 4. SYNTHETIC DATA — fix CGPA-dominance bias
#
#    The raw CSV has CGPA 7+ → 100% placed, which makes the
#    model ignore all other features. We inject realistic
#    counter-examples so the model learns that internships,
#    backlogs, and hostel also matter.
# ============================================================
rng = np.random.default_rng(42)
n_synth = 800  # counter-examples to inject

# Case A: High CGPA + 0 internships → NOT placed (CGPA alone isn't enough)
case_a = pd.DataFrame({
    "Age":               rng.integers(20, 25, n_synth // 4),
    "Gender":            rng.integers(0, 2, n_synth // 4),
    "Stream":            rng.integers(0, len(le_stream.classes_), n_synth // 4),
    "Internships":       np.zeros(n_synth // 4, dtype=int),
    "CGPA":              rng.uniform(7.5, 10.0, n_synth // 4),
    "Hostel":            rng.integers(0, 2, n_synth // 4),
    "HistoryOfBacklogs": rng.integers(0, 2, n_synth // 4),
    "PlacedOrNot":       0,
})

# Case B: High CGPA + backlog + ≤1 internship → NOT placed
case_b = pd.DataFrame({
    "Age":               rng.integers(20, 25, n_synth // 4),
    "Gender":            rng.integers(0, 2, n_synth // 4),
    "Stream":            rng.integers(0, len(le_stream.classes_), n_synth // 4),
    "Internships":       rng.integers(0, 2, n_synth // 4),   # 0 or 1
    "CGPA":              rng.uniform(7.0, 10.0, n_synth // 4),
    "Hostel":            rng.integers(0, 2, n_synth // 4),
    "HistoryOfBacklogs": np.ones(n_synth // 4, dtype=int),   # backlog = 1
    "PlacedOrNot":       0,
})

# Case C: Low CGPA + 2-3 internships + no backlog → placed
case_c = pd.DataFrame({
    "Age":               rng.integers(20, 25, n_synth // 4),
    "Gender":            rng.integers(0, 2, n_synth // 4),
    "Stream":            rng.integers(0, len(le_stream.classes_), n_synth // 4),
    "Internships":       rng.integers(2, 4, n_synth // 4),
    "CGPA":              rng.uniform(5.5, 7.0, n_synth // 4),
    "Hostel":            rng.integers(0, 2, n_synth // 4),
    "HistoryOfBacklogs": np.zeros(n_synth // 4, dtype=int),
    "PlacedOrNot":       1,
})

# Case D: Moderate CGPA + 2+ internships + no backlog → placed
case_d = pd.DataFrame({
    "Age":               rng.integers(20, 25, n_synth // 4),
    "Gender":            rng.integers(0, 2, n_synth // 4),
    "Stream":            rng.integers(0, len(le_stream.classes_), n_synth // 4),
    "Internships":       rng.integers(2, 4, n_synth // 4),
    "CGPA":              rng.uniform(7.0, 9.0, n_synth // 4),
    "Hostel":            rng.integers(0, 2, n_synth // 4),
    "HistoryOfBacklogs": np.zeros(n_synth // 4, dtype=int),
    "PlacedOrNot":       1,
})

df = pd.concat([df, case_a, case_b, case_c, case_d], ignore_index=True)
df = df.sample(frac=1, random_state=42).reset_index(drop=True)
print(f"After synthetic augmentation: {df.shape}")
print(f"Class distribution after augmentation:\n{df['PlacedOrNot'].value_counts()}\n")

# ============================================================
# 5. FEATURE ENGINEERING
# ============================================================
df["academic_score"] = df["CGPA"] * (1 - 0.15 * df["HistoryOfBacklogs"])
df["high_cgpa"]      = (df["CGPA"] >= 8.0).astype(int)
df["at_risk"]        = ((df["HistoryOfBacklogs"] == 1) & (df["CGPA"] < 7.0)).astype(int)

# Interaction: internships × CGPA — rewards well-rounded students
df["intern_cgpa"]    = df["Internships"] * df["CGPA"] / 10.0

FEATURES = [
    "Age", "Gender", "Stream", "Internships", "CGPA",
    "Hostel", "HistoryOfBacklogs",
    "academic_score", "high_cgpa", "at_risk", "intern_cgpa"
]

X = df[FEATURES]
y = df["PlacedOrNot"]

print(f"Features used for ML ({len(FEATURES)}): {FEATURES}")
print(f"X shape: {X.shape}")

# ============================================================
# 6. SCALE
# ============================================================
scaler   = StandardScaler()
X_scaled = scaler.fit_transform(X)

# ============================================================
# 7. STRATIFIED TRAIN / TEST SPLIT
# ============================================================
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y, test_size=0.2, random_state=42, stratify=y
)
print(f"\nTrain: {X_train.shape}  Test: {X_test.shape}")

# ============================================================
# 8. SMOTE — balance classes on training set only
# ============================================================
smote = SMOTE(random_state=42)
X_train_res, y_train_res = smote.fit_resample(X_train, y_train)
print(f"After SMOTE: {X_train_res.shape}")
print(f"Class dist after SMOTE: {pd.Series(y_train_res).value_counts().to_dict()}")

# ============================================================
# 9. MODEL — GradientBoosting
#    Better at learning non-linear feature interactions than RF.
#    Captures "high CGPA but 0 internships → not placed" patterns.
# ============================================================
from sklearn.ensemble import GradientBoostingClassifier

model = GradientBoostingClassifier(
    n_estimators=300,
    learning_rate=0.05,
    max_depth=5,
    min_samples_split=4,
    min_samples_leaf=2,
    subsample=0.8,
    max_features="sqrt",
    random_state=42,
)

# ============================================================
# 10. CROSS-VALIDATION
# ============================================================
print("\n--- 5-Fold Cross-Validation (F1) ---")
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
scores = cross_val_score(model, X_train_res, y_train_res, cv=cv, scoring="f1", n_jobs=-1)
print(f"  GradientBoosting  F1 = {scores.mean():.4f} ± {scores.std():.4f}")

# ============================================================
# 11. TRAIN FINAL MODEL
# ============================================================
print("\nTraining GradientBoosting on full resampled training set...")
model.fit(X_train_res, y_train_res)

# ============================================================
# 12. EVALUATE
# ============================================================
y_pred      = model.predict(X_test)
y_pred_prob = model.predict_proba(X_test)[:, 1]

acc     = accuracy_score(y_test, y_pred)
f1      = f1_score(y_test, y_pred)
prec    = precision_score(y_test, y_pred)
rec     = recall_score(y_test, y_pred)
roc_auc = roc_auc_score(y_test, y_pred_prob)
cm      = confusion_matrix(y_test, y_pred)

print("\n" + "="*55)
print("        FINAL MODEL EVALUATION (Test Set)")
print("="*55)
print(f"  Accuracy  : {acc:.4f}  ({acc*100:.2f}%)")
print(f"  F1 Score  : {f1:.4f}")
print(f"  Precision : {prec:.4f}")
print(f"  Recall    : {rec:.4f}")
print(f"  ROC-AUC   : {roc_auc:.4f}")
print("="*55)

print("\nConfusion Matrix:")
print(f"                 Predicted")
print(f"              Not Placed  Placed")
print(f"Actual Not Placed  {cm[0,0]:4d}    {cm[0,1]:4d}")
print(f"Actual Placed      {cm[1,0]:4d}    {cm[1,1]:4d}")

print("\nClassification Report:")
print(classification_report(y_test, y_pred, target_names=["Not Placed", "Placed"]))

# ============================================================
# 13. FEATURE IMPORTANCE
# ============================================================
importances = pd.Series(model.feature_importances_,
                        index=FEATURES).sort_values(ascending=False)
print("Feature Importances:")
for feat, imp in importances.items():
    bar = "█" * int(imp * 60)
    print(f"  {feat:22s} {imp:.4f}  {bar}")

# ============================================================
# 14. SANITY CHECK — edge cases the model must handle correctly
# ============================================================
print("\n--- Sanity Checks ---")
from sklearn.preprocessing import LabelEncoder as _LE

def _check(label, age, gender_str, stream_str, internships, cgpa, hostel, backlog):
    g = le_gender.transform([gender_str])[0]
    s = le_stream.transform([stream_str])[0]
    academic_score = cgpa * (1 - 0.15 * backlog)
    high_cgpa_f    = 1 if cgpa >= 8.0 else 0
    at_risk_f      = 1 if (backlog == 1 and cgpa < 7.0) else 0
    intern_cgpa_f  = internships * cgpa / 10.0
    x = np.array([[age, g, s, internships, cgpa, hostel, backlog,
                   academic_score, high_cgpa_f, at_risk_f, intern_cgpa_f]])
    x_sc = scaler.transform(x)
    pred = model.predict(x_sc)[0]
    prob = model.predict_proba(x_sc)[0][1]
    result = "Placed" if pred == 1 else "Not Placed"
    print(f"  {label:45s} → {result} ({prob*100:.1f}%)")

_check("CGPA=10, 0 internships, 0 projects, backlog=1", 21, "Male", "Computer Science", 0, 10.0, 0, 1)
_check("CGPA=10, 0 internships, no backlog",             21, "Male", "Computer Science", 0, 10.0, 0, 0)
_check("CGPA=10, 1 internship,  backlog=1",              21, "Male", "Computer Science", 1, 10.0, 0, 1)
_check("CGPA=10, 1 internship,  no backlog",             21, "Male", "Computer Science", 1, 10.0, 0, 0)
_check("CGPA=6,  3 internships, no backlog",             21, "Male", "Computer Science", 3,  6.0, 0, 0)
_check("CGPA=7.5, 1 internship, no backlog",             21, "Male", "Computer Science", 1,  7.5, 0, 0)
_check("CGPA=8,  2 internships, no backlog",             22, "Male", "Computer Science", 2,  8.0, 0, 0)
_check("CGPA=9,  0 internships, backlog=1",              21, "Male", "Computer Science", 0,  9.0, 0, 1)

# ============================================================
# 15. SAVE
# ============================================================
_joblib.dump({
    "model":     model,
    "le_gender": le_gender,
    "le_stream":  le_stream,
    "features":  FEATURES
}, "model.sav", compress=3)

_joblib.dump(scaler, "scaler.sav", compress=3)

print("\n✅ MODEL SAVED — model.sav & scaler.sav")
print(f"   Features ({len(FEATURES)}): {FEATURES}")
