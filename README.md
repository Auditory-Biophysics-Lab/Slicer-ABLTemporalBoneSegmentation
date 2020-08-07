**ABL Temporal Bone Segmentation Module**

*Developed by HML & SKA Auditory Medical Biophysics Lab at Western University, London, ON, CA*

## About
This 3D Slicer module handles spacing resampling, fiducial registration, rigid registration, and inference of the major structures of CT temporal bone scans. Inference is done using ABL's [Temporal Bone Segmentation Network](https://github.com/Auditory-Biophysics-Lab/temporal-bone-segmentation).

Also included is a module for batch registration of temporal bone scans.

## Dependencies
This module requires the [SlicerElastix](https://github.com/lassoan/SlicerElastix) module to be installed in 3D Slicer. 

This module also requires either a functional [ABLInfer Server](https://github.com/Auditory-Biophysics-Lab/ablinfer) or a local [Docker](https://www.docker.com/) instance. Specific system requirements for running the network may be found on the [Temporal Bone Segmentation Network page](https://github.com/Auditory-Biophysics-Lab/temporal-bone-segmentation).

## Screenshot
![Screenshot](/Images/main.png)

## Basic Tutorial
1. Load the CT scan into 3D Slicer and navigate to the "ABL Temporal Bone Segmentation Module"
   - If desired, the `CBCTDentalSurgery` sample data set should provide enough of a scan to work with
2. Choose the volume to segment and which side of the head the scan is of
![Choose volume](/Images/00_choosevolume.png)
3. Align and register the image using fiducial selection; select at least three points and locate them on your CT scan
![Fiducal registration](/Images/01_fiducial.png)
4. Run automated rigid registration
![Rigid registration](/Images/02_rigid.png)
5. Finalize the transformation and choose the region of interest (ROI) before segmentation
![Finalize](/Images/03_finalize.png)
6. Run the inference, either on a remote ABLInfer server or using a local Docker instance
![Remote](/Images/04a_inferenceremote.png)
![Docker](/Images/04b_inferencelocal.png)
7. Display and manipulate the result
![Render](/Images/05_render.png)
