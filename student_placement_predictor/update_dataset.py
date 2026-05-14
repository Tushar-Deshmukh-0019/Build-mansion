"""
Update dataset to include:
1. Number of backlogs (0, 1, 2, 3) instead of binary
2. Project domains
"""

import pandas as pd
import numpy as np

# Load dataset
df = pd.read_csv('collegePlace.csv')

print("Original dataset shape:", df.shape)
print("Original columns:", df.columns.tolist())

# 1. Convert HistoryOfBacklogs from binary to number (0-3)
# Current: 0 = no backlogs, 1 = has backlogs
# New: 0, 1, 2, or 3 backlogs

np.random.seed(42)

# For students with backlogs (1), distribute them across 1, 2, or 3 backlogs
# Weighted: 60% have 1 backlog, 30% have 2, 10% have 3
backlog_distribution = np.random.choice([1, 2, 3], 
                                        size=df[df['HistoryOfBacklogs'] == 1].shape[0],
                                        p=[0.6, 0.3, 0.1])

df.loc[df['HistoryOfBacklogs'] == 1, 'HistoryOfBacklogs'] = backlog_distribution

print("\nNew backlog distribution:")
print(df['HistoryOfBacklogs'].value_counts().sort_index())

# 2. Add ProjectDomain column
# Domains based on stream
domain_mapping = {
    'Computer Science': ['Web Development', 'Mobile App', 'Machine Learning', 'Data Science', 'Cloud Computing', 'Cybersecurity'],
    'Information Technology': ['Web Development', 'Mobile App', 'Database Management', 'Network Security', 'Cloud Computing'],
    'Mechanical': ['CAD Design', 'Robotics', 'Thermal Systems', 'Manufacturing', 'Automotive'],
    'Civil': ['Structural Design', 'Construction Management', 'Urban Planning', 'Environmental Engineering'],
    'Electrical': ['Power Systems', 'Embedded Systems', 'Renewable Energy', 'Control Systems'],
    'Electronics And Communication': ['IoT', 'Signal Processing', 'VLSI Design', 'Embedded Systems', 'Telecommunications']
}

def assign_domain(stream):
    """Assign a random domain based on stream"""
    if stream in domain_mapping:
        return np.random.choice(domain_mapping[stream])
    return 'General'

df['ProjectDomain'] = df['Stream'].apply(assign_domain)

print("\nProject domains added:")
print(df['ProjectDomain'].value_counts())

# 3. Save updated dataset
df.to_csv('collegePlace_updated.csv', index=False)
print("\n✅ Updated dataset saved as 'collegePlace_updated.csv'")

# Backup original
import shutil
shutil.copy('collegePlace.csv', 'collegePlace_backup.csv')
print("✅ Original dataset backed up as 'collegePlace_backup.csv'")

# Replace original with updated
shutil.copy('collegePlace_updated.csv', 'collegePlace.csv')
print("✅ Original dataset replaced with updated version")

print("\n📊 Final dataset info:")
print(df.info())
print("\nFirst 5 rows:")
print(df.head())
