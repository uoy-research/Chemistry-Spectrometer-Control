import numpy as np
from scipy import stats
import matplotlib.pyplot as plt

# Your data
x = [0, 1023]
y = [-2.5, 10]

print("Data:")
print(f"X: {x}")
print(f"Y: {y}")
print()

# Calculate correlation coefficient
correlation, p_value = stats.pearsonr(x, y)
print(f"Correlation coefficient (r): {correlation:.4f}")
print(f"P-value: {p_value:.4f}")
print()

# Calculate linear regression
slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
print(f"Slope (m): {slope:.4f}")
print(f"Intercept (b): {intercept:.4f}")
print(f"R-squared (R²): {r_value**2:.4f}")
print(f"Standard error: {std_err:.4f}")
print()

# Linear equation
print(f"Linear equation: y = {slope:.4f}x + {intercept:.4f}")
print()

# Calculate predicted values
y_pred = [slope * xi + intercept for xi in x]
print(f"Predicted values: {[round(val, 2) for val in y_pred]}")

# Calculate residuals
residuals = [yi - ypi for yi, ypi in zip(y, y_pred)]
print(f"Residuals: {[round(val, 2) for val in residuals]}")

# Calculate R-squared manually to verify
ss_res = sum([(yi - ypi)**2 for yi, ypi in zip(y, y_pred)])
ss_tot = sum([(yi - np.mean(y))**2 for yi in y])
r_squared_manual = 1 - (ss_res / ss_tot)
print(f"R-squared (manual calculation): {r_squared_manual:.4f}")

# Create a simple plot
plt.figure(figsize=(10, 6))
plt.scatter(x, y, color='blue', label='Data points')
plt.plot(x, y_pred, color='red', label=f'Linear fit: y = {slope:.2f}x + {intercept:.2f}')
plt.xlabel('X values')
plt.ylabel('Y values')
plt.title('Linear Relationship Analysis')
plt.legend()
plt.grid(True, alpha=0.3)
plt.savefig('linear_relationship.png', dpi=300, bbox_inches='tight')
plt.show()

print("\nSummary:")
print(f"• Strong positive correlation: r = {correlation:.4f}")
print(f"• Linear relationship: y = {slope:.2f}x + {intercept:.2f}")
print(f"• Model explains {r_value**2*100:.1f}% of the variance in Y")
print(f"• For every unit increase in X, Y increases by {slope:.2f} units")