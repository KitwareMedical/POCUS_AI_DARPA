import numpy as np

import itk
from itk import TubeTK as ttk

import torch

from monai.networks.nets import UNet
from monai.transforms import ( ScaleIntensityRange, ToTensor )
from monai.networks.layers import Norm
from monai.inferers import sliding_window_inference

from ARGUS_Transforms import *


def ARGUS_PTX_arnet_load_model(filename, device):
    num_classes = 3

    net_in_dims = 3
    net_in_channels = 1
    net_channels=(16, 32, 64, 128, 32)
    net_strides=(2, 2, 2, 2)

    model = UNet(
        dimensions=net_in_dims,
        in_channels=net_in_channels,
        out_channels=num_classes,
        channels=net_channels,
        strides=net_strides,
        num_res_units=2,
        norm=Norm.BATCH,
        ).to(device)    
    model.load_state_dict(torch.load(filename, map_location=device))
    model.eval()

    return model

def ARGUS_PTX_arnet_preprocess_video(input_array):
    num_slices = 48

    arnet_input_array = np.empty([1, 1,
                           input_array.shape[0], input_array.shape[1],
                           num_slices])

    Scale = ScaleIntensityRange(
        a_min=0, a_max=255,
        b_min=0.0, b_max=1.0)
    input_array_scaled = Scale(input_array)

    Crop = ARGUS_RandSpatialCropSlices(
        num_slices=num_slices,
        center_slice=30,
        axis=2)
    arnet_input_array[0, 0] = Crop(input_array_scaled)

    ConvertToTensor = ToTensor()
    arnet_input_tensor = ConvertToTensor(arnet_input_array.astype(np.float32))

    return arnet_input_tensor

def ARGUS_PTX_arnet_inference(arnet_input_tensor, arnet_model, device):
    num_classes = 3

    num_slices = 48

    size_x = 320
    size_y = 320
    roi_size = (size_x,size_y,num_slices)

    pleura_prior = 1

    class_pleura = 1
    class_rib = 2

    min_size = 110000
    max_size = 160000

    with torch.no_grad():
        test_outputs = sliding_window_inference(
            arnet_input_tensor.to(device), roi_size, 1, arnet_model)
        prob_shape = test_outputs[0,:,:,:,:].shape
        prob = np.empty(prob_shape)
        for c in range(num_classes):
            itkProb = itk.GetImageFromArray(test_outputs[0,c,:,:,:].cpu())
            imMathProb = ttk.ImageMath.New(itkProb)
            imMathProb.Blur(5)
            itkProb = imMathProb.GetOutput()
            prob[c] = itk.GetArrayFromImage(itkProb)
        class_array = np.zeros(prob[0].shape)
        pmin = prob[0].min()
        pmax = prob[0].max()
        for c in range(1,num_classes):
            pmin = min(pmin, prob[c].min())
            pmax = max(pmax, prob[c].max())
        prange = pmax - pmin
        prob = (prob - pmin) / prange
        prob[class_pleura] = prob[class_pleura] * pleura_prior
        done = False
        while not done:
            done = True
            count = np.count_nonzero(class_array>0)
            while count<min_size:
                prob[class_pleura] = prob[class_pleura] * 1.05
                prob[class_rib] = prob[class_rib] * 1.05
                class_array = np.argmax(prob,axis=0)
                count = np.count_nonzero(class_array>0)
                done = False
            while count>max_size:
                prob[class_pleura] = prob[class_pleura] * 0.95
                prob[class_rib] = prob[class_rib] * 0.95
                class_array = np.argmax(prob,axis=0)
                count = np.count_nonzero(class_array>0)
                done = False

        class_array = np.where(class_array==1,1,0)
        class_image = itk.GetImageFromArray(class_array.astype(np.float32))
        imMathClassCleanup = ttk.ImageMath.New(class_image)
        imMathClassCleanup.Erode(5,class_pleura,0)
        imMathClassCleanup.Dilate(5,class_pleura,0)
        class_output = imMathClassCleanup.GetOutputUChar()
        
        seg = itk.itkARGUS.SegmentConnectedComponents.New(Input=class_output)
        seg.SetKeepOnlyLargestComponent(True)
        seg.Update()

        class_output = seg.GetOutput()
        class_output_array = itk.GetArrayFromImage(class_output)

        return class_output_array
