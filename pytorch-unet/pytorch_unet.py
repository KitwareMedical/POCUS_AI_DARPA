import torch
from torch.autograd.grad_mode import F
import torch.nn as nn
import unittest
import numpy as np
from unet_components import *

class UNet(nn.Module):
	"""
	This unet is used in Kitware's Darpa Anatomic Reconstruction POCUS-AI project.
	Github Repo: https://github.com/KitwareMedical/AnatomicRecon-POCUS-AI
	Based on model from https://ieeexplore.ieee.org/document/9034149
	We expect 1 channel in the input images: 
	Grayscale US image
	We expect 4 channels in the labels: 
	Background, Pleura, Bone, Lung
	As of now, the unet does not deal with box annotations.
	"""

	def __init__(self, input_size, num_classes, channels_in=1, filter_multiplier=10, regularization_rate=0.):
		"""
		Initialize UNet values which will be used during forward pass.
		"""
		super(UNet, self).__init__()
		self.num_classes = num_classes
		self.filter_multiplier = filter_multiplier
		self.regularization_rate = regularization_rate

		self.num_layers = int(np.floor(np.log2(input_size)))

		self.down_layers = []
		self.up_layers = []

		down_conv_kernel_sizes = np.zeros([self.num_layers], dtype=int)	
		down_filter_numbers = np.zeros([self.num_layers + 1], dtype=int)
		up_conv_kernel_sizes = np.zeros([self.num_layers], dtype=int)
		up_filter_numbers = np.zeros([self.num_layers+1], dtype=int)

		down_filter_numbers[0] = channels_in
		up_filter_numbers[0] = int((self.num_layers) * self.filter_multiplier + self.num_classes)

		# init layer parameters
		for layer_index in range(self.num_layers):
			down_conv_kernel_sizes[layer_index] = int(3)
			down_filter_numbers[layer_index + 1] = int((layer_index + 1) * self.filter_multiplier + self.num_classes)
			up_conv_kernel_sizes[layer_index] = int(4)
			up_filter_numbers[layer_index + 1] = int((self.num_layers - layer_index - 1) * self.filter_multiplier + self.num_classes)
			
		# init layers
		for i in range(self.num_layers):
			#down_layer
			in_size = down_filter_numbers[i]
			out_size = down_filter_numbers[i+1]
			shape = down_conv_kernel_sizes[i]

			layer = UNet_down(in_size, out_size, shape, 'same', 'relu', True)
			self.down_layers.append(layer)

			#up_layer
			in_size = up_filter_numbers[i] + down_filter_numbers[len(down_filter_numbers) - i - 2]
			out_size = up_filter_numbers[i+1]
			shape = up_conv_kernel_sizes[i]

			if (i == self.num_layers - 1):
				layer = UNet_up(in_size, out_size, shape, 'same', 'relu', True)
			else:					
				layer = UNet_up(in_size,out_size, shape, 'same', None, False)
			
			self.up_layers.append(layer)
		
	def forward(self, x):
		"""
		Forward pass of the UNet on a tensor x.
		Depends on 'unet_components.py'
		"""
		skips = []

		for i in range(self.num_layers):
			skips.append(x)
			x = self.down_layers[i](x)

		for i in range(self.num_layers):
			skip_output = skips.pop()
			x = self.up_layers[i](x, skip_output)

		assert len(skips) == 0
		return x
	
	def get_parameters(self):
		"""
		Gets a list of all the parameters in this model.
		For some reason, model.parameters() isn't working
		so I made this method instead.
		"""
		# print(list(self.down_layers[0].parameters()))

		res = []
		for layer in self.down_layers:
			res.extend(list(layer.parameters()))

		for layer in self.up_layers:
			res.extend(list(layer.parameters()))
		
		return res

class UnetUnitTest(unittest.TestCase):
    def test_create_model(self):
        model = UNet(128, 2)

if __name__ == '__main__':
    unittest.main()