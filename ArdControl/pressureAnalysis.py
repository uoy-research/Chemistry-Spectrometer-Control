import pandas as pd
import numpy as np
import csv
from sklearn.linear_model import LinearRegression


data = {
    'number': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17],
    'real pressure': [189, 236, 286, 336, 386, 436, 486, 537, 587, 638, 688, 738, 788, 839, 889, 940, 990, 1039],
    'recorded pressure': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
}

df = pd.DataFrame(data)

for i in range(0, 18):
    temp_df = pd.read_csv('C:\\NMR Results\\pressure_data' + str(i) + '.csv')
    temp_df = temp_df['Pressure1']
    temp_df = temp_df.to_numpy()
    avg = np.mean(temp_df)
    df['recorded pressure'][i] = avg

#df.to_csv('C:\\NMR Results\\pressure_data_final.csv', index=False)

# Prepare the data for linear regression
X = df[['real pressure']][0:16]  # Independent variable
y = df['recorded pressure'][0:16]  # Dependent variable

# Create and fit the linear regression model
model = LinearRegression()
model.fit(X, y)

# Optionally, make predictions
predictions = model.predict(X)

# Print the coefficients
print(f"Intercept: {model.intercept_}")
print(f"Coefficient: {model.coef_[0]}")

print(model.predict([[1000]]))  # Predict the pressure for a real pressure of 1000
print((1000*0.8247) + 203.61)

print((1023-203.61)/0.8247)  # Predict the real pressure for a recorded pressure of 1023
