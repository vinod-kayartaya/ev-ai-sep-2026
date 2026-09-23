import numpy as np

# Create a 1D array
array_1d = np.array([1, 2, 3, 4, 5])
print('1D Array:', array_1d)

# Create a 2D array
array_2d = np.array([[1, 2, 3], [4, 5, 6]])
print('2D Array:
', array_2d)

# Array operations
sum_array = np.sum(array_1d)
print('Sum of 1D Array:', sum_array)

mean_array = np.mean(array_1d)
print('Mean of 1D Array:', mean_array)

# Reshape the array
reshaped_array = array_1d.reshape((5, 1))
print('Reshaped Array:
', reshaped_array)