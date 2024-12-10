import os
import numpy as np
from scipy.stats import linregress

# Select the "scale factor error" folder
main_folder = 'scale factor error'

sub_folders = [f for f in os.listdir(main_folder) if os.path.isdir(os.path.join(main_folder, f))]

# Loop through each subfolder
for sub_folder in sub_folders:
    # Copy the crossover file
    output_subfolder = os.path.join(main_folder, sub_folder)
    print(f'Currently processing folder: {output_subfolder}')


    with open(f'{output_subfolder}/topo.xyz', 'r') as topo_file:
        # Read the file line by line and store each line as an array
        topo = [list(map(float, line.strip().split())) for line in topo_file]
    print('Topo data loaded successfully')


    with open(f'{output_subfolder}/bathy.xyz', 'r') as ship_file:
        # Read the file line by line and store each line as an array
        ship = [list(map(float, line.strip().split())) for line in ship_file]
    print('Ship depth data loaded successfully')
    # print(ship)
    print(len(ship))


    # Clean the ship data by removing rows where the third column is NaN or zero
    new_ship = []
    for item in ship:
        if np.isnan(item[2]) or item[2] == 0:
            continue
        else:
            new_ship.append(item)
    # Assign the new Ship list back to the original Ship
    ship = np.array(new_ship)


    # Create a dictionary of topo data with (x, y) as keys and z values as values
    topo_dict = {(x, y): z for x, y, z in topo}
    z_combined = []
    # Iterate through each element in the ship data
    for x, y, z_ship in ship:
        # Check if matching XY coordinates exist in the topo dictionary
        if (x, y) in topo_dict:
            z_topo = np.round(topo_dict[(x, y)], 1)
            z_combined.append([x, y, z_ship, z_topo])


    # Create lists of z_ship, z_topo, and pairs of z_topo and z_ship for further processing
    z_ship_list = [entry[2] for entry in z_combined]
    z_topo_list = [entry[3] for entry in z_combined]
    z_topo_ship_list = [[entry[3], entry[2]] for entry in z_combined]


    # Keep only the first occurrence of each unique z_topo value and remove the rest
    unique_z_topo_ship = []
    seen_z_topo = set()
    for z_topo, z_ship in z_topo_ship_list:
        if z_topo not in seen_z_topo:
            unique_z_topo_ship.append([z_topo, z_ship])
            seen_z_topo.add(z_topo)


    # Perform linear regression on the remaining z_topo and z_ship values, ensuring the intercept is 0
    z_topo_ship_array = np.array(unique_z_topo_ship)
    z_topo = z_topo_ship_array[:, 0]
    z_ship = z_topo_ship_array[:, 1]
    z_ship -= np.mean(z_ship)  # Subtract the mean of z_ship


    # Perform linear regression and calculate slope and R-value
    slope, _, r_value, _, _ = linregress(z_topo, z_ship)
    print(f"Slope: {slope}, Intercept: 0, R-value: {r_value}")

    # Correct the z_ship values by dividing by the slope
    z_ship_corrected = np.round(z_ship_list / slope, 1)

    # Replace the z_ship values in z_combined with the corrected z_ship values
    for i, entry in enumerate(z_combined):
        entry[2] = z_ship_corrected[i]


    # Extract x, y, z_ship data for output
    x_modify = [entry[0] for entry in z_combined]
    y_modify = [entry[1] for entry in z_combined]
    z_modify = [entry[2] for entry in z_combined]
    with open(f'{output_subfolder}/modify_bathy.xyz', 'w') as f:
        for x, y, z_ship in zip(x_modify, y_modify, z_modify):
            f.write(f'{x} {y} {z_ship}\n')
    print("Data written successfully, results saved to modify_bathy.xyz file.")
