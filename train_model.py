import pandas as pd
import pickle
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier

df = pd.read_csv("collegePlace.csv")

df.drop_duplicates(inplace=True)
df.ffill(inplace=True)

for col in ['CGPA', 'Internships']:
    Q1 = df[col].quantile(0.25)
    Q3 = df[col].quantile(0.75)
    IQR = Q3 - Q1
    df = df[(df[col] >= Q1 - 1.5 * IQR) & (df[col] <= Q3 + 1.5 * IQR)]

le_gender = LabelEncoder()
le_stream = LabelEncoder()

df['Gender'] = le_gender.fit_transform(df['Gender'])
df['Stream'] = le_stream.fit_transform(df['Stream'])

X = df[['Age', 'Gender', 'Stream', 'Internships', 'CGPA', 'HistoryOfBacklogs']]
y = df['PlacedOrNot']

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y, test_size=0.2, random_state=42
)

model = RandomForestClassifier(random_state=42)

param_grid = {
    'n_estimators': [100, 200],
    'max_depth': [5, 10, None]
}

grid = GridSearchCV(model, param_grid, cv=5, n_jobs=-1)
grid.fit(X_train, y_train)

best_model = grid.best_estimator_

print("Train Accuracy:", best_model.score(X_train, y_train))
print("Test Accuracy:", best_model.score(X_test, y_test))

pickle.dump({
    "model": best_model,
    "le_gender": le_gender,
    "le_stream": le_stream
}, open("model.sav", "wb"))

pickle.dump(scaler, open("scaler.sav", "wb"))

print("✅ MODEL TRAINED")