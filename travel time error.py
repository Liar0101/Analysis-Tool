import os
import numpy as np

def read_file(file_path):
    # Read the file and convert each line into a list of floating-point numbers
    with open(file_path, 'r') as data_file:
        # Read the file line by line and store each line as an array
        data = [list(map(float, line.strip().split())) for line in data_file]

    print(f'{file_path} data reading completed')
    return data


def process_data(data):
    # Process a single data list, removing items where z is NaN or 0,
    # and rounding z to one decimal place.
    new_data = []
    for x, y, z in data:
        if not np.isnan(z) and z != 0:
            z = np.round(z, 1)
            new_data.append([x, y, z])

    # Convert the new data list to a numpy array and return it
    return np.array(new_data)

# Specify the main folder containing travel time error data
main_folder = 'travel time error'

# Get the list of subfolders
sub_folders = [f for f in os.listdir(main_folder) if os.path.isdir(os.path.join(main_folder, f))]
count = 0

for sub_folder in sub_folders:
    absolute_subfolder = os.path.join(main_folder, sub_folder)

    single_file_path = os.path.join(main_folder, sub_folder, 'bathy.xyz')
    topo_file_path = os.path.join(main_folder, sub_folder, 'topo.xyz')

    single = read_file(single_file_path)
    topo = read_file(topo_file_path)

    single = process_data(single)

    z_combined = []

    # Create a dictionary from topo data with (x, y) as keys and z as values
    topo_dict = {(x, y): z for x, y, z in topo}
    # Iterate through each element in `single`
    for x, y, z_single in single:
        # Check if matching (x, y) coordinates exist in the dictionary
        if (x, y) in topo_dict:
            z_topo = np.round(topo_dict[(x, y)])
            z_combined.append([x, y, z_single, z_topo])
    print('z_combined data reading completed')

    z_modify = []
    for x, y, z_single, z_topo in z_combined:
        difference = z_single - z_topo
        if difference > 0:
            # Calculate the integer multiple of the difference divided by 750 (rounded)
            multiplier = round(difference / 750)
            range_lower = multiplier * 750 * 0.95  # Lower bound of the range
            range_upper = multiplier * 750 * 1.05  # Upper bound of the range
            # Check if the difference is within a 5% tolerance range
            if range_lower <= difference <= range_upper:
                z_single -= 750 * multiplier
                count += 1
        if difference < 0:
            # Calculate the integer multiple of the negative difference divided by 750 (rounded)
            multiplier = round(abs(difference) / 750)
            range_upper = multiplier * -750 * 0.95  # Lower bound of the range
            range_lower = multiplier * -750 * 1.05  # Upper bound of the range
            # Check if the difference is within a 5% tolerance range
            if range_lower <= difference <= range_upper:
                z_single += 750 * multiplier
                count += 1
        z_modify.append([x, y, z_single, z_topo])
    z_combined_array = np.array(z_modify)
    z_modify = np.array(z_modify)
    topo_data = z_combined_array[:, [0, 1, 3]].tolist()
    single_data = z_combined_array[:, [0, 1, 2]].tolist()

    deleted_ship = []
    z_modify1 = []
    for x, y, z_ship in single_data:
        # Check if matching (x, y) coordinates exist in the dictionary
        if (x, y) in topo_dict:
            z_topo = topo_dict[(x, y)]
            # Apply conditions for filtering data
            if z_topo > 0:
                deleted_ship.append([x, y, z_ship, z_topo])
                continue
            elif z_topo < 0 and abs(z_topo - z_ship) > 1000:
                deleted_ship.append([x, y, z_ship, z_topo])  # Add data exceeding the threshold to `deleted_ship`
                continue
            else:
                z_modify1.append([x, y, z_ship, z_topo])

    # Extract x, y, z_ship data
    x_data = [entry[0] for entry in z_modify1]
    y_data = [entry[1] for entry in z_modify1]
    z_ship_data = [entry[2] for entry in z_modify1]

    # Write to newbathy.xyz file
    with open(f'{absolute_subfolder}/newbathy.xyz', 'w') as f:
        for x, y, z_ship in zip(x_data, y_data, z_ship_data):
            f.write(f'{x} {y} {z_ship}\n')

    # Extract x, y, z_ship, z_topo data
    x_delete = [entry[0] for entry in deleted_ship]
    y_delete = [entry[1] for entry in deleted_ship]
    z_delete = [entry[2] for entry in deleted_ship]
    z_topo_delete = [entry[3] for entry in deleted_ship]  # Extract z_topo data
    # Write to deletebathy.xyz file
    with open(f'{absolute_subfolder}/deletebathy.xyz', 'w') as f:
        for x, y, z_ship, z_topo in zip(x_delete, y_delete, z_delete, z_topo_delete):
            f.write(f'{x} {y} {z_ship} {z_topo}\n')
