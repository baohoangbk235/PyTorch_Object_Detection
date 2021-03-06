import math
import itertools

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.nn.init as init

from torch.autograd import Variable

from multibox_layer import MultiBoxLayer
from fusion import FusionBlock
from norm import L2Norm
from attention import AttentionBlock

class MDSSD300(nn.Module):
	input_size = 300

	def __init__(self):
		super(MDSSD300, self).__init__()
		
		# Attention
		self.attn1 = AttentionBlock(3)

		# model
		self.base = self.VGG16()
		self.norm4 = L2Norm(512, 20) # 38

		self.conv5_1 = nn.Conv2d(512, 512, kernel_size=3, padding=1, dilation=1)
		self.conv5_2 = nn.Conv2d(512, 512, kernel_size=3, padding=1, dilation=1)
		self.conv5_3 = nn.Conv2d(512, 512, kernel_size=3, padding=1, dilation=1)
		self.bn5 = nn.BatchNorm2d(512)
		
		self.conv6 = nn.Conv2d(512, 1024, kernel_size=3, padding=6, dilation=6)
		self.bn6 = nn.BatchNorm2d(1024)

		self.conv7 = nn.Conv2d(1024, 1024, kernel_size=1) 
		self.bn7 = nn.BatchNorm2d(1024)
		# self.attn2 = AttentionBlock(1024)

		self.conv8_1 = nn.Conv2d(1024, 256, kernel_size=1)
		self.conv8_2 = nn.Conv2d(256, 512, kernel_size=3, padding=1, stride=2)
		self.bn8 = nn.BatchNorm2d(512)

		self.conv9_1 = nn.Conv2d(512, 128, kernel_size=1)
		self.conv9_2 = nn.Conv2d(128, 256, kernel_size=3, padding=1, stride=2)
		self.bn9 = nn.BatchNorm2d(256)

		self.conv10_1 = nn.Conv2d(256, 128, kernel_size=1)
		self.conv10_2 = nn.Conv2d(128, 256, kernel_size=3)

		self.conv11_1 = nn.Conv2d(256, 128, kernel_size=1)
		self.conv11_2 = nn.Conv2d(128, 256, kernel_size=3)

		self.Fusion1 = FusionBlock(256,512)
		self.Fusion2 = FusionBlock(512,256)
		self.Fusion3 = FusionBlock(1024,256)

		# multibox layer
		self.multibox = MultiBoxLayer()

	def forward(self, x):
		odd_count = 0
		odd = []
		hs = []
		vgg = []
		fusion_layers = []

		h= self.attn1(x)

		h = self.base[0](h)
		vgg.append(h)
		for i in range(1,len(self.base)):
			h = self.base[i](h)
			vgg.append(h)
		fusion_layers.append(vgg[15])
		odd.append(2)
		odd_count = 3
		fusion_layers.append(h)
		h = F.max_pool2d(h, kernel_size=2, stride=2, ceil_mode=True)

		h = F.relu(self.conv5_1(h))
		h = F.relu(self.conv5_2(h))
		h = F.relu(self.conv5_3(h))
		h = F.max_pool2d(self.bn5(h), kernel_size=3, padding=1, stride=1, ceil_mode=True)
		
		h = F.relu(self.bn6(self.conv6(h)))
		h = F.relu(self.bn7(self.conv7(h)))
		fusion_layers.append(h)
		# h = self.attn2(h)

		h = F.relu(self.conv8_1(h))
		h = F.relu(self.bn8(self.conv8_2(h)))
		hs.append(h)  # conv8_2

		h = F.relu(self.conv9_1(h))
		h = F.relu(self.bn9(self.conv9_2(h)))
		hs.append(h)  # conv9_2

		h = F.relu(self.conv10_1(h))
		h = F.relu(self.conv10_2(h))
		hs.append(h)  # conv10_2

		h = F.relu(self.conv11_1(h))
		h = F.relu(self.conv11_2(h))
		hs.append(h)  # conv11_2

		# Fusion Blocks
		f = self.Fusion1(fusion_layers[0],hs[-4])
		hs.append(f)
		f = self.Fusion2(fusion_layers[1],hs[-4])
		hs.append(f)
		diff_odd = fusion_layers[2].size()[-1] - hs[-4].size()[-1]
		f = self.Fusion3(fusion_layers[2],hs[-4])
		hs.append(f)

		loc_preds, conf_preds = self.multibox(hs)
 
		return loc_preds, conf_preds

	def VGG16(self):
		'''VGG16 layers.'''
		cfg = [64, 64, 'M', 128, 128, 'M', 256, 256, 256, 'M', 512, 512, 512]
		layers = []
		in_channels = 3
		for x in cfg:
			if x == 'M':
				layers += [nn.MaxPool2d(kernel_size=2, stride=2, ceil_mode=True)]
			else:
				layers += [nn.Conv2d(in_channels, x, kernel_size=3, padding=1),
						   nn.ReLU(True)]
				in_channels = x
		return nn.Sequential(*layers)

if __name__ == '__main__':
	t = torch.randn(1, 3, 300, 300)
	net = MDSSD300()
	# print(net)
	res = net.forward(t)
	