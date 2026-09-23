import pandas as pd

# Create a DataFrame
data = {'Name': ['Alice', 'Bob', 'Charlie'], 'Age': [24, 27, 22]}
df = pd.DataFrame(data)

# Display the DataFrame
print('DataFrame:')
print(df)

# Basic operations
print('\nBasic Statistics:')
print(df.describe())