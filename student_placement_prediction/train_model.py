import pandas as pd
import numpy as np
import pickle

from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier

# Load data
df = pd.read_csv("collegePlace.csv")

# ---------------- CLEANING ----------------
df.drop_duplicates(inplace=True)
df.fillna(method="ffill", inplace=True)

# Outlier handling (IQR method)
for col in ['CGPA', 'Internships']:
    Q1 = df[col].quantile(0.25)
    Q3 = df[col].quantile(0.75)
    IQR = Q3 - Q1
    df = df[(df[col] >= Q1 - 1.5*IQR) & (df[col] <= Q3 + 1.5*IQR)]

# ---------------- ENCODING ----------------
le_gender = LabelEncoder()
le_stream = LabelEncoder()

df['Gender'] = le_gender.fit_transform(df['Gender'])
df['Stream'] = le_stream.fit_transform(df['Stream'])

# Backlog already numeric in dataset (0/1)

# ---------------- FEATURES ----------------
X = df[['Age','Gender','Stream','Internships','CGPA','HistoryOfBacklogs']]
y = df['PlacedOrNot']

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# ---------------- MODEL + GRID SEARCH ----------------
model = RandomForestClassifier()

param_grid = {
    'n_estimators': [100, 200],
    'max_depth': [5, 10, None]
}

grid = GridSearchCV(model, param_grid, cv=5, n_jobs=-1)
grid.fit(X_scaled, y)

best_model = grid.best_estimator_

# ---------------- SAVE ----------------
data = {
    "model": best_model,
    "le_gender": le_gender,
    "le_stream": le_stream
}

pickle.dump(data, open("model.sav", "wb"))
pickle.dump(scaler, open("scaler.sav", "wb"))

print("✅ MODEL TRAINED WITH GRIDSEARCH + CLEANING")