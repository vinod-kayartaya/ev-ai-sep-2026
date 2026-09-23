import numpy as np

# Creating a 1D array
array_1d = np.array([1, 2, 3, 4, 5])
print("1D Array:", array_1d)

# Creating a 2D array
array_2d = np.array([[1, 2, 3], [4, 5, 6]])
print("2D Array:", array_2d)

# Array shape
print("Shape of 2D array:", array_2d.shape)

# Array operations
array_sum = array_1d + 10
print("Array after addition:", array_sum)

# Dot product
dot_product = np.dot(array_1d, array_1d)
print("Dot product of array with itself:", dot_product)

# Reshaping array
reshaped_array = np.reshape(array_2d, (3, 2))
print("Reshaped Array:", reshaped_array)