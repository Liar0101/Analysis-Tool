# Analysis-Tool
Analysis tools are divided into two parts: visualization tool and correction tool

Visualization tool
  
  The visualization tool is built on Python and Generic Mapping Tools, includes three parts: preprocessing, crossover analysis, and statistical results.

  The preprocessing module obtains the longitude, latitude, and depth information of the depth measurement points from the original mgd77 file, and interpolates the depth measurement points in the model from the bathymetric model file.
    The input folder contains the m77t suffix files that need to be preprocessed. The output folder contains multiple independent folders, which correspond one-to-one with the SID. The model file refers to the nc/grd file.

  The crossover analysis can obtain all crossover errors of the route.
    The input folder A as a cross track-line containing a single or multiple independent folders. The input folder B usually contains all track-lines

  The statistics module includes three windows to display the quality of depth measurement data.
    The input folder contains a main folder with multiple independent folders.


Correction tool

  We have identified three types of errors:
    
    (1)	Within the generally reliable ship track-lines, there are a few instances of significant errors in echo-sounding measurements, commonly referred to as outliers.
    (2)	Errors arise from inaccuracies in converting sonar propagation time into depth, known as scale factor error.
    (3)	The discrepancy in depth measurements caused by errors in recording the two-way propagation time of sonar is termed "travel time error".




Article: On the accuracy evaluation and correction of single-beam depths

Xing Liu 
Minzhang Hu 
Taoyong Jin


