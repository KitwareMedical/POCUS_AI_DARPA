from ARGUS_classification_inference import ARGUS_classification_inference

class ARGUS_taskid_inference(ARGUS_classification_inference):
    def __init__(self, config_file_name="ARGUS_taskid.cfg", network_name="final", device_num=0):
        super().__init__(config_file_name, network_name, device_num)
