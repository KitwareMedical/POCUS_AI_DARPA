import itk

import numpy as np

import ffmpeg
import av

def ARGUS_shape_video(filename):
    p = ffmpeg.probe(filename, select_streams='v');
    width = p['streams'][0]['width']
    height = p['streams'][0]['height']
    return height, width

def ARGUS_load_video(filename):
    container = None
    try:
        container = av.open(filename)
        stream = container.streams.video[0]
        stream.thread_type = 'AUTO'
        
        num_frames = stream.frames
        
        frames = None
        for i,frame in enumerate(container.decode(stream)):
            if i == 0:
                frames = np.empty((num_frames, frame.height, frame.width))
            frames[i] = frame.to_ndarray(format='gray')
            
        vid = itk.GetImageFromArray(frames.astype(np.float32))
        
        return vid
    finally:
        if container:
            container.close()