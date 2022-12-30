from os import path

import itk

from ARGUS_Timing import *
from ARGUS_IO import *
from ARGUS_PTX_Linearization import *
from ARGUS_PTX_ARNet import *
from ARGUS_PTX_ROINet import *

class ARGUS_PTX_LinearAR:
    def __init__(self, device_name='cpu', model_dir='Models'):
        self.device = torch.device(device_name)

        self.arnet_model_filename = path.join(model_dir, "BAMC_PTX_ARUNET-3D-PR-Final15", "Epoch333_model.pth")

        self.roinet_model0_filename = path.join(model_dir, "BAMC_PTX_ROINet-StdDevExtended-ExtrudedNS-Final15", "best_model.pth")
        self.roinet_model1_filename = path.join(model_dir, "BAMC_PTX_ROINet-StdDevExtended-ExtrudedNS-Final15", "Epoch333_model.pth")
        self.roinet_model2_filename = path.join(model_dir, "BAMC_PTX_ROINet-StdDevExtended-ExtrudedNS-Final15", "Epoch333_model-48s.pth")

        self.arnet_model = arnet_load_model(self.arnet_model_filename, self.device)
        self.roinet_model0 = roinet_load_model(self.roinet_model0_filename,self.device)
        self.roinet_model1 = roinet_load_model(self.roinet_model1_filename,self.device)
        self.roinet_model2 = roinet_load_model(self.roinet_model2_filename,self.device)
    
    def predict(self, filename, debug=False, stats=None):
        time_this = ARGUS_time_this
        if stats:
            time_this = stats.time
    
        with time_this("all"):
            with time_this("Read Video"):
                us_video = ARGUS_load_video(filename)

                with time_this("Linearization Video"):
                    us_video_linear = ARGUS_PTX_linearize_video(us_video).transpose([2,1,0])

            with time_this("Process Video"):
                with time_this("Preprocess for ARNet"):
                    arnet_input_tensor = ARGUS_PTX_arnet_preprocess_video(us_video_linear)

                with time_this("ARNet Inference Time:"):
                    arnet_output = ARGUS_PTX_arnet_inference(arnet_input_tensor,self.arnet_model,
                        self.device)
                
                with time_this("ROI Extraction Time:"):
                    roinet_input_roi = ARGUS_PTX_roinet_segment_roi(us_video_linear,arnet_output)

                with time_this("Preprocess for ROINet"):
                    roinet_input_tensor0 = ARGUS_PTX_roinet_preprocess_roi(roinet_input_roi, 0)
                    roinet_input_tensor1 = ARGUS_PTX_roinet_preprocess_roi(roinet_input_roi, 1)
                    roinet_input_tensor2 = ARGUS_PTX_roinet_preprocess_roi(roinet_input_roi, 2)

                with time_this("ROINet Inference Time:"):
                    decision0,not_sliding_count0,sliding_count0,class_array0 = ARGUS_PTX_roinet_inference(
                        roinet_input_tensor0,self.roinet_model0,self.device,True)
                    decision1,not_sliding_count1,sliding_count1,class_array1 = ARGUS_PTX_roinet_inference(
                        roinet_input_tensor1,self.roinet_model1,self.device,True)
                    decision2,not_sliding_count2,sliding_count2,class_array2 = ARGUS_PTX_roinet_inference(
                        roinet_input_tensor2,self.roinet_model2,self.device,True)
                    ns = 0
                    not_sliding_count = not_sliding_count0
                    sliding_count = sliding_count0
                    if(decision0 == "Not Sliding"):
                        ns += 1
                    not_sliding_count += not_sliding_count1
                    sliding_count += sliding_count1
                    if(decision1 == "Not Sliding"):
                        ns += 1
                    not_sliding_count += not_sliding_count2
                    sliding_count += sliding_count2
                    if(decision2 == "Not Sliding"):
                        ns += 1

                    if(ns >= 2):
                        decision = "Not Sliding"
                    else:
                        decision = "Sliding"

        return dict(
            decision=decision,
            # debug info
            not_sliding_count=not_sliding_count,
            sliding_count=sliding_count,
            voter_decisions=[
                decision0,
                decision1,
                decision2,
            ],
            voter_not_sliding_counts=[
                not_sliding_count0,
                not_sliding_count1,
                not_sliding_count2,
            ],
            voter_sliding_counts=[
                sliding_count0,
                sliding_count1,
                sliding_count2,
            ],
            arnet_input_tensor=arnet_input_tensor,
            arnet_output=arnet_output,
            roinet_input_roi=roinet_input_roi,
            roinet_input_tensors=[
                roinet_input_tensor0,
                roinet_input_tensor1,
                roinet_input_tensor2,
            ],
            class_arrays=[
                class_array0,
                class_array1,
                class_array2,
            ],
        )
