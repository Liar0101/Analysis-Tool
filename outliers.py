import numpy as np

with open(f'topo.xyz', 'r') as topo_file:
    # Read model value data
    topo = [list(map(float, line.strip().split())) for line in topo_file]
print('Topographic value file')

with open(f'bathy.xyz', 'r') as ship_file:
    # Read ship measurement data
    ship = [list(map(float, line.strip().split())) for line in ship_file]
print('Ship depth file')

with open(f'crossover.txt', 'r') as cross_file:
    # Read ECOE point data
    cross = [list(map(float, line.strip().split())) for line in cross_file]
print('ECOE data file')

print(len(ship))

new_ship = []
deleted_ship = []  # List to record data with large errors
outliers = []  # List to record outlier data
# Remove invalid ship measurement points
for item in ship:
    if np.isnan(item[2]) or item[2] == 0:
        continue
    else:
        new_ship.append(item)
# Assign the new ship list to the original ship
ship = np.array(new_ship)

topo_dict = {(x, y): z for x, y, z in topo}
z_combined = []
# Difference greater than 1000
for x, y, z_ship in ship:
    # Look for matching XY coordinates in the dictionary
    if (x, y) in topo_dict:
        z_topo = topo_dict[(x, y)]
        if z_topo > 0:
            deleted_ship.append([x, y, z_ship, z_topo])
            continue
        elif z_topo <= 0 and abs(z_topo - z_ship) > 1000:
            deleted_ship.append([x, y, z_ship, z_topo])  # Add data to deleted_ship if it exceeds the threshold
            continue
        else:
            z_combined.append([x, y, z_ship, z_topo])

longitude_tolerance = 0.0167
latitude_tolerance = 0.0167

# Iterate through the intersection points
for ship_point in deleted_ship:
    ship_longitude, ship_latitude, ship_measure, model_value = ship_point

    # Iterate through the ship measurement points
    for cross_point in cross:
        longitude, latitude, mismatch_value = cross_point
        # Check if the mismatch value exceeds 1000
        if abs(mismatch_value) > 1000:
            # Check if longitude and latitude are within the specified range
            if (longitude - longitude_tolerance <= ship_longitude <= longitude + longitude_tolerance) and \
                    (latitude - latitude_tolerance <= ship_latitude <= latitude + latitude_tolerance):
                outliers.append(ship_point)
                continue

ship = np.array([item for item in ship if item.tolist() in z_combined])

# Extract x, y, z_ship data
x_data = [entry[0] for entry in z_combined]
y_data = [entry[1] for entry in z_combined]
z_ship_data = [entry[2] for entry in z_combined]

# Write to newbathy.xyz file
with open(f'newbathy.xyz', 'w') as f:
    for x, y, z_ship in zip(x_data, y_data, z_ship_data):
        f.write(f'{x} {y} {z_ship}\n')

x_delete = [entry[0] for entry in deleted_ship]
y_delete = [entry[1] for entry in deleted_ship]
z_delete = [entry[2] for entry in deleted_ship]
z_topo_delete = [entry[3] for entry in deleted_ship]
# Write to deletebathy.xyz file
with open(f'deletebathy.xyz', 'w') as f:
    for x, y, z_ship, z_topo in zip(x_delete, y_delete, z_delete, z_topo_delete):
        f.write(f'{x} {y} {z_ship} {z_topo}\n')

x_outlier = [entry[0] for entry in outliers]
y_outlier = [entry[1] for entry in outliers]
z_outlier = [entry[2] for entry in outliers]
z_topo_outlier = [entry[3] for entry in outliers]
# Write to outliers.xyz file
with open(f'outliers.xyz', 'w') as f:
    for x, y, z_ship, z_topo in zip(x_outlier, y_outlier, z_outlier, z_topo_outlier):
        f.write(f'{x} {y} {z_ship} {z_topo}\n')
