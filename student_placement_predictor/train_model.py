import pandas as pd
import numpy as np
import pickle
import warnings
warnings.filterwarnings("ignore")

from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, f1_score, precision_score, recall_score,
    roc_auc_score, confusion_matrix, classification_report
)
from imblearn.over_sampling import SMOTE

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
#    Wider fence so real edge-case students are NOT removed.
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
# 4. FEATURE ENGINEERING
#    Only from columns that exist in the CSV.
# ============================================================
# Academic strength: CGPA penalised by backlog history
df["academic_score"] = df["CGPA"] * (1 - 0.15 * df["HistoryOfBacklogs"])

# High performer flag
df["high_cgpa"] = (df["CGPA"] >= 8.0).astype(int)

# At-risk flag: backlog AND low CGPA
df["at_risk"] = ((df["HistoryOfBacklogs"] == 1) & (df["CGPA"] < 7.0)).astype(int)

# NOTE: Projects and Hackathons are NOT in the CSV.
# They are collected from the user at prediction time and used
# only for the profile score and skill suggestions — NOT for ML.

FEATURES = [
    "Age", "Gender", "Stream", "Internships", "CGPA",
    "Hostel", "HistoryOfBacklogs",
    "academic_score", "high_cgpa", "at_risk"
]

X = df[FEATURES]
y = df["PlacedOrNot"]

print(f"\nFeatures used for ML ({len(FEATURES)}): {FEATURES}")
print(f"X shape: {X.shape}")

# ============================================================
# 5. SCALE
# ============================================================
scaler   = StandardScaler()
X_scaled = scaler.fit_transform(X)

# ============================================================
# 6. STRATIFIED TRAIN / TEST SPLIT
# ============================================================
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y, test_size=0.2, random_state=42, stratify=y
)
print(f"\nTrain: {X_train.shape}  Test: {X_test.shape}")

# ============================================================
# 7. SMOTE — balance classes on training set only
# ============================================================
smote = SMOTE(random_state=42)
X_train_res, y_train_res = smote.fit_resample(X_train, y_train)
print(f"After SMOTE: {X_train_res.shape}")
print(f"Class dist after SMOTE: {pd.Series(y_train_res).value_counts().to_dict()}")

# ============================================================
# 8. MODEL — RandomForest only (no VotingClassifier)
#    Avoids numpy random state serialisation issues across versions.
# ============================================================
from sklearn.ensemble import RandomForestClassifier

rf = RandomForestClassifier(
    n_estimators=300,
    max_depth=12,
    min_samples_split=4,
    min_samples_leaf=2,
    max_features="sqrt",
    class_weight="balanced",
    random_state=42,
    n_jobs=-1
)

# ============================================================
# 9. CROSS-VALIDATION
# ============================================================
print("\n--- 5-Fold Cross-Validation (F1) ---")
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
scores = cross_val_score(rf, X_train_res, y_train_res, cv=cv, scoring="f1", n_jobs=-1)
print(f"  RandomForest  F1 = {scores.mean():.4f} ± {scores.std():.4f}")

# ============================================================
# 10. TRAIN FINAL MODEL
# ============================================================
print("\nTraining RandomForest on full resampled training set...")
rf.fit(X_train_res, y_train_res)

# ============================================================
# 11. EVALUATE
# ============================================================
y_pred      = rf.predict(X_test)
y_pred_prob = rf.predict_proba(X_test)[:, 1]

acc       = accuracy_score(y_test, y_pred)
f1        = f1_score(y_test, y_pred)
prec      = precision_score(y_test, y_pred)
rec       = recall_score(y_test, y_pred)
roc_auc   = roc_auc_score(y_test, y_pred_prob)
cm        = confusion_matrix(y_test, y_pred)

print("\n" + "="*55)
print("        FINAL MODEL EVALUATION (Test Set)")
print("="*55)
print(f"  Accuracy  : {acc:.4f}  ({acc*100:.2f}%)")
print(f"  F1 Score  : {f1:.4f}")
print(f"  Precision : {prec:.4f}  (when model says Placed, {prec*100:.1f}% correct)")
print(f"  Recall    : {rec:.4f}")
print(f"  ROC-AUC   : {roc_auc:.4f}")
print("="*55)

print("\nConfusion Matrix:")
print(f"                 Predicted")
print(f"              Not Placed  Placed")
print(f"Actual Not Placed  {cm[0,0]:4d}    {cm[0,1]:4d}   (FP = wrong 'Placed' predictions)")
print(f"Actual Placed      {cm[1,0]:4d}    {cm[1,1]:4d}   (FN = missed placements)")
fpr = cm[0,1] / (cm[0,0] + cm[0,1]) * 100
fnr = cm[1,0] / (cm[1,0] + cm[1,1]) * 100
print(f"\n  False Positive Rate: {fpr:.1f}%  (students told 'Placed' but aren't)")
print(f"  False Negative Rate: {fnr:.1f}%  (placed students missed)")

print("\nClassification Report:")
print(classification_report(y_test, y_pred, target_names=["Not Placed", "Placed"]))

# ============================================================
# 12. FEATURE IMPORTANCE
# ============================================================
rf_fitted = rf
importances = pd.Series(rf_fitted.feature_importances_,
                        index=FEATURES).sort_values(ascending=False)
print("Feature Importances (from Random Forest component):")
for feat, imp in importances.items():
    bar = "█" * int(imp * 60)
    print(f"  {feat:22s} {imp:.4f}  {bar}")

# ============================================================
# 13. SAVE  — strip numpy random state before saving so the
#             model loads on any numpy version (1.x or 2.x)
# ============================================================
import joblib as _joblib

_joblib.dump({
    "model":     rf,
    "le_gender": le_gender,
    "le_stream":  le_stream,
    "features":  FEATURES
}, "model.sav", compress=3)

_joblib.dump(scaler, "scaler.sav", compress=3)

print("\n✅ MODEL SAVED — model.sav & scaler.sav")
print(f"   Model input features ({len(FEATURES)}): {FEATURES}")
print("   Projects & Hackathons → profile score & suggestions only (not ML input)")
