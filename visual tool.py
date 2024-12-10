import os
import sys
import glob
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog, QLabel, QListWidget, QHBoxLayout, QGroupBox, QMessageBox, QSizePolicy

)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import subprocess
import shutil
import concurrent.futures


def read_coordinates(file_path):
    coordinates = []
    with open(file_path, 'r') as file:
        for line in file:
            lon, lat = map(float, line.strip().split())
            if lon < 0:
                lon += 360
            coordinates.append((lon, lat))
    return coordinates


def get_bounding_box(coordinates):
    min_lon = min(lon for lon, _ in coordinates)
    max_lon = max(lon for lon, _ in coordinates)
    min_lat = min(lat for _, lat in coordinates)
    max_lat = max(lat for _, lat in coordinates)
    return min_lon, max_lon, min_lat, max_lat


def check_overlap(bbox1, bbox2):
    min_lon1, max_lon1, min_lat1, max_lat1 = bbox1
    min_lon2, max_lon2, min_lat2, max_lat2 = bbox2

    overlap_lon = max_lon1 >= min_lon2 and max_lon2 >= min_lon1
    overlap_lat = max_lat1 >= min_lat2 and max_lat2 >= min_lat1

    return overlap_lon and overlap_lat


def process_comparison(task):
    coordinates_file1, coordinates_file2, output_subfolder1, output_subfolder2, SID = task
    coordinates1 = read_coordinates(coordinates_file1)
    coordinates2 = read_coordinates(coordinates_file2)

    bbox1 = get_bounding_box(coordinates1)
    bbox2 = get_bounding_box(coordinates2)

    if check_overlap(bbox1, bbox2):
        inputfile = os.path.join(output_subfolder2, 'bathy.xyz')
        outputfile = os.path.join(output_subfolder1, f'bathy_{SID}.xyz')
        shutil.copy2(inputfile, outputfile)


def coe():
    # Filter data in the bathy.xyz file based on specific conditions
    with open("bathy.xyz", "r") as infile, open("filtered.xyz", "w") as outfile:
        for line in infile:
            parts = line.strip().split()
            if len(parts) == 3 and parts[2].lower() not in ("0", "nan"):
                outfile.write(line)

    # Find all files starting with bathy_ and ending with .xyz
    bathy_files = glob.glob("bathy_*.xyz")

    # Loop through each file and execute the x2sys_cross command
    for filename in bathy_files:
        output_file = f"{os.path.splitext(filename)[0]}_crossover.txt"

        cross_command = f'gmt x2sys_cross filtered.xyz {filename} -Qe -W2 -TXYZ > {output_file}'
        os.system(cross_command)

    # Process all *_crossover.txt files
    crossover_files = glob.glob("*_crossover.txt")
    with open("crossover.txt", "w") as combined_file:
        for file in crossover_files:
            with open(file, "r") as infile:
                for line_num, line in enumerate(infile, start=1):
                    if line_num >= 5:
                        parts = line.strip().split()
                        # Extract required columns and write them to the output file
                        combined_file.write(
                            f"{float(parts[0]):.5f} {float(parts[1]):.5f} "
                            f"{abs(float(parts[-2])):.1f}\n"
                        )


def process_folder(sub_folder1, main_folder1, main_folder2, sub_folders2):
    output_subfolder1 = os.path.join(main_folder1, sub_folder1)
    print(f'Currently processing folder: {output_subfolder1}')
    coordinates_file1 = os.path.join(output_subfolder1, 'lon_lat.txt')

    # Perform bounding box comparison
    tasks = [
        (coordinates_file1, os.path.join(main_folder2, sub_folder2, 'lon_lat.txt'), output_subfolder1,
         os.path.join(main_folder2, sub_folder2), sub_folder2)
        for sub_folder2 in sub_folders2 if sub_folder1 != sub_folder2
    ]

    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.map(process_comparison, tasks)

    # Run the `coe` function to complete `x2sys_cross` and subsequent processing
    os.chdir(output_subfolder1)
    coe()
    os.chdir("..")


class ImageViewer(QWidget):
    def __init__(self, folder_data, figsize=(8, 8), statistics_folder_path=None):
        super().__init__()
        self.folder_data = folder_data
        self.figsize = figsize
        self.statistics_folder_path = statistics_folder_path

        # Main layout
        layout = QHBoxLayout(self)

        # Left side: List of subfolders
        self.folder_list = QListWidget()
        self.folder_list.addItems(self.folder_data.keys())
        self.folder_list.currentItemChanged.connect(self.update_plots)
        layout.addWidget(self.folder_list, 1)  # Left side takes up 1 unit of width

        # Right side: Layout to display images
        self.right_layout = QVBoxLayout()
        right_widget = QWidget()
        right_widget.setLayout(self.right_layout)
        layout.addWidget(right_widget, 3)  # Right side takes up 3 units of width

        # Add initial image canvases
        self.canvas1 = self.create_square_canvas()
        self.canvas2 = self.create_square_canvas()
        self.canvas3 = self.create_square_canvas()  # New canvas for statistical plots
        self.right_layout.addWidget(self.canvas1)
        self.right_layout.addWidget(self.canvas2)
        self.right_layout.addWidget(self.canvas3)

    def create_square_canvas(self):
        """
        Create a square canvas
        """
        canvas = FigureCanvas(Figure(figsize=(8, 8)))  # Ensure the canvas is square
        canvas.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        canvas.setFixedSize(400, 400)  # Set a fixed size to maintain square proportions
        return canvas

    def add_folder(self, folder_name, Topo, Ship, longitudes, latitudes, CrossoverFile):
        """Add subfolder data to the list"""
        self.folder_data[folder_name] = (Topo, Ship, longitudes, latitudes, CrossoverFile)
        self.folder_list.addItem(folder_name)

    def update_plots(self, current, previous):
        """Update the display of images on the right side"""
        if not current:
            return  # Skip if no folder is selected

        folder_name = current.text()
        Topo, Ship, longitudes, latitudes, CrossoverFile = self.folder_data.get(folder_name,
                                                                                (None, None, None, None, None))
        if Topo is None or Ship is None or longitudes is None or latitudes is None or CrossoverFile is None:
            return  # Skip if data is missing

        # Remove old FigureCanvas
        for i in reversed(range(self.right_layout.count())):
            widget = self.right_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # Create new FigureCanvas
        self.canvas1 = FigureCanvas(Figure(figsize=self.figsize))
        self.canvas2 = FigureCanvas(Figure(figsize=self.figsize))
        self.canvas3 = FigureCanvas(Figure(figsize=self.figsize))  # New canvas for statistical plots
        self.right_layout.addWidget(self.canvas1)
        self.right_layout.addWidget(self.canvas2)
        self.right_layout.addWidget(self.canvas3)

        # Draw new images
        self.plot_scatter(Topo, Ship, folder_name)
        self.plot_line(Topo, Ship, folder_name)
        sub_folder_path = os.path.join(self.statistics_folder_path, folder_name)  # Get subfolder path
        self.plot_stat(longitudes, latitudes, sub_folder_path, CrossoverFile, folder_name)

    def plot_scatter(self, Topo, Ship, folder_name):
        """Plot a scatter plot"""
        ax = self.canvas1.figure.subplots()
        ax.scatter(Topo, Ship, s=0.5, label='Data Points')
        ax.plot([-10000, 100], [-10000, 100], label='Line of Unit Slope', color='#32CD32')
        ax.set_xlabel('Topo', fontsize=8)
        ax.set_ylabel('Ship', fontsize=8)
        ax.legend(fontsize=6)
        ax.set_title(f'Statistical Plot - {folder_name}', fontsize=10)
        ax.tick_params(axis='both', labelsize=6)
        self.canvas1.draw()

    def plot_line(self, Topo, Ship, folder_name):
        """Plot a line chart"""
        ax = self.canvas2.figure.subplots()
        ax.plot(np.arange(len(Ship)), Ship, label='Ship Data', color='red')
        ax.plot(np.arange(len(Topo)), Topo, label='Topo Data', color='#32CD32')
        ax.set_xlabel('X (Data Point)', fontsize=8)
        ax.set_ylabel('Z (Depth)', fontsize=8)
        ax.legend(fontsize=6)
        ax.set_title(f'Data Plot - {folder_name}', fontsize=10)
        ax.tick_params(axis='both', labelsize=6)
        self.canvas2.draw()

    def plot_stat(self, longitudes, latitudes, sub_folder_path, crossover_file, folder_name):
        """Plot a statistical map"""
        # Convert longitude and latitude to NumPy arrays
        longitudes = np.array(longitudes)
        latitudes = np.array(latitudes)

        # Check if the longitudes cross the 180/-180 boundary
        crosses_dateline = (longitudes.max() > 179) and (longitudes.min() < -179)

        # Adjust longitudes crossing the boundary by adding 360 to negative values
        if crosses_dateline:
            longitudes[longitudes < 0] += 360

        # Calculate min and max longitude and latitude
        minlon, maxlon = longitudes.min(), longitudes.max()
        minlat, maxlat = latitudes.min(), latitudes.max()

        shutil.copy(os.path.join(os.getcwd(), 'crosspoint.cpt'), os.path.join(sub_folder_path, 'crosspoint.cpt'))
        # Save the image to a temporary file
        output_image = "map_plot.png"

        # GMT command string
        command = f"""
        gmt begin map_plot png I+m0.2c
        gmt set FONT_TITLE 10p,1,black
        gmt set MAP_TITLE_OFFSET -5p
        gmt coast -R{minlon - 5}/{maxlon + 5}/{minlat - 5}/{maxlat + 5} -JQ15c -Baf -Df -BWSen+t"{folder_name} ECOEs" -A5000 -Ggray
        gmt plot bathy.xyz -R{minlon - 5}/{maxlon + 5}/{minlat - 5}/{maxlat + 5} -JQ15c -Sc0.01 -Gblue
        gmt plot {os.path.join(sub_folder_path, crossover_file)} -R{minlon - 5}/{maxlon + 5}/{minlat - 5}/{maxlat + 5} -JQ15c -St0.1 -Ccrosspoint.cpt
        gmt colorbar -DjBC+w5c/0.2c+o0c/-0.8c+m+h+e -S -Bxa1000f500 -G0/5000 -Ccrosspoint.cpt
        gmt end
        """

        # Execute GMT command
        os.chdir(sub_folder_path)  # Change to the subfolder path
        os.system(command)

        # Load the image in PyQt
        ax = self.canvas3.figure.subplots()
        image = plt.imread(output_image)
        ax.imshow(image)
        ax.axis("off")
        self.canvas3.draw()


class App(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Ship Data Analysis Tool")
        self.setGeometry(100, 100, 800, 600)

        # Main layout
        main_layout = QVBoxLayout(self)

        # Add each functional module
        self.add_preprocess_section(main_layout)
        self.add_intersection_analysis_section(main_layout)
        self.add_statistics_section(main_layout)

        self.setLayout(main_layout)

    def add_preprocess_section(self, layout):
        """Add preprocessing section"""
        group = QGroupBox("Preprocessing Module")
        preprocess_layout = QVBoxLayout()

        self.label_folder = QLabel("Input Folder: Not Selected")
        self.label_output_folder = QLabel("Output Folder: Not Selected")
        self.label_grd = QLabel("Model File: Not Selected")

        preprocess_layout.addWidget(self.label_folder)
        preprocess_layout.addWidget(self.label_output_folder)
        preprocess_layout.addWidget(self.label_grd)

        btn_select_folder = QPushButton("Select Input Folder")
        btn_select_folder.clicked.connect(self.select_folder)
        preprocess_layout.addWidget(btn_select_folder)

        btn_select_output_folder = QPushButton("Select Output Folder")
        btn_select_output_folder.clicked.connect(self.select_output_folder)
        preprocess_layout.addWidget(btn_select_output_folder)

        btn_select_grd = QPushButton("Select Model File")
        btn_select_grd.clicked.connect(self.select_grd_file)
        preprocess_layout.addWidget(btn_select_grd)

        btn_preprocess = QPushButton("Preprocess")
        btn_preprocess.clicked.connect(self.preprocess_folder)
        preprocess_layout.addWidget(btn_preprocess)

        group.setLayout(preprocess_layout)
        layout.addWidget(group)

    def add_intersection_analysis_section(self, layout):
        """Add intersection analysis section"""
        group = QGroupBox("Crossover Analysis Module")
        intersection_layout = QVBoxLayout()

        self.label_intersection_input_a = QLabel("Input Folder A: Not Selected")
        self.label_intersection_input_b = QLabel("Input Folder B: Not Selected")

        intersection_layout.addWidget(self.label_intersection_input_a)
        intersection_layout.addWidget(self.label_intersection_input_b)

        btn_select_input_folder_a = QPushButton("Select Input Folder A")
        btn_select_input_folder_a.clicked.connect(self.select_intersection_input_folder_a)
        intersection_layout.addWidget(btn_select_input_folder_a)

        btn_select_input_folder_b = QPushButton("Select Input Folder B")
        btn_select_input_folder_b.clicked.connect(self.select_intersection_input_folder_b)
        intersection_layout.addWidget(btn_select_input_folder_b)

        btn_analyze = QPushButton("Crossover Analysis")
        btn_analyze.clicked.connect(self.analyze_intersection)
        intersection_layout.addWidget(btn_analyze)

        group.setLayout(intersection_layout)
        layout.addWidget(group)

    def add_statistics_section(self, layout):
        """Add statistics generation section"""
        group = QGroupBox("Statistics Generation")
        statistics_layout = QVBoxLayout()

        self.label_statistics_folder = QLabel("Main Folder: Not Selected")
        statistics_layout.addWidget(self.label_statistics_folder)

        btn_select_statistics_folder = QPushButton("Select Main Folder")
        btn_select_statistics_folder.clicked.connect(self.select_statistics_folder)
        statistics_layout.addWidget(btn_select_statistics_folder)

        btn_generate_statistics = QPushButton("Generate Statistics")
        btn_generate_statistics.clicked.connect(self.generate_statistics)
        statistics_layout.addWidget(btn_generate_statistics)

        group.setLayout(statistics_layout)
        layout.addWidget(group)

    def select_folder(self):
        """Select the input folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select Input Folder")
        if folder:
            self.folder_path = folder
            self.label_folder.setText(f"Input Folder: {folder}")
        else:
            self.label_folder.setText("Input Folder: Not Selected")

    def select_output_folder(self):
        """Select the output folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_folder_path = folder
            self.label_output_folder.setText(f"Output Folder: {folder}")
        else:
            self.label_output_folder.setText("Output Folder: Not Selected")

    def select_grd_file(self):
        """Select the model (.grd) file"""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Model File", "", "All Files (*)")
        if file_path:
            self.grd_file_path = file_path
            self.label_grd.setText(f"Model File: {file_path}")
        else:
            self.label_grd.setText("Model File: Not Selected")

    def select_intersection_input_folder_a(self):
        """Select intersection input folder A"""
        folder = QFileDialog.getExistingDirectory(self, "Select Input Folder A")
        if folder:
            self.intersection_input_folder_a = folder
            self.label_intersection_input_a.setText(f"Input Folder A: {folder}")
        else:
            self.label_intersection_input_a.setText("Input Folder A: Not Selected")

    def select_intersection_input_folder_b(self):
        """Select intersection input folder B"""
        folder = QFileDialog.getExistingDirectory(self, "Select Input Folder B")
        if folder:
            self.intersection_input_folder_b = folder
            self.label_intersection_input_b.setText(f"Input Folder B: {folder}")
        else:
            self.label_intersection_input_b.setText("Input Folder B: Not Selected")

    def select_statistics_folder(self):
        """Select the main statistics folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select Main Folder")
        if folder:
            self.statistics_folder_path = folder
            self.label_statistics_folder.setText(f"Main Folder: {folder}")
        else:
            self.label_statistics_folder.setText("Main Folder: Not Selected")

    def preprocess_folder(self):
        """Run preprocessing logic"""
        if not hasattr(self, 'folder_path'):
            self.label_folder.setText("Please select an input folder first!")
            return
        if not hasattr(self, 'output_folder_path'):
            self.label_output_folder.setText("Please select an output folder first!")
            return
        if not hasattr(self, 'grd_file_path'):
            self.label_grd.setText("Please select a .grd model file first!")
            return
        # Process each .m77t file
        self.process_m77_files(self.folder_path, self.output_folder_path, self.grd_file_path)
        self.label_folder.setText("Preprocessing Complete!")

    def analyze_intersection(self):
        """Perform intersection analysis"""
        try:
            main_folder1 = self.intersection_input_folder_a
            main_folder2 = self.intersection_input_folder_b

            sub_folders1 = [f for f in os.listdir(main_folder1) if os.path.isdir(os.path.join(main_folder1, f))]
            sub_folders2 = [f for f in os.listdir(main_folder2) if os.path.isdir(os.path.join(main_folder2, f))]

            # Process each folder sequentially
            for sub_folder1 in sub_folders1:
                process_folder(sub_folder1, main_folder1, main_folder2, sub_folders2)

            QMessageBox.information(self, "Completed", "Intersection analysis completed successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

    def generate_statistics(self):
        """Generate statistical results"""
        if not hasattr(self, 'statistics_folder_path'):
            self.label_statistics_folder.setText("Please select the main folder first!")
            return

        folder_data = {}
        sub_folders = [f for f in os.listdir(self.statistics_folder_path) if
                       os.path.isdir(os.path.join(self.statistics_folder_path, f))]

        for sub_folder in sub_folders:
            sub_folder_path = os.path.join(self.statistics_folder_path, sub_folder)
            ship_file_path = os.path.join(sub_folder_path, "bathy.xyz")
            topo_file_path = os.path.join(sub_folder_path, "topo.xyz")
            crossover_file_path = os.path.join(sub_folder_path, "crossover.txt")  # Assume crossover file path

            if not os.path.exists(ship_file_path) or not os.path.exists(topo_file_path):
                continue

            ship = np.loadtxt(ship_file_path, usecols=(0, 1, 2))
            topo = np.loadtxt(topo_file_path, usecols=(0, 1, 2))

            topo_dict = {(x, y): z for x, y, z in topo}
            combined_data = [[topo_dict.get((x, y), None), z_ship] for x, y, z_ship in ship if (x, y) in topo_dict]
            combined_data = [item for item in combined_data if None not in item]

            if not combined_data:
                continue

            Topo, Ship = zip(*combined_data)
            longitudes = [x for x, _, _ in ship]
            latitudes = [y for _, y, _ in ship]
            CrossoverFile = crossover_file_path if os.path.exists(crossover_file_path) else None
            folder_data[sub_folder] = (
                np.array(Topo), np.array(Ship), np.array(longitudes), np.array(latitudes), CrossoverFile)

        if not folder_data:
            self.label_statistics_folder.setText("No valid data found!")
            return

        self.viewer = ImageViewer(folder_data=folder_data, statistics_folder_path=self.statistics_folder_path)
        self.viewer.show()

    def process_m77_files(self, folder_path, output_folder_path, grd_file_path):
        """Process all .m77t files in the main folder"""
        # Find all .m77t files that don't start with a dot
        m77_files = [f for f in os.listdir(folder_path) if f.endswith(".m77t") and not f.startswith(".")]

        for m77_file in m77_files:
            # Build the full path for the .m77t file
            m77_file_path = os.path.join(folder_path, m77_file)
            sub_folder_name = os.path.splitext(m77_file)[0]
            sub_folder_path = os.path.join(output_folder_path, sub_folder_name)
            os.makedirs(sub_folder_path, exist_ok=True)  # Create the subfolder if it doesn't exist

            # Copy the original .m77t file to the subfolder
            shutil.copy(m77_file_path, os.path.join(sub_folder_path, m77_file))

            # Generate the bathy.xyz file
            bathy_file_path = os.path.join(sub_folder_path, "bathy.xyz")
            with open(bathy_file_path, "w") as bathy_file:
                # Run the GMT command to extract data from the .m77t file
                mgd77_command = [
                    "gmt", "mgd77list", m77_file_path, "-Flon,lat,depth"
                ]
                process = subprocess.Popen(mgd77_command, stdout=subprocess.PIPE, text=True)
                for line in process.stdout:
                    parts = line.strip().split()
                    if len(parts) == 3:  # Check if the line has the expected number of columns
                        lon, lat, depth = map(float, parts)
                        bathy_file.write(f"{lon} {lat} {-depth}\n")  # Write data with depth as a negative value

            # Generate the lon_lat.txt file
            lon_lat_file_path = os.path.join(sub_folder_path, "lon_lat.txt")
            with open(bathy_file_path, "r") as bathy_file, open(lon_lat_file_path, "w") as lon_lat_file:
                for line in bathy_file:
                    parts = line.strip().split()
                    if len(parts) == 3:  # Check if the line has the expected number of columns
                        lon, lat, depth = map(float, parts)
                        if depth != 0 and not (depth != depth):  # Ensure depth is not zero or NaN
                            lon_lat_file.write(f"{lon} {lat}\n")  # Write longitude and latitude

            # Run the grdtrack command to create topo.xyz
            topo_file_path = os.path.join(sub_folder_path, "topo.xyz")
            grdtrack_command = [
                "gmt", "grdtrack", lon_lat_file_path, f"-G{grd_file_path}"
            ]
            with open(topo_file_path, "w") as topo_file:
                subprocess.run(grdtrack_command, stdout=topo_file, text=True)  # Run the command and write the output





if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = App()
    ex.show()
    sys.exit(app.exec_())
