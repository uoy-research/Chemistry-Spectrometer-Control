import os

def generate_pattern(start_num, count, increment, delay):
    pattern = "M"
    for i in range(count):
        pattern += f"d{delay}m{start_num-(i*increment)}"
    return pattern

# Create directory if it doesn't exist
directory = r"C:\ssbubble"
os.makedirs(directory, exist_ok=True)

# Generate the pattern starting from 364 and repeating 3 times
pattern = generate_pattern(364, 50, 1, 5000)

# Write both lines to the file
file_path = os.path.join(directory, "sequence.txt")
with open(file_path, "w") as f:
    f.write(pattern + "\n")
    f.write(r"C:\ssbubble")

print(f"File has been created at {file_path}")
